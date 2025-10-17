package org.gts3.atlantis.staticanalysis.taint;

import analysis.data.DFF;
import analysis.flowfunctions.ReturnFlowFunctionProvider;
import heros.FlowFunction;
import heros.FlowFunctions;
import heros.InterproceduralCFG;
import soot.*;
import soot.jimple.internal.JimpleLocal;
import soot.jimple.toolkits.ide.DefaultJimpleIFDSTabulationProblem;
import soot.toolkits.graph.BriefUnitGraph;
import soot.toolkits.graph.DirectedGraph;
import util.CFGUtil;

import java.util.*;

import static org.gts3.atlantis.staticanalysis.utils.LogLabel.LOG_ERROR;

public class TaintAnalysisProblem extends DefaultJimpleIFDSTabulationProblem<DFF, InterproceduralCFG<Unit, SootMethod>> {

    private final List<SootMethodRef> sources;
    private final List<SootMethod> entryPoints;

    protected InterproceduralCFG<Unit, SootMethod> icfg;

    public TaintAnalysisProblem(InterproceduralCFG<Unit, SootMethod> icfg, List<SootMethodRef> sources, List<SootMethod> entryPoints) {
        super(icfg);
        this.icfg = icfg;
        this.sources = sources;
        this.entryPoints = entryPoints;
    }

    @Override
    protected FlowFunctions<Unit, DFF, SootMethod> createFlowFunctionsFactory() {
        return new FlowFunctions<Unit, DFF, SootMethod>() {
            @Override
            public FlowFunction<DFF> getNormalFlowFunction(Unit curr, Unit succ) {
                NormalFlowFunctionProvider ffp = new NormalFlowFunctionProvider(icfg.getMethodOf(curr), curr, zeroValue());
                return ffp.getFlowFunction();
            }

            @Override
            public FlowFunction<DFF> getCallFlowFunction(Unit callStmt, SootMethod dest) {
                CallFlowFunctionProvider ffp = new CallFlowFunctionProvider(callStmt, dest, zeroValue());
                return ffp.getFlowFunction();
            }

            @Override
            public FlowFunction<DFF> getReturnFlowFunction(Unit callSite, SootMethod calleeMethod, Unit exitStmt, Unit returnSite) {
                ReturnFlowFunctionProvider ffp = new ReturnFlowFunctionProvider(callSite, exitStmt, icfg.getMethodOf(callSite), icfg.getMethodOf(exitStmt));
                return ffp.getFlowFunction();
            }

            @Override
            public FlowFunction<DFF> getCallToReturnFlowFunction(Unit callSite, Unit returnSite) {
                int calleeCount = icfg.getCalleesOfCallAt(callSite).size();
                PhantomCallToReturnFlowFunctionProvider ffp = new PhantomCallToReturnFlowFunctionProvider(icfg.getMethodOf(callSite), callSite, zeroValue(), calleeCount);
                return ffp.getFlowFunction();
            }
        };
    }

    @Override
    protected DFF createZeroValue() {
        return DFF.asDFF(new JimpleLocal("<<zero>>", NullType.v()));
    }

    @Override
    public Map<Unit, Set<DFF>> initialSeeds() {
        Map<Unit, Set<DFF>> result = new HashMap<>();
        for (SootMethod entryPoint : entryPoints) {
            DirectedGraph<Unit> unitGraph = new BriefUnitGraph(entryPoint.getActiveBody());
            Unit entryUnit = CFGUtil.getHead(unitGraph);

            Set<DFF> taintedLocals = new HashSet<>();
            taintedLocals.add(zeroValue());
            for (Local local : entryPoint.getActiveBody().getParameterLocals()) {
                taintedLocals.add(DFF.asDFF(local));
            }
            result.put(entryUnit, taintedLocals);
        }

        if (result.isEmpty()) {
            System.err.println(LOG_ERROR + "Cannot find any entry unit (" + entryPoints.size() + " entry points)");
            throw new IllegalStateException("Cannot find any entry unit (" + entryPoints.size() + " entry points)");
        }

        return result;
    }
}