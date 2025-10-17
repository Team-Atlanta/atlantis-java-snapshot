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
import java.util.Set;

/**
 * Assignment from a single local
 */
public class LocalFF implements FlowFunction<DFF> {

    private Local right;
    private Value lhs;
    private DFF zeroValue;
    private AliasHandler aliasHandler;

    public LocalFF(Local right, Value lhs, DFF zeroValue, AliasHandler aliasHandler) {
        this.right = right;
        this.lhs = lhs;
        this.zeroValue = zeroValue;
        this.aliasHandler = aliasHandler;
    }


    @Override
    public Set<DFF> computeTargets(DFF source) {
        if(source.equals(zeroValue)){
            return Collections.singleton(source);
        }
        Set<DFF> res = new HashSet<>();
        res.add(source);
        if (DFF.asDFF(right).equals(source)) {
            res.add(DFF.asDFF(lhs));
        }
        // for arrays
        if(source.getValue() instanceof JArrayRef){
            JArrayRef arrayRef = (JArrayRef) source.getValue();
            if(arrayRef.getBase().equals(right)){
                if(!(lhs instanceof FieldRef)){
                    if (lhs instanceof JArrayRef) {
                        res.add(DFF.asDFF(((JArrayRef) lhs).getBase()));
                    } else {
                        res.add(DFF.asDFF(lhs));
                    }
                }
            }
        }
        if (aliasHandler != null) {
            aliasHandler.handleAliases(res);
        }
        return res;
    }


}
