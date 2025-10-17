package com.oracle.truffle.api.concolic;

import java.util.concurrent.ConcurrentHashMap;
import java.util.Map;

public class ConcolicHelper {
    private static Map<Integer, ConcolicValueWrapper<?>> symbolicMap = new ConcurrentHashMap<>();
    public static Map<Long, ConcolicValueWrapper<?>> allocMap = new ConcurrentHashMap<>();
    public static Map<Long, Long> allocSizeMap = new ConcurrentHashMap<>();
    public static Map<Integer, String> fdPathMap = new ConcurrentHashMap<>();
    public static Map<Integer, Long> fdOffsetMap = new ConcurrentHashMap<>();
    public static Map<String, Map<Long, ConcolicValueWrapper<?>>> fileContentMap = new ConcurrentHashMap<>();

    public static void reset() {
        symbolicMap.clear();
        allocMap.clear();
        allocSizeMap.clear();
        fdPathMap.clear();
        fdOffsetMap.clear();
        fileContentMap.clear();
    }

    public static boolean isConcolic(Object value) {
        return value instanceof ConcolicValueWrapper<?>;
    }

    public static Object checkConcolic(Object value) {
        if (!isConcolic(value)) {
            System.out.println("checkConcolic failed");
            throw new RuntimeException();
        }
        return value;
    }

    public static Object checkConcrete(Object value) {
        if (isConcolic(value)) {
            System.out.println("checkConcrete failed");
            throw new RuntimeException();
        }
        return value;
    }

    public static Object[] checkConcolic(Object[] values) {
        for (Object value : values) {
            checkConcolic(value);
        }
        return values;
    }

    public static Object[] checkConcrete(Object[] values) {
        for (Object value : values) {
            checkConcrete(value);
        }
        return values;
    }

    public static Object toConcrete(Object value) {
        return toConcrete(value, true);
    }

    public static Object toConcrete(Object value, boolean verbose) {
        if (value instanceof ConcolicValueWrapper<?> concolic) {
            if (Logger.compileLog) {
                if (verbose) {
                    Logger.DEBUG("[toConcrete] " + concolic);
                }
            }
            if (concolic.isSymbolic()) {
                if (concolic instanceof ConcolicObject concolicObj) {
                    ConcolicHelper.symbolicMap.putIfAbsent(concolicObj.getIdentityHashCode(), concolicObj);
                }
            }
            return ((ConcolicValueWrapper<?>) value).getConcreteValue();
        }
        return value;
    }

    public static Object[] toConcrete(Object[] value) {
        return toConcrete(value, true);
    }

    public static Object[] toConcrete(Object[] values, boolean verbose) {
        for (int i=0; i<values.length; i++) {
            values[i] = ConcolicHelper.toConcrete(values[i], verbose);
        }
        return values;
    }

    public static ConcolicValueWrapper<?> toConcolic(Object value) {
        return toConcolic(value, true);
    }

    public static ConcolicValueWrapper<?> toConcolic(Object value, boolean verbose) {
        if (value == null) {
            return null;
        } else if (value instanceof ConcolicValueWrapper<?> v) {
            return v;
        }
        if (Logger.compileLog) {
            if (verbose) {
                Logger.DEBUG("[toConcolic] " + value);
            }
        }
        if (value instanceof Integer v) {
            return ConcolicInt.createWithoutConstraints(v);
        } else if (value instanceof Long v) {
            return ConcolicLong.createWithoutConstraints(v);
        } else if (value instanceof Float v) {
            return ConcolicFloat.createWithoutConstraints(v);
        } else if (value instanceof Double v) {
            return ConcolicDouble.createWithoutConstraints(v);
        } else if (value instanceof Boolean v) {
            return ConcolicBoolean.createWithoutConstraints(v);
        } else if (value instanceof Byte v) {
            return ConcolicByte.createWithoutConstraints(v);
        } else if (value instanceof Character v) {
            return ConcolicChar.createWithoutConstraints(v);
        } else if (value instanceof Short v) {
            return ConcolicShort.createWithoutConstraints(v);
        } else if (value instanceof Object) {
            ConcolicValueWrapper<?> concolic = ConcolicHelper.symbolicMap.get(System.identityHashCode(value));
            if (concolic != null) {
                if (value == concolic.getConcreteValue()) {
                    if (Logger.compileLog) {
                        Logger.DEBUG("Cached: " + value + "@" + System.identityHashCode(value));
                    }
                    return concolic;
                }
                if (Logger.compileLog) {
                    Logger.WARNING("object is different from the cached symbolic object: " + value + " vs " + concolic.getConcreteValue());
                }
            }
            return ConcolicObject.createWithoutConstraints(value);
        } else {
            throw new IllegalArgumentException("Unsupported argument type: " + value.getClass());
        }
    }
}
