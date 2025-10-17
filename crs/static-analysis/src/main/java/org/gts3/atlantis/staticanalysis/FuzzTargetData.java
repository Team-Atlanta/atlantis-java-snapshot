package org.gts3.atlantis.staticanalysis;

import org.gts3.atlantis.staticanalysis.taint.TaintStatus;
import soot.SootMethod;

import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

import static org.gts3.atlantis.staticanalysis.utils.LogLabel.LOG_ERROR;

/**
 * Represents data for a fuzzing target, including method distance maps and basic block distances.
 *
 * This class encapsulates all the information needed for fuzzing a specific target location,
 * including distance maps, basic block distances, and harness information. It also computes
 * and stores a hash of the distance map for efficient comparison and deduplication.
 */
public class FuzzTargetData {
    private SootMethodDistanceMap methodDistanceMap;
    private Map<SootMethod, BasicBlockDistance> basicBlockDistances;
    private TargetLocation targetLocation;
    private List<HarnessInfo> targetReachingHarnesses;
    private String mapHash;
    private TaintStatus taintStatus;

    /**
     * Constructs a new FuzzTargetData instance.
     *
     * @param methodDistanceMap The method distance map for the target
     * @param basicBlockDistances Map of methods to their basic block distances
     * @param targetLocation The target location
     * @param targetReachingHarnesses List of harnesses that can reach the target
     */
    public FuzzTargetData(SootMethodDistanceMap methodDistanceMap, Map<SootMethod, BasicBlockDistance> basicBlockDistances, TargetLocation targetLocation, List<HarnessInfo> targetReachingHarnesses) {
        this.methodDistanceMap = methodDistanceMap;
        this.basicBlockDistances = basicBlockDistances;
        this.targetLocation = targetLocation;
        this.targetReachingHarnesses = targetReachingHarnesses;

        this.taintStatus = TaintStatus.UNKNOWN;

        // Compute and store the hash
        this.mapHash = computeDistanceMapHash();
    }

    /**
     * Computes a simplified SHA-256 hash of the method signatures and distances.
     *
     * @return A hexadecimal string representation of the hash
     */
    private String computeDistanceMapHash() {
        try {
            // Create a map with method signatures and distances
            TreeMap<String, Integer> distanceMap = new TreeMap<>();
            for (SootMethod method : methodDistanceMap.getMethods()) {
                String signature = method.getSignature();
                // Store only the method signature and its distance
                distanceMap.put(signature.substring(1, signature.length()-1), methodDistanceMap.getDistance(method));
            }

            // Convert the sorted map to a string
            StringBuilder sb = new StringBuilder();
            for (Map.Entry<String, Integer> entry : distanceMap.entrySet()) {
                // Simple format: signature:distance|
                sb.append(entry.getKey()).append(":").append(entry.getValue()).append("|");
            }

            // Compute SHA-256 hash
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(sb.toString().getBytes());

            // Convert to hex string
            StringBuilder hexString = new StringBuilder();
            for (byte b : hash) {
                String hex = Integer.toHexString(0xff & b);
                if (hex.length() == 1) {
                    hexString.append('0');
                }
                hexString.append(hex);
            }
            return hexString.toString();
        } catch (NoSuchAlgorithmException e) {
            System.err.println(LOG_ERROR + "Error computing hash: " + e.getMessage());
            return "hash_computation_error";
        }
    }

    /**
     * Gets the method distance map for the target.
     *
     * @return The method distance map
     */
    public SootMethodDistanceMap getMethodDistanceMap() {
        return methodDistanceMap;
    }

    /**
     * Gets the map of methods to their basic block distances.
     *
     * @return Map of methods to basic block distances
     */
    public Map<SootMethod, BasicBlockDistance> getBasicBlockDistances() {
        return basicBlockDistances;
    }

    /**
     * Gets the target location.
     *
     * @return The target location
     */
    public TargetLocation getTargetLocation() {
        return targetLocation;
    }

    /**
     * Gets the list of harnesses that can reach the target.
     *
     * @return List of harnesses that can reach the target
     */
    public List<HarnessInfo> getTargetReachingHarnesses() {
        return targetReachingHarnesses;
    }

    /**
     * Gets the computed hash of the distance map.
     *
     * @return A hexadecimal string representation of the hash
     */
    public String getMapHash() {
        return mapHash;
    }

    /**
     * Gets the taint status of the target.
     *
     * @return The taint status
     */
    public TaintStatus getTaintStatus() {
        return taintStatus;
    }

    /**
     * Sets the taint status of the target.
     *
     * @param taintStatus The new taint status
     */
    public void setTaintStatus(TaintStatus taintStatus) {
        this.taintStatus = taintStatus;
    }
}
