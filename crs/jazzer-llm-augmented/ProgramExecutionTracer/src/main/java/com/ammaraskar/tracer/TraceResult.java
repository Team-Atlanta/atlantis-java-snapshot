package com.ammaraskar.tracer;

import java.util.Collection;
import java.util.Set;

/**
 * A little data class that gets serialized into json to be passed back to the python
 * module.
 */
public class TraceResult {
    private final StackTrace stuckCandidateTrace;
    private final boolean candidateFromException;
    private final String exceptionMessage;
    private final Collection<StackTraceFrame> leafFunctions;

    public TraceResult(StackTrace stuckCandidateTrace, boolean candidateFromException, String exceptionMessage, Collection<StackTraceFrame> leafFunctions) {
        this.stuckCandidateTrace = stuckCandidateTrace;
        this.candidateFromException = candidateFromException;
        this.exceptionMessage = exceptionMessage;
        this.leafFunctions = leafFunctions;
    }

    public StackTrace getStuckCandidateTrace() {
        return stuckCandidateTrace;
    }

    public Collection<StackTraceFrame> getLeafFunctions() {
        return leafFunctions;
    }

    public boolean isCandidateFromException() {
        return candidateFromException;
    }

    public String getExceptionMessage() {
        return exceptionMessage;
    }
}
