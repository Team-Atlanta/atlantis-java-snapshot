package org.gts3.atlantis.staticanalysis;

import com.google.gson.JsonObject;

import org.gts3.atlantis.staticanalysis.utils.SignatureUtils;
import soot.Body;
import soot.SootMethod;
import soot.Unit;
import soot.tagkit.LineNumberTag;
import soot.tagkit.Tag;

import java.util.Iterator;

import static org.gts3.atlantis.staticanalysis.utils.LogLabel.LOG_WARN;

/**
 * Represents a node in the call graph.
 * This class encapsulates the data of a function/method node in the call graph.
 */
public class CallGraphNode {
    private final String className;
    private final String methodDesc;
    private final String funcName;
    private final String fileName;
    private final String funcSig;
    private final int startLine;
    private final int endLine;

    /**
     * Constructs a CallGraphNode from a JsonObject.
     *
     * @param data The JsonObject containing node data
     */
    CallGraphNode(JsonObject data) {
        this.className = getStringOrEmpty(data, "class_name");
        this.methodDesc = getStringOrEmpty(data, "method_desc");
        this.funcName = getStringOrEmpty(data, "func_name");
        this.fileName = getStringOrEmpty(data, "file_name");
        this.funcSig = getStringOrEmpty(data, "func_sig");
        this.startLine = data.has("start_line") ? data.get("start_line").getAsInt() : -1;
        this.endLine = data.has("end_line") ? data.get("end_line").getAsInt() : -1;
    }

    /**
     * Constructs a CallGraphNode from individual fields.
     *
     * @param className The class name
     * @param methodDesc The method descriptor
     * @param funcName The function name
     * @param fileName The file name
     * @param funcSig The function signature
     * @param startLine The start line number
     * @param endLine The end line number
     */
    public CallGraphNode(String className, String methodDesc, String funcName,
                         String fileName, String funcSig, int startLine, int endLine) {
        this.className = className != null ? className : "";
        this.methodDesc = methodDesc != null ? methodDesc : "";
        this.funcName = funcName != null ? funcName : "";
        this.fileName = fileName != null ? fileName : "";
        this.funcSig = funcSig != null ? funcSig : "";
        this.startLine = startLine;
        this.endLine = endLine;
    }

    /**
     * Constructs a CallGraphNode from a SootMethod.
     *
     * @param method The SootMethod to convert to a CallGraphNode
     */
    public CallGraphNode(SootMethod method) {
        this.className = method.getDeclaringClass().getName();
        this.methodDesc = SignatureUtils.bytecodeSignature(method);
        this.funcName = method.getName();

        // Get file name from the source file attribute of the class if available
        String fileName = "";
        if (method.getDeclaringClass().hasTag("SourceFileTag")) {
            Tag sourceFileTag = method.getDeclaringClass().getTag("SourceFileTag");
            if (sourceFileTag != null) {
                fileName = sourceFileTag.toString();
            }
        }
        this.fileName = fileName;

        // Extract only the method name and parameters part (without the return type)
        this.funcSig = method.getSubSignature().substring(method.getReturnType().toQuotedString().length() + 1);

        // Get line numbers if available
        int startLine = Integer.MAX_VALUE;
        int endLine = Integer.MIN_VALUE;

        // Try to get line numbers from the method body if available
        if (method.hasActiveBody()) {
            try {
                Body body = method.retrieveActiveBody();

                // Traverse each unit (instruction)
                Iterator<Unit> unitIterator = body.getUnits().iterator();
                while (unitIterator.hasNext()) {
                    Unit unit = unitIterator.next();
                    LineNumberTag lineNumberTag = (LineNumberTag) unit.getTag(LineNumberTag.NAME);

                    if (lineNumberTag != null) {
                        int lineNumber = lineNumberTag.getLineNumber();
                        if (lineNumber < startLine) {
                            startLine = lineNumber;
                        }
                        if (lineNumber > endLine) {
                            endLine = lineNumber;
                        }
                    }
                }
            } catch (Exception e) {
                System.out.println(LOG_WARN + "Failed to get line numbers for method " + method.getName() + ": " + e.getMessage());
                // Ignore exceptions when getting line numbers
            }
        }

        if (startLine > endLine) {
            startLine = -1;
            endLine = -1;
        }

        this.startLine = startLine;
        this.endLine = endLine;
    }

    private String getStringOrEmpty(JsonObject obj, String key) {
        return obj != null && obj.has(key) ? obj.get(key).getAsString() : "";
    }

    /**
     * Gets the class name of the node.
     *
     * @return The class name
     */
    public String getClassName() {
        return className;
    }

    /**
     * Gets the method descriptor of the node.
     *
     * @return The method descriptor
     */
    public String getMethodDesc() {
        return methodDesc;
    }

    /**
     * Gets the function name of the node.
     *
     * @return The function name
     */
    public String getFuncName() {
        return funcName;
    }

    /**
     * Gets the file name of the node.
     *
     * @return The file name
     */
    public String getFileName() {
        return fileName;
    }

    /**
     * Gets the function signature of the node.
     *
     * @return The function signature
     */
    public String getFuncSig() {
        return funcSig;
    }

    /**
     * Gets the start line number of the node.
     *
     * @return The start line number, or -1 if not available
     */
    public int getStartLine() {
        return startLine;
    }

    /**
     * Gets the end line number of the node.
     *
     * @return The end line number, or -1 if not available
     */
    public int getEndLine() {
        return endLine;
    }

    /**
     * Creates a signature string for this node.
     *
     * @return A unique signature based on class_name + method_desc + func_name
     */
    String getSignature() {
        return className + "|" + methodDesc + "|" + funcName;
    }

    /**
     * Creates a JsonObject representing this node's data.
     * This method is package-private and not part of the public API.
     *
     * @return A JsonObject containing this node's data
     */
    JsonObject createDataJson() {
        JsonObject data = new JsonObject();
        data.addProperty("class_name", this.className);
        data.addProperty("method_desc", this.methodDesc);
        data.addProperty("func_name", this.funcName);
        data.addProperty("file_name", this.fileName);
        data.addProperty("func_sig", this.funcSig);
        data.addProperty("start_line", this.startLine);
        data.addProperty("end_line", this.endLine);
        return data;
    }

    @Override
    public String toString() {
        return "CallGraphNode{" +
                "className='" + className + '\'' +
                ", funcName='" + funcName + '\'' +
                ", fileName='" + fileName + '\'' +
                ", funcSig='" + funcSig + '\'' +
                ", startLine=" + startLine +
                ", endLine=" + endLine +
                '}';
    }
}
