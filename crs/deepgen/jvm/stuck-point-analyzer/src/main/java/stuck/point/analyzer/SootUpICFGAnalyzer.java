package stuck.point.analyzer;

import sootup.callgraph.CallGraph;
import sootup.callgraph.CallGraphAlgorithm;
import sootup.callgraph.ClassHierarchyAnalysisAlgorithm;
import sootup.core.inputlocation.AnalysisInputLocation;
import sootup.core.model.SootClass;
import sootup.core.model.SootMethod;
import sootup.java.core.JavaSootClass;
import sootup.core.signatures.MethodSignature;
import sootup.core.types.ClassType;
import sootup.core.views.View;
import sootup.java.bytecode.frontend.inputlocation.JavaClassPathAnalysisInputLocation;
import sootup.java.core.views.JavaView;

import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.List;
import java.util.Optional;
import java.util.Set;
import java.util.HashSet;
import java.util.Map;
import java.util.HashMap;
import java.util.Queue;
import java.util.LinkedList;

import sootup.core.graph.StmtGraph;
import sootup.core.jimple.common.stmt.Stmt;
import sootup.core.model.Body;
import sootup.core.jimple.basic.StmtPositionInfo;
import sootup.analysis.interprocedural.icfg.JimpleBasedInterproceduralCFG;
import sootup.core.model.Position;

/**
 * SootUp-based static analyzer for generating ICFG and analyzing reachability.
 * Based on the CallgraphExample from crs/deepgen/jvm/sootup-examples/CallgraphExample
 */
public class SootUpICFGAnalyzer {
    
    private final boolean verbose;
    private JavaView view;
    private CallGraph callGraph;
    private JimpleBasedInterproceduralCFG icfg;
    private Map<String, Map<Integer, CoverageLineInfo>> coverageData; // classFqn -> lineNumber -> CoverageLineInfo
    
    public SootUpICFGAnalyzer(boolean verbose) {
        this.verbose = verbose;
        this.coverageData = new HashMap<>();
    }
    
    /**
     * Set coverage data for scoring calculations.
     * This must be called before calculateStuckPointScore().
     */
    public void setCoverageData(List<CoverageLineInfo> allCoverageLines) {
        coverageData.clear();
        for (CoverageLineInfo lineInfo : allCoverageLines) {
            coverageData.computeIfAbsent(lineInfo.getClassFqn(), k -> new HashMap<>())
                       .put(lineInfo.getLineNumber(), lineInfo);
        }
        if (verbose) {
            System.out.printf("Loaded coverage data for %d classes%n", coverageData.size());
        }
    }
    
    /**
     * Initialize SootUp analysis with the given JAR files and entry point.
     * 
     * @param jarFiles Array of paths to JAR files or class directories
     * @param entryPointSignature Entry point method signature
     * @throws Exception if initialization fails
     */
    public void initialize(String[] jarFiles, String entryPointSignature) throws Exception {
        if (verbose) {
            System.out.println("Initializing SootUp ICFG analysis...");
        }
        
        // Create analysis input locations
        List<AnalysisInputLocation> inputLocations = new ArrayList<>();
        
        // Add all provided JAR files/directories
        for (String jarFile : jarFiles) {
            if (verbose) {
                System.out.printf("Adding input location: %s%n", jarFile);
            }
            inputLocations.add(new JavaClassPathAnalysisInputLocation(jarFile));
        }
        
        // Add Java runtime library (handle both Java 8 and 11+ layouts)
        String javaHome = System.getProperty("java.home");
        String rtJarPath = javaHome + "/lib/rt.jar";
        
        // Check if rt.jar exists (Java 8 and earlier)
        java.io.File rtJarFile = new java.io.File(rtJarPath);
        if (rtJarFile.exists()) {
            inputLocations.add(new JavaClassPathAnalysisInputLocation(rtJarPath));
            if (verbose) {
                System.out.printf("Added Java runtime (rt.jar): %s%n", rtJarPath);
            }
        } else {
            // Java 9+ uses modules, try jrt filesystem
            if (verbose) {
                System.out.println("Java 11+ detected, skipping rt.jar (using module system)");
            }
        }
        
        // Create JavaView
        this.view = new JavaView(inputLocations);
        
        // Parse and validate entry point
        MethodSignature entryMethod = parseEntryPointSignature(entryPointSignature);
        
        if (verbose) {
            System.out.printf("Entry point method: %s%n", entryMethod);
        }
        
        // Create call graph using Class Hierarchy Analysis
        CallGraphAlgorithm cha = new ClassHierarchyAnalysisAlgorithm(view);
        this.callGraph = cha.initialize(Collections.singletonList(entryMethod));
        
        // Initialize ICFG
        this.icfg = new JimpleBasedInterproceduralCFG(
            view,
            Collections.singletonList(entryMethod),
            false,  // enableExceptions
            false   // includeReflectiveCalls
        );
        
        if (verbose) {
            System.out.println("ICFG analysis initialized successfully");
        }
    }
    
    /**
     * Parse entry point signature from string format.
     * Expected format: "com.example.ClassName.methodName(param1,param2,...)"
     * or "com.example.ClassName.methodName" for no-parameter methods
     */
    private MethodSignature parseEntryPointSignature(String signature) throws Exception {
        // Simple parsing - can be enhanced later
        // For now, assume format: "className.methodName"
        int lastDot = signature.lastIndexOf('.');
        if (lastDot == -1) {
            throw new IllegalArgumentException("Invalid entry point format. Expected: com.example.Class.method");
        }
        
        String className = signature.substring(0, lastDot);
        String methodName = signature.substring(lastDot + 1);
        
        // Remove parameters if present (simple case)
        if (methodName.contains("(")) {
            methodName = methodName.substring(0, methodName.indexOf('('));
        }
        
        ClassType classType = view.getIdentifierFactory().getClassType(className);
        
        // For now, create a simple method signature - this can be enhanced
        // to properly parse parameter types
        return view.getIdentifierFactory()
                   .getMethodSignature(classType, methodName, "void", Collections.emptyList());
    }
    
    /**
     * Calculate reachability score for a given line coordinate.
     * Returns the number of reachable but not covered lines.
     */
    public int calculateStuckPointScore(CoverageLineInfo lineInfo) {
        if (icfg == null) {
            throw new IllegalStateException("ICFG not initialized. Call initialize() first.");
        }
        
        if (verbose) {
            System.out.printf("Calculating stuck point score for %s:%d%n", 
                lineInfo.getClassFqn(), lineInfo.getLineNumber());
        }
        
        // Find statements that correspond to the given line
        Set<Stmt> targetStatements = findStatementsAtLine(lineInfo.getClassFqn(), lineInfo.getLineNumber());
        
        if (targetStatements.isEmpty()) {
            if (verbose) {
                System.out.printf("No statements found at line %d in class %s%n", 
                    lineInfo.getLineNumber(), lineInfo.getClassFqn());
            }
            return 0;
        }
        
        if (verbose) {
            System.out.printf("Found %d statements at line %d%n", targetStatements.size(), lineInfo.getLineNumber());
        }
        
        // Find all reachable statements from the target statements
        Set<Stmt> reachableStatements = findReachableStatements(targetStatements);
        
        if (verbose) {
            System.out.printf("Found %d reachable statements%n", reachableStatements.size());
        }
        
        // Filter out statements that are already covered
        int uncoveredCount = 0;
        for (Stmt stmt : reachableStatements) {
            if (!isStatementCovered(stmt)) {
                uncoveredCount++;
            }
        }
        
        if (verbose) {
            System.out.printf("Stuck point score: %d uncovered reachable statements%n", uncoveredCount);
        }
        
        return uncoveredCount;
    }
    
    /**
     * Find all statements that correspond to a given line number in a class.
     */
    private Set<Stmt> findStatementsAtLine(String classFqn, int lineNumber) {
        Set<Stmt> statements = new HashSet<>();
        
        try {
            ClassType classType = view.getIdentifierFactory().getClassType(classFqn);
            Optional<JavaSootClass> classOpt = view.getClass(classType);
            
            if (!classOpt.isPresent()) {
                if (verbose) {
                    System.out.printf("Class not found: %s%n", classFqn);
                }
                return statements;
            }
            
            JavaSootClass sootClass = classOpt.get();
            
            // Iterate through all methods in the class
            for (SootMethod method : sootClass.getMethods()) {
                if (!method.hasBody()) {
                    continue;
                }
                
                Body body = method.getBody();
                for (Stmt stmt : body.getStmts()) {
                    if (isStatementAtLine(stmt, lineNumber)) {
                        statements.add(stmt);
                    }
                }
            }
        } catch (Exception e) {
            if (verbose) {
                System.out.printf("Error finding statements at line %d in class %s: %s%n", 
                    lineNumber, classFqn, e.getMessage());
            }
        }
        
        return statements;
    }
    
    /**
     * Check if a statement is at the given line number.
     */
    private boolean isStatementAtLine(Stmt stmt, int lineNumber) {
        StmtPositionInfo posInfo = stmt.getPositionInfo();
        Position pos = posInfo.getStmtPosition();
        
        if (pos.getFirstLine() > 0) {
            // Check if the line number falls within the statement's line range
            return lineNumber >= pos.getFirstLine() && lineNumber <= pos.getLastLine();
        }
        
        return false;
    }
    
    /**
     * Find all statements reachable from the given set of starting statements.
     */
    private Set<Stmt> findReachableStatements(Set<Stmt> startStatements) {
        Set<Stmt> reachable = new HashSet<>();
        Queue<Stmt> worklist = new LinkedList<>();
        Set<Stmt> visited = new HashSet<>();
        
        // Initialize worklist with starting statements
        for (Stmt stmt : startStatements) {
            worklist.add(stmt);
            visited.add(stmt);
            reachable.add(stmt);
        }
        
        // BFS traversal of ICFG
        while (!worklist.isEmpty()) {
            Stmt currentStmt = worklist.poll();
            
            // Add successors within the same method
            List<Stmt> successors = icfg.getSuccsOf(currentStmt);
            for (Stmt successor : successors) {
                if (!visited.contains(successor)) {
                    visited.add(successor);
                    worklist.add(successor);
                    reachable.add(successor);
                }
            }
            
            // Handle interprocedural calls - add entry points of called methods
            if (icfg.isCallStmt(currentStmt)) {
                Collection<SootMethod> callees = icfg.getCalleesOfCallAt(currentStmt);
                for (SootMethod callee : callees) {
                    if (callee.hasBody()) {
                        Collection<Stmt> calleeStartPoints = icfg.getStartPointsOf(callee);
                        for (Stmt startPoint : calleeStartPoints) {
                            if (!visited.contains(startPoint)) {
                                visited.add(startPoint);
                                worklist.add(startPoint);
                                reachable.add(startPoint);
                            }
                        }
                    }
                }
            }
        }
        
        return reachable;
    }
    
    /**
     * Check if a statement is covered by analyzing its line number against coverage data.
     */
    private boolean isStatementCovered(Stmt stmt) {
        SootMethod method = icfg.getMethodOf(stmt);
        if (method == null) {
            return false;
        }
        
        String classFqn = method.getSignature().getDeclClassType().getFullyQualifiedName();
        
        StmtPositionInfo posInfo = stmt.getPositionInfo();
        Position pos = posInfo.getStmtPosition();
        
        if (pos.getFirstLine() > 0) {
            // Check coverage for all lines this statement spans
            for (int line = pos.getFirstLine(); line <= pos.getLastLine(); line++) {
                CoverageLineInfo coverageInfo = getCoverageForLine(classFqn, line);
                if (coverageInfo != null && coverageInfo.isFullyCovered()) {
                    return true; // At least one line is fully covered
                }
            }
        }
        
        return false; // No coverage information or not covered
    }
    
    /**
     * Get coverage information for a specific class and line number.
     */
    private CoverageLineInfo getCoverageForLine(String classFqn, int lineNumber) {
        Map<Integer, CoverageLineInfo> classMap = coverageData.get(classFqn);
        if (classMap != null) {
            return classMap.get(lineNumber);
        }
        return null;
    }

    /**
     * Get the SootUp view for advanced analysis.
     */
    public View getView() {
        return view;
    }
    
    /**
     * Get the call graph for advanced analysis.
     */
    public CallGraph getCallGraph() {
        return callGraph;
    }
    
    /**
     * Get the ICFG for advanced analysis.
     */
    public JimpleBasedInterproceduralCFG getICFG() {
        return icfg;
    }
    
}