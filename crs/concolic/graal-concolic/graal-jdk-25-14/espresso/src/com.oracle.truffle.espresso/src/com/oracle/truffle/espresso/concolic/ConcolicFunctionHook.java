package com.oracle.truffle.espresso.concolic;

import com.oracle.truffle.api.concolic.*;
import com.oracle.truffle.espresso.impl.Field;
import com.oracle.truffle.espresso.runtime.staticobject.StaticObject;
import com.oracle.truffle.espresso.vm.InterpreterToVM;
import com.oracle.truffle.espresso.concolic.box.*;

import com.oracle.truffle.espresso.concolic.*;
import com.oracle.truffle.espresso.concolic.hook.*;
import com.oracle.truffle.espresso.concolic.hook.harness.*;

import com.microsoft.z3.*;

import java.io.*;
import java.util.*;

public class ConcolicFunctionHook {
    public static enum Type {
        STATIC,
        VIRTUAL,
        DYNAMIC,
        SPECIAL,
        INTERFACE,
    }

    static HashMap<String, HashSet<String>> shouldNotTrackExpressions = new HashMap<>();

    static {
        // java/lang/String
        // shouldNotTrackExpressions.put("java/lang/String", StringMethodHook.shouldNotTrackExpressions);
    }

    public static boolean shouldNotTrackExpression(String className, String methodName) {
        if (!shouldNotTrackExpressions.containsKey(className)) {
            return false;
        }
        return shouldNotTrackExpressions.get(className).contains(methodName);
    }

    public static Expr<?>[] backupExpressions(Object[] args) {
        Expr<?>[] backup = new Expr<?>[args.length];
        for (int i=0; i<args.length; ++i) {
            if (args[i] instanceof ConcolicValueWrapper<?>) {
                backup[i] = ((ConcolicValueWrapper<?>) args[i]).getExpr();
            } else {
                backup[i] = null;
            }
        }
        return backup;
    }

    public static void restoreExpressions(Object[] args, Expr<?>[] backup) {
        for (int i=0; i<args.length; ++i) {
            if (backup[i] != null) {
                ((ConcolicValueWrapper<?>) args[i]).setExpr(backup[i]);
            }
        }
    }

    public static void invokeHook(String className, String methodName, Type type,
            Object this_obj, Object[] args, String signature) {
        if (Logger.compileLog) {
            String classAndMethodName = className + "." + methodName;
            Logger.DEBUG("[INVOKEHOOK] " + type.toString() + " " + classAndMethodName + signature);
        }

        try {
            if (Logger.compileLog) {
                synchronized (Z3Helper.getInstance()) {
                    for (int i=0; i<args.length; ++i) {
                        Logger.DEBUG(String.format("args[%d]: %s", i, args[i].toString()));
                    }
                }
            }

            // Method name
            // switch (methodName) {
            //     case "fuzzerTestOneInput", "startSymbolicExecutionBytes", "startSymbolicExecutionProvider": {
            //         ConcolicExecutionManager.atStartSymbolicExecution(args);
            //         break;
            //     }
            //     default:
            //         break;
            // }
            switch(className) {
                case "sun/nio/fs/UnixNativeDispatcher", "sun/nio/ch/UnixFileDispatcherImpl",
                            "java/io/FileOutputStream", "java/io/FileInputStream", "java/io/RandomAccessFile":
                    FileIOHook.wrapInvokeMethod(className, methodName, args, signature);
                    break;
            }

            SentinelHook.wrapMethod(className, methodName, args, signature);

        } catch (Exception e) {
            if (Logger.compileLog) {
                StringWriter sw = new StringWriter();
                e.printStackTrace(new PrintWriter(sw));
                System.out.println("[INVOKEHOOK] Exception: " + sw.toString());
            }
        }
    }

    public static Object returnHook(String className, String methodName,
            Type type, Object returnedObject, Object this_obj, Object[] args, String signature) {
        String classAndMethodName = className + "." + methodName;
        if (Logger.compileLog) {
            Logger.DEBUG("[RETURNHOOK] " + type.toString() + " " + classAndMethodName + signature);
        }
        try {
            // Method name
            switch (methodName) {
                case "fuzzerTestOneInput", "startSymbolicExecutionBytes", "startSymbolicExecutionProvider": {
                    ConcolicExecutionManager.atFinishSymbolicExecution();
                    return returnedObject;
                }
                default:
                    break;
            }

            switch (className) {
                case "com/code_intelligence/jazzer/api/FuzzedDataProvider",
                        "com/code_intelligence/jazzer/driver/FuzzedDataProviderImpl":
                    return FuzzedDataProviderMethodHook.wrapMethod(className, methodName, this_obj, args, signature, returnedObject);
                case "java/lang/System": {
                    returnedObject = SystemMethodHook.wrapMethod(className, methodName, this_obj, args, signature, returnedObject);
                    return returnedObject;
                }
                case "java/lang/String": {
                    returnedObject = StringMethodHook.wrapMethod(className, methodName, this_obj, args, signature, returnedObject);
                    return returnedObject;
                }
                case "java/lang/StringBuilder": {
                    returnedObject = StringBuilderMethodHook.wrapMethod(className, methodName, this_obj, args, signature, returnedObject);
                    return returnedObject;
                }
                case "java/lang/invoke/StringConcatFactory": {
                    // TODO: Implement this for 'String s20 = "000" + s17.toUpperCase();'
                    return returnedObject;
                }
                case "jdk/internal/misc/Unsafe":
                    return UnsafeHook.wrapMethod(className, methodName, args, signature, returnedObject);
                case "java/lang/Object":
                    return ObjectHook.wrapMethod(className, methodName, args, signature, returnedObject);
                case "java/lang/Math": {
                    return MathHook.wrapMethod(className, methodName, args, signature, returnedObject);
                }case "sun/nio/fs/UnixNativeDispatcher", "sun/nio/ch/UnixFileDispatcherImpl",
                        "java/io/FileOutputStream", "java/io/FileInputStream":
                    return FileIOHook.wrapMethod(className, methodName, args, signature, returnedObject);
                default:
                    break;
            }

            switch (classAndMethodName) {
                case "java/lang/ref/Reference.<init>": {
                    if (signature.equals("(Ljava/lang/Object;Ljava/lang/ref/ReferenceQueue;)V")) {
                        if (Logger.compileLog) {
                            Logger.DEBUG("HOOK " + classAndMethodName);
                        }
                        StaticObject receiver = (StaticObject) ((ConcolicObject) this_obj).getConcreteValue();
                        Field referentField = receiver.getKlass().getMeta().java_lang_ref_Reference_referent;
                        Field queueField = receiver.getKlass().getMeta().java_lang_ref_Reference_queue;
                        ((ConcolicObjectImpl) this_obj).putField(referentField.getSlot(), (ConcolicObject) args[1]);
                        ((ConcolicObjectImpl) this_obj).putField(queueField.getSlot(), (ConcolicObject) args[2]);
                    } else {
                        if (Logger.compileLog) {
                            Logger.DEBUG("Unknown signature: " + signature);
                        }
                    }
                    break;
                }
                case "java/io/FileDescriptor.close0": {
                    if (signature.equals("()V")) {
                        ConcolicObjectImpl fdObj = (ConcolicObjectImpl) ConcolicHelper.toConcolic(args[0]);
                        int fd = (int) ConcolicHelper.toConcrete(fdObj.getOrCreateField(0));
                        String path = ConcolicHelper.fdPathMap.remove(fd);
                        if (Logger.compileLog) {
                            Logger.DEBUG("[FileDescriptor] close0 fd: " + fd + ", path: " + path);
                        }
                    }
                }
                case "java/lang/Integer.valueOf": {
                    return IntegerBox.wrapValueOf(args, signature, returnedObject);
                }
                case "java/lang/Long.valueOf": {
                    return LongBox.wrapValueOf(args, signature, returnedObject);
                }
                case "java/lang/Short.valueOf": {
                    return ShortBox.wrapValueOf(args, signature, returnedObject);
                }
                case "java/lang/Byte.valueOf": {
                    return ByteBox.wrapValueOf(args, signature, returnedObject);
                }
                case "java/lang/Character.valueOf": {
                    // TODO: Test this
                    return CharacterBox.wrapValueOf(args, signature, returnedObject);
                }
                case "java/lang/Boolean.valueOf": {
                    // TODO: Test this
                    return BooleanBox.wrapValueOf(args, signature, returnedObject);
                }
                default:
                    break;
            }

            // if (this_obj instanceof ConcolicObjectImpl concolic) {
            //     if (concolic.isCollection() && !concolic.isSet()) { // Set is internally using Map
            //         return CollectionHook.wrapMethod(className, methodName, args, signature, returnedObject);
            //     }
            // }

            if (returnedObject instanceof ConcolicValueWrapper<?>)
                return returnedObject;
            if (returnedObject instanceof StaticObject) {
                return ConcolicObjectFactory.createWithoutConstraints(returnedObject);
            }
            switch (signature.charAt(signature.length() -1)) {
                case 'Z':
                    return ConcolicBoolean.createWithoutConstraints((Boolean) returnedObject);
                case 'B':
                    return ConcolicByte.createWithoutConstraints((Byte) returnedObject);
                case 'C':
                    return ConcolicChar.createWithoutConstraints((Character) returnedObject);
                case 'D':
                    return ConcolicDouble.createWithoutConstraints((Double) returnedObject);
                case 'F':
                    return ConcolicFloat.createWithoutConstraints((Float) returnedObject);
                case 'I':
                    return ConcolicInt.createWithoutConstraints((Integer) returnedObject);
                case 'J':
                    return ConcolicLong.createWithoutConstraints((Long) returnedObject);
                case 'S':
                    return ConcolicShort.createWithoutConstraints((Short) returnedObject);
                case ';':
                    return ConcolicObjectFactory.createWithoutConstraints(returnedObject);
                default:
                    if (Logger.compileLog) {
                        Logger.DEBUG("Unsupported: " + signature);
                    }
                    return returnedObject;
            }
        } catch (Exception e) {
            if (Logger.compileLog) {
                StringWriter sw = new StringWriter();
                e.printStackTrace(new PrintWriter(sw));
                System.out.println("[RETURNHOOK] Exception: " + sw.toString());
            }
            return returnedObject;
        }
    }
}
