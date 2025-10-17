package com.oracle.truffle.espresso.concolic.hook;

import com.oracle.truffle.api.concolic.*;
import com.oracle.truffle.espresso.concolic.*;
import com.oracle.truffle.espresso.meta.Meta;
import com.oracle.truffle.espresso.runtime.staticobject.StaticObject;
import com.oracle.truffle.espresso.descriptors.*;
import com.oracle.truffle.espresso.vm.InterpreterToVM;
import com.oracle.truffle.espresso.impl.*;

public class SystemMethodHook extends CompleteHook {
    public static Object wrapMethod(String className,
                                    String methodName,
                                    Object target_obj,
                                    Object[] args,
                                    String signature,
                                    Object returnedObject) {
        if (!className.equals("java/lang/System")) {
            throw new RuntimeException("[SystemMethodHook] bad className: " + className);
        }

        switch (methodName) {
            case "arraycopy": {
                return wrapArraycopy(target_obj, args, signature, returnedObject);
            }
            default:
                break;
        }

        return returnedObject;
    }

    public static Object wrapArraycopy(Object target_obj,
                                      Object[] args,
                                      String signature,
                                      Object returnedObject) {
        if (Logger.compileLog) {
            Logger.DEBUG("[SystemMethodHook.wrapArraycopy]: " + signature);
        }
        switch (signature) {
            case "(Ljava/lang/Object;ILjava/lang/Object;II)V": {
                if (args[0] instanceof ConcolicObjectImpl srcArray) {
                    if (!srcArray.isSymbolic()) {
                        return returnedObject;
                    }
                    if (args[2] instanceof ConcolicObjectImpl dstArray) {
                        ConcolicInt srcStartIdx = (ConcolicInt) args[1];
                        ConcolicInt dstStartIdx = (ConcolicInt) args[3];
                        ConcolicInt length = (ConcolicInt) args[4];
                        int c_srcStartIdx = srcStartIdx.getConcreteValue();
                        int c_dstStartIdx = dstStartIdx.getConcreteValue();
                        int c_length = length.getConcreteValue();
                        for (int i=0; i<c_length; ++i) {
                            ConcolicValueWrapper<?> src = srcArray.getOrCreateField(c_srcStartIdx + i);
                            ConcolicValueWrapper<?> dstField = dstArray.getConcreteFieldValue(c_dstStartIdx + i);
                            if (src instanceof ConcolicObjectImpl srcObj) {
                                if (dstField instanceof ConcolicObjectImpl dstObj) {
                                    ObjectHook.copyFields(dstObj, srcObj);
                                    dstArray.putField(c_dstStartIdx + i, dstObj);
                                } else if (Logger.compileLog) {
                                    Logger.WARNING("[SystemMethodHook] Unexpected state");
                                }
                            } else if (dstField.getConcreteValue() != src.getConcreteValue()) {
                                if (Logger.compileLog && src.isSymbolic()) {
                                    synchronized (Z3Helper.getInstance()) {
                                        Logger.WARNING("[SystemMethodHook] Mismatch arraycopy concolic: " + src + ", concrete: " + dstField);
                                    }
                                }
                                ConcolicValueWrapper<?> dst = dstArray.getOrCreateField(c_dstStartIdx + i);
                                dst.setValueWithConstraints(dstField.getConcreteValue(), null);
                            } else {
                                ConcolicValueWrapper<?> dst = dstArray.getOrCreateField(c_dstStartIdx + i);
                                dst.setValueWithConstraints(src.getConcreteValue(), src.getExpr());
                            }
                        }
                    }
                }
                break;
            }
            default:
                break;
        }
        return returnedObject;
    }
}
