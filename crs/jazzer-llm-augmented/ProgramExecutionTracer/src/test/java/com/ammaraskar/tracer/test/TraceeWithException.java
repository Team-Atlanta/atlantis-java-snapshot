package com.ammaraskar.tracer.test;

import java.io.IOException;

/**
 * A test program to use as a candidate for tracing.
 */
public class TraceeWithException {
    public static void main(String[] args) {
        fuzzerTestOneInput(null);
    }

    public static void fuzzerTestOneInput(byte[] input) {
        System.out.println("Hello World");
        callFunctions1();
    }

    public static void callFunctions1() {
        callFunctions2();
    }

    public static void callFunctions2() {
        callFunctions3();
    }

    public static void callFunctions3() {
        callFunctions4();
    }

    public static void callFunctions4() {
        TraceeWithException tracee = new TraceeWithException();
        tracee.innerFunction("xyz");
        tracee.functionThatThrows();
    }

    public void innerFunction(String x) {
        stuckHere(x);
    }

    public void functionThatThrows() {
        throw new IndexOutOfBoundsException("oops threw an exception");
    }

    public void stuckHere(String x) {
        if (x.startsWith("Hello")) {
            System.out.println("You win!");
        }
    }
}
