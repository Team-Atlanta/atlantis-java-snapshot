package com.oracle.truffle.espresso.concolic.box;

import com.oracle.truffle.api.concolic.*;
import com.oracle.truffle.espresso.concolic.*;
import com.oracle.truffle.espresso.meta.Meta;
import com.oracle.truffle.espresso.runtime.staticobject.StaticObject;
import com.oracle.truffle.espresso.descriptors.*;
import com.oracle.truffle.espresso.vm.InterpreterToVM;
import com.oracle.truffle.espresso.impl.*;

public class BooleanBox extends TopBox {
    public static Object wrapValueOf(Object[] args, String signature, Object returnedObject) {
        switch (signature) {
            case "(Z)Ljava/lang/Boolean;": {
                ConcolicBoolean arg0 = (ConcolicBoolean) args[0];
                if (!arg0.isSymbolic()) return returnedObject;
                ConcolicObjectImpl ret = ((ConcolicObjectImpl) returnedObject).clone();
                if (ret != null) {
                    ret.getOrCreateField(0).setExpr(arg0.getExpr());
                    return ret;
                }
                break;
            }
            // TODO: Add other cases
            default:
                break;
        }
        return returnedObject;
    }
}
