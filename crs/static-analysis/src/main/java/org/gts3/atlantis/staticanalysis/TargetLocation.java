package org.gts3.atlantis.staticanalysis;

import org.gts3.atlantis.staticanalysis.utils.SignatureUtils;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;

import soot.SootMethod;
import soot.Unit;
import soot.tagkit.BytecodeOffsetTag;
import soot.toolkits.graph.Block;

/**
 * Represents a specific location in code that is a target for analysis.
 *
 * This class encapsulates information about a method, including its signature,
 * source file, line number, bytecode offset, and other metadata needed to
 * precisely identify a location in the code.
 */
public class TargetLocation implements CodeLocation {
    private final SootMethod sootMethod;
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

    private TargetLocation callee;
    private Unit srcUnit;

    /**
     * Constructs a TargetLocation with detailed location information.
     *
     * @param sootMethod The Soot method representing the target
     * @param fileName The source file name containing the target
     * @param lineNumber The line number in the source file
     * @param bytecodeOffset The bytecode offset within the method
     * @param markDescriptor A descriptor for marking this target
     */
    public TargetLocation(SootMethod sootMethod, String fileName, int lineNumber, int bytecodeOffset, String markDescriptor) {
        this(sootMethod, fileName, lineNumber, bytecodeOffset, markDescriptor, false, false, null,
             null, false, false);
    }

    /**
     * Constructs a TargetLocation with detailed location information.
     *
     * @param sootMethod The Soot method representing the target
     * @param fileName The source file name containing the target
     * @param lineNumber The line number in the source file
     * @param bytecodeOffset The bytecode offset within the method
     * @param markDescriptor A descriptor for marking this target
     * @param inDiff Whether this target location is derived from a diff file
     * @param sarifTarget Whether this target location is derived from a sarif report
     * @param anaReachability Reachability analysis results
     * @param anaExploitability Exploitability analysis results
     * @param sarifTarget Whether this target location is already reached by a fuzzer
     * @param sarifTarget Whether this target location is already exploited
     */
    public TargetLocation(SootMethod sootMethod, String fileName, int lineNumber, int bytecodeOffset, String markDescriptor, boolean inDiff,
                          boolean sarifTarget, Map<String, Boolean> anaReachability,
                          Map<String, Boolean> anaExploitability, boolean reached, boolean exploited) {
        this.sootMethod = sootMethod;
        this.fileName = fileName;
        this.lineNumber = lineNumber;
        this.bytecodeOffset = bytecodeOffset;
        this.markDescriptor = markDescriptor;

        // By default, callee and srcUnit information are not set
        this.callee = null;
        this.srcUnit = null;

        this.inDiff = inDiff;
        this.sarifTarget = sarifTarget;
        this.anaReachability = anaReachability;
        this.anaExploitability = anaExploitability;
        this.reached = reached;
        this.exploited = exploited;
    }

    /**
     * Constructs a simplified TargetLocation with just the method information.
     *
     * This constructor sets default values for file name, line number, and other fields.
     *
     * @param sootMethod The Soot method representing the target
     */
    public TargetLocation(SootMethod sootMethod) {
        this.sootMethod = sootMethod;
        this.fileName = null;
        this.lineNumber = -1;
        this.bytecodeOffset = 0;
        this.markDescriptor = null;

        // By default, callee and srcUnit information are not set
        this.callee = null;
        this.srcUnit = null;

        this.inDiff = false;
        this.sarifTarget = false;
        this.anaReachability = null;
        this.anaExploitability = null;
        this.reached = false;
        this.exploited = false;
    }

    /**
     * Gets the Soot method associated with this target location.
     *
     * @return The Soot method
     */
    public SootMethod getSootMethod() {
        return sootMethod;
    }

    /**
     * Gets the signature of the method associated with this target location.
     *
     * @return The method signature
     */
    public String getMethodSignature() {
        return sootMethod.getSignature();
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
     * Gets the signature of the class containing this target location.
     *
     * @return The class signature
     */
    public String getClassSignature() {
        return sootMethod.getDeclaringClass().getName();
    }

    /**
     * Gets the name of the class containing this target location,
     * with dots replaced by forward slashes.
     *
     * @return The class name in JVM format
     */
    public String getClassName() {
        return sootMethod.getDeclaringClass().getName().replace('.', '/');
    }

    /**
     * Gets the name of the method associated with this target location.
     *
     * @return The method name
     */
    public String getMethodName() {
        return sootMethod.getName();
    }

    /**
     * Gets the method descriptor in bytecode format.
     *
     * @return The method descriptor
     */
    public String getMethodDesc() {
        return SignatureUtils.bytecodeSignature(sootMethod);
    }

    /**
     * Gets the mark descriptor for this target location.
     *
     * @return The mark descriptor, or null if not available
     */
    public String getMarkDesc() {
        return markDescriptor;
    }

    /**
     * Gets the source file name containing this target location.
     *
     * @return The file name, or null if not available
     */
    public String getFileName() {
        return fileName;
    }

    /**
     * Sets the callee target location for this target.
     *
     * @param calleeTargetLocation The callee target location
     */
    public void setCallee(TargetLocation calleeTargetLocation) {
        this.callee = calleeTargetLocation;
    }

    /**
     * Gets the callee target location if this target represents a method call.
     *
     * @return The callee target location, or null if not available
     */
    public TargetLocation getCallee() {
        return callee;
    }

    /**
     * Checks if this target location has callee information.
     *
     * @return true if callee information is available, false otherwise
     */
    public boolean hasCallee() {
        return callee != null;
    }

    /**
     * Sets the source unit for this target.
     *
     * @param srcUnit The source unit, which we target
     */
    public void setSrcUnit(Unit srcUnit) {
        this.srcUnit = srcUnit;
    }

    /**
     * Gets the source unit for this target.
     *
     * @return The source unit, or null if not available
     */
    public Unit getSrcUnit() {
        return srcUnit;
    }

    /**
     * Checks if this target location has a source unit.
     *
     * @return true if source unit information is available, false otherwise
     */
    public boolean hasSrcUnit() {
        return srcUnit != null;
    }

    public boolean isInDiff() {
        return inDiff;
    }

    public boolean isSarifTarget() {
        return sarifTarget;
    }

    public Map<String, Boolean> getAnaReachability() {
        return anaReachability == null ? new HashMap<>() : anaReachability;
    }

    public Map<String, Boolean> getAnaExploitability() {
        return anaExploitability == null ? new HashMap<>() : anaExploitability;
    }

    public boolean isReached() {
        return reached;
    }

    public boolean isExploited() {
        return exploited;
    }

    /**
     * Checks if this target location is contained within the specified method and block.
     *
     * This method attempts to match the target location to a specific block in the control
     * flow graph by comparing bytecode offsets and line numbers.
     *
     * @param method The method to check
     * @param block The block within the method to check
     * @return true if this target location is contained in the specified block, false otherwise
     */
    public boolean containedIn(SootMethod method, Block block) {
        // Make sure we are in the right method
        if (!sootMethod.equals(method)) {
            return false;
        }

        // Try to match the bytecode offset
        int startBco = Integer.MAX_VALUE;
        int endBco = Integer.MIN_VALUE;

        for (Unit unit : block) {
            BytecodeOffsetTag bci = (BytecodeOffsetTag) unit.getTag("BytecodeOffsetTag");
            if (bci != null) {
                int bco = bci.getBytecodeOffset();
                if (bco >= 0) {
                    startBco = Math.min(startBco, bco);
                    endBco = Math.max(endBco, bco);
                }
            }
        }

        if (startBco <= endBco) {
            // In this case, we were able to find the start and end bytecode offsets
            if (bytecodeOffset >= startBco &&
                    bytecodeOffset <= endBco) {
                return true;
            }
        }

        // If bytecode offset matching failed, check for the source line number
        for (Unit unit : block) {
            if (unit.getJavaSourceStartLineNumber() == lineNumber) {
                return true;
            }
        }

        return false;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        TargetLocation that = (TargetLocation) o;
        return lineNumber == that.lineNumber && bytecodeOffset == that.bytecodeOffset && Objects.equals(sootMethod, that.sootMethod) && Objects.equals(fileName, that.fileName);
    }

    @Override
    public int hashCode() {
        return Objects.hash(sootMethod, fileName, lineNumber, bytecodeOffset);
    }
}
