package com.oracle.truffle.api.concolic;
import com.oracle.truffle.api.concolic.ConcolicValue;

import com.oracle.truffle.api.frame.VirtualFrame;
import com.microsoft.z3.*;

public class ConcolicValueHelper {

    // var args to support any number of args
    public static boolean eitherSymbolic(ConcolicValueWrapper<?>... args) {
        for (ConcolicValueWrapper<?> v : args) {
            if (v.isSymbolic()) {
                return true;
            }
        }
        return false;
    }

    public static boolean eitherSymbolicExpr(Expr<?>... args) {
        synchronized (Z3Helper.getInstance()) {
            boolean flag = false;
            for (Expr<?> e : args) {
                if (e == null) {
                    continue;
                }
                Expr<?>[] constArgs = e.getArgs();
                for (Expr<?> constArg : constArgs) {
                    if(constArg.toString().contains("_")) {
                        flag = true;
                        return flag;
                    }
                }
            }
            return flag;
        }
    }

    // start from B_0 - bytearray length
    // B_1 - 1st element in the byte array
    private static int variableCount = -1;
    private static int collectionCount = -1;

    public synchronized static int getVariableCount() {
        return ++variableCount;
    }

    public synchronized static void resetVariableCount() {
        variableCount = -1;
    }

    public synchronized static int getCollectionCount() {
        return ++collectionCount;
    }

    public static String getSymbolicIntegerName() {
        return ("I_" + getVariableCount());
    }

    public static String getSymbolicByteName() {
        return ("B_" + getVariableCount());
    }

    public static String getSymbolicShortName() {
        return ("S_" + getVariableCount());
    }

    public static String getSymbolicBooleanName() {
        return ("Z_" + getVariableCount());
    }

    public static String getSymbolicLongName() {
        return ("J_" + getVariableCount());
    }

    public static String getSymbolicCharName() {
        return ("C_" + getVariableCount());
    }

    public static String getSymbolicFloatName() {
        return ("F_" + getVariableCount());
    }

    public static String getSymbolicDoubleName() {
        return ("D_" + getVariableCount());
    }

    public static String getSymbolicMapName() {
        return ("MAP_" + getCollectionCount());
    }

}
