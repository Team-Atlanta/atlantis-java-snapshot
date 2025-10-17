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

public final class ArithmeticOperations {

  public int method1(int a, int b) {
    return a + b;
  }

  public int method2(int a, int b) {
    int x = a;
    x = x + b;
    if (x == 104) {
      throw new TargetFoundException("SUCCESS".getBytes());
    }
    return a - b;
  }

  public int method3(int a, int b) {
    if (a > b) {
      return method1(a, b) * method2(a, b);
    } else {
      return a * b;
    }
  }

  public int method4(int a, int b) {
    if (b != 0) {
      return method2(a, b) / b; // Prevent division by zero
    } else {
      return a;
    }
  }

  public int method5(int a, int b) {
    return b == 0 ? a % (b + 1) : a % b; // Prevent modulus by zero
  }

  public int method6(int a, int b) {
    if (a % 2 == 0) {
      return method5(a, b) + 10;
    } else {
      return a - b;
    }
  }

  public int method7(int a, int b) {
    if ((a + b) % 2 == 0) {
      return method5(a, b) - method4(a, b);
    } else {
      return a + b;
    }
  }

  public int method8(int a, int b) {
    return (a > 0) ? method7(a, b) / (a + 1) : b; // Prevent division by zero
  }

  public int method9(int a, int b) {
    if (b > 1) {
      return method6(a, b) % b; // Prevent modulus by zero
    } else {
      return method3(a, b);
    }
  }

  public int method10(int a, int b) {
    if (a > b) {
      return method8(a, b) + b;
    } else {
      return method2(a, b) - method9(a, b);
    }
  }

  public int method11(int a, int b) {
    return a - method1(a, b);
  }

  public int method12(int a, int b) {
    if (a * b < 50) {
      return method11(a, b) * 3;
    } else {
      return method11(a, b) / 2;
    }
  }

  public int method13(int a, int b) {
    if (method12(a, b) != 0) {
      return method10(a, b) / method12(a, b); // Avoid division by zero
    } else {
      return a + b;
    }
  }

  public int method14(int a, int b) {
    if (a > 1 && b > 1) {
      return a * method13(a, b) - b;
    } else {
      return a + method4(a, b);
    }
  }

  public int method15(int a, int b) {
    if (method1(a, b) % 2 == 0) {
      return method5(a, b) + method14(a, b) - b;
    } else {
      return method8(a, b) * method11(a, b) + method6(a, b);
    }
  }

  public static void main(String[] args) {
    ArithmeticOperations ao = new ArithmeticOperations();
    int a = 5;
    int b = 3;
    System.out.println("Result of method1: " + ao.method1(a, b));
    System.out.println("Result of method2: " + ao.method2(a, b));
    System.out.println("Result of method3: " + ao.method3(a, b));
    System.out.println("Result of method4: " + ao.method4(a, b));
    System.out.println("Result of method5: " + ao.method5(a, b));
    System.out.println("Result of method6: " + ao.method6(a, b));
    System.out.println("Result of method7: " + ao.method7(a, b));
    System.out.println("Result of method8: " + ao.method8(a, b));
    System.out.println("Result of method9: " + ao.method9(a, b));
    System.out.println("Result of method10: " + ao.method10(a, b));
    System.out.println("Result of method11: " + ao.method11(a, b));
    System.out.println("Result of method12: " + ao.method12(a, b));
    System.out.println("Result of method13: " + ao.method13(a, b));
    System.out.println("Result of method14: " + ao.method14(a, b));
    System.out.println("Result of method15: " + ao.method15(a, b));
  }

  private static class TargetFoundException extends RuntimeException {
    TargetFoundException(byte[] input) {
      super(Arrays.toString(input));
    }
  }

  // Jazzer fuzz target for method15, takes byte array as input
  public static void fuzzerTestOneInput(byte[] input) {
    ArithmeticOperations ao = new ArithmeticOperations();
    if (input.length < 2) return;
    int a = input[0];
    int b = input[1];
    ao.method15(a, b);
  }
}
