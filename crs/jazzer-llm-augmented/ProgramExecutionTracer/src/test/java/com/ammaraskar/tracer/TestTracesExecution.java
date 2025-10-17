package com.ammaraskar.tracer;

import org.junit.jupiter.api.Test;

import java.io.File;
import java.util.ArrayList;
import java.util.Collection;
import java.util.List;

import static java.util.Comparator.comparing;
import static org.hamcrest.MatcherAssert.assertThat;
import static org.hamcrest.Matchers.contains;
import static org.hamcrest.Matchers.containsString;
import static org.junit.jupiter.api.Assertions.assertEquals;

public class TestTracesExecution {

    @Test
    public void testTraceSuccessfullyGetsInnermostFunction() {
        System.out.println(new File(".").getAbsolutePath());
        String MAIN = "com.ammaraskar.tracer.test.Tracee";

        ExecutionTracer tracer = new ExecutionTracer("target/test-classes", MAIN);
        tracer.startExecution();
        TraceResult traceResult = tracer.getBestCandidateForWhereExecutionIsStuck();

        StackTrace stuckReason = traceResult.getStuckCandidateTrace();
        stuckReason.filterFramesBeforeFunctionCall("fuzzerTestOneInput");

        StackTraceFrame innerMostFrame = stuckReason.getFrames().get(0);
        assertEquals(innerMostFrame.getMethodName(), "stuckHere");

        // List of leaf calls so we can sort and test reliably.
        List<StackTraceFrame> leafCalls = traceResult.getLeafFunctions().stream().sorted(comparing(StackTraceFrame::getMethodName)).toList();
        assertEquals(2, leafCalls.size());
        assertEquals("<init>", leafCalls.get(0).getMethodName());
        assertEquals("stuckHere", leafCalls.get(1).getMethodName());
    }

    @Test
    public void testTraceGetsStackFrameForException() {
        String MAIN = "com.ammaraskar.tracer.test.TraceeWithException";

        ExecutionTracer tracer = new ExecutionTracer("target/test-classes", MAIN);
        tracer.startExecution();
        TraceResult traceResult = tracer.getBestCandidateForWhereExecutionIsStuck();

        StackTrace stuckReason = traceResult.getStuckCandidateTrace();
        stuckReason.filterFramesBeforeFunctionCall("fuzzerTestOneInput");

        StackTraceFrame innerMostFrame = stuckReason.getFrames().get(0);
        assertEquals("functionThatThrows", innerMostFrame.getMethodName());

        // List of leaf calls so we can sort and test reliably.
        List<StackTraceFrame> leafCalls = traceResult.getLeafFunctions().stream().sorted(comparing(StackTraceFrame::getMethodName)).toList();
        assertEquals(3, leafCalls.size());
        assertEquals("<init>", leafCalls.get(0).getMethodName());
        assertEquals("functionThatThrows", leafCalls.get(1).getMethodName());
        assertEquals("stuckHere", leafCalls.get(2).getMethodName());

        assertThat(traceResult.getExceptionMessage(), containsString("IndexOutOfBoundsException"));
        assertThat(traceResult.getExceptionMessage(), containsString("oops threw an exception"));
    }

    @Test
    public void testTraceCorrectlyHandlesLambdas() {
        String MAIN = "com.ammaraskar.tracer.test.TraceeWithLambda";

        ExecutionTracer tracer = new ExecutionTracer("target/test-classes", MAIN);
        tracer.startExecution();
        TraceResult traceResult = tracer.getBestCandidateForWhereExecutionIsStuck();

        StackTrace stuckReason = traceResult.getStuckCandidateTrace();
        StackTraceFrame innerMostFrame = stuckReason.getFrames().get(0);
        assertEquals("functionCalledByLambda", innerMostFrame.getMethodName());

        // List of leaf calls so we can sort and test reliably.
        List<StackTraceFrame> leafCalls = traceResult.getLeafFunctions().stream().sorted(comparing(StackTraceFrame::getMethodName)).toList();
        assertEquals(2, leafCalls.size());
        assertEquals("<init>", leafCalls.get(0).getMethodName());
        assertEquals("functionCalledByLambda", leafCalls.get(1).getMethodName());
    }
}
