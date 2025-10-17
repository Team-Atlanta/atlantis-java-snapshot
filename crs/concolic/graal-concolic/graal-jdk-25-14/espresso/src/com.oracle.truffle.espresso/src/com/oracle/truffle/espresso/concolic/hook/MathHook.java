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

public class MathHook {
    public static Object wrapMethod(String className,
                                    String methodName,
                                    Object[] args,
                                    String signature,
                                    Object returnedObject) {
        if (!className.equals("java/lang/Math")) {
            throw new RuntimeException("[MathHook] bad className: " + className);
        }
        switch (methodName) {
            case "abs":
                if (Logger.compileLog) {
                    Logger.DEBUG("[MathHook] " + methodName);
                }
                switch (signature) {
                    case "(I)I": {
                        ConcolicInt arg0 = (ConcolicInt) args[0];
                        if (arg0.isSymbolic()) {
                            ConcolicInt ret = (ConcolicInt) ConcolicHelper.toConcolic(returnedObject);
                            ret.setExpr(Z3Helper.mkITE(Z3Helper.mkBVSGT(arg0.getExpr(), Z3Helper.getInstance().zeroExpr),
                                    arg0.getExpr(),
                                    arg0.Multiply(ConcolicInt.createWithoutConstraints(-1)).getExpr()));
                            return ret;
                        }
                        break;
                    }
                    case "(L)L": {
                        ConcolicLong arg0 = (ConcolicLong) args[0];
                        if (arg0.isSymbolic()) {
                            ConcolicLong ret = (ConcolicLong) ConcolicHelper.toConcolic(returnedObject);
                            ret.setExpr(Z3Helper.mkITE(Z3Helper.mkBVSGT(arg0.getExpr(), Z3Helper.getInstance().zeroExpr64),
                                    arg0.getExpr(),
                                    arg0.Multiply(ConcolicLong.createWithoutConstraints(-1)).getExpr()));
                            return ret;
                        }
                        break;
                    }
                }
                return returnedObject;
        }
        return returnedObject;
    }
}
