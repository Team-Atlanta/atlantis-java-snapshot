package org.gts3.atlantis.staticanalysis.taint;

import analysis.data.DFF;
import analysis.flowfunctions.FlowFunctionProvider;
import analysis.flowfunctions.normal.AliasHandlerProvider;
import analysis.flowfunctions.normal.ArrayLoadFF;
import analysis.flowfunctions.normal.FieldLoadFF;
import analysis.flowfunctions.normal.KillFF;
import heros.FlowFunction;
import heros.flowfunc.Identity;
import soot.Local;
import soot.SootMethod;
import soot.Unit;
import soot.Value;
import soot.jimple.*;
import soot.jimple.internal.JArrayRef;

import java.util.List;


public class NormalFlowFunctionProvider implements FlowFunctionProvider<DFF> {

    private FlowFunction<DFF> flowFunction;

    public NormalFlowFunctionProvider(SootMethod method, Unit curr, DFF zeroValue) {
        flowFunction = Identity.v(); // always id as fallback
        if (curr instanceof DefinitionStmt) {
            DefinitionStmt assignment = (DefinitionStmt) curr;
            Value lhs = assignment.getLeftOp();
            Value rhs = assignment.getRightOp();
            if (rhs instanceof Local) {
                // assignment of local
                Local right = (Local) rhs;
                //flowFunction = new LocalFF(right, lhs, zeroValue, AliasHandlerProvider.get(method, curr, lhs));
                flowFunction = new LocalFF(right, lhs, zeroValue, null);
            } else if (rhs instanceof FieldRef) {
                // assignment of instance field
                FieldRef fieldRef = (FieldRef) rhs;
                flowFunction = new FieldLoadFF(fieldRef, lhs, zeroValue, AliasHandlerProvider.get(method, curr, lhs));
                //flowFunction = new FieldLoadFF(fieldRef, lhs, zeroValue, null);
            } else if (rhs instanceof JArrayRef) {
                JArrayRef arrRef = (JArrayRef) rhs;
                flowFunction = new ArrayLoadFF(arrRef, lhs, zeroValue, AliasHandlerProvider.get(method, curr, lhs));
                //flowFunction = new ArrayLoadFF(arrRef, lhs, zeroValue, null);
            } else if(rhs instanceof Constant){
                flowFunction = new KillFF(lhs, zeroValue);
            } else if (rhs instanceof UnopExpr) {
                UnopExpr unopExpr = (UnopExpr) rhs;
                Value op = unopExpr.getOp();
                if (op instanceof Local) {
                    //flowFunction = new LocalFF((Local) op, lhs, zeroValue, AliasHandlerProvider.get(method, curr, lhs));
                    flowFunction = new LocalFF((Local) op, lhs, zeroValue, null);
                }
            } else if (rhs instanceof CastExpr) {
                CastExpr castExpr = (CastExpr) rhs;
                Value op = castExpr.getOp();
                if (op instanceof Local) {
                    flowFunction = new LocalFF((Local) op, lhs, zeroValue, null);
                }
            } else if (rhs instanceof BinopExpr) {
                BinopExpr binopExpr = (BinopExpr) rhs;
                Value op1 = binopExpr.getOp1();
                Value op2 = binopExpr.getOp2();
                List<Local> locals = List.of(op1, op2)
                    .stream()
                    .filter(o -> o instanceof Local)
                    .map(o -> (Local) o)
                    .toList();
                if (!locals.isEmpty()) {
                    //flowFunction = new MultiLocalFF(locals, lhs, zeroValue, AliasHandlerProvider.get(method, curr, lhs));
                    flowFunction = new MultiLocalFF(locals, lhs, zeroValue, null);
                }
            } else if (rhs instanceof NewArrayExpr) {
                NewArrayExpr newArrayExpr = (NewArrayExpr) rhs;
                Value size = newArrayExpr.getSize();
                if (size instanceof Local) {
                    //flowFunction = new LocalFF((Local) size, lhs, zeroValue, AliasHandlerProvider.get(method, curr, lhs));
                    flowFunction = new LocalFF((Local) size, lhs, zeroValue, null);
                }
            }
        }
    }

    public FlowFunction<DFF> getFlowFunction() {
        return flowFunction;
    }

}
