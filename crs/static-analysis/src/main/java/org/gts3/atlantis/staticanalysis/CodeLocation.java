package org.gts3.atlantis.staticanalysis;

import soot.SootMethod;
import soot.toolkits.graph.Block;

/**
 * Interface representing a location in code.
 *
 * This interface must be implemented by any class that represents a specific location
 * in code, such that it can be used to check the CFG (Control Flow Graph) for
 * containment within a specific basic block.
 */
public interface CodeLocation {
    /**
     * Checks if this code location is contained within the specified method and block.
     *
     * @param method The method to check
     * @param block The block within the method to check
     * @return true if this code location is contained in the specified block, false otherwise
     */
    boolean containedIn(SootMethod method, Block block);
}
