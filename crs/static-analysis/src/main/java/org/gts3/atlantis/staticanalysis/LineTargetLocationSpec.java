package org.gts3.atlantis.staticanalysis;

import org.gts3.atlantis.staticanalysis.utils.SignatureUtils;
import soot.Scene;
import soot.SootClass;
import soot.SootMethod;
import soot.Unit;
import soot.jimple.toolkits.callgraph.CallGraph;
import soot.tagkit.BytecodeOffsetTag;
import soot.tagkit.LineNumberTag;
import soot.tagkit.Tag;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Objects;

/**
 * Implementation of TargetLocationSpec that identifies target locations based on coordinates.
 *
 * This class locates methods by class name, method name, and method descriptor, and creates
 * target locations at specific bytecode offsets or line numbers within those methods.
 */
public class LineTargetLocationSpec implements TargetLocationSpec {
    private final String className;
    private final int lineNumber;
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
     * @param lineNumber The line number in the source file, or -1 if not available
     * @param markDescriptor A descriptor for marking the target location
     */
    public LineTargetLocationSpec(String className, int lineNumber, String markDescriptor, boolean inDiff,
                                  boolean sarifTarget, Map<String, Boolean> anaReachability,
                                  Map<String, Boolean> anaExploitability, boolean reached, boolean exploited) {
        this.className = className.replace('/', '.');
        this.lineNumber = lineNumber;
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
     * Gets the line number in the source file.
     *
     * @return The line number, or -1 if not available
     */
    public int getLineNumber() {
        return lineNumber;
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
            for (Unit unit : sootMethod.getActiveBody().getUnits()) {
                int bytecodeOffset = 0;
                Tag tag = unit.getTag("BytecodeOffsetTag");
                if (tag != null && tag instanceof BytecodeOffsetTag bytecodeOffsetTag) {
                    bytecodeOffset = bytecodeOffsetTag.getBytecodeOffset();
                }

                int lineNumber = -1;
                tag = unit.getTag("LineNumberTag");
                if (tag != null && tag instanceof LineNumberTag lineNumberTag) {
                    lineNumber = lineNumberTag.getLineNumber();
                }

                if (lineNumber == this.lineNumber) {
                    result.add(new TargetLocation(sootMethod, fileName, lineNumber, bytecodeOffset, markDescriptor, inDiff,
                            sarifTarget, anaReachability, anaExploitability, reached, exploited));
                }
            }
        }

        return result;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        LineTargetLocationSpec that = (LineTargetLocationSpec) o;
        return Objects.equals(className, that.className) && lineNumber == that.lineNumber && Objects.equals(markDescriptor, that.markDescriptor);
    }

    @Override
    public int hashCode() {
        return Objects.hash(className, lineNumber, markDescriptor);
    }
}
