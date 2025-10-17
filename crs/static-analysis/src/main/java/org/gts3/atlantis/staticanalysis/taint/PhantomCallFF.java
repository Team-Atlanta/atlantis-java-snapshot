package org.gts3.atlantis.staticanalysis.taint;

import analysis.data.DFF;
import analysis.flowfunctions.normal.AliasHandler;
import heros.FlowFunction;
import soot.Value;

import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

public class PhantomCallFF implements FlowFunction<DFF> {

    private final DFF genValue;
    private final DFF zeroValue;
    private AliasHandler aliasHandler;
    private final List<Value> callArgs;
    private final Value base;

    public PhantomCallFF(DFF genValue, DFF zeroValue, AliasHandler aliasHandler, List<Value> callArgs, Value base) {
        this.genValue = genValue;
        this.zeroValue = zeroValue;
        this.aliasHandler = aliasHandler;
        this.callArgs = callArgs;
        this.base = base;
    }

    public PhantomCallFF(DFF genValue, DFF zeroValue, AliasHandler aliasHandler, List<Value> callArgs) {
        this(genValue, zeroValue, aliasHandler, callArgs, null);
    }

    @Override
    public Set<DFF> computeTargets(DFF source) {
        if(source.equals(zeroValue)){
            return Collections.singleton(source);
        }

        Set<DFF> res = new HashSet<>();
        res.add(source);

        if (base != null && DFF.asDFF(base).equals(source)) {
            res.add(genValue);
        } else {
            for (Value v : callArgs) {
                if (DFF.asDFF(v).equals(source)) {
                    res.add(genValue);
                    break;
                }
            }
        }

        if (aliasHandler != null) {
            aliasHandler.handleAliases(res);
        }

        return res;
    }
}
