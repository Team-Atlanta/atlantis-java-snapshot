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

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.Arrays;

// Simple Byte Array Fuzzer to check directed fuzzing
public final class ByteArrayFuzzer {
  public static void fuzzerTestOneInput(byte[] input) {
    init();

    // Call readAndVerifyBytes with the input
    try {
      readAndVerifyBytes(
          new InputStream() {
            int index = 0;

            @Override
            public int read() {
              if (index >= input.length) {
                return -1;
              }
              return input[index++];
            }
          },
          new BinaryConstant("myPNGhdr".getBytes()),
          "Invalid input");

      // If no exception, call success
      success();
    } catch (IOException e) {
      // e.printStackTrace();
    } catch (IllegalArgumentException e) {
      // e.printStackTrace();
    }
  }

  private static void readAndVerifyBytes(
      final InputStream is, final BinaryConstant expected, final String exception)
      throws IOException {
    for (int i = 0; i < expected.size(); i++) {
      final int data = is.read();
      final byte b = (byte) (0xff & data);

      if (data < 0) {
        throw new IllegalArgumentException("Unexpected EOF.");
      }

      if (b != expected.get(i)) {
        throw new IllegalArgumentException(exception);
      }
    }
  }

  private static void init() {
    // System.out.println("init");
  }

  private static void success() {
    throw new ByteArrayFoundException("SUCCESS".getBytes());
  }

  public static class ByteArrayFoundException extends RuntimeException {
    ByteArrayFoundException(byte[] input) {
      super(Arrays.toString(input));
    }
  }

  private static class BinaryConstant {
    private final byte[] value;

    public BinaryConstant(final byte[] value) {
      this.value = value.clone();
    }

    public boolean equals(final byte[] bytes) {
      return Arrays.equals(value, bytes);
    }

    @Override
    public boolean equals(final Object obj) {
      if (obj == null) {
        return false;
      }
      if (!(obj instanceof BinaryConstant)) {
        return false;
      }
      final BinaryConstant other = (BinaryConstant) obj;
      return equals(other.value);
    }

    public byte get(final int i) {
      return value[i];
    }

    @Override
    public int hashCode() {
      return Arrays.hashCode(value);
    }

    public int size() {
      return value.length;
    }

    public void writeTo(final OutputStream os) throws IOException {
      for (final byte element : value) {
        os.write(element);
      }
    }
  }
}
