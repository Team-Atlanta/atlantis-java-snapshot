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

/** Class representing a tuple of block distance and method call distance. */
public class ControlFlowDistance {
  private final int blockDistance;
  private final int methodCallDistance;

  /**
   * Creates a new ControlFlowDistance instance.
   *
   * @param blockDistance The block distance (previously intraMethodDistance)
   * @param methodCallDistance The method call distance (previously methodDistance)
   */
  public ControlFlowDistance(int blockDistance, int methodCallDistance) {
    this.blockDistance = blockDistance;
    this.methodCallDistance = methodCallDistance;
  }

  /**
   * Gets the block distance.
   *
   * @return The block distance
   */
  public int getBlockDistance() {
    return blockDistance;
  }

  /**
   * Gets the method call distance.
   *
   * @return The method call distance
   */
  public int getMethodCallDistance() {
    return methodCallDistance;
  }

  /**
   * Gets the total distance (sum of block and method call distances).
   *
   * @return The total distance
   */
  public int getTotalDistance() {
    return blockDistance + methodCallDistance;
  }
}
