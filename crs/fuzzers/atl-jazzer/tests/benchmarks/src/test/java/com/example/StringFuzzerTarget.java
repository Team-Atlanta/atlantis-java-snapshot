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

package com.example;

// Simple String Fuzzer to check directed fuzzing
public final class StringFuzzerTarget {
  public static void secondStage(byte b) {
    int a = 5;

    if (a + b == 'X') {
      throw new StringFuzzer.StringFoundException("SUCCESS".getBytes());
    } else {
      a = 0;
    }
  }
}
