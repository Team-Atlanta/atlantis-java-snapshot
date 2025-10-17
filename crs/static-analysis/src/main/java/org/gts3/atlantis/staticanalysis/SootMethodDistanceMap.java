package org.gts3.atlantis.staticanalysis;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Iterator;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;
import java.util.Queue;
import java.util.Set;

import org.gts3.atlantis.staticanalysis.utils.SignatureUtils;
import soot.SootMethod;
import soot.jimple.toolkits.callgraph.CallGraph;
import soot.jimple.toolkits.callgraph.Edge;

/**
 * A Soot-based implementation of MethodDistanceMap that calculates and stores the distance
 * of methods to a target method using Soot's call graph.
 *
 * This implementation performs a breadth-first search on the call graph to calculate
 * the distance from each method to the target method.
 */
public class SootMethodDistanceMap implements MethodDistanceMap {
    private static final int DISTANCE_INCREMENT = 50;

    private final CallGraph callGraph;
    private final SootMethod targetMethod;
    private final Map<SootMethod, Integer> methodDistanceMap = new HashMap<>();

    /**
     * Constructs a new SootMethodDistanceMap and calculates distances from methods to the target.
     *
     * @param callGraph The call graph to use for distance calculation
     * @param targetMethod The target method to calculate distances to
     */
    public SootMethodDistanceMap(CallGraph callGraph, SootMethod targetMethod) {
        this.callGraph = callGraph;
        this.targetMethod = targetMethod;
        calculateDistances();
    }

    /**
     * Gets all methods that have a calculated distance to the target.
     *
     * @return A list of all methods in the distance map
     */
    public List<SootMethod> getMethods() {
        return new ArrayList<>(methodDistanceMap.keySet());
    }

    /**
     * Calculates the distances from all methods to the target method.
     *
     * This method performs a breadth-first search starting from the target method
     * and traversing the call graph in reverse to find all methods that can reach the target.
     */
    private void calculateDistances() {
        Queue<SootMethod> queue = new LinkedList<>();
        Set<SootMethod> visited = new HashSet<>();

        List<SootMethod> targets = SignatureUtils.getImplementationsOf(targetMethod);
        queue.addAll(targets);
        visited.addAll(targets);

        for (SootMethod target : targets) {
            methodDistanceMap.put(target, 0);
        }

        while (!queue.isEmpty()) {
            SootMethod currentMethod = queue.poll();
            int currentDistance = methodDistanceMap.get(currentMethod);

            Iterator<Edge> edges = callGraph.edgesInto(currentMethod);
            while (edges.hasNext()) {
                SootMethod caller = edges.next().src();
                if (!visited.contains(caller)) {
                    visited.add(caller);
                    queue.add(caller);
                    methodDistanceMap.put(caller, currentDistance + DISTANCE_INCREMENT);
                }
            }
        }
    }

    /**
     * {@inheritDoc}
     *
     * This implementation checks if the method is in the calculated distance map,
     * which means it can reach the target method through the call graph.
     */
    @Override
    public boolean hasDistance(SootMethod method) {
        return methodDistanceMap.containsKey(method);
    }

    /**
     * {@inheritDoc}
     *
     * This implementation returns the calculated distance from the method to the target method,
     * or -1 if the method cannot reach the target method through the call graph.
     */
    @Override
    public int getDistance(SootMethod method) {
        return methodDistanceMap.getOrDefault(method, -1);
    }

    /**
     * {@inheritDoc}
     *
     * This implementation prints the target method's signature and all methods that can reach it,
     * along with their calculated distances.
     */
    @Override
    public void printMethodDistanceMap() {
        System.out.println("Method Distance Map for target: " + targetMethod.getSignature());
        for (Map.Entry<SootMethod, Integer> entry : methodDistanceMap.entrySet()) {
            System.out.println(entry.getKey().getSignature() + ": " + entry.getValue());
        }
    }

    /**
     * Checks if the distance map contains at least one application method.
     *
     * An application method is a method that belongs to the application being analyzed,
     * as opposed to a library method.
     *
     * @return true if at least one application method can reach the target, false otherwise
     */
    public boolean containsApplicationMethod() {
        // Go through all methods and check if any of them are application methods
        for (SootMethod method : methodDistanceMap.keySet()) {
            if (method.getDeclaringClass().isApplicationClass()) {
                return true;
            }
        }

        return false;
    }
}
