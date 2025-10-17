package org.gts3.atlantis.staticanalysis.taint;

import analysis.data.DFF;
import analysis.flowfunctions.FlowFunctionProvider;
import analysis.flowfunctions.call.KillStaticCTRFF;
import analysis.flowfunctions.normal.AliasHandlerProvider;
import heros.FlowFunction;
import soot.*;
import soot.jimple.DefinitionStmt;
import soot.jimple.InvokeExpr;
import soot.jimple.InvokeStmt;
import soot.jimple.internal.AbstractInstanceInvokeExpr;

public class PhantomCallToReturnFlowFunctionProvider implements FlowFunctionProvider<DFF> {

    private FlowFunction<DFF> flowFunction;

    public PhantomCallToReturnFlowFunctionProvider(SootMethod method, Unit curr, DFF zeroValue, int calleeCount) {
        InvokeExpr invokeExpr = null;
        Value lhs = null;
        if (curr instanceof DefinitionStmt) {
            DefinitionStmt def = (DefinitionStmt) curr;
            Value rhs = def.getRightOp();
            if (rhs instanceof InvokeExpr) {
                invokeExpr = (InvokeExpr) rhs;
                lhs = def.getLeftOp();
            }
        } else if (curr instanceof InvokeStmt) {
            InvokeStmt invokeStmt = (InvokeStmt) curr;
            if (invokeStmt.getInvokeExpr() instanceof AbstractInstanceInvokeExpr) {
                AbstractInstanceInvokeExpr abstractInstanceInvokeExpr = (AbstractInstanceInvokeExpr) invokeStmt.getInvokeExpr();
                invokeExpr = abstractInstanceInvokeExpr;
                lhs = abstractInstanceInvokeExpr.getBase();
            }
        }

        if (invokeExpr != null && lhs != null) {
            //System.out.println("Found a call with 0 callee count: " + method + ", " + curr);

            Value base = null;

            if (invokeExpr instanceof AbstractInstanceInvokeExpr) {
                AbstractInstanceInvokeExpr instanceInvoke = (AbstractInstanceInvokeExpr) invokeExpr;
                base = instanceInvoke.getBase();
            }

            //flowFunction = new PhantomCallFF(new DFF(lhs, curr), zeroValue, AliasHandlerProvider.get(method, curr, lhs), invokeExpr.getArgs(), base);
            flowFunction = new PhantomCallFF(new DFF(lhs, curr), zeroValue, null, invokeExpr.getArgs(), base);
            return;
        }

        flowFunction = new KillStaticCTRFF();
    }

    @Override
    public FlowFunction<DFF> getFlowFunction() {
        return flowFunction;
    }
}
