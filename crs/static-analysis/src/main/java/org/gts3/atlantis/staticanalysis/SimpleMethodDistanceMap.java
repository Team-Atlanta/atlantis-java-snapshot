package org.gts3.atlantis.staticanalysis;

import java.util.HashMap;
import java.util.Map;

import soot.SootMethod;

/**
 * A simple implementation of MethodDistanceMap that uses a pre-computed map of method signatures to distances.
 */
public class SimpleMethodDistanceMap implements MethodDistanceMap {
    private final String targetMethod;
    private final Map<String, Integer> methodDistanceMap = new HashMap<>();

    /**
     * Creates a new SimpleMethodDistanceMap with the given target method and distance map.
     *
     * @param targetMethod the target method
     * @param signatureDistanceMap a map of method signatures to distances
     */
    public SimpleMethodDistanceMap(String targetMethod, Map<String, Integer> signatureDistanceMap) {
        this.targetMethod = targetMethod;
        this.methodDistanceMap.putAll(signatureDistanceMap);
    }

    /**
     * {@inheritDoc}
     *
     * This implementation checks if the method's signature is in the pre-computed distance map.
     */
    @Override
    public boolean hasDistance(SootMethod method) {
        return methodDistanceMap.containsKey(method.getSignature());
    }

    /**
     * {@inheritDoc}
     *
     * This implementation returns the distance from the pre-computed map, or -1 if not found.
     */
    @Override
    public int getDistance(SootMethod method) {
        return methodDistanceMap.getOrDefault(method.getSignature(), -1);
    }

    /**
     * {@inheritDoc}
     *
     * This implementation prints the target method and all method signatures with their distances.
     */
    @Override
    public void printMethodDistanceMap() {
        System.out.println("Method Distance Map for target: " + targetMethod);
        for (Map.Entry<String, Integer> entry : methodDistanceMap.entrySet()) {
            System.out.println(entry.getKey() + ": " + entry.getValue());
        }
    }
}
