package com.oracle.truffle.espresso.concolic;

import com.oracle.truffle.api.concolic.*;
import com.oracle.truffle.espresso.meta.Meta;
import com.oracle.truffle.espresso.runtime.staticobject.StaticObject;

public class ConcolicExecutionManager {

    public static void atStartSymbolicExecution(Object[] args) {
        // enable logging starting from here
        Logger.enableLogging();
        ConcolicBranch.enableLogging();

        // YJ: This is where symbolic execution starts.
        // we can initialize anything required here
        if (Logger.compileLog) {
            Logger.DEBUG("[Starting symbolic execution]");
            Logger.DEBUG("Branch stack size: " + ConcolicBranch.getBranchList().size());
            Logger.DEBUG("Original target function arguments: ");
        }
        for (int i=0; i<args.length; ++i) {
            String s = "ARG[" + i + "] : ";
            if (args[i] == null) {
                s += "NULL";
            } else {
                String className = args[i].getClass().getName();
                if (args[i] instanceof ConcolicObject cObj) {
                    className += " - " + cObj.getClassName();
                } else if (args[i] instanceof ConcolicValueWrapper<?> cv) {
                    synchronized (Z3Helper.getInstance()) {
                        className += " : " + cv.getExpr();
                    }
                }
                s += className;
            }
            if (Logger.compileLog) {
                Logger.DEBUG(s);
            }
            if (args[i] instanceof ConcolicValueWrapper<?> cv) {
                if (cv.isSymbolic()) {
                    if (Logger.compileLog) {
                        Logger.WARNING("Don't symbolize: already symbolic");
                    }
                    return;
                }
            }
        }
        // symbolize arguments
        for (int i=0; i<args.length; ++i) {
            if (args[i] instanceof ConcolicLong cl) {
                args[i] = ConcolicLong.createNewSymbolicLong(cl. getConcreteValue());
            } else if (args[i] instanceof ConcolicInt ci) {
                args[i] = ConcolicInt.createNewSymbolicInt(ci.getConcreteValue());
            } else if (args[i] instanceof ConcolicShort cs) {
                args[i] = ConcolicShort.createNewSymbolicShort(cs.getConcreteValue());
            } else if (args[i] instanceof ConcolicByte cb) {
                args[i] = ConcolicByte.createNewSymbolicByte(cb.getConcreteValue());
            } else if (args[i] instanceof ConcolicObject co) {
                if (Logger.compileLog) {
                    Logger.DEBUG("[OBJECT] " + ((StaticObject) co.getConcreteValue()).getKlass().getName());
                }
                args[i] = ConcolicObjectFactory.createNewSymbolic((StaticObject) co.getConcreteValue());
            }
        }
        if (Logger.compileLog) {
            Logger.DEBUG("Symbolized target function arguments: ");
        }
        for (int i=0; i<args.length; ++i) {
            String s = "ARG[" + i + "] : ";
            if (args[i] == null) {
                s += "NULL";
            } else {
                String className = args[i].getClass().getName();
                if (args[i] instanceof ConcolicObject cObj) {
                    className += " - " + cObj.getClassName();
                } else if (args[i] instanceof ConcolicValueWrapper<?> cv) {
                    synchronized (Z3Helper.getInstance()) {
                        className += " : " + cv.getExpr();
                    }
                }
                s += className;
            }
            if (Logger.compileLog) {
                Logger.DEBUG(s);
            }
        }

    }

    public static void atFinishSymbolicExecution() {
        // Here, we do not check Logger.compileLog
        Logger.ALWAYS("[Finishing symbolic execution]");
        Logger.ALWAYS("Branch stack size: " + ConcolicBranch.getBranchList().size());

        //ConstraintManager.processConstraints();
        Logger.disableLogging();
        ConcolicBranch.disableLogging();
    }
}
