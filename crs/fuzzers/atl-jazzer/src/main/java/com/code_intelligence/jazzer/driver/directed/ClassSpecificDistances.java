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

import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Class representing control flow distances for a specific class. This encapsulates the mapping of
 * coverage IDs to distances for a class, as well as the target-specific control flow distances for
 * that class. Each coverage ID is mapped to a ControlFlowDistance object containing block distance
 * and method call distance.
 */
public class ClassSpecificDistances {
  private final String className;
  private final Map<Integer, ControlFlowDistance> controlFlowDistances = new HashMap<>();
  private final Map<FuzzTarget, TargetSpecificDistances> targetSpecificDistances = new HashMap<>();

  /**
   * Creates a new ClassSpecificDistances instance.
   *
   * @param className The name of the class
   */
  public ClassSpecificDistances(String className) {
    this.className = className;
  }

  /**
   * Creates a new ClassSpecificDistances instance with pre-computed control flow distances.
   *
   * @param className The name of the class
   * @param controlFlowDistances The pre-computed control flow distances
   */
  public ClassSpecificDistances(
      String className, Map<Integer, ControlFlowDistance> controlFlowDistances) {
    this.className = className;
    if (controlFlowDistances != null) {
      this.controlFlowDistances.putAll(controlFlowDistances);
    }
  }

  /**
   * Gets the class name.
   *
   * @return The class name
   */
  public String getClassName() {
    return className;
  }

  /**
   * Gets the control flow distances map for the class.
   *
   * @return Map of coverage IDs to ControlFlowDistance objects
   */
  public Map<Integer, ControlFlowDistance> getEdgeDistances() {
    return controlFlowDistances;
  }

  /**
   * Gets the control flow distances for a specific target.
   *
   * @param target The target information
   * @return The TargetSpecificDistances for the target, or null if not found
   */
  public TargetSpecificDistances getTargetEdgeDistances(FuzzTarget target) {
    return targetSpecificDistances.get(target);
  }

  /**
   * Puts a control flow distance into the class-level map.
   *
   * @param coverageId The coverage ID
   * @param blockDistance The block distance value
   * @param methodCallDistance The method call distance value
   */
  public void putControlFlowDistance(int coverageId, int blockDistance, int methodCallDistance) {
    controlFlowDistances.put(
        coverageId, new ControlFlowDistance(blockDistance, methodCallDistance));
  }

  /**
   * Puts a control flow distance into the class-level map.
   *
   * @param coverageId The coverage ID
   * @param controlFlowDistance The ControlFlowDistance object containing both distance values
   */
  public void putControlFlowDistance(int coverageId, ControlFlowDistance controlFlowDistance) {
    controlFlowDistances.put(coverageId, controlFlowDistance);
  }

  /**
   * Gets the ControlFlowDistance for a coverage ID from the class-level map.
   *
   * @param coverageId The coverage ID
   * @return The ControlFlowDistance object, or null if not found
   */
  public ControlFlowDistance getControlFlowDistance(int coverageId) {
    return controlFlowDistances.get(coverageId);
  }

  /**
   * Checks if the class-level map contains a coverage ID.
   *
   * @param coverageId The coverage ID
   * @return True if the map contains the coverage ID, false otherwise
   */
  public boolean hasCoverageId(int coverageId) {
    return controlFlowDistances.containsKey(coverageId);
  }

  /**
   * Updates the class-level control flow distances by aggregating the target-level distances. For
   * each coverage ID, the minimum total distance across all targets is used. This method also
   * updates the internal target distances map.
   *
   * @param targetEdgeDistancesList List of target control flow distances to use for aggregation
   */
  public void updateFromTargets(List<TargetSpecificDistances> targetEdgeDistancesList) {
    // Clear the current class-level distances and target distances
    controlFlowDistances.clear();
    targetSpecificDistances.clear();

    // Add all target control flow distances to the map
    for (TargetSpecificDistances targetDistance : targetEdgeDistancesList) {
      targetSpecificDistances.put(targetDistance.getTarget(), targetDistance);
    }

    // Aggregate the target-level distances
    for (TargetSpecificDistances targetDistance : targetEdgeDistancesList) {
      Map<Integer, ControlFlowDistance> targetEdgeDistances = targetDistance.getEdgeDistances();
      for (Map.Entry<Integer, ControlFlowDistance> entry : targetEdgeDistances.entrySet()) {
        int coverageId = entry.getKey();
        ControlFlowDistance distance = entry.getValue();
        if (controlFlowDistances.containsKey(coverageId)) {
          // If we already have a distance for this edge, we take the minimum total distance
          ControlFlowDistance existingDistance = controlFlowDistances.get(coverageId);
          if (distance.getTotalDistance() < existingDistance.getTotalDistance()) {
            controlFlowDistances.put(coverageId, distance);
          }
        } else {
          controlFlowDistances.put(coverageId, distance);
        }
      }
    }
  }
}
