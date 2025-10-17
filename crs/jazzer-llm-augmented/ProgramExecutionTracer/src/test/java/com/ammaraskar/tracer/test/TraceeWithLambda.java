package com.ammaraskar.tracer.test;

import java.util.stream.Stream;

public class TraceeWithLambda {
    public static void main(String[] args) {
        fuzzerTestOneInput(null);
    }

    public static void fuzzerTestOneInput(byte[] input) {
        System.out.println("Hello World");

        Stream.of(true).forEach(TraceeWithLambda::functionCalledByLambda);
    }

    private static void functionCalledByLambda(boolean x) {
    }

}
