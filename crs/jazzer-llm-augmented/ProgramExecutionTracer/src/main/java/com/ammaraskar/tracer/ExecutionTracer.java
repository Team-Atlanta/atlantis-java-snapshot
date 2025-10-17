package com.ammaraskar.tracer;

import com.sun.jdi.*;
import com.sun.jdi.event.ExceptionEvent;
import com.sun.jdi.event.LocatableEvent;
import com.sun.jdi.event.MethodEntryEvent;
import org.jdiscript.JDIScript;
import org.jdiscript.handlers.OnException;
import org.jdiscript.handlers.OnMethodEntry;
import org.jdiscript.handlers.OnVMStart;
import org.jdiscript.requests.ChainingMethodEntryRequest;
import org.jdiscript.util.VMLauncher;

import java.util.*;

public class ExecutionTracer implements OnMethodEntry, OnException {

    /**
     * Don't trace inside these classes, we don't care what happens in the internals of the standard library.
     */
    public static String[] CLASS_EXCLUSIONS_PREFIXES = {
            "java.", "jdk.internal.", "java.security.", "sun.", "com.sun."
    };

    private final String classPath;
    private final String mainClass;

    // Note the last N deepest call stacks.
    private static final int LAST_N_CALLS = 5;
    Deque<StackTrace> callStacks = new ArrayDeque<>();
    // Note the last N exceptions.
    private static final int LAST_N_EXCEPTIONS = 3;
    Deque<StackTrace> exceptionStacks = new ArrayDeque<>();
    Deque<String> exceptionMessages = new ArrayDeque<>();

    // Note the number of methods we've entered. This can be used to gauge "distance".
    private long numMethodEntries = 0;

    // Note which function calls are leaf calls and do not call any further functions.
    HashMap<String, StackTraceFrame> leafCalls = new HashMap<>();

    public ExecutionTracer(String classPath, String mainClass) {
        this.classPath = classPath;
        this.mainClass = mainClass;
    }

    public void startExecution() {
        JDIScript j = new JDIScript(new VMLauncher("-cp \"" + classPath + "\"", mainClass).start());

        OnVMStart onStart = se -> {
            // Create a method entry listener to hook into when we call methods.
            ChainingMethodEntryRequest entryRequest = j.methodEntryRequest(this);
            for (String exclusion : CLASS_EXCLUSIONS_PREFIXES) {
                entryRequest.addClassExclusionFilter(exclusion + "*");
            }
            entryRequest.enable();

            j.exceptionRequest(/*refType of null means all exceptions */null,
                    /*notifyCaught=*/true, /*notifyUncaught=*/true).addHandler(this).enable();
        };

        j.run(onStart);
    }

    /**
     * Picks the likely reason why execution is stuck right now.
     */
    public TraceResult getBestCandidateForWhereExecutionIsStuck() {
        // Pick the deepest call from callStacks.
        StackTrace candidate = callStacks.peek();
        for (StackTrace stackTrace : callStacks) {
            if (stackTrace.getFrames().size() > candidate.getFrames().size()) {
                candidate = stackTrace;
            }
        }

        // Whether the candidate we returned was caused by an exception or not.
        boolean candidateIsFromException = false;
        String exceptionMessage = null;
        // Always prefer exceptions if it looks like they were the last thing that happened before execution stopped.
        if (candidate == null) {
            candidate = exceptionStacks.peek();
        }
        Iterator<StackTrace> it = exceptionStacks.descendingIterator();
        Iterator<String> messageIt = exceptionMessages.descendingIterator();
        while (it.hasNext()) {
            StackTrace exceptionStackTrace = it.next();
            String message = messageIt.next();
            if (Math.abs(exceptionStackTrace.getNumMethodExecutions() - candidate.getNumMethodExecutions()) > 30) {
                continue;
            }

            candidate = exceptionStackTrace;
            candidateIsFromException = true;
            exceptionMessage = message;
            break;
        }

        return new TraceResult(candidate, candidateIsFromException, exceptionMessage, leafCalls.values());
    }

    @Override
    public void exception(ExceptionEvent exceptionEvent) {
        // Note exceptions, if they are close to the stack at the end they are probably the reason that fuzzing is
        // stalled out.
        StackTrace trace = stackTraceFromEvent(exceptionEvent, numMethodEntries);

        String exceptionToString = null;
        try {
            ObjectReference e = exceptionEvent.exception();
            Method toStringMethod = e.referenceType().methodsByName("toString").get(0);
            StringReference s = (StringReference)e.invokeMethod(exceptionEvent.thread(), toStringMethod, List.of(), ObjectReference.INVOKE_SINGLE_THREADED);
            exceptionToString = s.value();
        } catch (Exception e) {
            // Failed to get the string, oh well.
        }

        exceptionStacks.push(trace);
        exceptionMessages.push(exceptionToString);
        if (exceptionStacks.size() > LAST_N_EXCEPTIONS) {
            exceptionStacks.removeLast();
            exceptionMessages.removeLast();
        }
    }

    @Override
    public void methodEntry(MethodEntryEvent entry) {
        numMethodEntries++;
        // Peek the current call stack to see average depth. As a heuristic we want to only do the deepest last N
        // stacks.
        int averageStackDepth = 0;
        for (StackTrace trace : callStacks) {
            averageStackDepth += trace.getFrames().size();
        }
        averageStackDepth = !callStacks.isEmpty() ? averageStackDepth / callStacks.size() : 0;

        StackTrace trace = stackTraceFromEvent(entry, numMethodEntries);
        // If we're around 3 frames of the average stack depth, add it in.
        if ((trace.getFrames().size() + 3) >= averageStackDepth) {
            callStacks.push(trace);
            if (callStacks.size() > LAST_N_CALLS) {
                callStacks.removeLast();
            }
        }

        // Note any leaf function calls. Anything high up in the frame called us, so they are not leaf calls.
        for (StackTraceFrame frame : trace.getFrames()) {
            leafCalls.remove(classAndMethod(frame));
        }
        StackTraceFrame leafFrame = trace.getFrames().get(0);
        leafCalls.put(classAndMethod(leafFrame), leafFrame);

        //System.out.println("Class: " + entry.method().declaringType().name() + ", Method: " + entry.method().name());
        //System.out.println(trace);
    }

    // Used as a key to distinguish just a unique class and method, not caring about the particular line.
    private static String classAndMethod(StackTraceFrame frame) {
        return frame.getQualifiedClassName() + "." + frame.getMethodName() + " " + frame.getSignature();
    }

    private static StackTrace stackTraceFromEvent(LocatableEvent event, long numMethodEntries) {
        try {
            StackTrace trace = new StackTrace(numMethodEntries);
            for (StackFrame f : event.thread().frames()) {
                Location loc = f.location();
                StackTraceFrame frame = StackTraceFrame.fromJdiLocation(loc);

                // Filter them stack execution locations from java internal methods that we don't really care about.
                // For example, lambdas have a dozen frames of java.lang.invoke in them.
                boolean partOfIgnoredClasses = false;
                for (String ignoredClassPrefix : CLASS_EXCLUSIONS_PREFIXES) {
                    if (frame.getQualifiedClassName().startsWith(ignoredClassPrefix)) {
                        partOfIgnoredClasses = true;
                        break;
                    }
                }
                if (partOfIgnoredClasses) {
                    continue;
                }

                trace.addFrame(frame);
            }
            return trace;
        } catch (IncompatibleThreadStateException e) {
            throw new RuntimeException(e);
        }
    }
}
