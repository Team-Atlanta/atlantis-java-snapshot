package org.gts3.atlantis.staticanalysis;

import com.google.gson.JsonObject;
import com.google.gson.JsonPrimitive;

/**
 * Represents an edge in the call graph.
 * This class encapsulates the data of a function call relationship in the call graph.
 */
public class CallGraphEdge {
    private final int sourceId;
    private final int targetId;
    private final String callType;
    private final String edgeType;

    /**
     * Constructs a CallGraphEdge from a JsonObject.
     *
     * @param edgeJson The JsonObject containing edge data
     */
    CallGraphEdge(JsonObject edgeJson) {
        this.sourceId = edgeJson.get("source").getAsInt();
        this.targetId = edgeJson.get("target").getAsInt();
        this.callType = edgeJson.has("callType") ? edgeJson.get("callType").getAsString() : "";
        this.edgeType = edgeJson.has("edgeType") ? edgeJson.get("edgeType").getAsString() : "";
    }

    /**
     * Constructs a CallGraphEdge from individual fields.
     *
     * @param sourceId The ID of the source node
     * @param targetId The ID of the target node
     * @param callType The type of the call
     * @param edgeType The type of the edge
     */
    public CallGraphEdge(int sourceId, int targetId, String callType, String edgeType) {
        this.sourceId = sourceId;
        this.targetId = targetId;
        this.callType = callType != null ? callType : "";
        this.edgeType = edgeType != null ? edgeType : "";
    }

    /**
     * Gets the ID of the source node.
     *
     * @return The source node ID
     */
    public int getSourceId() {
        return sourceId;
    }

    /**
     * Gets the ID of the target node.
     *
     * @return The target node ID
     */
    public int getTargetId() {
        return targetId;
    }

    /**
     * Gets the type of the call.
     *
     * @return The call type
     */
    public String getCallType() {
        return callType;
    }

    /**
     * Gets the type of the edge.
     *
     * @return The edge type
     */
    public String getEdgeType() {
        return edgeType;
    }

    /**
     * Creates a JsonObject representing this edge.
     * This method constructs the JsonObject on demand rather than storing it.
     *
     * @return A JsonObject containing the edge data
     */
    JsonObject createDataJson() {
        JsonObject edgeJson = new JsonObject();
        edgeJson.addProperty("source", sourceId);
        edgeJson.addProperty("target", targetId);
        edgeJson.addProperty("callType", callType);
        edgeJson.addProperty("edgeType", edgeType);
        return edgeJson;
    }

    @Override
    public String toString() {
        return "CallGraphEdge{" +
                "sourceId=" + sourceId +
                ", targetId=" + targetId +
                ", callType='" + callType + '\'' +
                ", edgeType='" + edgeType + '\'' +
                '}';
    }
}
