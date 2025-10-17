package com.oracle.truffle.espresso.concolic.hook;

import com.oracle.truffle.api.concolic.*;
import com.oracle.truffle.espresso.EspressoLanguage;
import com.oracle.truffle.espresso.classfile.JavaKind;
import com.oracle.truffle.espresso.concolic.*;
import com.oracle.truffle.espresso.meta.Meta;
import com.oracle.truffle.espresso.runtime.staticobject.StaticObject;
import com.oracle.truffle.espresso.descriptors.*;
import com.oracle.truffle.espresso.vm.InterpreterToVM;
import com.oracle.truffle.espresso.impl.*;

public class ObjectHook {
    private static boolean isFieldKindsEqual(ConcolicObjectImpl o1, ConcolicObjectImpl o2) {
        if (o1 == null || StaticObject.isNull(o1.getConcreteObject())) {
            return (o2 == null || StaticObject.isNull(o2.getConcreteObject()));
        }
        if (o1.getConcreteSize() != o2.getConcreteSize()) {
            if (Logger.compileLog) {
                Logger.WARNING("isFieldKindsEqual: size mismatch: " + o1.getConcreteSize() + " vs " + o2.getConcreteSize());
            }
            return false;
        }
        for (int i = 0; i < o1.getConcreteSize(); i++) {
            JavaKind o1FieldKind = o1.getFieldKind(i);
            JavaKind o2FieldKind = o2.getFieldKind(i);
            if (!o1FieldKind.equals(o2FieldKind)) {
                if (Logger.compileLog) {
                    Logger.WARNING("isFieldKindsEqual: type mismatch at field " + i + ": " + o1FieldKind + " vs " + o2FieldKind);
                }
                return false;
            }
        }
        return true;
    }

    public static void copyFields(ConcolicObjectImpl o1, ConcolicObjectImpl o2) {
        if (StaticObject.isNull(o1.getConcreteObject()) || StaticObject.isNull(o2.getConcreteObject())) {
            if (Logger.compileLog) {
                Logger.DEBUG("copyFields: isNull");
            }
            return;
        }
        // Check equality of types, not values (StaticObjects should be different)
        if (!isFieldKindsEqual(o1, o2)) {
            return;
        }
        // Copy Expr
        for (int i = 0; i < o2.getConcreteSize(); i++) {
            ConcolicValueWrapper<?> o2Field = o2.getField(i);
            if (o2Field == null) {
                continue;
            }
            if (o2Field instanceof ConcolicObjectImpl o2FieldObject) {
                if (o2FieldObject.isSymbolic()) {
                    copyFields((ConcolicObjectImpl) o1.getOrCreateField(i), o2FieldObject);
                }
            } else if (o2Field.isSymbolic()) {
                ConcolicValueWrapper<?> o1Concrete = o1.getConcreteFieldValue(i);
                if (!o1Concrete.getConcreteValue().equals(o2Field.getConcreteValue())) {
                    if (Logger.compileLog) {
                        synchronized (Z3Helper.getInstance()) {
                            Logger.WARNING("[ObjectHook] Mismatch clone() concolic: " + o2Field + ", concrete: " + o1Concrete);
                        }
                    }
                    o1.getOrCreateField(i).setValueWithConstraints(o1Concrete.getConcreteValue(), null);
                } else {
                    o1.getOrCreateField(i).setValueWithConstraints(o2Field.getConcreteValue(), o2Field.getExpr());
                }
            }
        }
    }

    public static Object wrapMethod(String className,
                                    String methodName,
                                    Object[] args,
                                    String signature,
                                    Object returnedObject) {
        if (!className.equals("java/lang/Object")) {
            throw new RuntimeException("[ObjectHook] bad className: " + className);
        }
        switch (methodName) {
            case "clone":
                switch (signature) {
                    case "()Ljava/lang/Object;":
                        if (Logger.compileLog) {
                            Logger.DEBUG("HOOK java/lang/Object.clone()");
                        }
                        if (returnedObject instanceof StaticObject) {
                            returnedObject = ConcolicObjectFactory.createWithoutConstraints(returnedObject);
                        }
                        if (returnedObject instanceof ConcolicObjectImpl ret) {
                            if (args[0] instanceof ConcolicObjectImpl obj) {
                                copyFields(ret, obj);
                            }
                        }
                        break;
                    default:
                        if (Logger.compileLog) {
                            Logger.DEBUG("Unsupported: " + signature);
                        }
                        break;
                }
                break;
        }
        return returnedObject;
    }
}
