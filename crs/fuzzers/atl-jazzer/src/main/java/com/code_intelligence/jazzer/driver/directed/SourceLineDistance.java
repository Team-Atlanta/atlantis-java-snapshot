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

/**
 * Class representing a distance to a specific line in a file. This is used to track the distance to
 * target lines in the code.
 */
public class SourceLineDistance {
  private final String filePath;
  private final int lineNumber;
  private final double distance;

  /**
   * Creates a new SourceLineDistance instance.
   *
   * @param filePath The path to the file
   * @param lineNumber The line number in the file
   * @param distance The distance value
   */
  public SourceLineDistance(String filePath, int lineNumber, double distance) {
    this.filePath = filePath;
    this.lineNumber = lineNumber;
    this.distance = distance;
  }

  /**
   * Gets the file path.
   *
   * @return The file path
   */
  public String getFilePath() {
    return filePath;
  }

  /**
   * Gets the line number.
   *
   * @return The line number
   */
  public int getLineNumber() {
    return lineNumber;
  }

  /**
   * Gets the distance value.
   *
   * @return The distance value
   */
  public double getDistance() {
    return distance;
  }

  @Override
  public String toString() {
    return filePath + ":" + lineNumber + ":" + distance;
  }
}
