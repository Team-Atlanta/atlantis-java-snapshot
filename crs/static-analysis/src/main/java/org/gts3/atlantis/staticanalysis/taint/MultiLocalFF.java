package org.gts3.atlantis.staticanalysis.taint;

import analysis.data.DFF;
import analysis.flowfunctions.normal.AliasHandler;
import heros.FlowFunction;
import soot.Local;
import soot.Value;
import soot.jimple.FieldRef;
import soot.jimple.internal.JArrayRef;

import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * Assignment from a single local
 */
public class MultiLocalFF implements FlowFunction<DFF> {

    private final List<Local> right;
    private final Value lhs;
    private final DFF zeroValue;
    private final AliasHandler aliasHandler;

    public MultiLocalFF(List<Local> right, Value lhs, DFF zeroValue, AliasHandler aliasHandler) {
        this.right = right;
        this.lhs = lhs;
        this.zeroValue = zeroValue;
        this.aliasHandler = aliasHandler;
    }


    @Override
    public Set<DFF> computeTargets(DFF source) {
        if (source.equals(zeroValue)) {
            return Collections.singleton(source);
        }
        Set<DFF> res = new HashSet<>();
        res.add(source);
        if (right.stream().anyMatch(r -> DFF.asDFF(r).equals(source))) {
            res.add(DFF.asDFF(lhs));
        }
        // for arrays
        if (source.getValue() instanceof JArrayRef) {
            JArrayRef arrayRef = (JArrayRef) source.getValue();
            if (right.stream().anyMatch(r -> arrayRef.getBase().equals(r))) {
                if (!(lhs instanceof FieldRef)) {
                    JArrayRef newRef = new JArrayRef(lhs, arrayRef.getIndex());
                    res.add(DFF.asDFF(newRef));
                }
            }
        }
        if (aliasHandler != null) {
            aliasHandler.handleAliases(res);
        }
        return res;
    }


}
