package org.gts3.atlantis.staticanalysis;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import soot.SootMethod;
import soot.Unit;
import soot.baf.Inst;
import soot.baf.InterfaceInvokeInst;
import soot.baf.SpecialInvokeInst;
import soot.baf.StaticInvokeInst;
import soot.baf.VirtualInvokeInst;
import soot.baf.internal.BDynamicInvokeInst;
import soot.jimple.InvokeExpr;
import soot.jimple.InvokeStmt;
import soot.jimple.Stmt;
import soot.tagkit.BytecodeOffsetTag;
import soot.toolkits.graph.*;

/**
 * Calculates and stores distances between basic blocks in a method's control flow graph.
 *
 * This class analyzes a method's control flow graph to determine the distance from each
 * basic block to a target location or to a call to a method that is in the method distance map.
 * These distances can be used for guiding fuzzing or other program analysis tasks.
 */
public class BasicBlockDistance {
    private final MethodDistanceMap methodDistanceMap;
    private final SootMethod method;
    private final CodeLocation targetCodeLocation;
    private final Map<Block, Integer> blockDistanceMap = new HashMap<>();
    private final CompleteBlockGraph blockGraph;
    private final DominatorsFinder<Block> dominatorsFinder;

    /**
     * Constructs a new BasicBlockDistance and calculates distances in the method's control flow graph.
     *
     * @param methodDistanceMap The method distance map to use for identifying important method calls
     * @param method The method to analyze
     * @param targetCodeLocation The target code location to calculate distances to
     */
    public BasicBlockDistance(MethodDistanceMap methodDistanceMap, SootMethod method, CodeLocation targetCodeLocation) {
        this.methodDistanceMap = methodDistanceMap;
        this.method = method;
        this.targetCodeLocation = targetCodeLocation;

        if (method.isAbstract()) {
            this.blockGraph = null;
            this.dominatorsFinder = null;
        } else {
            this.blockGraph = new CompleteBlockGraph(method.retrieveActiveBody());
            this.dominatorsFinder = new MHGDominatorsFinder<>(blockGraph);
            calculateDistances();
        }
    }

    /**
     * Calculates distances from each basic block to blocks containing calls to methods
     * in the method distance map or to the target code location.
     *
     * This method performs a breadth-first search on the control flow graph, starting from
     * blocks that contain calls to methods in the method distance map or the target location.
     */
    private void calculateDistances() {
        // First, set the distance of all blocks with a call to method that is in the distance map to 0
        List<Block> workingList = new ArrayList<>();
        for (Block block : blockGraph) {
            for (Unit unit : block) {
                if (unit instanceof Inst inst) {
                    if (inst.containsInvokeExpr()) {
                        SootMethod targetMethod;
                        if (inst instanceof BDynamicInvokeInst bDynamicInvokeInst) {
                            targetMethod = bDynamicInvokeInst.getMethod();
                        } else if (inst instanceof InterfaceInvokeInst interfaceInvokeInst) {
                            targetMethod = interfaceInvokeInst.getMethod();
                        } else if (inst instanceof SpecialInvokeInst specialInvokeInst) {
                            targetMethod = specialInvokeInst.getMethod();
                        } else if (inst instanceof StaticInvokeInst staticInvokeInst) {
                            targetMethod = staticInvokeInst.getMethod();
                        } else if (inst instanceof VirtualInvokeInst virtualInvokeInst) {
                            targetMethod = virtualInvokeInst.getMethod();
                        } else {
                            continue;
                        }

                        if (methodDistanceMap.hasDistance(targetMethod)) {
                            blockDistanceMap.put(block, 0);
                            workingList.add(block);
                            break;
                        }
                    }
                }

                if (unit instanceof Stmt stmt) {
                    if (stmt.containsInvokeExpr()) {
                        InvokeExpr invokeExpr = stmt.getInvokeExpr();
                        SootMethod invokedMethod = invokeExpr.getMethod();

                        if (methodDistanceMap.hasDistance(invokedMethod)) {
                            blockDistanceMap.put(block, 0);
                            workingList.add(block);
                        }
                    }
                } else if (unit instanceof InvokeStmt invokeStmt) {
                    InvokeExpr invokeExpr = invokeStmt.getInvokeExpr();
                    SootMethod invokedMethod = invokeExpr.getMethod();

                    if (methodDistanceMap.hasDistance(invokedMethod)) {
                        blockDistanceMap.put(block, 0);
                        workingList.add(block);
                    }
                }
            }

            // Alternatively, if this is the target location, the distance also is 0
            if (targetCodeLocation.containedIn(method, block)) {
                blockDistanceMap.put(block, 0);
                workingList.add(block);
                break;
            }
        }

        while (!workingList.isEmpty()) {
            Block block = workingList.remove(0);
            int currentDistance = blockDistanceMap.get(block);

            // Now, look at all the predecessors of the block
            for (Block predecessor : blockGraph.getPredsOf(block)) {
                int updatedDistance = currentDistance + 1;
                if (updatedDistance < blockDistanceMap.getOrDefault(predecessor, Integer.MAX_VALUE)) {
                    blockDistanceMap.put(predecessor, updatedDistance);
                    workingList.add(predecessor);
                }
            }
        }
    }

    /**
     * Gets an identifier for a basic block based on the bytecode offset of its first instruction.
     *
     * @param block The basic block
     * @return The bytecode offset of the first instruction, or -1 if not available
     */
    public int getBlockId(Block block) {
        for (Unit unit : block) {
            BytecodeOffsetTag bci = (BytecodeOffsetTag) unit.getTag("BytecodeOffsetTag");
            if (bci != null) {
                int bco = bci.getBytecodeOffset();
                if (bco >= 0) {
                    return bco;
                }
            }
        }
        return -1;
    }

    /**
     * Checks if a basic block has a calculated distance.
     *
     * @param block The basic block to check
     * @return true if the block has a distance, false otherwise
     */
    public boolean hasDistance(Block block) {
        return blockDistanceMap.containsKey(block);
    }

    /**
     * Gets the distance of a basic block to the nearest block containing a call to a method
     * in the method distance map or to the target code location.
     *
     * @param block The basic block
     * @return The distance, or Integer.MAX_VALUE if not reachable
     */
    public int getDistance(Block block) {
        return blockDistanceMap.getOrDefault(block, Integer.MAX_VALUE);
    }

    /**
     * Gets the map of basic blocks to their distances.
     *
     * @return The block distance map
     */
    public Map<Block, Integer> getBlockDistanceMap() {
        return blockDistanceMap;
    }

    /**
     * Gets all basic blocks in the method's control flow graph.
     *
     * @return A list of all basic blocks
     */
    public List<Block> getAllBlocks() {
        return blockGraph.getBlocks();
    }

    /**
     * Gets the dominators finder of the basic blocks in this method.
     *
     * @return The dominators finder
     */
    public DominatorsFinder<Block> getDominatorsFinder() {
        return dominatorsFinder;
    }

    /**
     * Prints the block distance map to the console.
     *
     * This method is useful for debugging and visualization of the control flow graph.
     */
    public void printBlockDistanceMap() {
        System.out.println("Block distance map for " + method.getSignature() + ":");
        for (Block block : blockDistanceMap.keySet()) {
            System.out.println(block.toString() + ": " + blockDistanceMap.get(block));
        }
    }
}
