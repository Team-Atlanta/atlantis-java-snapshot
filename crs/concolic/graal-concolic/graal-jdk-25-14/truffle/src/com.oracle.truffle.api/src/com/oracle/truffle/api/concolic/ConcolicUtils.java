package com.oracle.truffle.api.concolic;

public class ConcolicUtils {
    public static ThreadLocal<Object> latestReturnValue = ThreadLocal.withInitial(() -> new Object());
}
