package org.gts3.atlantis.staticanalysis;

import soot.jimple.toolkits.callgraph.CallGraph;

import java.util.Collection;

/**
 * Interface for specifications that can be converted to concrete target locations.
 *
 * This interface defines a method to convert a specification (which might be in various formats)
 * into a collection of concrete TargetLocation objects using a call graph.
 */
public interface TargetLocationSpec {
    /**
     * Converts this specification into a collection of concrete target locations.
     *
     * @param callGraph The call graph to use for resolving the target locations
     * @return A collection of target locations derived from this specification
     */
    Collection<? extends TargetLocation> toTargetLocations(CallGraph callGraph);
}
