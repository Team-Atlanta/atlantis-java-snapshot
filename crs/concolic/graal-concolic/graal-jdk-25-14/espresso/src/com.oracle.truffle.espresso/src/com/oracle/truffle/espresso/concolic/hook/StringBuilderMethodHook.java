package com.oracle.truffle.espresso.concolic.hook;

import com.oracle.truffle.api.concolic.*;
import com.oracle.truffle.espresso.concolic.*;
import com.oracle.truffle.espresso.meta.Meta;
import com.oracle.truffle.espresso.runtime.staticobject.StaticObject;
import com.oracle.truffle.espresso.descriptors.*;
import com.oracle.truffle.espresso.vm.InterpreterToVM;
import com.oracle.truffle.espresso.impl.*;

import com.microsoft.z3.*;

public class StringBuilderMethodHook extends CompleteHook {
    public static Object wrapMethod(String className,
                                    String methodName,
                                    Object target_obj,
                                    Object[] args,
                                    String signature,
                                    Object returnedObject) {
        if (!className.equals("java/lang/StringBuilder")) {
            throw new RuntimeException("[StringBuilderMethodHook] bad className: " + className);
        }

        switch (methodName) {
            case "<init>": {
                return wrapInit(target_obj, args, signature, returnedObject);
            }
            case "append": {
                return wrapAppend(target_obj, args, signature, returnedObject);
            }
            case "appendCodePoint": {
                return wrapAppendCodePoint(target_obj, args, signature, returnedObject);
            }
            case "capacity": {
                return wrapCapacity(target_obj, args, signature, returnedObject);
            }
            case "charAt": {
                return wrapCharAt(target_obj, args, signature, returnedObject);
            }
            case "chars": {
                return wrapChars(target_obj, args, signature, returnedObject);
            }
            case "codePointAt": {
                return wrapCodePointAt(target_obj, args, signature, returnedObject);
            }
            case "codePointBefore": {
                return wrapCodePointBefore(target_obj, args, signature, returnedObject);
            }
            case "codePointCount": {
                return wrapCodePointCount(target_obj, args, signature, returnedObject);
            }
            case "codePoints": {
                return wrapCodePoints(target_obj, args, signature, returnedObject);
            }
            case "compareTo": {
                return wrapCompareTo(target_obj, args, signature, returnedObject);
            }
            case "delete": {
                return wrapDelete(target_obj, args, signature, returnedObject);
            }
            case "deleteCharAt": {
                return wrapDeleteCharAt(target_obj, args, signature, returnedObject);
            }
            case "ensureCapacity": {
                return wrapEnsureCapacity(target_obj, args, signature, returnedObject);
            }
            case "getChars": {
                return wrapGetChars(target_obj, args, signature, returnedObject);
            }
            case "indexOf": {
                return wrapIndexOf(target_obj, args, signature, returnedObject);
            }
            case "insert": {
                return wrapInsert(target_obj, args, signature, returnedObject);
            }
            case "lastIndexOf": {
                return wrapLastIndexOf(target_obj, args, signature, returnedObject);
            }
            case "length": {
                return wrapLength(target_obj, args, signature, returnedObject);
            }
            case "offsetByCodePoints": {
                return wrapOffsetByCodePoints(target_obj, args, signature, returnedObject);
            }
            case "replace": {
                return wrapReplace(target_obj, args, signature, returnedObject);
            }
            case "reverse": {
                return wrapReverse(target_obj, args, signature, returnedObject);
            }
            case "setCharAt": {
                return wrapSetCharAt(target_obj, args, signature, returnedObject);
            }
            case "setLength": {
                return wrapSetLength(target_obj, args, signature, returnedObject);
            }
            case "subSequence": {
                return wrapSubSequence(target_obj, args, signature, returnedObject);
            }
            case "substring": {
                return wrapSubstring(target_obj, args, signature, returnedObject);
            }
            case "toString": {
                return wrapToString(target_obj, args, signature, returnedObject);
            }
            case "trimToSize": {
                return wrapTrimToSize(target_obj, args, signature, returnedObject);
            }
            default: {
                break;
            }
        }

        return returnedObject;
    }

    public static Object wrapInit(Object target_obj,
                                      Object[] args,
                                      String signature,
                                      Object returnedObject) {
        if (Logger.compileLog) {
            Logger.DEBUG("[StringBuilderMethodHook.<init>]: " + signature);
        }
        return returnedObject;
    }

    public static Object wrapAppend(Object target_obj,
                                     Object[] args,
                                     String signature,
                                     Object returnedObject) {
        if (Logger.compileLog) {
            Logger.DEBUG("[StringBuilderMethodHook.append]: Not implemented " + signature);
        }
        return returnedObject;
    }

    public static Object wrapAppendCodePoint(Object target_obj,
                                             Object[] args,
                                             String signature,
                                             Object returnedObject) {
        if (Logger.compileLog) {
            Logger.DEBUG("[StringBuilderMethodHook.appendCodePoint]: Not implemented " + signature);
        }
        return returnedObject;
    }

    public static Object wrapCapacity(Object target_obj,
                                       Object[] args,
                                       String signature,
                                       Object returnedObject) {
        if (Logger.compileLog) {
            Logger.DEBUG("[StringBuilderMethodHook.capacity]: Not implemented " + signature);
        }
        return returnedObject;
    }

    public static Object wrapCharAt(Object target_obj,
                                     Object[] args,
                                     String signature,
                                     Object returnedObject) {
        if (Logger.compileLog) {
            Logger.DEBUG("[StringBuilderMethodHook.charAt]: Not implemented " + signature);
        }
        return returnedObject;
    }

    public static Object wrapChars(Object target_obj,
                                    Object[] args,
                                    String signature,
                                    Object returnedObject) {
        if (Logger.compileLog) {
            Logger.DEBUG("[StringBuilderMethodHook.chars]: Not implemented " + signature);
        }
        return returnedObject;
    }

    public static Object wrapCodePointAt(Object target_obj,
                                          Object[] args,
                                          String signature,
                                          Object returnedObject) {
        if (Logger.compileLog) {
            Logger.DEBUG("[StringBuilderMethodHook.codePointAt]: Not implemented " + signature);
        }
        return returnedObject;
    }

    public static Object wrapCodePointBefore(Object target_obj,
                                              Object[] args,
                                              String signature,
                                              Object returnedObject) {
        if (Logger.compileLog) {
            Logger.DEBUG("[StringBuilderMethodHook.codePointBefore]: Not implemented " + signature);
        }
        return returnedObject;
    }

    public static Object wrapCodePointCount(Object target_obj,
                                             Object[] args,
                                             String signature,
                                             Object returnedObject) {
        if (Logger.compileLog) {
            Logger.DEBUG("[StringBuilderMethodHook.codePointCount]: Not implemented " + signature);
        }
        return returnedObject;
    }

    public static Object wrapCodePoints(Object target_obj,
                                         Object[] args,
                                         String signature,
                                         Object returnedObject) {
        if (Logger.compileLog) {
            Logger.DEBUG("[StringBuilderMethodHook.codePoints]: Not implemented " + signature);
        }
        return returnedObject;
    }

    public static Object wrapCompareTo(Object target_obj,
                                        Object[] args,
                                        String signature,
                                        Object returnedObject) {
        if (Logger.compileLog) {
            Logger.DEBUG("[StringBuilderMethodHook.compareTo]: Not implemented " + signature);
        }
        return returnedObject;
    }

    public static Object wrapDelete(Object target_obj,
                                     Object[] args,
                                     String signature,
                                     Object returnedObject) {
        if (Logger.compileLog) {
            Logger.DEBUG("[StringBuilderMethodHook.delete]: Not implemented " + signature);
        }
        return returnedObject;
    }

    public static Object wrapDeleteCharAt(Object target_obj,
                                           Object[] args,
                                           String signature,
                                           Object returnedObject) {
        if (Logger.compileLog) {
            Logger.DEBUG("[StringBuilderMethodHook.deleteCharAt]: Not implemented " + signature);
        }
        return returnedObject;
    }

    public static Object wrapEnsureCapacity(Object target_obj,
                                             Object[] args,
                                             String signature,
                                             Object returnedObject) {
        if (Logger.compileLog) {
            Logger.DEBUG("[StringBuilderMethodHook.ensureCapacity]: Not implemented " + signature);
        }
        return returnedObject;
    }

    public static Object wrapGetChars(Object target_obj,
                                       Object[] args,
                                       String signature,
                                       Object returnedObject) {
        if (Logger.compileLog) {
            Logger.DEBUG("[StringBuilderMethodHook.getChars]: Not implemented " + signature);
        }
        return returnedObject;
    }

    public static Object wrapIndexOf(Object target_obj,
                                      Object[] args,
                                      String signature,
                                      Object returnedObject) {
        if (Logger.compileLog) {
            Logger.DEBUG("[StringBuilderMethodHook.indexOf]: Not implemented " + signature);
        }
        return returnedObject;
    }

    public static Object wrapInsert(Object target_obj,
                                     Object[] args,
                                     String signature,
                                     Object returnedObject) {
        if (Logger.compileLog) {
            Logger.DEBUG("[StringBuilderMethodHook.insert]: Not implemented " + signature);
        }
        return returnedObject;
    }

    public static Object wrapLastIndexOf(Object target_obj,
                                          Object[] args,
                                          String signature,
                                          Object returnedObject) {
        if (Logger.compileLog) {
            Logger.DEBUG("[StringBuilderMethodHook.lastIndexOf]: Not implemented " + signature);
        }
        return returnedObject;
    }

    public static Object wrapLength(Object target_obj,
                                     Object[] args,
                                     String signature,
                                     Object returnedObject) {
        if (Logger.compileLog) {
            Logger.DEBUG("[StringBuilderMethodHook.length]: Not implemented " + signature);
        }
        return returnedObject;
    }

    public static Object wrapOffsetByCodePoints(Object target_obj,
                                                 Object[] args,
                                                 String signature,
                                                 Object returnedObject) {
        if (Logger.compileLog) {
            Logger.DEBUG("[StringBuilderMethodHook.offsetByCodePoints]: Not implemented " + signature);
        }
        return returnedObject;
    }

    public static Object wrapReplace(Object target_obj,
                                      Object[] args,
                                      String signature,
                                      Object returnedObject) {
        if (Logger.compileLog) {
            Logger.DEBUG("[StringBuilderMethodHook.replace]: Not implemented " + signature);
        }
        return returnedObject;
    }

    public static Object wrapReverse(Object target_obj,
                                     Object[] args,
                                     String signature,
                                     Object returnedObject) {
        if (Logger.compileLog) {
            Logger.DEBUG("[StringBuilderMethodHook.reverse]: Not implemented " + signature);
        }
        return returnedObject;
    }

    public static Object wrapSetCharAt(Object target_obj,
                                        Object[] args,
                                        String signature,
                                        Object returnedObject) {
        if (Logger.compileLog) {
            Logger.DEBUG("[StringBuilderMethodHook.setCharAt]: Not implemented " + signature);
        }
        return returnedObject;
    }

    public static Object wrapSetLength(Object target_obj,
                                        Object[] args,
                                        String signature,
                                        Object returnedObject) {
        if (Logger.compileLog) {
            Logger.DEBUG("[StringBuilderMethodHook.setLength]: Not implemented " + signature);
        }
        return returnedObject;
    }

    public static Object wrapSubSequence(Object target_obj,
                                          Object[] args,
                                          String signature,
                                          Object returnedObject) {
        if (Logger.compileLog) {
            Logger.DEBUG("[StringBuilderMethodHook.subSequence]: Not implemented " + signature);
        }
        return returnedObject;
    }

    public static Object wrapSubstring(Object target_obj,
                                        Object[] args,
                                        String signature,
                                        Object returnedObject) {
        if (Logger.compileLog) {
            Logger.DEBUG("[StringBuilderMethodHook.substring]: Not implemented " + signature);
        }
        return returnedObject;
    }

    public static Object wrapToString(Object target_obj,
                                       Object[] args,
                                       String signature,
                                       Object returnedObject) {
        if (Logger.compileLog) {
            Logger.DEBUG("[StringBuilderMethodHook.toString]: Not implemented " + signature);
        }
        return returnedObject;
    }

    public static Object wrapTrimToSize(Object target_obj,
                                         Object[] args,
                                         String signature,
                                         Object returnedObject) {
        if (Logger.compileLog) {
            Logger.DEBUG("[StringBuilderMethodHook.trimToSize]: Not implemented " + signature);
        }
        return returnedObject;
    }
}
