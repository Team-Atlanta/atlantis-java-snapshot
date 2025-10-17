package com.oracle.truffle.api.concolic;

import com.microsoft.z3.*;
import java.util.Objects;

public class ExposedMethods {
    public static ConcolicInt graalSymbolizeIntFromRaw(Integer value, String name) {
        ConcolicInt concolicInt = new ConcolicInt();
        Expr<?> expr = Z3Helper.createIntVar(name);
        return concolicInt;
    }
    public static void graalSymbolizeInt(ConcolicInt value, String name) {
        Expr<?> expr = Z3Helper.createIntVar(name);
        value.setValueWithConstraints(value.getConcreteValue(), expr);
    }

    public static void printExprFromObject(ConcolicObject value) {
        // NOTE: keep System.out.println instead of Logger.*
        System.out.println("[ExposedMethods] printExprFromObject");
        System.out.println(Objects.toString(value.getExpr(), null));

        ConcolicValueWrapper<?>[] fields = value.getFields();
        for (int slot = 0; slot < fields.length; slot++) {
            ConcolicValueWrapper<?> field_obj = fields[slot];
            if (field_obj != null && field_obj.getExpr() != null) {
                System.out.println("[ExposedMethods] Slot " + slot + " : " + field_obj.getExpr());
            }
        }
    }
}
