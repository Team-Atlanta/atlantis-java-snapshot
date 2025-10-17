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
import java.util.Map;

/**
 * Class representing control flow distances for a combination of a target and a class. This
 * encapsulates the mapping of coverage IDs to distances for that particular target. Each coverage
 * ID is mapped to a ControlFlowDistance object containing block distance and method call distance.
 */
public class TargetSpecificDistances {
  private final String className;
  private final FuzzTarget target;
  private final Map<Integer, ControlFlowDistance> controlFlowDistances = new HashMap<>();

  /**
   * Creates a new TargetSpecificDistances instance.
   *
   * @param className The name of the class
   * @param target The target information
   */
  public TargetSpecificDistances(String className, FuzzTarget target) {
    this.className = className;
    this.target = target;
  }

  /**
   * Creates a new TargetSpecificDistances instance with pre-computed control flow distances.
   *
   * @param className The name of the class
   * @param target The target information
   * @param controlFlowDistances The pre-computed control flow distances
   */
  public TargetSpecificDistances(
      String className, FuzzTarget target, Map<Integer, ControlFlowDistance> controlFlowDistances) {
    this.className = className;
    this.target = target;
    this.controlFlowDistances.putAll(controlFlowDistances);
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
   * Gets the target information.
   *
   * @return The target information
   */
  public FuzzTarget getTarget() {
    return target;
  }

  /**
   * Gets the control flow distances map.
   *
   * @return Map of coverage IDs to ControlFlowDistance objects
   */
  public Map<Integer, ControlFlowDistance> getEdgeDistances() {
    return controlFlowDistances;
  }

  /**
   * Puts a control flow distance into the map.
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
   * Puts a control flow distance into the map.
   *
   * @param coverageId The coverage ID
   * @param controlFlowDistance The ControlFlowDistance object containing both distance values
   */
  public void putControlFlowDistance(int coverageId, ControlFlowDistance controlFlowDistance) {
    controlFlowDistances.put(coverageId, controlFlowDistance);
  }

  /**
   * Gets the total distance (sum of block and method call distances) for a coverage ID.
   *
   * @param coverageId The coverage ID
   * @return The total distance value, or null if not found
   */
  public Integer getTotalDistanceForId(int coverageId) {
    ControlFlowDistance distance = controlFlowDistances.get(coverageId);
    return distance != null ? distance.getBlockDistance() + distance.getMethodCallDistance() : null;
  }

  /**
   * Checks if the map contains a coverage ID.
   *
   * @param coverageId The coverage ID
   * @return True if the map contains the coverage ID, false otherwise
   */
  public boolean hasCoverageId(int coverageId) {
    return controlFlowDistances.containsKey(coverageId);
  }
}
