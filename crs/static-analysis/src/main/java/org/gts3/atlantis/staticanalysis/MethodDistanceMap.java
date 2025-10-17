package org.gts3.atlantis.staticanalysis;

import soot.SootMethod;

/**
 * An interface that defines operations for storing and retrieving distances of methods to a target method.
 */
public interface MethodDistanceMap {
    /**
     * Checks if a method has a distance in the map.
     *
     * @param method the method to check
     * @return true if the method has a distance, false otherwise
     */
    boolean hasDistance(SootMethod method);

    /**
     * Gets the distance of a method.
     *
     * @param method the method to get the distance for
     * @return the distance of the method to the target, or -1 if not found
     */
    int getDistance(SootMethod method);

    /**
     * Prints the method distance map to the console.
     */
    void printMethodDistanceMap();
}
