package org.gts3.atlantis.staticanalysis;

import java.io.FileWriter;
import java.io.IOException;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;

import org.gts3.atlantis.staticanalysis.taint.TaintStatus;
import soot.SootMethod;
import soot.toolkits.graph.Block;

import static org.gts3.atlantis.staticanalysis.utils.LogLabel.LOG_ERROR;
import org.gts3.atlantis.staticanalysis.utils.FileUtils;

/**
 * Utility class for serializing distance data to JSON format.
 *
 * This class provides methods to convert method distance maps, basic block distances,
 * and target location information into structured JSON data that can be saved to files.
 * It handles the formatting and organization of complex distance data for analysis and visualization.
 */
public class DistanceDataSerializer {
    private static final Gson gson = new GsonBuilder().setPrettyPrinting().create();

    /**
     * Creates a JSON object with distance data for a target location.
     * This method generates a structured map containing distance information for methods and basic blocks
     * relative to a specified target location. The resulting map can be serialized to JSON format.
     *
     * @param fuzzTargetData The FuzzTargetData object containing method distances, basic block distances,
     *                       target location information, and harness reachability data
     * @param allMappedMethods Set of all methods mapped across all targets, used for comprehensive analysis
     * @param includeDistanceMap Whether to include the detailed distance map in the output
     * @return A map containing structured distance data ready for JSON serialization,
     * including method distances, basic block distances, and target location information
     */
    public static Map<String, Object> createTargetData(FuzzTargetData fuzzTargetData, Set<SootMethod> allMappedMethods, boolean includeDistanceMap) {
        Map<String, Object> jsonData = new HashMap<>();
        SootMethodDistanceMap methodDistanceMap = fuzzTargetData.getMethodDistanceMap();

        // Add the detailed distance map only if requested
        if (includeDistanceMap) {
            Map<String, Object> distanceMap = new HashMap<>();
            for (SootMethod method : methodDistanceMap.getMethods()) {
                Map<String, Object> methodData = new HashMap<>();
                methodData.put("method_distance", methodDistanceMap.getDistance(method));

                BasicBlockDistance blockDistance = fuzzTargetData.getBasicBlockDistances().get(method);
                if (blockDistance != null) {
                    Map<String, Integer> blockDistances = new HashMap<>();
                    for (Block block : blockDistance.getBlockDistanceMap().keySet()) {
                        if (blockDistance.hasDistance(block)) {
                            int blockId = blockDistance.getBlockId(block);
                            if (blockId >= 0) {
                                blockDistances.put(Integer.toString(blockId), blockDistance.getDistance(block));
                            }
                        }
                    }
                    if (!blockDistances.isEmpty()) {
                        methodData.put("block_distances", blockDistances);
                    }
                }

                String signature = method.getSignature();
                distanceMap.put(signature.substring(1, signature.length()-1), methodData);
            }
            jsonData.put("distance_map", distanceMap);
        }

        // Add a list of method distances for all mapped methods
        // The list is ordered the same way as the all_mapped_methods list in the container object
        List<Integer> allMethodDistances = new ArrayList<>();
        for (SootMethod method : allMappedMethods) {
            // If the method has a distance in this target, use it; otherwise, use null
            if (methodDistanceMap.hasDistance(method)) {
                allMethodDistances.add(methodDistanceMap.getDistance(method));
            } else {
                allMethodDistances.add(null);
            }
        }
        jsonData.put("all_method_distances", allMethodDistances);

        // Generate target location data and add it to the JSON data
        jsonData.put("target_location", createTargetLocationData(fuzzTargetData));

        // Use the hash from the FuzzTargetData object
        jsonData.put("map_hash", fuzzTargetData.getMapHash());

        return jsonData;
    }

    /**
     * Creates a map containing the target location data.
     *
     * @param fuzzTargetData The fuzz target data object
     * @return A map containing the target location data ready for JSON serialization
     */
    private static Map<String, Object> createTargetLocationData(FuzzTargetData fuzzTargetData) {
        TargetLocation targetLocation = fuzzTargetData.getTargetLocation();

        Map<String, Object> targetLocationData = new HashMap<>();

        // Add the coordinate
        Map<String, Object> coord = new HashMap<>();
        coord.put("method_signature", targetLocation.getMethodSignature().substring(1, targetLocation.getMethodSignature().length()-1));
        coord.put("line_num", targetLocation.getLineNumber());
        coord.put("bytecode_offset", targetLocation.getBytecodeOffset());

        coord.put("class_name", targetLocation.getClassName());
        coord.put("method_name", targetLocation.getMethodName());
        coord.put("method_desc", targetLocation.getMethodDesc());
        coord.put("mark_desc", targetLocation.getMarkDesc());
        coord.put("file_name", targetLocation.getFileName());
        targetLocationData.put("coord", coord);

        // Add callee information
        if (targetLocation.hasCallee()) {
            TargetLocation callee = targetLocation.getCallee();
            Map<String, Object> calleeInfo = new HashMap<>();

            calleeInfo.put("class_name", callee.getClassName());
            calleeInfo.put("method_name", callee.getMethodName());
            calleeInfo.put("method_desc", callee.getMethodDesc());
            calleeInfo.put("mark_desc", targetLocation.getMarkDesc());

            targetLocationData.put("callee_api", calleeInfo);
        }

        // Priority information
        targetLocationData.put("in_diff", targetLocation.isInDiff());
        targetLocationData.put("sarif_target", targetLocation.isSarifTarget());
        targetLocationData.put("tainted", fuzzTargetData.getTaintStatus() != TaintStatus.NOT_TAINTED);

        // Reachability and exploitability
        Map<String, Boolean> reachabilityInfo = new HashMap<>();
        for (HarnessInfo harnessInfo : fuzzTargetData.getTargetReachingHarnesses()) {
            reachabilityInfo.put(harnessInfo.getName(), true);
        }
        targetLocationData.put("ana_reachability", reachabilityInfo);
        targetLocationData.put("ana_exploitability", targetLocation.getAnaExploitability());

        return targetLocationData;
    }


    /**
     * Serializes a list of JSON data along with all mapped methods to a file atomically.
     * This method uses the FileUtils utility to write the file atomically,
     * preventing partial writes and data corruption.
     *
     * @param path The path to the file where the data will be saved
     * @param jsonDataList The list of JSON data to serialize and save
     * @param allMappedMethods Set of all methods mapped across all targets
     * @return The serialized JSON content as a string
     */
    public static String serializeJsonDataWithMethodsToFile(Path path, List<Map<String, Object>> jsonDataList, Set<SootMethod> allMappedMethods) {
        try {
            // Create a container object that includes both the target data list and all mapped methods
            Map<String, Object> containerObject = new HashMap<>();

            // Add the target data list
            containerObject.put("target_data", jsonDataList);

            // Add the all mapped methods list (just the signatures)
            List<String> methodSignatures = allMappedMethods.stream()
                .map(method -> {
                    String signature = method.getSignature();
                    return signature.substring(1, signature.length()-1);
                })
                .collect(Collectors.toList());
            containerObject.put("all_mapped_methods", methodSignatures);

            // Serialize the container object to string
            String jsonContent = gson.toJson(containerObject);

            // Write the content to file atomically
            FileUtils.writeFileAtomically(path, tempPath -> {
                try (FileWriter writer = new FileWriter(tempPath.toFile())) {
                    writer.write(jsonContent);
                } catch (IOException e) {
                    throw new RuntimeException("Error writing JSON content", e);
                }
            });

            return jsonContent;
        } catch (IOException e) {
            System.err.println(LOG_ERROR + "Error writing JSON file: " + e.getMessage());
            return null;
        }
    }
}
