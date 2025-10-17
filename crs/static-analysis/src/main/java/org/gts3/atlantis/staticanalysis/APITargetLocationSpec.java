package org.gts3.atlantis.staticanalysis;

import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;

import org.gts3.atlantis.staticanalysis.utils.SignatureUtils;
import soot.Scene;
import soot.SootClass;
import soot.SootMethod;
import soot.Unit;
import soot.baf.Inst;
import soot.jimple.Stmt;
import soot.jimple.toolkits.callgraph.CallGraph;
import soot.jimple.toolkits.callgraph.Edge;
import soot.tagkit.BytecodeOffsetTag;
import soot.tagkit.LineNumberTag;
import soot.tagkit.Tag;

import static org.gts3.atlantis.staticanalysis.utils.LogLabel.LOG_ERROR;

/**
 * Implementation of TargetLocationSpec that identifies target locations based on API calls.
 *
 * This class locates all calls to a specified method in a specified class, and creates
 * target locations at the call sites. It can match methods by name only or by both
 * name and descriptor.
 */
public class APITargetLocationSpec implements TargetLocationSpec {
    private final String className;
    private final String methodName;
    private final String methodDescriptor;
    private final String markDescriptor;

    /**
     * Constructs a new APITargetLocationSpec.
     *
     * @param className The name of the class containing the target method
     * @param methodName The name of the target method
     * @param methodDescriptor The descriptor of the target method, or null to match any descriptor
     * @param markDescriptor A descriptor for marking the target locations
     */
    public APITargetLocationSpec(String className, String methodName, String methodDescriptor, String markDescriptor) {
        this.className = className.replace('/', '.');
        this.methodName = methodName;
        this.methodDescriptor = methodDescriptor;
        this.markDescriptor = markDescriptor;
    }

    /**
     * Gets the name of the class containing the target method.
     *
     * @return The class name
     */
    public String getClassName() {
        return className;
    }

    /**
     * Gets the name of the target method.
     *
     * @return The method name
     */
    public String getMethodName() {
        return methodName;
    }

    /**
     * Gets the descriptor of the target method.
     *
     * @return The method descriptor, or null if matching any descriptor
     */
    public String getMethodDescriptor() {
        return methodDescriptor;
    }

    /**
     * Gets the descriptor for marking the target locations.
     *
     * @return The mark descriptor
     */
    public String getMarkDescriptor() {
        return markDescriptor;
    }

    /**
     * {@inheritDoc}
     *
     * This implementation finds all methods in the specified class that match the
     * specified name and descriptor, and then locates all call sites to those methods
     * in the call graph.
     */
    @Override
    public List<TargetLocation> toTargetLocations(CallGraph callGraph) {
        List<TargetLocation> result = new ArrayList<>();

        // First, get the Soot Class
        SootClass sootClass = Scene.v().getSootClass(className);

        // Go through all the methods
        for (SootMethod sootMethod : sootClass.getMethods()) {
            if (!sootMethod.getName().equals(methodName)) {
                continue;
            }

            if (methodDescriptor != null && !SignatureUtils.bytecodeSignature(sootMethod).equals(methodDescriptor)) {
                continue;
            }

            result.addAll(getCallerTargetLocations(callGraph, sootMethod, markDescriptor));
        }

        return result;
    }

    /**
     * Gets target locations for all callers of the specified method.
     *
     * This method finds all call sites to the specified method in the call graph,
     * and creates target locations at those call sites.
     *
     * @param callGraph The call graph to search
     * @param sootMethod The method to find callers for
     * @param markDescriptor The descriptor for marking the target locations
     * @return A list of target locations at call sites to the specified method
     */
    private static List<TargetLocation> getCallerTargetLocations(CallGraph callGraph, SootMethod sootMethod, String markDescriptor) {
        List<TargetLocation> result = new ArrayList<>();

        List<SootMethod> targetMethods = SignatureUtils.getImplementationsOf(sootMethod);

        for (SootMethod targetMethod : targetMethods) {
            for (Iterator<Edge> it = callGraph.edgesInto(targetMethod); it.hasNext(); ) {
                try {
                    Edge edge = it.next();

                    SootMethod callerSootMethod = edge.src();

                    Unit srcUnit = edge.srcUnit();

                    int bytecodeOffset = 0;
                    Tag tag = srcUnit.getTag("BytecodeOffsetTag");
                    if (tag != null && tag instanceof BytecodeOffsetTag bytecodeOffsetTag) {
                        bytecodeOffset = bytecodeOffsetTag.getBytecodeOffset();
                    }

                    int lineNumber = -1;
                    tag = srcUnit.getTag("LineNumberTag");
                    if (tag != null && tag instanceof LineNumberTag lineNumberTag) {
                        lineNumber = lineNumberTag.getLineNumber();
                    }

                    // Try to get the source file name from the declaring class
                    String fileName = callerSootMethod.getDeclaringClass().hasTag("SourceFileTag") ?
                            callerSootMethod.getDeclaringClass().getTag("SourceFileTag").toString() :
                            null;

                    TargetLocation targetLocation = new TargetLocation(callerSootMethod, fileName, lineNumber, bytecodeOffset, markDescriptor);
                    targetLocation.setCallee(new TargetLocation(sootMethod));
                    targetLocation.setSrcUnit(srcUnit);

                    result.add(targetLocation);
                } catch (Exception e) {
                    System.err.println(LOG_ERROR + "Failed to process a caller target: " + e.getMessage());
                    // Just ignore this target and continue with the next one
                }
            }
        }
        return result;
    }
}
