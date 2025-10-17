package org.gts3.atlantis.staticanalysis;

import java.io.File;
import java.nio.file.Paths;
import java.util.*;
import java.util.stream.Collectors;

import analysis.data.DFF;
import org.gts3.atlantis.staticanalysis.taint.TaintAnalysisProblem;
import org.gts3.atlantis.staticanalysis.taint.TaintStatus;
import org.gts3.atlantis.staticanalysis.utils.JarUtils;
import org.gts3.atlantis.staticanalysis.utils.SignatureUtils;
import soot.*;
import soot.baf.*;
import soot.jimple.InvokeExpr;
import soot.jimple.InvokeStmt;
import soot.jimple.Stmt;
import soot.jimple.internal.AbstractInstanceInvokeExpr;
import soot.jimple.toolkits.callgraph.CHATransformer;
import soot.jimple.toolkits.callgraph.CallGraph;
import soot.jimple.toolkits.callgraph.Edge;
import soot.jimple.toolkits.ide.JimpleIFDSSolver;
import soot.jimple.toolkits.ide.icfg.JimpleBasedInterproceduralCFG;
import soot.options.Options;
import soot.tagkit.BytecodeOffsetTag;

import boomerang.scene.jimple.BoomerangPretransformer;

import static org.gts3.atlantis.staticanalysis.utils.LogLabel.LOG_ERROR;
import static org.gts3.atlantis.staticanalysis.utils.LogLabel.LOG_WARN;

/**
 * A class that performs static analysis using the Soot framework to build and analyze
 * call graphs for Java applications. This class is responsible for setting up the Soot
 * environment, building call graphs with different levels of precision, and providing
 * methods to analyze and manipulate the call graph.
 *
 * The analysis can be configured with different call graph construction algorithms
 * (CHA or RTA) and different levels of call graph precision.
 *
 * Only one instance of SootAnalysis can be active at a time, as Soot doesn't
 * support multiple analyses in parallel.
 */
public class SootAnalysis implements AutoCloseable {
    /**
     * Tracks the currently active SootAnalysis instance.
     * This ensures that only one instance can be active at a time.
     */
    private static SootAnalysis activeInstance;
    private String cpName;
    private List<String> allClasspaths;
    private Collection<HarnessInfo> harnesses;
    private List<String> rawPkgList;
    private List<String> pkgList;
    private CallGraph cg;
    private ArgumentParser.CGLevel callGraphLevel;
    private boolean callGraphAlgoRta;

    /**
     * Constructs a new SootAnalysis instance and builds a call graph based on the provided parameters.
     * Throws an IllegalStateException if another SootAnalysis instance is already active.
     *
     * @param cpName The name of the classpath
     * @param allClasspaths List of all classpath entries to be analyzed
     * @param harnesses Collection of harness information containing entry points for analysis
     * @param pkgList List of package names to be included in the analysis
     * @param callGraphLevel The level of call graph precision to use (ZERO, ONE, or TWO)
     * @param callGraphAlgoRta Whether to use RTA algorithm instead of CHA for call graph construction
     * @throws IllegalStateException if another SootAnalysis instance is already active
     */
    public SootAnalysis(String cpName, List<String> allClasspaths, Collection<HarnessInfo> harnesses,
            List<String> pkgList, ArgumentParser.CGLevel callGraphLevel, boolean callGraphAlgoRta) {
        if (activeInstance != null) {
            throw new IllegalStateException("Another SootAnalysis instance is already active. Close the existing instance before creating a new one.");
        }
        this.cpName = cpName;
        this.allClasspaths = allClasspaths.stream()
                .filter(path -> new File(path).exists()) // Filter classpath to only contain existing files
                .toList();
        this.harnesses = harnesses;
        this.rawPkgList = pkgList;
        this.callGraphLevel = callGraphLevel;
        this.callGraphAlgoRta = callGraphAlgoRta;
        this.pkgList = pkgList.stream()
                .map(pkg -> pkg + ".*")
                .toList();

        System.out.println("CP Name: " + cpName);
        System.out.println("All Classpaths: " + this.allClasspaths);
        System.out.println("Harness Classes: " + harnesses);
        System.out.println("Package List: " + pkgList);
        if (this.allClasspaths.isEmpty()) {
            System.err.println(LOG_ERROR + "Empty classpath");
            throw new RuntimeException("Cannot run static analysis on empty classpath");
        }

        // A new SootAnalysis assumes that we discard all previous analyses
        System.out.println("Resetting Soot...");
        G.reset();

        long startTime = System.currentTimeMillis();
        this.cg = buildCallgraph();
        long endTime = System.currentTimeMillis();
        System.out.println("Total time taken to execute buildCallgraph: " + ((endTime - startTime) / 1000.0) + " seconds");

        // Register this instance as the active one
        activeInstance = this;
    }

    /**
     * Builds a call graph based on the configuration provided in the constructor.
     * This method sets up the Soot environment, configures the analysis options,
     * loads the necessary classes, and constructs the call graph.
     *
     * @return The constructed call graph
     */
    private CallGraph buildCallgraph() {
        String classpath = String.join(System.getProperty("path.separator"), allClasspaths);

        Options.v().set_keep_line_number(true);
        Options.v().set_keep_offset(true);
        Options.v().set_whole_program(true);
        Options.v().set_soot_classpath(classpath);  // The class path to find classes
        //Options.v().set_no_bodies_for_excluded(true);  // Do not load bodies for "excluded" classes
        Options.v().set_allow_phantom_refs(true);  // Allow unresolved classes
        //Options.v().setPhaseOption("jb", "use-original-names:true");
        Options.v().set_prepend_classpath(true);  // Prepend the soot classpath (set above) to the default class path
        Options.v().set_ignore_classpath_errors(true);  // Ignore classpath errors
        //Options.v().set_exclude(Constants.excludedClassList);
        Options.v().set_include(pkgList);

        if (callGraphAlgoRta) {
            System.out.println("Using RTA (spark) as call graph algorithm instead of CHA");
            Options.v().setPhaseOption("cg.spark", "enabled:true");
            Options.v().setPhaseOption("cg.spark", "verbose:true");

            //Options.v().setPhaseOption("cg.spark", "rta:true");
            //Options.v().setPhaseOption("cg.spark", "vta:true");
            Options.v().setPhaseOption("cg.spark", "on-fly-cg:true");
        }

        Scene.v().setPkgList(pkgList);

        List<String> l = new ArrayList<>();
        for (HarnessInfo harness : harnesses) {
            l.add(harness.getTargetClass());
        }

        for (String jarPath : allClasspaths) {
            for (String className : JarUtils.getClassNames(Paths.get(jarPath))) {
                if (!className.contains(".")) {
                    // Handle default package classes (no package qualifier)
                    l.add(className);
                } else {
                    // Check if class belongs to any of the specified packages
                    for (String pkg : rawPkgList) {
                        if (!pkg.isEmpty() && className.startsWith(pkg)) {
                            l.add(className);
                            break;
                        }
                    }
                }
            }
        }

        Options.v().parse(l.stream().toArray(String[]::new));  // Add the harness classes as main classes

        System.out.println("Options exclude list: " + Options.v().exclude());
        System.out.println("Options include list: " + Options.v().include());
        System.out.println("Scene pkglist: " + Scene.v().getPkgList());

        Scene.v().loadNecessaryClasses();

        printSceneStats();

        // Add all methods from all harnesses as entry points
        for (HarnessInfo harness : harnesses) {
            List<SootMethod> methods = harness.getSootMethods();
            for (SootMethod method : methods) {
                if (method.isConcrete()) {
                    Scene.v().getEntryPoints().add(method);
                    System.out.println("Added entry point: " + method.getDeclaration());
                }
            }
        }

        switch (callGraphLevel) {
            case ZERO:
                System.out.println("Using pruned call graph (Setting all non-app classes as phantom)");
                for (SootClass sootClass : getClassesForPackages(rawPkgList)) {
                    for (SootMethod method : sootClass.getMethods()) {
                        if (!method.isConcrete()) {
                            continue;
                        }
                        if (!method.hasActiveBody()) {
                            method.retrieveActiveBody();
                        }
                    }
                }
                setNonPackageClassesAsPhantom(rawPkgList);
                break;
            case ONE:
                System.out.println("Using pruned call graph (Setting non-app classes as phantom if not directly invoked)");
                List<String> extendedPkgList = getExtendedPackageList(rawPkgList);
                setNonPackageClassesAsPhantom(extendedPkgList);
                break;
            case TWO:
                System.out.println("Using full call graph (not setting any classes as phantom)");
        }

        printSceneStats();

        if (callGraphLevel != ArgumentParser.CGLevel.ZERO) {
            int totalClasses = Scene.v().getClasses().size();
            if (totalClasses > 50000) {
                System.err.println(LOG_WARN + "Number of classes (" + totalClasses +
                        ") exceeds 50,000 in full cg mode. This will lead to long analysis time which is meaningless in our usage scenario. Just exit to save resources.");
                System.exit(1);
            }
        }

        CHATransformer.v().transform();

        //PackManager.v().runPacks();
        PackManager.v().getPack("cg").apply();

        return Scene.v().getCallGraph();
    }

    public void runTaintAnalysis(List<FuzzTargetData> fuzzTargets) {
        try {
            Transform transform = new Transform("wjtp.ifds", createAnalysisTransformer(fuzzTargets));
            PackManager.v().getPack("wjtp").remove("wjtp.ifds");
            PackManager.v().getPack("wjtp").add(transform);

            // Must have for Boomerang
            BoomerangPretransformer.v().reset();
            BoomerangPretransformer.v().apply();
            PackManager.v().getPack("wjtp").apply();
        } catch (Exception e) {
            System.err.println(LOG_ERROR + "Failed to run taint analysis: " + e.getMessage());
            e.printStackTrace();
        }
    }

    protected Transformer createAnalysisTransformer(List<FuzzTargetData> fuzzTargets) {
        List<SootMethodRef> sources = new ArrayList<>();
        List<SootMethod> entryPoints = this.harnesses.stream().map(h -> h.getSootMethods()).flatMap(List::stream).collect(Collectors.toList());

        return new SceneTransformer() {
            @Override
            protected void internalTransform(String phaseName, Map<String, String> options) {
                JimpleBasedInterproceduralCFG icfg = new JimpleBasedInterproceduralCFG(true, true);
                TaintAnalysisProblem problem = new TaintAnalysisProblem(icfg, sources, entryPoints);
                @SuppressWarnings({"rawtypes", "unchecked"})
                JimpleIFDSSolver<?, ?> solver = new JimpleIFDSSolver<>(problem);
                solver.solve();
                System.out.println("Solver finished");

                for (FuzzTargetData fuzzTargetData : fuzzTargets) {
                    TargetLocation targetLocation = fuzzTargetData.getTargetLocation();
                    if (targetLocation.hasSrcUnit()) {
                        try {
                            Map<?, ?> res = solver.resultsAt(targetLocation.getSrcUnit());

                            if (res == null || res.size() == 0) {
                                fuzzTargetData.setTaintStatus(TaintStatus.NOT_TAINTED);
                                continue;
                            }

                            Unit srcUnit = targetLocation.getSrcUnit();
                            if (srcUnit instanceof InvokeStmt) {
                                InvokeStmt invokeStmt = (InvokeStmt) srcUnit;
                                InvokeExpr invokeExpr = invokeStmt.getInvokeExpr();
                                List<Value> args = invokeExpr.getArgs();

                                if (args.isEmpty()) {
                                    continue;
                                }

                                if (args.stream().anyMatch(arg -> res.keySet().contains(DFF.asDFF(arg)))) {
                                    fuzzTargetData.setTaintStatus(TaintStatus.TAINTED);
                                } else if (invokeExpr instanceof AbstractInstanceInvokeExpr) {
                                    AbstractInstanceInvokeExpr abstractInstanceInvokeExpr = (AbstractInstanceInvokeExpr) invokeExpr;
                                    if (res.keySet().contains(DFF.asDFF(abstractInstanceInvokeExpr.getBase()))) {
                                        fuzzTargetData.setTaintStatus(TaintStatus.TAINTED);
                                    }
                                } else {
                                    fuzzTargetData.setTaintStatus(TaintStatus.NOT_TAINTED);
                                }
                            }
                        } catch (Exception e) {
                            System.err.println(LOG_ERROR + "Failed to taint target (" + fuzzTargetData + "): " + e.getMessage());
                            e.printStackTrace();
                        }
                    }
                }
            }
        };
    }

    /**
     * Prints stats about classes loaded in the scene.
     */
    public void printSceneStats() {
        System.out.println("Current number of application classes: " + Scene.v().getApplicationClasses().size() +
                           ", library classes: " + Scene.v().getLibraryClasses().size() +
                           ", and total number of classes in scene: " + Scene.v().getClasses().size());
    }

    /**
     * Returns the call graph that was built during initialization.
     *
     * @return The call graph object
     */
    public CallGraph getCallGraph() {
        return cg;
    }

    /**
     * Prints all edges in the call graph where either the source or target method
     * is within the scope of the analysis.
     */
    public void printCallGraphEdges() {
        // Print all edges in the call graph
        for (Edge e : cg) {
            SootMethod source = e.src();
            SootMethod target = e.tgt();

            if (isInScope(source) || isInScope(target)) {
                System.out.println("Found edge: " + source.toString() + " -> " + target.toString());
            }
        }
        System.out.println("cg.size = " + cg.size());
    }

    /**
     * Prints the bytecode offsets for all methods in the harness classes.
     */
    public void printBytecodeOffsetsHarnessClasses() {
        for (HarnessInfo harness : harnesses) {
            String className = harness.getTargetClass();
            System.out.println("Loading class " + className);

            SootClass s = Scene.v().loadClass(className, SootClass.BODIES);
            printClassBytecodeOffsets(s);
        }
    }

    /**
     * Prints the bytecode offsets for all methods in the specified Soot class.
     * For each unit (statement) in the method body, it prints the bytecode offset
     * and the unit itself.
     *
     * @param s The Soot class to print bytecode offsets for
     */
    public void printClassBytecodeOffsets(SootClass s) {
        System.out.println("Got class " + s.getFilePath());
        for (SootMethod method : s.getMethods()) {
            System.out.println(method.getDeclaration());

            Body body = method.retrieveActiveBody();

            // print the Jimple units
            PatchingChain<Unit> u = body.getUnits();
            for (Unit unit : u) {
                BytecodeOffsetTag bci = (BytecodeOffsetTag) unit.getTag("BytecodeOffsetTag");
                int bytecodeOffset = bci != null ? bci.getBytecodeOffset() : -1;

                System.out.println("\t" + bytecodeOffset + ": " + unit);
            }
        }
    }

    /**
     * Determines if a method is within the scope of the analysis.
     * A method is in scope if its declaring class is included in the analysis.
     *
     * @param sootMethod The method to check
     * @return true if the method is in scope, false otherwise
     */
    private boolean isInScope(SootMethod sootMethod) {
        if (sootMethod == null) {
            return false;
        }
        return Scene.v().isIncluded(sootMethod.getDeclaringClass());
    }

    /**
     * Sets classes not in the pkgList (target project) as phantom.
     * This sacrifices accuracy to ensure reasonable analysis time by excluding
     * classes that are not part of the target packages from detailed analysis.
     *
     * @param pkgList List of package names to be included in the analysis
     */
    private void setNonPackageClassesAsPhantom(List<String> pkgList) {
        int phantomCount = 0;

        for (SootClass sc : Scene.v().getClasses()) {
            try {
                String className = sc.getName();
                className = className.replace('/', '.');

                boolean inPackageList = false;

                if (!className.contains(".")) {
                    // Include classes in the default package (no package qualifier)
                    System.out.println("Found class in default package: " + className);
                    inPackageList = true;
                } else {
                    for (String pkg : pkgList) {
                        if (!pkg.isEmpty() && className.startsWith(pkg)) {
                            inPackageList = true;
                            break;
                        }
                    }
                }

                if (!inPackageList) {
                    sc.setPhantomClass();

                    for (SootMethod sm : sc.getMethods()) {
                        sm.setPhantom(true);
                    }

                    phantomCount++;
                }
            } catch (Exception e) {
                System.out.println(LOG_ERROR + "Error setting class as phantom: " + e.getMessage());
            }
        }

        System.out.println("Total classes marked as phantom: " + phantomCount);
    }

    /**
     * Returns a list of Soot classes that belong to the specified packages.
     * This includes classes in the default package (no package qualifier)
     * and classes that start with any of the package prefixes in the list.
     *
     * @param packageList List of package names to filter classes by
     * @return List of Soot classes that belong to the specified packages
     */
    List<SootClass> getClassesForPackages(List<String> packageList) {
        List<SootClass> classes = new ArrayList<>();
        for (SootClass sc : Scene.v().getClasses()) {
            String className = sc.getName();
            if (!className.contains(".")) {
                // Handle default package classes (no package qualifier)
                classes.add(sc);
                System.out.println("Added default package class to process: " + className);
            } else {
                // Check if class belongs to any of the specified packages
                for (String pkg : packageList) {
                    if (!pkg.isEmpty() && className.startsWith(pkg)) {
                        classes.add(sc);
                        break;
                    }
                }
            }
        }
        return classes;
    }

    /**
     * Extends the package list to include classes that are directly invoked by
     * classes in the original package list. This heuristic helps to cover more
     * classes that are not in the original package list but are meaningful in
     * call graph construction.
     *
     * @param packageList The original list of package names
     * @return An extended list of package names that includes directly invoked classes
     */
    private List<String> getExtendedPackageList(List<String> packageList) {
        Set<String> extendedSet = new HashSet<>(packageList);

        // First, get all the classes in the specified packages
        List<SootClass> classesToProcess = getClassesForPackages(packageList);
        Set<String> processedClasses = new TreeSet<>(classesToProcess.stream().map(c -> c.getName()).toList());

        System.out.println("Found " + classesToProcess.size() + " classes in the specified packages");

        // For each class in our packages, analyze its methods to find direct invocations
        for (SootClass sc : classesToProcess) {
            try {
                for (SootMethod method : sc.getMethods()) {
                    if (!method.isConcrete()) continue;

                    try {
                        // Get method body
                        if (!method.hasActiveBody()) {
                            method.retrieveActiveBody();
                        }

                        Body body = method.getActiveBody();
                        PatchingChain<Unit> units = body.getUnits();

                        for (Unit unit : units) {
                            if (unit instanceof Stmt) {
                                Stmt stmt = (Stmt) unit;

                                if (stmt.containsInvokeExpr()) {
                                    InvokeExpr invoke = stmt.getInvokeExpr();
                                    SootMethod invokedMethod = invoke.getMethod();
                                    String invokedClass = invokedMethod.getDeclaringClass().getName();

                                    // Add the class of the invoked method to our extended list
                                    if (!processedClasses.contains(invokedClass)) {
                                        String pkg = getPackagePrefix(invokedClass);
                                        if (pkg != null) {
                                            extendedSet.add(pkg);
                                            System.out.println("Adding invoked class to extended list: " + invokedClass);
                                        }
                                        processedClasses.add(invokedClass);
                                    }
                                }
                            }
                        }
                    } catch (Exception e) {
                        System.out.println(LOG_WARN + "Error analyzing method " + method.getSignature() + ": " + e.getMessage());
                    }
                }
            } catch (Exception e) {
                System.out.println(LOG_WARN + "Error analyzing class " + sc.getName() + ": " + e.getMessage());
            }
        }

        List<String> extendedList = new ArrayList<>(extendedSet);
        System.out.println("Extended package/class list: " + extendedList);
        System.out.println("Original list size: " + packageList.size() +
                           ", Extended list size: " + extendedList.size());

        return extendedList;
    }

    /**
     * Extracts the package prefix from a fully qualified class name.
     * Returns the most significant package part to avoid being too specific.
     * For classes in the default package (no dots), returns the class name
     * to ensure these classes are preserved.
     *
     * @param className The fully qualified class name
     * @return The package prefix or the class name for default package classes
     */
    private String getPackagePrefix(String className) {
        int lastDot = className.lastIndexOf('.');
        if (lastDot > 0) {
            String packageName = className.substring(0, lastDot);

            // TODO: @fabian, I'm not sure if this always works, pls check this after round 1
            // If the package is very nested, extract the first two levels
            // to avoid being too specific
            String[] parts = packageName.split("\\.");
            if (parts.length > 2) {
                return parts[0] + "." + parts[1];
            }
            return packageName;
        }

        // No package (default package class), preserve it by returning its name
        // This ensures default package classes are kept in the extended list
        System.out.println("Found invoked class in default package: " + className);
        return className;
    }

    /**
     * Merges a CallGraphJson into the current Soot CallGraph.
     * This method takes nodes and edges from the provided CallGraphJson
     * and adds them to the current Soot CallGraph if they don't already exist.
     *
     * @param callGraphJson The CallGraphJson to merge from
     */
    public void mergeCallGraph(CallGraphJson callGraphJson) {
        System.out.println("Merging call graph from external source");

        if (callGraphJson == null) {
            System.out.println("Cannot merge null call graph");
            return;
        }

        // Create a map to store the mapping between CallGraphNode and SootMethod
        Map<CallGraphNode, SootMethod> nodeToMethodMap = processNodes(callGraphJson);
        int edgesAdded = processEdges(callGraphJson, nodeToMethodMap);

        System.out.println("Merged call graph: Checked " + nodeToMethodMap.size() + " nodes and added " + edgesAdded + " edges");
    }

    /**
     * Processes nodes from the external call graph and creates a mapping to SootMethods.
     *
     * @param callGraphJson The CallGraphJson containing the nodes to process
     * @return A map from CallGraphNode to SootMethod
     */
    private Map<CallGraphNode, SootMethod> processNodes(CallGraphJson callGraphJson) {
        Map<CallGraphNode, SootMethod> nodeToMethodMap = new HashMap<>();

        // Process all nodes from the external call graph
        for (CallGraphNode node : callGraphJson.getAllNodes()) {
            try {
                SootMethod sootMethod = findCorrespondingSootMethod(node);
                if (sootMethod != null) {
                    // Store the mapping
                    nodeToMethodMap.put(node, sootMethod);
                }
            } catch (Exception e) {
                System.out.println(LOG_ERROR + "Error processing node: " + e.getMessage());
            }
        }

        return nodeToMethodMap;
    }

    /**
     * Finds the corresponding SootMethod for a given CallGraphNode.
     *
     * @param node The CallGraphNode to find a SootMethod for
     * @return The corresponding SootMethod, or null if not found
     */
    private SootMethod findCorrespondingSootMethod(CallGraphNode node) {
        // Try to find the corresponding SootClass and SootMethod
        String className = node.getClassName();
        String methodName = node.getFuncName();

        if (className.isEmpty() || methodName.isEmpty()) {
            System.out.println(LOG_WARN + "Skipping node with empty class or method name: " + node);
            return null;
        }

        // Check if the class exists in the scene
        if (!Scene.v().containsClass(className)) {
            System.out.println(LOG_WARN + "Class not found in scene: " + className);
            return null;
        }

        SootClass sootClass = Scene.v().getSootClass(className);
        return findMethodInClass(sootClass, methodName, node.getMethodDesc(), node.getFuncSig());
    }

    /**
     * Finds a method in a SootClass by name and optionally by descriptor.
     *
     * @param sootClass  The SootClass to search in
     * @param methodName The name of the method to find
     * @param methodDesc The method descriptor (optional)
     * @param funcSig    The method signature (optional)
     * @return The found SootMethod, or null if not found
     */
    private SootMethod findMethodInClass(SootClass sootClass, String methodName, String methodDesc, String funcSig) {
        // Find the method in the class
        for (SootMethod method : sootClass.getMethods()) {
            if (method.getName().equals(methodName)) {
                // If we have a method descriptor, check it matches
                if (!methodDesc.isEmpty()) {
                    String methodDescSig = methodDesc;
                    if (methodDescSig.contains("^")) {
                        methodDescSig = methodDescSig.substring(0, methodDescSig.indexOf('^'));
                    }
                    if (SignatureUtils.bytecodeSignature(method).equals(methodDescSig)) {
                        return method;
                    }
                }
                // Check if func_sig matches
                if (!funcSig.isEmpty()) {
                    String funcSigWithMethodName = funcSig.replaceFirst("\\(", " " + methodName + "(");
                    if (funcSigWithMethodName.equals(method.getSubSignature())) {
                        return method;
                    }
                }
            }
        }

        System.out.println(LOG_WARN + "Method not found in class: " + sootClass.getName() + "." + methodName);
        return null;
    }

    /**
     * Processes edges from the external call graph and adds them to the current call graph.
     *
     * @param callGraphJson The CallGraphJson containing the edges to process
     * @param nodeToMethodMap The mapping from CallGraphNode to SootMethod
     * @return The number of edges added to the call graph
     */
    private int processEdges(CallGraphJson callGraphJson, Map<CallGraphNode, SootMethod> nodeToMethodMap) {
        int edgesAdded = 0;

        // Process all edges from the external call graph
        for (CallGraphEdge edge : callGraphJson.getAllEdges()) {
            try {
                if (addEdgeToCallGraph(callGraphJson, edge, nodeToMethodMap)) {
                    edgesAdded++;
                }
            } catch (Exception e) {
                System.out.println(LOG_ERROR + "Error processing edge: " + e.getMessage());
            }
        }

        return edgesAdded;
    }

    /**
     * Adds an edge from the external call graph to the current call graph.
     *
     * @param callGraphJson The CallGraphJson containing the edge
     * @param edge The CallGraphEdge to add
     * @param nodeToMethodMap The mapping from CallGraphNode to SootMethod
     * @return true if the edge was added, false otherwise
     */
    private boolean addEdgeToCallGraph(CallGraphJson callGraphJson, CallGraphEdge edge,
                                      Map<CallGraphNode, SootMethod> nodeToMethodMap) {
        // Get the source and target nodes
        Optional<CallGraphNode> sourceNodeOpt = callGraphJson.getNodeById(edge.getSourceId());
        Optional<CallGraphNode> targetNodeOpt = callGraphJson.getNodeById(edge.getTargetId());

        if (!sourceNodeOpt.isPresent() || !targetNodeOpt.isPresent()) {
            System.out.println(LOG_WARN + "Skipping edge with missing source or target node: " + edge);
            return false;
        }

        CallGraphNode sourceNode = sourceNodeOpt.get();
        CallGraphNode targetNode = targetNodeOpt.get();

        // Get the corresponding SootMethods
        SootMethod srcMethod = nodeToMethodMap.get(sourceNode);
        SootMethod tgtMethod = nodeToMethodMap.get(targetNode);

        if (srcMethod == null || tgtMethod == null) {
            System.out.println(LOG_WARN + "Skipping edge with missing source or target method: " + edge);
            return false;
        }

        // Check if the edge already exists in the call graph
        if (edgeExistsInCallGraph(srcMethod, tgtMethod)) {
            return false;
        }

        // Find the call statement in the source method that calls the target method
        Unit callUnit = findCallStatement(srcMethod, tgtMethod);

        if (callUnit == null) {
            return false;
        }

        // Ensure classes and methods are not phantom
        if (srcMethod.isPhantom()) {
            srcMethod.getDeclaringClass().setApplicationClass();
            srcMethod.setPhantom(false);
        }
        if (tgtMethod.isPhantom()) {
            tgtMethod.getDeclaringClass().setApplicationClass();
            tgtMethod.setPhantom(false);
        }

        // Create a new edge in the call graph
        Edge newEdge = null;
        if (callUnit instanceof Inst) {
            newEdge = new Edge(srcMethod, (Inst) callUnit, tgtMethod, null);
        } else if (callUnit instanceof Stmt) {
            newEdge = new Edge(srcMethod, (Stmt) callUnit, tgtMethod);
        }

        if (newEdge == null) {
            return false;
        }

        cg.addEdge(newEdge);
        return true;
    }

    /**
     * Finds the statement in the source method that calls the target method.
     * This method searches through all statements in the source method to find
     * invoke expressions that match the target method.
     *
     * @param srcMethod The source method containing the call
     * @param tgtMethod The target method being called
     * @return The statement containing the call, or null if not found
     */
    private Unit findCallStatement(SootMethod srcMethod, SootMethod tgtMethod) {
        try {
            // Ensure the source method has an active body
            if (!srcMethod.hasActiveBody()) {
                try {
                    srcMethod.retrieveActiveBody();
                } catch (Exception e) {
                    System.out.println(LOG_WARN + "Could not retrieve active body for method: " + srcMethod.getSignature());
                    return null;
                }
            }

            Body body = srcMethod.getActiveBody();

            // Iterate through all units (instructions) in the method body
            for (Unit unit : body.getUnits()) {
                if (unit instanceof Inst) {
                    Inst inst = (Inst) unit;

                    if (inst.containsInvokeExpr()) {
                        SootMethodRef callee = null;
                        if (inst instanceof DynamicInvokeInst) {
                            DynamicInvokeInst dynamicInvokeInst = (DynamicInvokeInst) inst;
                            callee = dynamicInvokeInst.getMethodRef();
                        } else if (inst instanceof InterfaceInvokeInst) {
                            InterfaceInvokeInst interfaceInvokeInst = (InterfaceInvokeInst) inst;
                            callee = interfaceInvokeInst.getMethodRef();
                        } else if (inst instanceof SpecialInvokeInst) {
                            SpecialInvokeInst specialInvokeInst = (SpecialInvokeInst) inst;
                            callee = specialInvokeInst.getMethodRef();
                        } else if (inst instanceof StaticInvokeInst) {
                            StaticInvokeInst staticInvokeInst = (StaticInvokeInst) inst;
                            callee = staticInvokeInst.getMethodRef();
                        } else if (inst instanceof VirtualInvokeInst) {
                            VirtualInvokeInst virtualInvokeInst = (VirtualInvokeInst) inst;
                            callee = virtualInvokeInst.getMethodRef();
                        } else {
                            System.out.println(LOG_ERROR + "Missing an invoke instruction of unknown type");
                        }

                        if (callee == null) {
                            continue;
                        }
                        // Now, try to match the callee with the source and target method
                        if (callee.resolve().equals(tgtMethod)) {
                            return inst;
                        }

                        // If method name and signature match, it likely is an interface call
                        if (callee.getSubSignature().getString().equals(tgtMethod.getSubSignature())) {
                            return inst;
                        }
                    }

                }

                if (unit instanceof Stmt) {
                    Stmt stmt = (Stmt) unit;

                    if (stmt.containsInvokeExpr()) {
                        InvokeExpr invokeExpr = stmt.getInvokeExpr();
                        SootMethodRef callee = invokeExpr.getMethodRef();
                        if (callee.resolve().equals(tgtMethod)) {
                            return stmt;
                        }
                        if (callee.getSubSignature().getString().equals(tgtMethod.getSubSignature())) {
                            return stmt;
                        }
                    }
                }
            }

            // If we reach here, no matching statement was found
            System.out.println("No call statement found from " + srcMethod.getSignature() +
                               " to " + tgtMethod.getSignature());
        } catch (Exception e) {
            System.out.println(LOG_ERROR + "Error finding call statement: " + e.getMessage());
        }

        return null;
    }

    /**
     * Checks if an edge already exists in the call graph.
     *
     * @param srcMethod The source method of the edge
     * @param tgtMethod The target method of the edge
     * @return true if the edge exists, false otherwise
     */
    private boolean edgeExistsInCallGraph(SootMethod srcMethod, SootMethod tgtMethod) {
        for (Iterator<Edge> it = cg.edgesOutOf(srcMethod); it.hasNext(); ) {
            Edge existingEdge = it.next();
            if (existingEdge.tgt().equals(tgtMethod)) {
                return true;
            }
        }
        return false;
    }

    /**
     * Converts the current Soot CallGraph to a CallGraphJson.
     * This method iterates through all edges in the Soot CallGraph and creates
     * corresponding nodes and edges in the CallGraphJson.
     *
     * @return The converted CallGraphJson
     */
    public CallGraphJson convertToCallGraphJson() {
        System.out.println("Converting call graph to JSON format");
        CallGraphJson callGraphJson = new CallGraphJson(true); // Create a directed call graph

        // Iterate through all edges in the call graph
        for (Iterator<Edge> it = cg.iterator(); it.hasNext(); ) {
            Edge edge = it.next();
            SootMethod srcMethod = edge.src();
            SootMethod tgtMethod = edge.tgt();

            // Only include edges where either the source or target method is in scope
            if (isInScope(srcMethod) || isInScope(tgtMethod)) {
                // Create nodes for source and target methods using the new constructor
                CallGraphNode srcNode = new CallGraphNode(srcMethod);
                CallGraphNode tgtNode = new CallGraphNode(tgtMethod);

                // Add edge between the nodes
                // Use the edge kind as the call type and "CALL" as the edge type
                callGraphJson.addEdge(srcNode, tgtNode, "direct", "strong");
            }
        }

        System.out.println("Converted " + callGraphJson.getNodeCount() + " nodes and " +
                           callGraphJson.getEdgeCount() + " edges to JSON format");

        return callGraphJson;
    }

    /**
     * Closes this SootAnalysis instance and releases it as the active instance.
     * This method should be called when the instance is no longer needed.
     */
    @Override
    public void close() {
        if (this == activeInstance) {
            activeInstance = null;
            System.out.println("SootAnalysis instance closed and released");
        }
    }

    /**
     * Checks if there is an active SootAnalysis instance.
     *
     * @return true if there is an active instance, false otherwise
     */
    public static boolean hasActiveInstance() {
        return activeInstance != null;
    }

    /**
     * Gets the currently active SootAnalysis instance.
     *
     * @return the active SootAnalysis instance, or null if none is active
     */
    public static SootAnalysis getActiveInstance() {
        return activeInstance;
    }
}
