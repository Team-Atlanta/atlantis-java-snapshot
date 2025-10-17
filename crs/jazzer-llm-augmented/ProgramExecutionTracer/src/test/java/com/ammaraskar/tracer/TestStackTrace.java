package com.ammaraskar.tracer;

import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

public class TestStackTrace {

    @Test
    public void testStackTraceFrameEquality() {
        // Two stack frames on the same line and class should be the same.
        StackTraceFrame frame1 = new StackTraceFrame("com.foo.bar", "myMethod", "Bar.java", 23, "java.lang.Object");
        StackTraceFrame frame2 = new StackTraceFrame("com.foo.bar", "myMethod", "Bar.java", 23, "java.lang.Object");
        assertEquals(frame1, frame2);

        // Two stack frames on different lines but same class should not be the same.
        StackTraceFrame frame3 = new StackTraceFrame("com.foo.bar", "myMethod", "Bar.java", 24, "java.lang.Object");
        assertNotEquals(frame1, frame3);
    }

    @Test
    public void testStackTraceFrameToString() {
        StackTraceFrame frame1 = new StackTraceFrame("com.foo.bar", "myMethod", "Bar.java", 23, "java.lang.Object");
        assertEquals(frame1.toString(), "com.foo.bar.myMethod(Bar.java:23)");
    }

    @Test
    public void testStackTraceRemoveUpToFunctionCallThrowsWhenNoCall() {
        StackTrace trace = new StackTrace(0);
        trace.addFrame(new StackTraceFrame("com.foo.bar", "inner", "Bar.java", 23, "java.lang.Object"));
        trace.addFrame(new StackTraceFrame("com.foo.bar", "middle", "Bar.java", 13, "java.lang.Object"));

        assertThrows(IllegalArgumentException.class, () -> { trace.filterFramesBeforeFunctionCall("asdf"); });
    }

    @Test
    public void testStackTraceRemoveUpToFunctionCall() {
        StackTrace trace = new StackTrace(0);
        trace.addFrame(new StackTraceFrame("com.foo.bar", "inner", "Bar.java", 23, "java.lang.Object"));
        trace.addFrame(new StackTraceFrame("com.foo.bar", "middle", "Bar.java", 13, "java.lang.Object"));
        trace.addFrame(new StackTraceFrame("com.foo.bar", "outer", "Bar.java", 3, "java.lang.Object"));

        trace.filterFramesBeforeFunctionCall("middle");

        assertEquals(trace.toString(),
                """
                          com.foo.bar.inner(Bar.java:23)
                          com.foo.bar.outer(Bar.java:3)
                        """);
    }
}
