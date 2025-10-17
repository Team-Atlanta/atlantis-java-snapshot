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

package com.code_intelligence.jazzer.runtime;

/**
 * An event representing the hitting of a code marker within the Jazzer runtime.
 *
 * <p>This class extends {@link Throwable} to: 1) record crash stack; 2) leverage Jazzer's existing
 * funcs like stack trace based deduplication.
 */
public class CodeMarkerHitEvent extends Throwable {
  private final int markId;

  /**
   * Constructs a new {@code CodeMarkerHitEvent} with the specified marker ID.
   *
   * @param markId the unique identifier for the code marker
   */
  public CodeMarkerHitEvent(int markId) {
    super();
    this.markId = markId;
  }

  /**
   * Returns the marker ID associated with this event.
   *
   * @return the marker ID
   */
  public int getMarkId() {
    return markId;
  }
}
