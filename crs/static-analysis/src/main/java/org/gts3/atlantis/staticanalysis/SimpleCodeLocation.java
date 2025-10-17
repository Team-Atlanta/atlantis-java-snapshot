package org.gts3.atlantis.staticanalysis;

import org.gts3.atlantis.staticanalysis.utils.SignatureUtils;
import soot.SootMethod;
import soot.Unit;
import soot.tagkit.BytecodeOffsetTag;
import soot.tagkit.LineNumberTag;
import soot.toolkits.graph.Block;

/**
 * A simple implementation of CodeLocation that uses string-based method identification.
 *
 * This class represents a location in code identified by class name, method name,
 * method descriptor, line number, and bytecode offset. It provides a way to check
 * if this location is contained within a specific method and control flow graph block.
 */
public class SimpleCodeLocation implements CodeLocation {
    private final String className;
    private final String methodName;
    private final String methodDesc;
    private final int lineNumber;
    private final int bytecodeOffset;

    /**
     * Constructs a new SimpleCodeLocation with the specified parameters.
     *
     * @param className The name of the class containing the code location
     * @param methodName The name of the method containing the code location
     * @param methodDesc The descriptor of the method containing the code location
     * @param lineNumber The line number in the source file, or -1 if not available
     * @param bytecodeOffset The bytecode offset within the method
     */
    public SimpleCodeLocation(String className, String methodName, String methodDesc, int lineNumber, int bytecodeOffset) {
        this.className = className;
        this.methodName = methodName;
        this.methodDesc = methodDesc;
        this.lineNumber = lineNumber;
        this.bytecodeOffset = bytecodeOffset;
    }

    /**
     * Gets the name of the class containing this code location.
     *
     * @return The class name
     */
    public String getClassName() {
        return className;
    }

    /**
     * Gets the name of the method containing this code location.
     *
     * @return The method name
     */
    public String getMethodName() {
        return methodName;
    }

    /**
     * Gets the descriptor of the method containing this code location.
     *
     * @return The method descriptor
     */
    public String getMethodDesc() {
        return methodDesc;
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
     * {@inheritDoc}
     *
     * This implementation checks if the specified method matches the class name,
     * method name, and method descriptor of this code location, and then checks
     * if the bytecode offset or line number is within the specified block.
     */
    @Override
    public boolean containedIn(SootMethod method, Block block) {
        // Make sure we are in the right method
        if (!method.getDeclaringClass().getName().equals(className.replace('/', '.'))
            || !method.getName().equals(methodName)
            || !SignatureUtils.bytecodeSignature(method).equals(methodDesc)) {
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
            LineNumberTag lineNumberTag = (LineNumberTag) unit.getTag("LineNumberTag");
            if (lineNumberTag != null && lineNumberTag.getLineNumber() == lineNumber) {
                return true;
            }
        }

        return false;
    }
}
