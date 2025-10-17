package org.gts3.atlantis.staticanalysis;

import java.io.FileReader;
import java.io.FileWriter;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.stream.Collectors;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

import static org.gts3.atlantis.staticanalysis.utils.LogLabel.LOG_WARN;

/**
 * A wrapper class for the call graph JSON file that represents function call relationships.
 * This class provides methods to read, manipulate, and write call graph data in JSON format.
 * It encapsulates the JSON structure and provides a clean API using domain-specific classes.
 *
 * This class supports dynamic modification of the call graph by allowing the addition of
 * new nodes and edges at runtime. Users can create an empty call graph and populate it
 * with nodes and edges, or load an existing call graph from a file and modify it.
 */
public class CallGraphJson {
    private final boolean directed;
    private final Instant creationTime;

    // Indexes for quick lookups
    private Map<Integer, CallGraphNode> nodeById = new HashMap<>();
    private Map<String, Integer> nodeIdBySignature = new HashMap<>();
    private List<CallGraphEdge> edges = new ArrayList<>();

    /**
     * Constructs a new empty CallGraphJson instance.
     * This constructor creates an empty call graph that can be populated dynamically.
     *
     * @param directed Whether the graph is directed or undirected
     */
    public CallGraphJson(boolean directed) {
        this.directed = directed;
        this.creationTime = Instant.now();
    }

    /**
     * Constructs a new CallGraphJson instance by loading data from the specified file path.
     *
     * @param filePath The path to the JSON file containing call graph data
     * @throws IOException If an I/O error occurs while reading the file
     */
    public CallGraphJson(Path filePath) throws IOException {
        if (!Files.exists(filePath)) {
            throw new IOException("Call graph file does not exist: " + filePath);
        }

        this.creationTime = Files.getLastModifiedTime(filePath).toInstant();

        try (FileReader reader = new FileReader(filePath.toFile())) {
            JsonObject graphData = JsonParser.parseReader(reader).getAsJsonObject();
            buildIndexes(graphData);

            this.directed = graphData.has("directed") && graphData.get("directed").getAsBoolean();
        } catch (Exception e) {
            System.out.println(LOG_WARN + "Failed to parse call graph JSON file: " + e.getMessage());
            throw new IOException("Failed to parse call graph JSON file: " + e.getMessage(), e);
        }
    }

    /**
     * Builds internal indexes for quick lookups of nodes and edges.
     *
     * @param graphData The JSON object containing the call graph data
     */
    private void buildIndexes(JsonObject graphData) {
        nodeById.clear();
        nodeIdBySignature.clear();
        edges.clear();

        JsonArray nodes = graphData.getAsJsonArray("nodes");
        JsonArray linksArray = graphData.getAsJsonArray("links");

        if (nodes != null) {
            for (JsonElement nodeElement : nodes) {
                JsonObject nodeJson = nodeElement.getAsJsonObject();
                int id = nodeJson.get("id").getAsInt();
                JsonObject data = nodeJson.getAsJsonObject("data");

                CallGraphNode node = new CallGraphNode(data);
                nodeById.put(id, node);

                String signature = node.getSignature();
                nodeIdBySignature.put(signature, id);
            }
        }

        if (linksArray != null) {
            for (JsonElement linkElement : linksArray) {
                JsonObject edgeJson = linkElement.getAsJsonObject();
                CallGraphEdge edge = new CallGraphEdge(edgeJson);
                edges.add(edge);
            }
        }
    }

    /**
     * Creates a unique signature for a node based on class_name + method_desc + func_name.
     *
     * @param data The data object from a node
     * @return A unique signature string
     */
    private String createNodeSignature(JsonObject data) {
        String className = data.has("class_name") ? data.get("class_name").getAsString() : "";
        String methodDesc = data.has("method_desc") ? data.get("method_desc").getAsString() : "";
        String funcName = data.has("func_name") ? data.get("func_name").getAsString() : "";
        return className + "|" + methodDesc + "|" + funcName;
    }

    /**
     * Creates a JsonObject representing the current state of the call graph.
     *
     * @return A JsonObject containing all nodes and edges in the call graph
     */
    public JsonObject createJsonObject() {
        JsonObject graphData = new JsonObject();

        // Set directed property
        graphData.addProperty("directed", directed);
        graphData.addProperty("multigraph", false);
        graphData.add("graph", new JsonObject());

        // Add nodes
        JsonArray nodesArray = new JsonArray();
        for (Map.Entry<Integer, CallGraphNode> entry : nodeById.entrySet()) {
            int id = entry.getKey();
            CallGraphNode node = entry.getValue();

            JsonObject nodeJson = new JsonObject();
            nodeJson.addProperty("id", id);
            nodeJson.add("data", node.createDataJson());

            nodesArray.add(nodeJson);
        }
        graphData.add("nodes", nodesArray);

        // Add edges
        JsonArray linksArray = new JsonArray();
        for (CallGraphEdge edge : edges) {
            linksArray.add(edge.createDataJson());
        }
        graphData.add("links", linksArray);

        return graphData;
    }

    /**
     * Saves the call graph data to the specified file.
     *
     * @param outputPath The path to save the call graph data to
     * @throws IOException If an I/O error occurs while writing the file
     */
    public void saveToFile(String outputPath) throws IOException {
        try (FileWriter writer = new FileWriter(outputPath)) {
            Gson gson = new GsonBuilder().setPrettyPrinting().create();
            gson.toJson(createJsonObject(), writer);
        }
    }

    /**
     * Gets all nodes in the call graph.
     *
     * @return A list of all node objects
     */
    public List<CallGraphNode> getAllNodes() {
        return new ArrayList<>(nodeById.values());
    }

    /**
     * Gets all edges in the call graph.
     *
     * @return A list of all edge objects
     */
    public List<CallGraphEdge> getAllEdges() {
        return new ArrayList<>(edges);
    }

    /**
     * Gets a node by its ID.
     *
     * @param id The ID of the node to retrieve
     * @return An Optional containing the node if found, or empty if not found
     */
    public Optional<CallGraphNode> getNodeById(int id) {
        return Optional.ofNullable(nodeById.get(id));
    }

    /**
     * Gets a node by its signature (class_name + method_desc + func_name).
     *
     * @param className The class name
     * @param methodDesc The method descriptor
     * @param funcName The function name
     * @return An Optional containing the node if found, or empty if not found
     */
    public Optional<CallGraphNode> getNodeBySignature(String className, String methodDesc, String funcName) {
        String signature = className + "|" + methodDesc + "|" + funcName;
        Integer nodeId = nodeIdBySignature.get(signature);
        if (nodeId == null) {
            return Optional.empty();
        }
        return Optional.ofNullable(nodeById.get(nodeId));
    }

    /**
     * Gets all edges where the specified node is the source.
     *
     * @param sourceId The ID of the source node
     * @return A list of edges where the specified node is the source
     */
    public List<CallGraphEdge> getOutgoingEdges(int sourceId) {
        return edges.stream()
                .filter(edge -> edge.getSourceId() == sourceId)
                .collect(Collectors.toList());
    }

    /**
     * Gets all edges where the specified node is the target.
     *
     * @param targetId The ID of the target node
     * @return A list of edges where the specified node is the target
     */
    public List<CallGraphEdge> getIncomingEdges(int targetId) {
        return edges.stream()
                .filter(edge -> edge.getTargetId() == targetId)
                .collect(Collectors.toList());
    }

    /**
     * Finds nodes by function name.
     *
     * @param funcName The function name to search for
     * @return A list of nodes with the specified function name
     */
    public List<CallGraphNode> findNodesByFunctionName(String funcName) {
        return nodeById.values().stream()
                .filter(node -> node.getFuncName().equals(funcName))
                .collect(Collectors.toList());
    }

    /**
     * Finds nodes by class name.
     *
     * @param className The class name to search for
     * @return A list of nodes with the specified class name
     */
    public List<CallGraphNode> findNodesByClassName(String className) {
        return nodeById.values().stream()
                .filter(node -> node.getClassName().equals(className))
                .collect(Collectors.toList());
    }

    /**
     * Finds nodes by file name.
     *
     * @param fileName The file name to search for
     * @return A list of nodes with the specified file name
     */
    public List<CallGraphNode> findNodesByFileName(String fileName) {
        return nodeById.values().stream()
                .filter(node -> node.getFileName().contains(fileName))
                .collect(Collectors.toList());
    }

    /**
     * Gets the total number of nodes in the call graph.
     *
     * @return The number of nodes
     */
    public int getNodeCount() {
        return nodeById.size();
    }

    /**
     * Gets the total number of edges in the call graph.
     *
     * @return The number of edges
     */
    public int getEdgeCount() {
        return edges.size();
    }

    /**
     * Checks if the call graph is directed.
     *
     * @return True if the graph is directed, false otherwise
     */
    public boolean isDirected() {
        return directed;
    }

    /**
     * Gets the creation time of the call graph.
     *
     * @return The Instant at which the call graph was created
     */
    public Instant getCreationTime() {
        return creationTime;
    }

    /**
     * Gets the maximum node ID in the call graph.
     * This is useful for generating new unique node IDs when adding nodes.
     *
     * @return The maximum node ID, or -1 if there are no nodes
     */
    public int getMaxNodeId() {
        if (nodeById.isEmpty()) {
            return -1;
        }

        return nodeById.keySet().stream()
                .mapToInt(Integer::intValue)
                .max()
                .orElse(-1);
    }

    /**
     * Adds a new node to the call graph.
     * This method automatically generates a unique ID for the node.
     *
     * @param callGraphNode The node to add
     * @return The ID of the newly added node
     */
    public int addNode(CallGraphNode callGraphNode) {
        // Check if the node already exists
        String signature = callGraphNode.getSignature();
        if (nodeIdBySignature.containsKey(signature)) {
            return nodeIdBySignature.get(signature);
        }

        // Generate a unique ID
        int newId = getMaxNodeId() + 1;

        // Add to indexes
        nodeById.put(newId, callGraphNode);
        nodeIdBySignature.put(callGraphNode.getSignature(), newId);

        return newId;
    }

    /**
     * Adds a new edge between two nodes in the call graph.
     * This method uses the node objects directly.
     *
     * @param sourceNode The source node
     * @param targetNode The target node
     * @param callType The type of the call
     * @param edgeType The type of the edge
     * @return The newly created edge, or null if either node doesn't exist in the graph
     */
    public CallGraphEdge addEdge(CallGraphNode sourceNode, CallGraphNode targetNode,
                                String callType, String edgeType) {
        // Ensure both nodes exist in the graph
        Integer sourceId = addNode(sourceNode);
        Integer targetId = addNode(targetNode);

        // Create and add the edge
        CallGraphEdge edge = new CallGraphEdge(sourceId, targetId, callType, edgeType);
        edges.add(edge);

        return edge;
    }
}
