package com.ammaraskar.tracer.test;

/**
 * A test program to use as a candidate for tracing.
 */
public class Tracee {
    public static void main(String[] args) {
        fuzzerTestOneInput(null);
    }

    public static void fuzzerTestOneInput(byte[] input) {
        System.out.println("Hello World");

        Tracee tracee = new Tracee();
        tracee.innerFunction("Mufasa");
    }

    public void innerFunction(String x) {
        stuckHere(x);
    }

    public void stuckHere(String x) {
        if (x.startsWith("Hello")) {
            System.out.println("You win!");
        }
    }
}
