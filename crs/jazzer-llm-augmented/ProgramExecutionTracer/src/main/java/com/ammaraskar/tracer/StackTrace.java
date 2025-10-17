package com.ammaraskar.tracer;

import java.util.ArrayList;
import java.util.List;

/**
 * Identifies a code location with a series of {@link StackTraceFrame} elements.
 */
public class StackTrace {
    private final List<StackTraceFrame> frames;

    /**
     * After how many method entries was this stack trace reached?
     */
    private final long numMethodExecutions;

    public StackTrace(long numMethodExecutions) {
        frames = new ArrayList<>();
        this.numMethodExecutions = numMethodExecutions;
    }

    public List<StackTraceFrame> getFrames() {
        return frames;
    }

    public long getNumMethodExecutions() {
        return numMethodExecutions;
    }

    public void addFrame(StackTraceFrame element) {
        frames.add(element);
    }

    /**
     * Filters out any stack frames that happened before a function call. For example, if the stack looks like:
     * - innerMost
     * - caller
     * - outsideCaller
     * then filtering with "caller" will keep caller and innerMost, discarding outsideCaller.
     */
    public void filterFramesBeforeFunctionCall(String methodName) {
        int index = -1;
        for (int i = frames.size() - 1; i >= 0; i--) {
            if (!frames.get(i).getMethodName().equals(methodName)) {
                continue;
            }
            index = i;
            break;
        }
        if (index == -1) {
            throw new IllegalArgumentException("No method call found for " + methodName);
        }
        this.frames.subList(index, frames.size() - 1).clear();
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        for (StackTraceFrame element : frames) {
            sb.append("  ").append(element.toString()).append("\n");
        }
        return sb.toString();
    }

    @Override
    public final boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof StackTrace that)) return false;

        return frames.equals(that.frames);
    }

    @Override
    public int hashCode() {
        return frames.hashCode();
    }
}
