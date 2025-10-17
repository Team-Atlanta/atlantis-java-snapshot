/*
 * Copyright 2025 Code Intelligence GmbH
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package com.code_intelligence.jazzer.driver.directed;

import static com.code_intelligence.jazzer.driver.directed.LogLabel.LOG_ERROR;
import static com.code_intelligence.jazzer.driver.directed.LogLabel.LOG_WARN;

import com.code_intelligence.jazzer.driver.Opt;
import com.code_intelligence.jazzer.instrumentor.CoverageRecorder;
import com.code_intelligence.jazzer.runtime.CoverageMap;
import com.code_intelligence.jazzer.utils.Log;
import java.io.File;
import java.io.IOException;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ThreadLocalRandom;
import java.util.stream.Collectors;

/**
 * Class for calculating the distance of a fuzzing input to targets. This class uses control flow
 * distances to determine how close a fuzzing input is to reaching targets.
 */
public class FuzzInputDistanceCalculator {
  private static final ControlFlowDistanceRegistry distanceRegistry =
      new ControlFlowDistanceRegistry();
  private static boolean inited = false;
  private static List<FuzzTarget> allTargets = null;
  private static Set<FuzzTarget> foundTargets = new HashSet<>();
  private static Set<FuzzTarget> scheduledNormalTargets = new HashSet<>();
  private static Set<FuzzTarget> scheduledPrioritizedTargets = new HashSet<>();
  private static Instant lastScheduleTime = null;
  private static long lastUpdateTime = 0;
  private static boolean newTargetFound = false;

  /**
   * Creates a new FuzzInputDistanceCalculator instance. Initializes the CodeAnalyzer if it hasn't
   * been initialized yet.
   */
  public FuzzInputDistanceCalculator() {
    if (!inited)
      synchronized (this.getClass()) {
        CodeAnalyzer.init(getClassPath());
        inited = true;
      }
  }

  /**
   * Gets the classpath for Soot analysis. Filters out Jazzer-related paths to avoid conflicts.
   *
   * @return The classpath string
   */
  private String getClassPath() {
    String instrumentedClassesDir = new File(Opt.dumpClassesDir.get()).toPath().toString();
    String classpath = System.getProperty("java.class.path");

    // Remove all paths that contain Jazzer classes
    classpath =
        Arrays.stream(classpath.split(File.pathSeparator))
            .filter(x -> !x.contains("/code_intelligence/"))
            .filter(x -> !x.contains("/jazzer/"))
            .filter(x -> !x.contains("soot"))
            .collect(Collectors.joining(File.pathSeparator));

    String result = instrumentedClassesDir + File.pathSeparator + classpath;
    Log.info("Using classpath for soot: " + result);
    return result;
  }

  /**
   * Loads targets from distance files.
   *
   * @param distancePath Path to the distance file or directory containing distance files
   * @return List of loaded FuzzTarget objects
   */
  private List<FuzzTarget> loadTargets(String distancePath) {
    long updateStartTime = System.currentTimeMillis();
    Log.info("Loading distance path: " + distancePath);
    List<FuzzTarget> loadedTargets = new ArrayList<>();

    // Check env variable FUZZ_TARGET_HARNESS for the harness name
    String harnessName = System.getenv("FUZZ_TARGET_HARNESS");

    // For every distance file, create a FuzzTarget object using the new fromDistanceFile method
    for (File distanceFile : getDistanceFiles(distancePath)) {
      try {
        // Create a FuzzTarget object for this target using the new method
        List<FuzzTarget> fuzzTargets = FuzzTarget.fromDistanceFile(distanceFile);
        for (FuzzTarget fuzzTarget : fuzzTargets) {
          if (!fuzzTarget.reachableFrom(harnessName) || !fuzzTarget.exploitableFrom(harnessName)) {
            continue;
          }
          loadedTargets.add(fuzzTarget);
          Log.info("Loaded target " + fuzzTarget + " from " + distanceFile.getAbsolutePath());
        }
      } catch (IOException exception) {
        Log.error(LOG_ERROR + "Error parsing distance file: " + exception.getMessage());
      }
    }

    int prioCount = (int) loadedTargets.stream().filter(FuzzTarget::prioritized).count();
    Log.info("Loaded overall " + loadedTargets.size() + " targets (" + prioCount + " prioritized)");

    lastUpdateTime = updateStartTime;
    return loadedTargets;
  }

  /**
   * Calculates the distance of the current fuzzing input to the targets. This method uses the
   * coverage information from the current execution to determine how close the fuzzing input is to
   * reaching the targets.
   *
   * @return The calculated distance, or -1.0 if no distance could be calculated
   */
  public synchronized double calculateDistanceToTargets(boolean corpusUpdate) {
    String distancePath = Opt.directedFuzzingDistances.get();

    // Load targets from distance files
    if (allTargets == null) {
      allTargets = loadTargets(distancePath);
      invokeScheduler();
      Log.info("Updated targets in the FuzzInputDistanceCalculator.");
    }

    // Get the execution trace of the input
    Set<Integer> featureIDSet = CoverageMap.getCoveredIds();
    Map<String, List<Integer>> edgeMapping = CoverageRecorder.getCoveredEdgeIdMapping(featureIDSet);

    List<Integer> distances = new ArrayList<>();
    for (Map.Entry<String, List<Integer>> entry : edgeMapping.entrySet()) {
      String className = entry.getKey();
      List<Integer> coveredEdges = entry.getValue();
      Log.debug("Edges covered in " + className + ": " + coveredEdges);

      // Consult the ControlFlowDistanceRegistry to get the mapping of coverage ids to distances for
      // this class
      Map<Integer, ControlFlowDistance> controlFlowDistanceMap =
          distanceRegistry.getDistancesForClass(className);

      for (FuzzTarget fuzzTarget : distanceRegistry.getTargets()) {
        if (distanceRegistry
            .getClassSpecificDistances(className)
            .getTargetEdgeDistances(fuzzTarget)
            .getEdgeDistances()
            .entrySet()
            .stream()
            .filter(e -> coveredEdges.contains(e.getKey()))
            .anyMatch(e -> e.getValue().getTotalDistance() == 0)) {
          Log.info("Found target, ignoring with next update: " + fuzzTarget + "");
          foundTargets.add(fuzzTarget);
          newTargetFound = true;
        }
      }

      // Calculate the distance from the controlFlowDistanceMap and the coveredEdges
      for (Integer coverageId : coveredEdges) {
        if (controlFlowDistanceMap.containsKey(coverageId)) {
          ControlFlowDistance controlFlowDistance = controlFlowDistanceMap.get(coverageId);
          distances.add(controlFlowDistance.getTotalDistance());
        }
      }
    }

    if (distances.isEmpty()) {
      Log.info("Unable to calculate fuzzing input distance: No distances found");

      return -1.0;
    }

    if (corpusUpdate) {
      lastScheduleTime = Instant.now();
    }

    double result = distances.stream().mapToDouble(Integer::doubleValue).average().orElse(-1.0);

    Log.info("Calculated fuzzing input distance: " + result);

    return result;
  }

  /**
   * Retrieves a list of distance files from the specified path.
   *
   * @param distancePath Path to the distance file or directory
   * @return A list of distance files
   */
  private static List<File> getDistanceFiles(String distancePath) {
    List<File> distanceFiles = new ArrayList<>();
    File path = new File(distancePath);
    if (path.isDirectory()) {
      File[] files = path.listFiles();
      if (files != null) {
        for (File file : files) {
          if (file.isFile()) {
            distanceFiles.add(file);
          }
        }
      }
    } else if (path.isFile()) {
      distanceFiles.add(path);
    }
    return distanceFiles;
  }

  /**
   * Resets the target caches if any distance file has been modified since the last update or if one
   * of the targets has been found.
   *
   * <p>This method gets called every 60 seconds (configurable via libfuzzer's -target_reload). If
   * it returns true, the entire corpus will be re-run to update the target distances.
   *
   * @return True if the target caches were reset, false otherwise
   */
  public synchronized boolean updateTargetConfigs() {
    boolean schedulingUpdateNeeded = false;

    if (newTargetFound) {
      Log.info("Recalculating target distances since some of the targets were reached.");
      newTargetFound = false;
      schedulingUpdateNeeded = true;
    }

    // Go through all the distance files and check if there is one that is newer than the last
    // update time
    String distancePath = Opt.directedFuzzingDistances.get();
    boolean targetFilesChanged = false;

    for (File distanceFile : getDistanceFiles(distancePath)) {
      if (distanceFile.lastModified() > lastUpdateTime) {
        Log.info(
            "Distance file "
                + distanceFile.getAbsolutePath()
                + " has changed, invalidating target info.");
        targetFilesChanged = true;
        break;
      }
    }

    if (targetFilesChanged) {
      try {
        allTargets = loadTargets(distancePath);
        schedulingUpdateNeeded = true;
      } catch (Exception e) {
        Log.error(LOG_WARN + "Error updating targets: " + e.getMessage());
      }
    }

    Set<FuzzTarget> allUnreachedTargets = new HashSet<>(allTargets);
    allUnreachedTargets.removeAll(foundTargets);

    if (!allUnreachedTargets.isEmpty()) {
      int scheduleIntervalMin = 30 * 15 / allUnreachedTargets.size();
      scheduleIntervalMin = Math.min(1, Math.max(5, scheduleIntervalMin));
      if (lastScheduleTime == null
          || Instant.now().isAfter(lastScheduleTime.plusSeconds(scheduleIntervalMin * 60))) {
        schedulingUpdateNeeded = true;
      }
    }

    if (schedulingUpdateNeeded) {
      // Update the scheduled targets
      schedulingUpdateNeeded = invokeScheduler();
    }

    return schedulingUpdateNeeded;
  }

  private boolean invokeScheduler() {
    Set<FuzzTarget> nextTargets = schedulerNext();

    if (!nextTargets.equals(distanceRegistry.getTargets())) {
      distanceRegistry.updateTargets(nextTargets);
      int prioCount = (int) nextTargets.stream().filter(FuzzTarget::prioritized).count();
      Log.info(
          "Scheduling " + nextTargets.size() + " directed targets (" + prioCount + " prioritized)");

      return true;
    }

    return false;
  }

  private Set<FuzzTarget> schedulerNext() {
    Set<FuzzTarget> allUnreachedTargets = new HashSet<>(allTargets);
    allUnreachedTargets.removeAll(foundTargets);

    if (allUnreachedTargets.size() <= 25) {
      return allUnreachedTargets;
    }

    // Find targets that haven't been scheduled yet in this round
    List<FuzzTarget> unscheduledNormalTargets = new ArrayList<>();
    List<FuzzTarget> unscheduledPrioritizedTargets = new ArrayList<>();
    for (FuzzTarget target : allUnreachedTargets) {
      if (target.prioritized() && !scheduledPrioritizedTargets.contains(target)) {
        unscheduledPrioritizedTargets.add(target);
      } else if (!scheduledNormalTargets.contains(target)) {
        unscheduledNormalTargets.add(target);
      }
    }

    // Round-robin scheduling: pick next 15 targets
    Set<FuzzTarget> nextTargets = new HashSet<>();
    int prioCount = 0;
    for (int i = 0; i < 15; i++) {
      // If we've added all unscheduled targets and still need more, start over
      if (unscheduledNormalTargets.isEmpty() && unscheduledPrioritizedTargets.isEmpty()) {
        // Reset and continue from beginning of allUnreachedTargets
        scheduledNormalTargets.clear();
        scheduledPrioritizedTargets.clear();

        unscheduledNormalTargets.clear();
        unscheduledPrioritizedTargets.clear();
        for (FuzzTarget target : allUnreachedTargets) {
          if (nextTargets.contains(target)) {
            continue;
          }
          if (target.prioritized()) {
            unscheduledPrioritizedTargets.add(target);
          } else {
            unscheduledNormalTargets.add(target);
          }
        }
      }

      FuzzTarget nextTarget = null;
      if (!unscheduledPrioritizedTargets.isEmpty()) {
        // Prefer prioritized targets first
        nextTarget =
            unscheduledPrioritizedTargets.get(
                ThreadLocalRandom.current().nextInt(unscheduledPrioritizedTargets.size()));
        unscheduledPrioritizedTargets.remove(nextTarget);
        scheduledPrioritizedTargets.add(nextTarget);
        prioCount++;
      } else if (!unscheduledNormalTargets.isEmpty()) {
        // If no prioritized targets, pick from normal targets
        nextTarget =
            unscheduledNormalTargets.get(
                ThreadLocalRandom.current().nextInt(unscheduledNormalTargets.size()));
        unscheduledNormalTargets.remove(nextTarget);
        scheduledNormalTargets.add(nextTarget);
      }

      if (nextTarget == null) {
        // This is impossible
        System.err.println(LOG_ERROR + "No next target found, this should never happen.");
        continue;
      }

      // Add it to nextTargets
      nextTargets.add(nextTarget);
    }

    Log.info("Scheduler picked " + prioCount + " prioritized targets");

    lastScheduleTime = Instant.now();
    return nextTargets;
  }
}
