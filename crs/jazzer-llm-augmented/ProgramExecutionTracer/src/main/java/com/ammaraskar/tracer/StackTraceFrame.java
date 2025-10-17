package com.ammaraskar.tracer;

import com.sun.jdi.AbsentInformationException;
import com.sun.jdi.Location;

import java.util.Objects;

/**
 * A basic class that holds a stack trace/stack frame code location.
 */
public class StackTraceFrame {
    private final String qualifiedClassName;
    private final String methodName;
    private final String sourceFileName;
    private final int lineNumber;
    private final String signature;

    public StackTraceFrame(String qualifiedClassName, String methodName, String sourceFileName, int lineNumber, String signature) {
        this.qualifiedClassName = qualifiedClassName;
        this.methodName = methodName;
        this.sourceFileName = sourceFileName;
        this.lineNumber = lineNumber;
        this.signature = signature;
    }

    @Override
    public String toString() {
        return qualifiedClassName + "." + methodName + "(" + sourceFileName + ":" + lineNumber + ")";
    }

    public static StackTraceFrame fromJdiLocation(Location loc) {
        String sourceFile = "unknown";
        try {
            sourceFile = loc.sourceName();
        } catch (AbsentInformationException ignored) {
        }

        return new StackTraceFrame(loc.declaringType().name(), loc.method().name(), sourceFile, loc.lineNumber(), loc.method().signature());
    }

    public String getMethodName() {
        return methodName;
    }

    public String getQualifiedClassName() {
        return qualifiedClassName;
    }

    public String getSourceFileName() { return sourceFileName; }

    public int getLineNumber() { return lineNumber; }

    public String getSignature() {return signature; }

    @Override
    public final boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof StackTraceFrame that)) return false;

        return lineNumber == that.lineNumber && qualifiedClassName.equals(that.qualifiedClassName);
    }

    @Override
    public int hashCode() {
        int result = qualifiedClassName.hashCode();
        result = 31 * result + lineNumber;
        return result;
    }

}
