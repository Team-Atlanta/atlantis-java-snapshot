package org.gts3.atlantis.staticanalysis;

import java.io.FileReader;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.time.Instant;
import java.util.*;
import java.util.stream.Collectors;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import org.gts3.atlantis.staticanalysis.taint.TaintStatus;
import soot.Scene;
import soot.SootMethod;

import soot.jimple.toolkits.callgraph.CallGraph;

import static org.gts3.atlantis.staticanalysis.utils.LogLabel.LOG_ERROR;
import static org.gts3.atlantis.staticanalysis.utils.LogLabel.LOG_WARN;
import static org.gts3.atlantis.staticanalysis.utils.StatUtils.getMaxRssKB;
import static org.gts3.atlantis.staticanalysis.utils.StatUtils.formatMemorySize;

/**
 * Main entry point for the static analysis application. This class processes command-line arguments,
 * builds call graphs, analyzes target methods, and generates distance maps for fuzzing targets.
 *
 * The application performs static analysis on Java bytecode using the Soot framework to identify
 * reachable methods and calculate distances between methods in the call graph.
 */
public class Main {
    private static final Instant START_TIME = Instant.now();

    /**
     * The main entry point of the application.
     *
     * @param args Command-line arguments for the application, which are parsed by ArgumentParser
     */
    public static void main(String[] args) {
        ArgumentParser argumentParser = parseArguments(args);
        if (argumentParser == null) {
            return; // Error occurred during argument parsing
        }

        // Try to restore cached result early if cache is available
        if (argumentParser.getCacheDir() != null && argumentParser.getDistanceMapOutputFile() != null) {
            boolean cacheRestored = ResultCache.tryRestoreFromCache(
                argumentParser.getCacheDir(),
                argumentParser.getDistanceMapOutputFile()
            );
            if (cacheRestored) {
                System.out.println("Cache restored successfully, continuing with analysis");
            }
        }

        List<ArgumentParser.CGConfig> cgConfigs = argumentParser.getCGConfigs();
        System.out.println("Running analysis for " + cgConfigs.size() + " configurations: " +
                           cgConfigs.stream().map(Object::toString).collect(Collectors.joining(", ")));

        // Main analysis loop
        SootAnalysis sootAnalysis = null;
        Set<TargetLocationSpec> sarifSinkpoints = new HashSet<>();
        Set<TargetLocation> reachedLocations = new HashSet<>();
        int i = 0;
        int phaseCount = cgConfigs.size();
        Map<Path, Instant> lastExternalUpdate = new HashMap<>();
        while (true) {
            boolean targetUpdateNeeded = false;
            if (!cgConfigs.isEmpty()) {
                ArgumentParser.CGConfig config = cgConfigs.remove(0);
                System.out.println("\n[Configuration " + (i + 1) + "/" + phaseCount + "] " + config);

                // Close the previous SootAnalysis instance if it exists
                if (sootAnalysis != null) {
                    System.out.println("Closing previous SootAnalysis instance");
                    sootAnalysis.close();
                }

                // Create a new SootAnalysis instance with the current configuration
                sootAnalysis = new SootAnalysis(
                        argumentParser.getCpName(),
                        argumentParser.getAllClasspaths(),
                        argumentParser.getHarnesses().values(),
                        argumentParser.getPkgList(),
                        config.getLevel(),
                        config.isRta()
                );
                targetUpdateNeeded = true;
            } else {
                if (argumentParser.isServerMode()) {
                    System.out.println("[Server mode] Waiting for CG or sinkpoint update");
                    waitForExternalUpdate(argumentParser.externalInputFiles(), lastExternalUpdate);
                } else {
                    break;
                }
            }

            // If input call graph files are provided, load and merge them with the current analysis
            List<Path> inputCallGraphFiles = argumentParser.getInputCallGraphFiles();
            if (inputCallGraphFiles != null && !inputCallGraphFiles.isEmpty()) {
                targetUpdateNeeded |= loadAndMergeExternalCGs(inputCallGraphFiles, sootAnalysis, lastExternalUpdate);
            }

            // If an output call graph file is provided, save the call graph to that file
            if (targetUpdateNeeded && argumentParser.getOutputCallGraphFile() != null) {
                saveOutputCG(argumentParser, sootAnalysis);
            }

            // Re-load the global sinkpoints if needed
            if (argumentParser.getSarifSinkpointsFile() != null) {
                Set<TargetLocationSpec> reachedLocationSpecs = new HashSet<>();
                targetUpdateNeeded |= updateSarifSinkpoints(argumentParser.getSarifSinkpointsFile(), sarifSinkpoints,
                        reachedLocationSpecs, lastExternalUpdate);
                int prevReachedCount = reachedLocations.size();
                for (TargetLocationSpec targetLocationSpec : reachedLocationSpecs) {
                    reachedLocations.addAll(targetLocationSpec.toTargetLocations(sootAnalysis.getCallGraph()));
                }
                targetUpdateNeeded |= prevReachedCount != reachedLocations.size();
            }

            if (!targetUpdateNeeded) {
                System.out.println("No target update needed, skipping");
                continue;
            }

            ArrayList<TargetLocationSpec> allSinkpoints = new ArrayList<>(argumentParser.getTargets());
            allSinkpoints.addAll(sarifSinkpoints);
            List<TargetLocation> targetLocations = convertTargetSpecs(
                allSinkpoints,
                sootAnalysis.getCallGraph()
            );

            Set<TargetLocation> filteredTargetLocations = new HashSet<>(targetLocations);
            filteredTargetLocations.removeAll(reachedLocations);

            List<FuzzTargetData> allFuzzTargetData = processAllTargets(
                filteredTargetLocations.stream().toList(),
                sootAnalysis.getCallGraph(),
                argumentParser.isIncludeCfg(),
                argumentParser.getHarnesses().values()
            );

            sootAnalysis.runTaintAnalysis(allFuzzTargetData);

            if (allFuzzTargetData.isEmpty()) {
                System.out.println(LOG_WARN + "No valid targets found");
                continue; // Skip to the next configuration
            }

            List<FuzzTargetData> possiblyTaintedFuzzTargetData = allFuzzTargetData.stream().filter(t -> t.getTaintStatus() != TaintStatus.NOT_TAINTED).toList();
            System.out.println("Possibly tainted fuzz targets: " + possiblyTaintedFuzzTargetData.size() + " out of " + allFuzzTargetData.size());

            Set<SootMethod> allMappedMethods = collectAllMappedMethods(allFuzzTargetData);

            // Save results for this configuration, overwriting any previous results
            serializeAndSaveResults(
                allFuzzTargetData,
                allMappedMethods,
                argumentParser.isIncludeDistanceMap(),
                argumentParser.getDistanceMapOutputFile(),
                argumentParser.getCacheDir()
            );

            Duration executedTime = Duration.between(START_TIME, Instant.now()).abs();
            long maxRssKB = getMaxRssKB();
            System.out.println("Completed analysis for current configuration (overall time: " + executedTime.getSeconds() + "s, max RSS: " + formatMemorySize(maxRssKB) + ")");
            i++;
        }
    }

    /**
     * Parses command-line arguments and initializes the ArgumentParser.
     *
     * @param args Command-line arguments for the application
     * @return Initialized ArgumentParser or null if an error occurred
     */
    private static ArgumentParser parseArguments(String[] args) {
        try {
            ArgumentParser argumentParser = new ArgumentParser(args);
            return argumentParser;
        } catch (IOException e) {
            System.err.println(LOG_WARN + "Error reading config file: " + e.getMessage());
            return null;
        } catch (IllegalArgumentException e) {
            System.err.println(LOG_ERROR + "Argument error: " + e.getMessage());
            return null;
        }
    }

    /**
     * Converts TargetLocationSpec objects to TargetLocation objects.
     *
     * @param targetMethodSpecs List of target method specifications
     * @param callGraph The call graph of the analyzed program
     * @return List of TargetLocation objects
     */
    private static List<TargetLocation> convertTargetSpecs(
            List<TargetLocationSpec> targetMethodSpecs,
            CallGraph callGraph) {
        List<TargetLocation> targetMethods = new ArrayList<>();
        for (TargetLocationSpec targetLocationSpec : targetMethodSpecs) {
            targetMethods.addAll(targetLocationSpec.toTargetLocations(callGraph));
        }
        return targetMethods;
    }

    /**
     * Processes all target locations and collects fuzzing target data.
     *
     * @param targetMethods List of target locations to process
     * @param callGraph The call graph on which to calculate distances
     * @param includeCfg Whether to include control flow graph information
     * @param harnesses Collection of harness information
     * @return List of FuzzTargetData for all successfully processed targets
     */
    private static List<FuzzTargetData> processAllTargets(
            List<TargetLocation> targetMethods,
            CallGraph callGraph,
            boolean includeCfg,
            Collection<HarnessInfo> harnesses) {
        List<FuzzTargetData> allFuzzTargetData = new ArrayList<>();

        for (TargetLocation targetLocation : targetMethods) {
            try {
                FuzzTargetData targetData = processTarget(targetLocation, callGraph, includeCfg, harnesses);
                if (targetData != null) {
                    allFuzzTargetData.add(targetData);
                }
            } catch (Exception e) {
                System.out.println(LOG_WARN + "Error processing target " + targetLocation + ": " + e.getMessage());
            }
        }

        return allFuzzTargetData;
    }

    /**
     * Collects all mapped methods from the target data.
     *
     * @param targetData List of fuzzing target data
     * @return Set of all mapped SootMethod objects
     */
    private static Set<SootMethod> collectAllMappedMethods(List<FuzzTargetData> targetData) {
        return targetData.stream()
            .flatMap(data -> data.getMethodDistanceMap().getMethods().stream())
            .distinct()
            .sorted(Comparator.comparing(SootMethod::getSignature))
            .collect(Collectors.toCollection(LinkedHashSet::new));
    }

    /**
     * Serializes and saves the results to a file if an output file is specified.
     * Also saves the results to cache if a cache directory is provided.
     *
     * @param targetData List of fuzzing target data
     * @param allMappedMethods Set of all mapped methods
     * @param includeDistanceMap Whether to include distance map in serialized data
     * @param outputFile Path to the output file, or null if no output is needed
     * @param cacheDir Path to the cache directory, or null if caching is disabled
     */
    private static void serializeAndSaveResults(
            List<FuzzTargetData> targetData,
            Set<SootMethod> allMappedMethods,
            boolean includeDistanceMap,
            Path outputFile,
            Path cacheDir) {
        if (outputFile == null) {
            System.out.println(LOG_WARN + "Target output file not provided, not saving target specifications");
            return;
        }

        List<Map<String, Object>> serializedTargetData = targetData.stream()
            .map(data -> DistanceDataSerializer.createTargetData(data, allMappedMethods, includeDistanceMap))
            .toList();

        if (serializedTargetData.isEmpty()) {
            System.out.println(LOG_WARN + "No serialized target data, not saving target specifications");
            return;
        }

        String jsonContent = DistanceDataSerializer.serializeJsonDataWithMethodsToFile(
                outputFile,
                serializedTargetData,
                allMappedMethods
        );

        System.out.println("Saved method distance maps for "
                + serializedTargetData.size() + " targets to " + outputFile);

        // Save to cache if both cache directory and content are available
        if (cacheDir != null && jsonContent != null) {
            ResultCache.saveToCache(cacheDir, jsonContent);
        }
    }

    /**
     * Processes a target location to generate fuzzing target data.
     *
     * This method analyzes a target method, calculates method distances in the call graph,
     * optionally includes control flow graph information, and identifies harnesses that can reach the target.
     *
     * @param targetLocation The target location to process
     * @param callGraph The call graph of the program
     * @param includeCfg Whether to include control flow graph information
     * @param harnesses Collection of harness information
     * @return FuzzTargetData containing distance information, or null if the target is not reachable
     */
    private static FuzzTargetData processTarget(TargetLocation targetLocation, CallGraph callGraph, boolean includeCfg,
            Collection<HarnessInfo> harnesses) {
        if (!Scene.v().containsClass(targetLocation.getClassSignature())) {
            System.err.println(LOG_WARN + "Target " + targetLocation.getClassSignature() + " not reachable, "
                    + "not saving distance data.");
            return null;
        }

        SootMethod targetMethod = targetLocation.getSootMethod();
        SootMethodDistanceMap sootMethodDistanceMap = new SootMethodDistanceMap(callGraph, targetMethod);
        //sootMethodDistanceMap.printMethodDistanceMap();

        if (!sootMethodDistanceMap.containsApplicationMethod()) {
            System.err.println(LOG_WARN + "No application method reaches " +
                targetMethod.getSignature() + ", not saving distance data (" +
                sootMethodDistanceMap.getMethods().size() + " methods).");
            return null;
        }

        Map<SootMethod, BasicBlockDistance> basicBlockDistances = new HashMap<>();
        if (includeCfg) {
            basicBlockDistances = new HashMap<>();
            for (SootMethod method : sootMethodDistanceMap.getMethods()) {
                BasicBlockDistance basicBlockDistance = new BasicBlockDistance(sootMethodDistanceMap, method,
                        targetLocation);

                basicBlockDistances.put(method, basicBlockDistance);
            }

            // For debugging
            //basicBlockDistance.printBlockDistanceMap();
        }

        // Get the list of all harnesses that can trigger this target location
        List<HarnessInfo> targetReachingHarnesses = getTargetReachingHarnesses(sootMethodDistanceMap, harnesses);

        // Return the target data for potential inclusion in the combined file
        return new FuzzTargetData(sootMethodDistanceMap, basicBlockDistances, targetLocation, targetReachingHarnesses);
    }

    /**
     * Identifies harnesses that can reach the target method.
     *
     * @param methodDistanceMap The method distance map for the target
     * @param harnesses Collection of all available harnesses
     * @return List of harnesses that can reach the target method
     */
    private static List<HarnessInfo> getTargetReachingHarnesses(MethodDistanceMap methodDistanceMap,
            Collection<HarnessInfo> harnesses) {
        return harnesses.stream()
            .filter(h -> {
                List<SootMethod> methods = h.getSootMethods();
                // Include harness if any of its methods have a distance
                return methods.stream().anyMatch(methodDistanceMap::hasDistance);
            })
            .toList();
    }

    /**
     * Waits for an update to any of the external input files in server mode.
     *
     * This method monitors the specified input files for changes.
     * It will wait until either:
     * 1. Any file exists and this is the first check (lastExternalUpdate entry is null)
     * 2. Any file has been modified since the last time it was loaded
     *
     * @param externalInputFile List of paths to input files to monitor
     * @param lastExternalUpdate Map containing timestamp of the last update for each file
     * @return true if waiting completed successfully, false if an error occurred
     */
    private static boolean waitForExternalUpdate(List<Path> externalInputFile, Map<Path, Instant> lastExternalUpdate) {
        if (externalInputFile == null || externalInputFile.isEmpty()) {
            System.err.println(LOG_WARN + "No input call graph files to monitor");
            return false;
        }

        while (true) {
            try {
                Thread.sleep(1000);

                boolean anyFileUpdated = false;

                for (Path inputFile : externalInputFile) {
                    if (!Files.exists(inputFile)) {
                        continue;
                    }

                    Instant fileUpdateTime = Files.getLastModifiedTime(inputFile).toInstant();
                    if (lastExternalUpdate.get(inputFile) == null ||
                            lastExternalUpdate.get(inputFile).isBefore(fileUpdateTime)) {
                        anyFileUpdated = true;
                        break;
                    }
                }

                if (anyFileUpdated) {
                    break;
                }
            } catch (IOException e) {
                System.err.println(LOG_WARN + "Failed to wait for external update: " + e.getMessage());
            } catch (InterruptedException e) {
                System.err.println(LOG_WARN + "Sleep failed while waiting for external update: " + e.getMessage());
            }
        }
        return true;
    }

    /**
     * Loads and merges multiple external call graphs with the current analysis.
     * <p>
     * This method loads call graphs from the specified files and merges them with
     * the current SootAnalysis instance.
     *
     * @param inputCallGraphFiles List of paths to the input call graph files
     * @param sootAnalysis        The current SootAnalysis instance to merge with
     * @param lastExternalUpdate  The time of the last update
     * @return True if the call graph was updated
     */
    private static boolean loadAndMergeExternalCGs(List<Path> inputCallGraphFiles, SootAnalysis sootAnalysis,
                                                   Map<Path, Instant> lastExternalUpdate) {
        if (inputCallGraphFiles == null || inputCallGraphFiles.isEmpty()) {
            System.err.println(LOG_WARN + "No input call graph files to load");
            return false;
        }

        boolean updated = false;
        int successCount = 0;
        int totalCount = inputCallGraphFiles.size();

        for (Path inputCallGraphFile : inputCallGraphFiles) {
            try {
                if (!Files.exists(inputCallGraphFile)) {
                    System.out.println("Skipping non-existent CG file: " + inputCallGraphFile);
                    continue;
                }

                System.out.println("Checking call graph from " + inputCallGraphFile);
                CallGraphJson inputCallGraph = new CallGraphJson(inputCallGraphFile);

                // Only merge if new
                Instant creationTime = inputCallGraph.getCreationTime();
                Instant lastUpdate = lastExternalUpdate.get(inputCallGraphFile);
                if (lastUpdate == null || (creationTime != null && creationTime.isAfter(lastUpdate))) {
                    sootAnalysis.mergeCallGraph(inputCallGraph);

                    System.out.println("Successfully merged call graph from " + inputCallGraphFile);
                    lastExternalUpdate.put(inputCallGraphFile, creationTime);

                    updated = true;
                    successCount++;
                }
            } catch (Exception e) {
                System.err.println(LOG_WARN + "Error loading call graph from " +
                    inputCallGraphFile + ": " + e.getMessage());
            }
        }

        if (successCount > 0) {
            System.out.println("Successfully merged " + successCount + " out of " + totalCount + " call graph files");
            sootAnalysis.printSceneStats();
            return updated;
        } else {
            System.err.println("Failed to load any call graph files");
            return false;
        }
    }

    /**
     * Saves the current call graph to an output file.
     *
     * This method converts the current SootAnalysis call graph to a JSON format
     * and saves it to the specified output file.
     *
     * @param argumentParser The argument parser containing output file information
     * @param sootAnalysis The current SootAnalysis instance containing the call graph to save
     */
    private static void saveOutputCG(ArgumentParser argumentParser, SootAnalysis sootAnalysis) {
        try {
            System.out.println("Saving call graph to " + argumentParser.getOutputCallGraphFile());
            CallGraphJson outputCallGraph = sootAnalysis.convertToCallGraphJson();
            outputCallGraph.saveToFile(argumentParser.getOutputCallGraphFile());
            System.out.println("Successfully saved call graph to " + argumentParser.getOutputCallGraphFile());
        } catch (IOException e) {
            System.err.println(LOG_WARN + "Error saving call graph to " +
                argumentParser.getOutputCallGraphFile() + ": " + e.getMessage());
        }
    }

    /**
     * Updates the list of SARIF sinkpoint targets from the sinkpoints json file.
     */
    private static boolean updateSarifSinkpoints(Path sinkpointsFile,
            Set<TargetLocationSpec> sarifSinkpoints, Set<TargetLocationSpec> reachedLocationSpecs,
            Map<Path, Instant> lastExternalUpdate) {
        int prevSinkpointCount = sarifSinkpoints.size();

        if (!sinkpointsFile.toFile().exists()) {
            return false;
        }

        Instant fileUpdateTime = null;
        try {
            fileUpdateTime = Files.getLastModifiedTime(sinkpointsFile).toInstant();
        } catch (IOException e) {
            System.err.println(LOG_WARN + "Error loading sinkpoints from " +
                    sinkpointsFile + ": " + e.getMessage());
            return false;
        }
        Instant lastUpdate = lastExternalUpdate.get(sinkpointsFile);
        if (fileUpdateTime == null || lastUpdate != null && !fileUpdateTime.isAfter(lastUpdate)) {
            System.out.println("Sinkpoints file not updated");
            return false;
        }

        // Load from sinkpoints file
        int parseFails = 0;
        try (FileReader reader = new FileReader(sinkpointsFile.toFile())) {
            JsonArray sinkpointData = JsonParser.parseReader(reader).getAsJsonArray();
            for (JsonElement jsonElement : sinkpointData) {
                try {
                    JsonObject jsonObject = jsonElement.getAsJsonObject();
                    boolean reached = jsonObject.get("reached").getAsBoolean();
                    boolean exploited = jsonObject.get("exploited").getAsBoolean();

                    boolean inDiff = jsonObject.get("in_diff").getAsBoolean();
                    boolean sarifTarget = !jsonObject.get("sarif_reports").getAsJsonArray().isEmpty();

                    Map<String, Boolean> anaReachability = jsonObject.get("ana_reachability")
                            .getAsJsonObject()
                            .entrySet()
                            .stream()
                            .collect(Collectors.toMap(
                                    Map.Entry::getKey,
                                    entry -> entry.getValue().getAsBoolean()
                                    ));
                    Map<String, Boolean> anaExploitability = jsonObject.get("ana_exploitability")
                            .getAsJsonObject()
                            .entrySet()
                            .stream()
                            .collect(Collectors.toMap(
                                    Map.Entry::getKey,
                                    entry -> entry.getValue().getAsBoolean()
                                    ));

                    JsonObject coordObject = jsonObject.get("coord").getAsJsonObject();

                    if (!coordObject.has("class_name")
                            || !coordObject.has("method_name")
                            || !coordObject.has("method_desc")) {
                        continue;
                    }


                    String fileName = coordObject.has("file_name") && !coordObject.get("file_name").isJsonNull()
                            ? coordObject.get("file_name").getAsString()
                            : null;

                    int lineNum = coordObject.has("line_num") && !coordObject.get("line_num").isJsonNull()
                            ? coordObject.get("line_num").getAsInt()
                            : -1;

                    int bytecodeOffset = coordObject.has("bytecode_offset") && !coordObject.get("bytecode_offset").isJsonNull()
                            ? coordObject.get("bytecode_offset").getAsInt()
                            : -1;

                    String markDesc = coordObject.has("mark_desc") && !coordObject.get("mark_desc").isJsonNull()
                            ? coordObject.get("mark_desc").getAsString()
                            : null;

                    TargetLocationSpec targetLocationSpec = coordObject.get("method_name").isJsonNull() || coordObject.get("method_desc").isJsonNull()
                        ? new LineTargetLocationSpec(
                                coordObject.get("class_name").getAsString(),
                                lineNum,
                                markDesc,
                                inDiff,
                                sarifTarget,
                                anaReachability,
                                anaExploitability,
                                reached,
                                exploited
                        )
                        : new CoordinateTargetLocationSpec(
                                coordObject.get("class_name").getAsString(),
                                coordObject.get("method_name").getAsString(),
                                coordObject.get("method_desc").getAsString(),
                                fileName,
                                lineNum,
                                bytecodeOffset,
                                markDesc,
                                inDiff,
                                sarifTarget,
                                anaReachability,
                                anaExploitability,
                                reached,
                                exploited
                        );

                    if (reached || exploited) {
                        reachedLocationSpecs.add(targetLocationSpec);
                    } else {
                        sarifSinkpoints.add(targetLocationSpec);
                    }
                } catch (Exception e) {
                    System.err.println(LOG_WARN + "Failed to parse json sinkpoint: " + e.getMessage());
                    e.printStackTrace();
                    parseFails++;
                }
            }
        } catch (Exception e) {
            System.err.println(LOG_WARN + "Failed to parse json sinkpoint file: " + e.getMessage());
            e.printStackTrace();
            return false;
        }

        if (parseFails > 0) {
            System.out.println("Failed to parse " + parseFails + " sinkpoints");
        }

        // Update lastExternalUpdate timestamp
        lastExternalUpdate.put(sinkpointsFile, fileUpdateTime);

        System.out.println("Updated SARIF sinkpoints (before: " + prevSinkpointCount + ", after: "
                + sarifSinkpoints.size() + ") and reached locations (found " + reachedLocationSpecs.size() + ")");
        return prevSinkpointCount != sarifSinkpoints.size();
    }
}
