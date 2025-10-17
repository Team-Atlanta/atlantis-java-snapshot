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

import java.util.Arrays;

// Simple String Fuzzer to check directed fuzzing
public final class StringFuzzer {
  public static void fuzzerTestOneInput(byte[] input) {
    init();
    if (input == null) return;
    if (input.length < 31) return;

    if (input[0] != 'L') return;
    if (input[1] != 'E') return;
    if (input[2] != 'F') return;
    if (input[3] != 'T') return;
    if (input[4] != 'P') return;
    if (input[5] != 'A') return;
    if (input[6] != 'D') return;
    if (input[7] != 'D') return;
    if (input[8] != 'I') return;
    if (input[9] != 'N') return;
    if (input[10] != 'G') return;
    if (input[11] != 'S') return;
    if (input[12] != 'U') return;
    if (input[13] != 'C') return;
    if (input[14] != 'C') return;
    if (input[15] != 'E') return;
    if (input[16] != 'S') return;
    if (input[17] != 'S') return;
    if (input[18] != 'I') return;
    if (input[19] != 'S') return;
    if (input[20] != 'N') return;
    if (input[21] != 'O') return;
    if (input[22] != 'T') return;
    if (input[23] != 'A') return;
    if (input[24] != 'L') return;
    if (input[25] != 'W') return;
    if (input[26] != 'A') return;
    if (input[27] != 'Y') return;
    if (input[28] != 'S') return;
    if (input[29] != 'W') return;

    StringFuzzerTarget.secondStage(input[30]);
  }

  private static void init() {
    // System.out.println("init");
  }

  private static void success() {
    throw new StringFoundException("SUCCESS".getBytes());
  }

  public static class StringFoundException extends RuntimeException {
    StringFoundException(byte[] input) {
      super(Arrays.toString(input));
    }
  }
}
