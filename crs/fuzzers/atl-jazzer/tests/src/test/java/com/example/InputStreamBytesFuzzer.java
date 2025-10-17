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

import com.code_intelligence.jazzer.api.FuzzerSecurityIssueLow;
import java.io.ByteArrayInputStream;

public class InputStreamBytesFuzzer {
  public static void fuzzerTestOneInput(byte[] data) {
    if (data.length < 1024) {
      return;
    }

    ByteArrayInputStream bis = new ByteArrayInputStream(data);
    int first = bis.read();
    bis.skip(120);
    int second = bis.read();
    bis.skip(300);
    int third = bis.read();
    bis.skip(40);
    int fourth = bis.read();
    if (first == 0xDE && second == 0xAD && third == 0xBE && fourth == 0xEF) {
      throw new FuzzerSecurityIssueLow("Found the secret message!");
    }
  }
}
