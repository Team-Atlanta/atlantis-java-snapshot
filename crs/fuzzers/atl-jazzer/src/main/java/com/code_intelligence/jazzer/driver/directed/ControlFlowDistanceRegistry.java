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

package com.code_intelligence.jazzer.driver.directed;

import com.code_intelligence.jazzer.utils.Log;
import java.util.*;
import org.gts3.atlantis.staticanalysis.BasicBlockDistance;
import org.gts3.atlantis.staticanalysis.CodeLocation;
import org.gts3.atlantis.staticanalysis.SimpleMethodDistanceMap;
import soot.Local;
import soot.SootClass;
import soot.SootMethod;
import soot.Unit;
import soot.Value;
import soot.jimple.AssignStmt;
import soot.jimple.CastExpr;
import soot.jimple.IntConstant;
import soot.jimple.InvokeStmt;
import soot.toolkits.graph.Block;
import soot.toolkits.graph.DominatorsFinder;

/**
 * Class for managing control flow distances for classes and targets. This class maintains mappings
 * of coverage IDs to distances at both the class level and the target level.
 */
public class ControlFlowDistanceRegistry {
  private Set<FuzzTarget> targets;

  // For each class name, we store a ClassSpecificDistances object
  private final Map<String, ClassSpecificDistances> classDistanceRegistry = new HashMap<>();

  // Cache for target control flow distances computations
  // Map<ClassName+TargetSignature, TargetSpecificDistances>
  private final Map<String, TargetSpecificDistances> targetDistanceCache = new HashMap<>();

  /**
   * Creates a new ControlFlowDistanceRegistry instance. Initializes the maps for storing class and
   * target control flow distances.
   */
  public ControlFlowDistanceRegistry() {}

  /**
   * Creates a cache key for target control flow distances. The key is a combination of class name,
   * method signature, and bytecode offset.
   *
   * @param className The name of the class
   * @param target The target information
   * @return The cache key string
   */
  private String createTargetCacheKey(String className, FuzzTarget target) {
    return className + "::" + target.hashCode();
  }

  /**
   * Gets the control flow distances map for a class.
   *
   * @param className The name of the class
   * @return Map of coverage IDs to ControlFlowDistance objects for the class
   */
  public Map<Integer, ControlFlowDistance> getDistancesForClass(String className) {
    ClassSpecificDistances classDistances = getClassSpecificDistances(className);
    return classDistances.getEdgeDistances();
  }

  /**
   * Gets the ClassSpecificDistances for a class, computing it if necessary.
   *
   * @param className The name of the class
   * @return The ClassSpecificDistances for the class
   */
  public ClassSpecificDistances getClassSpecificDistances(String className) {
    if (classDistanceRegistry.containsKey(className)) {
      return classDistanceRegistry.get(className);
    }

    // We haven't computed the control flow distances for this class yet
    ClassSpecificDistances classDistances = computeClassSpecificDistances(className);
    classDistanceRegistry.put(className, classDistances);

    return classDistances;
  }

  /**
   * Updates the targets list.
   *
   * @param targets The new list of targets
   */
  public void updateTargets(Set<FuzzTarget> targets) {
    this.targets = targets;
    recalculateDistances();
  }

  /** Resets the cache to trigger distance calculation. */
  public void recalculateDistances() {
    // Clear the cache when targets are updated
    classDistanceRegistry.clear();
  }

  /**
   * Computes the control flow distances for a class by aggregating distances from all targets.
   *
   * @param className The name of the class
   * @return The ClassSpecificDistances for the class
   */
  private ClassSpecificDistances computeClassSpecificDistances(String className) {
    ClassSpecificDistances classDistances = new ClassSpecificDistances(className);
    List<TargetSpecificDistances> targetSpecificDistancesList = new ArrayList<>();

    // Go through all the targets and compute the control flow distances for every target
    for (FuzzTarget target : targets) {
      TargetSpecificDistances targetDistances = getTargetSpecificDistances(className, target);
      targetSpecificDistancesList.add(targetDistances);
    }

    // Aggregate the target-level distances to get the aggregated class-level distances
    classDistances.updateFromTargets(targetSpecificDistancesList);

    return classDistances;
  }

  /**
   * Computes the control flow distances for a specific target within a class. Uses caching to avoid
   * recomputing distances for the same target and class.
   *
   * <p>This method handles the caching logic and delegates the actual computation to the
   * computeDistancesForTarget method, which implements the specific algorithm for computing control
   * flow distances.
   *
   * @param className The name of the class
   * @param target The target information
   * @return The TargetSpecificDistances for the target
   */
  private TargetSpecificDistances getTargetSpecificDistances(String className, FuzzTarget target) {
    // Check if we have already computed the distances for this target and class
    String cacheKey = createTargetCacheKey(className, target);
    if (targetDistanceCache.containsKey(cacheKey)) {
      return targetDistanceCache.get(cacheKey);
    }

    // Compute the control flow distances for the given target and class name
    Map<Integer, ControlFlowDistance> controlFlowDistances =
        computeDistancesForTarget(className, target);

    TargetSpecificDistances result =
        new TargetSpecificDistances(className, target, controlFlowDistances);

    // Cache the result
    targetDistanceCache.put(cacheKey, result);

    return result;
  }

  /**
   * Computes the control flow distances for a specific target within a class.
   *
   * @param className The name of the class
   * @param target The target information
   * @return Map of coverage IDs to ControlFlowDistance objects for the target
   */
  protected Map<Integer, ControlFlowDistance> computeDistancesForTarget(
      String className, FuzzTarget target) {
    Log.debug("Computing control flow distances for class: " + className);

    // Here, we use the static analyzer to compute the control flow distances
    Map<Integer, ControlFlowDistance> result = new HashMap<>();

    CodeAnalyzer codeAnalyzer = CodeAnalyzer.getInstance();
    SootClass sootClass = codeAnalyzer.loadClass(className);

    SimpleMethodDistanceMap methodDistanceMap =
        new SimpleMethodDistanceMap(target.getMethodSignature(), target.getMethodCallDistanceMap());

    CodeLocation targetLocation = target.asCodeLocation();

    // Go through all the methods in the class and calculate the basic block distances
    for (SootMethod method : sootClass.getMethods()) {
      int methodCallDistance =
          target.getMethodCallDistanceMap().getOrDefault(method.getSignature(), -1);

      if (methodCallDistance < 0) {
        continue;
      }

      Log.debug("Computing control flow distances for method: " + method.getSignature());
      BasicBlockDistance basicBlockDistance =
          new BasicBlockDistance(methodDistanceMap, method, targetLocation);

      Map<Block, Integer> blockDistanceMap = basicBlockDistance.getBlockDistanceMap();
      for (Block block : basicBlockDistance.getAllBlocks()) {
        int blockDist = blockDistanceMap.getOrDefault(block, -1);
        Set<Integer> coverageIds =
            inferCoverageIds(block, basicBlockDistance.getDominatorsFinder());

        if (coverageIds.isEmpty()) {
          continue;
        }

        if (blockDist >= 0) {
          ControlFlowDistance controlFlowDistance =
              new ControlFlowDistance(blockDist, methodCallDistance);
          updateResultMapIfNeeded(result, coverageIds, methodCallDistance, controlFlowDistance);
        } else {
          // In this case, we need to check the predecessors of the block.
          // Go up the CFG as long as there is only one predecessor and that predecessor doesn't
          // have it's own coverage id.
          Block ptr = block;
          while (ptr.getPreds().size() == 1) {
            Block predecessor = ptr.getPreds().get(0);
            int predecessorCoverageId = extractCoverageIdFromBlock(predecessor);
            if (predecessorCoverageId >= 0) {
              break;
            }
            ptr = predecessor;
            blockDist = blockDistanceMap.getOrDefault(ptr, -1);
            if (blockDist >= 0) {
              ControlFlowDistance controlFlowDistance =
                  new ControlFlowDistance(blockDist, methodCallDistance);
              updateResultMapIfNeeded(result, coverageIds, methodCallDistance, controlFlowDistance);
              break;
            }
          }
        }
      }
    }

    return result;
  }

  private Set<Integer> inferCoverageIds(Block block, DominatorsFinder<Block> dominatorsFinder) {
    int coverageId = extractCoverageIdFromBlock(block);
    if (coverageId >= 0) {
      return Collections.singleton(coverageId);
    }

    Set<Integer> coverageIds = new HashSet<>();
    List<Block> workQueue = new ArrayList<>();
    workQueue.add(block);

    for (int i = 0; i < 3; i++) {
      List<Block> currentBlocks = new ArrayList<>(workQueue);
      workQueue.clear();

      for (Block currentBlock : currentBlocks) {
        for (Block successor : currentBlock.getSuccs()) {
          if (!dominatorsFinder.isDominatedBy(successor, block)) {
            // If there are multiple successors, we can't be sure if the covId in that block
            // is triggered by this parent block or by a different one.
            continue;
          }

          coverageId = extractCoverageIdFromBlock(successor);

          if (coverageId >= 0) {
            coverageIds.add(coverageId);
          } else {
            workQueue.add(successor);
          }
        }
      }
    }

    return coverageIds;
  }

  /**
   * Extracts the coverage ID from a given block.
   *
   * @param block The block
   * @return The coverage ID
   */
  private int extractCoverageIdFromBlock(Block block) {
    // For now, we just use the block ID as the coverage ID
    for (Unit unit : block) {
      Log.debug("Instruction: " + unit);
      if (unit instanceof InvokeStmt) {
        InvokeStmt invokeStmt = (InvokeStmt) unit;
        SootMethod invokedMethod = invokeStmt.getInvokeExpr().getMethod();
        if (invokedMethod
            .getSignature()
            .equals(
                "<com.code_intelligence.jazzer.runtime.CoverageMap: void recordCoverage(int)>")) {
          Value argument = invokeStmt.getInvokeExpr().getArg(0);
          Optional<Integer> value = resolveIntValue(argument);
          if (value.isPresent()) {
            return value.get();
          } else {
            assert argument instanceof Local;
            Local local = (Local) argument;

            // Go through all units in this block and try to get the value assigned to this local
            for (Unit unit2 : block) {
              if (unit2.equals(unit)) {
                break;
              }
              if (unit2 instanceof AssignStmt) {
                AssignStmt assignStmt = (AssignStmt) unit2;
                if (assignStmt.getLeftOp().equals(local)) {
                  Optional<Integer> rightOpValue = resolveIntValue(assignStmt.getRightOp());
                  if (rightOpValue.isPresent()) {
                    return rightOpValue.get();
                  }
                }
              }
            }
          }
        }
      }
    }
    return -1;
  }

  /**
   * Updates the result map with the new control flow distance if needed. The update only happens if
   * there's no existing entry for the coverage ID or if the new distance is smaller.
   *
   * @param result The result map to update
   * @param coverageIds The set of coverage IDs to update
   * @param methodCallDistance The method call distance
   * @param controlFlowDistance The control flow distance object
   */
  private void updateResultMapIfNeeded(
      Map<Integer, ControlFlowDistance> result,
      Set<Integer> coverageIds,
      int methodCallDistance,
      ControlFlowDistance controlFlowDistance) {
    for (int coverageId : coverageIds) {
      // Only update if there's no existing entry or the new distance is smaller
      ControlFlowDistance existingDistance = result.get(coverageId);
      if (existingDistance != null
          && existingDistance.getMethodCallDistance() != methodCallDistance) {
        Log.warn(
            "Conflicting method call distances for coverage ID "
                + coverageId
                + ": existing distance = "
                + existingDistance.getMethodCallDistance()
                + ", new distance = "
                + methodCallDistance);
      }
      if (existingDistance == null
          || controlFlowDistance.getTotalDistance() < existingDistance.getTotalDistance()) {
        result.put(coverageId, controlFlowDistance);
      }
    }
  }

  private Optional<Integer> resolveIntValue(Value value) {
    if (value instanceof IntConstant) {
      return Optional.of(((IntConstant) value).value);
    }
    if (value instanceof CastExpr) {
      CastExpr castExpr = (CastExpr) value;
      return resolveIntValue(castExpr.getOp());
    }
    return Optional.empty();
  }

  public Set<FuzzTarget> getTargets() {
    return targets;
  }
}
