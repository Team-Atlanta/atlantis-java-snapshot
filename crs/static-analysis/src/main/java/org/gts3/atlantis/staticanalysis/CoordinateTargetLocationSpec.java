package org.gts3.atlantis.staticanalysis;

import java.util.*;

import org.gts3.atlantis.staticanalysis.utils.SignatureUtils;
import soot.Scene;
import soot.SootClass;
import soot.SootMethod;
import soot.jimple.toolkits.callgraph.CallGraph;

/**
 * Implementation of TargetLocationSpec that identifies target locations based on coordinates.
 *
 * This class locates methods by class name, method name, and method descriptor, and creates
 * target locations at specific bytecode offsets or line numbers within those methods.
 */
public class CoordinateTargetLocationSpec implements TargetLocationSpec {
    private final String className;
    private final String methodName;
    private final String methodDescriptor;
    private final String fileName;
    private final int lineNumber;
    private final int bytecodeOffset;
    private final String markDescriptor;
    private final boolean inDiff;
    private final boolean sarifTarget;
    private final Map<String, Boolean> anaReachability;
    private final Map<String, Boolean> anaExploitability;
    private final boolean reached;
    private final boolean exploited;

    /**
     * Constructs a new CoordinateTargetLocationSpec.
     *
     * @param className The name of the class containing the target method
     * @param methodName The name of the target method
     * @param methodDescriptor The descriptor of the target method
     * @param fileName The source file name, or null if not available
     * @param lineNumber The line number in the source file, or -1 if not available
     * @param bytecodeOffset The bytecode offset within the method
     * @param markDescriptor A descriptor for marking the target location
     */
    public CoordinateTargetLocationSpec(String className, String methodName, String methodDescriptor, String fileName,
                                        int lineNumber, int bytecodeOffset, String markDescriptor) {
        this(className, methodName, methodDescriptor, fileName, lineNumber, bytecodeOffset, markDescriptor, false,
             false, null, null, false, false);
    }

    /**
     * Constructs a new CoordinateTargetLocationSpec.
     *
     * @param className The name of the class containing the target method
     * @param methodName The name of the target method
     * @param methodDescriptor The descriptor of the target method
     * @param fileName The source file name, or null if not available
     * @param lineNumber The line number in the source file, or -1 if not available
     * @param bytecodeOffset The bytecode offset within the method
     * @param markDescriptor A descriptor for marking the target location
     * @param inDiff Whether this spec is derived from a diff file
     * @param sarifTarget Whether this spec is derived from a sarif report
     * @param anaReachability Reachability analysis results
     * @param anaExploitability Exploitability analysis results
     * @param sarifTarget Whether this spec is already reached by a fuzzer
     * @param sarifTarget Whether this spec is already exploited
     */
    public CoordinateTargetLocationSpec(String className, String methodName, String methodDescriptor, String fileName,
                                        int lineNumber, int bytecodeOffset, String markDescriptor, boolean inDiff,
                                        boolean sarifTarget, Map<String, Boolean> anaReachability,
                                        Map<String, Boolean> anaExploitability, boolean reached, boolean exploited) {
        this.className = className.replace('/', '.');
        this.methodName = methodName;
        this.methodDescriptor = methodDescriptor;
        this.fileName = fileName;
        this.lineNumber = lineNumber;
        this.bytecodeOffset = bytecodeOffset;
        this.markDescriptor = markDescriptor;
        this.inDiff = inDiff;
        this.sarifTarget = sarifTarget;
        this.anaReachability = anaReachability;
        this.anaExploitability = anaExploitability;
        this.reached = reached;
        this.exploited = exploited;
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
     * @return The method descriptor
     */
    public String getMethodDescriptor() {
        return methodDescriptor;
    }

    /**
     * Gets the source file name.
     *
     * @return The file name, or null if not available
     */
    public String getFileName() {
        return fileName;
    }

    /**
     * Gets the line number in the source file.
     *
     * @return The line number, or -1 if not available
     */
    public int getLineNumber() {
        return lineNumber;
    }

    /**
     * Gets the bytecode offset within the method.
     *
     * @return The bytecode offset
     */
    public int getBytecodeOffset() {
        return bytecodeOffset;
    }

    /**
     * Gets the descriptor for marking the target location.
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
     * specified name and descriptor, and creates target locations at the specified
     * bytecode offset or line number within those methods.
     */
    @Override
    public List<TargetLocation> toTargetLocations(CallGraph callGraph) {
        List<TargetLocation> result = new ArrayList<>();

        // First, get the Soot Class
        SootClass sootClass = Scene.v().getSootClass(className);

        // Try to get the source file name from the declaring class
        String fileName = sootClass.hasTag("SourceFileTag") ?
                sootClass.getTag("SourceFileTag").toString() :
                null;

        // Go through all the methods
        for (SootMethod sootMethod : sootClass.getMethods()) {
            if (!sootMethod.getName().equals(methodName)) {
                continue;
            }

            if (methodDescriptor != null && !SignatureUtils.bytecodeSignature(sootMethod).equals(methodDescriptor)) {
                continue;
            }

            result.add(new TargetLocation(sootMethod, fileName, lineNumber, bytecodeOffset, markDescriptor, inDiff,
                       sarifTarget, anaReachability, anaExploitability, reached, exploited));
        }

        return result;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        CoordinateTargetLocationSpec that = (CoordinateTargetLocationSpec) o;
        return lineNumber == that.lineNumber && bytecodeOffset == that.bytecodeOffset && Objects.equals(className, that.className) && Objects.equals(methodName, that.methodName) && Objects.equals(methodDescriptor, that.methodDescriptor) && Objects.equals(fileName, that.fileName) && Objects.equals(markDescriptor, that.markDescriptor);
    }

    @Override
    public int hashCode() {
        return Objects.hash(className, methodName, methodDescriptor, fileName, lineNumber, bytecodeOffset, markDescriptor);
    }
}
