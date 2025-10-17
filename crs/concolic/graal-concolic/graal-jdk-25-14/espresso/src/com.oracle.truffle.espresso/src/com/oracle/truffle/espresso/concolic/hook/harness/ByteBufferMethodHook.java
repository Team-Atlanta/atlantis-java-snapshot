package com.oracle.truffle.espresso.concolic.hook.harness;

import com.oracle.truffle.api.concolic.*;
import com.oracle.truffle.espresso.concolic.*;
import com.oracle.truffle.espresso.meta.Meta;
import com.oracle.truffle.espresso.runtime.staticobject.StaticObject;
import com.oracle.truffle.espresso.descriptors.*;
import com.oracle.truffle.espresso.vm.InterpreterToVM;
import com.oracle.truffle.espresso.impl.*;

import com.oracle.truffle.espresso.concolic.hook.*;

import com.microsoft.z3.*;

public class ByteBufferMethodHook extends CompleteHook {
    public static Object wrapMethod(String className,
                                    String methodName,
                                    Object target_obj,
                                    Object[] args,
                                    String signature,
                                    Object returnedObject) {
        if (Logger.compileLog) {
            Logger.DEBUG("[ByteBufferHook]: " + className + "." + methodName + signature);
        }
        /*
        if (!className.equals("java/nio/ByteBuffer")) {
            throw new RuntimeException("[ByteBufferHook] bad className: " + className);
        }
        */
        if (target_obj != null) {
            if (!(target_obj instanceof ConcolicObjectImpl)) {
                if (Logger.compileLog) {
                    Logger.DEBUG("[ByteBufferHook.get()] target_obj class mismatch: " + target_obj.getClass().getName().toString());
                }
                return returnedObject;
            }
            ConcolicObjectImpl targetObject = (ConcolicObjectImpl) target_obj;
            Integer isSymbolicInt = (Integer) (targetObject.getExtraData("isSymbolicInt"));
            if (isSymbolicInt == null || isSymbolicInt.intValue() == 0) {
                return returnedObject;
            }
        }
        switch (methodName) {
            case "wrap": {
                return wrapWrap(target_obj, args, signature, returnedObject);
            }
            case "getInt": {
                return wrapGetInt(target_obj, args, signature, returnedObject);
            }
            case "getShort":  {
                return wrapGetShort(target_obj, args, signature, returnedObject);
            }
            case "getLong":  {
                return wrapGetLong(target_obj, args, signature, returnedObject);
            }
            case "get": {
                return wrapGet(target_obj, args, signature, returnedObject);
            }
            default:
                break;
        }
        switch (signature) {
            default:
                break;
        }
        return returnedObject;
    }

    public static Object wrapWrap(Object target_obj,
                                        Object[] args,
                                        String signature,
                                        Object returnedObject) {
        if (Logger.compileLog) {
            Logger.DEBUG("[ByteBufferHook] - static wrap(): " + signature);
        }
        switch (signature) {
            case "([B)Ljava/nio/ByteBuffer;": {
                ConcolicObjectImpl retObject = (ConcolicObjectImpl) returnedObject;
                retObject.putExtraData("byteStream", args[0]);
                retObject.putExtraData("prevIndex", Integer.valueOf(0));
                retObject.putExtraData("currentIndex", Integer.valueOf(0));
                ConcolicArrayObject byteStreamArray = (ConcolicArrayObject) args[0];
                ConcolicInt arraySize = byteStreamArray.getSize();
                int arraysize = arraySize.getConcreteValue();
                int isSymbolicInt = 0;
                for (int i=0; i < arraysize; ++i) {
                    ConcolicValueWrapper<?> element = byteStreamArray.getElement(i);
                    if (element.getExpr() != null) {
                        isSymbolicInt = 1;
                        break;
                    }
                }
                if (isSymbolicInt == 1) {
                    if (Logger.compileLog) {
                        Logger.DEBUG("Wrapping Symbolic bytestream");
                    }
                }
                else {
                    if (Logger.compileLog) {
                        Logger.DEBUG("Wrapping non-symbolic bytestream");
                    }
                }
                retObject.putExtraData("isSymbolicInt", Integer.valueOf(isSymbolicInt));

                if (Logger.compileLog) {
                    Logger.DEBUG("Put bytestream = " + args[0].toString());
                }
                break;
            }
            default:
                break;
        }
        return returnedObject;
    }

    public static Object wrapGet(Object target_obj, Object[] args, String signature, Object returnedObject) {
        if (Logger.compileLog) {
            Logger.DEBUG("[ByteBufferHook] - virtual get(): " + signature);
            Logger.DEBUG("this - " + target_obj.toString());
            Logger.DEBUG("returnedObject - " + returnedObject.toString());
        }
        if (!(target_obj instanceof ConcolicObjectImpl)) {
            if (Logger.compileLog) {
                Logger.DEBUG("[ByteBufferHook.get()] target_obj class mismatch: " + target_obj.getClass().getName().toString());
            }
            return returnedObject;
        }
        if (!(returnedObject instanceof ConcolicByte)) {
            if (Logger.compileLog) {
                Logger.DEBUG("[ByteBufferHook.get()] returnedObject class mismatch: " + returnedObject.getClass().getName().toString());
            }
            return returnedObject;
        }

        ConcolicObjectImpl targetObject = (ConcolicObjectImpl) target_obj;
        ConcolicObjectImpl byteStreamObject = (ConcolicObjectImpl) targetObject.getExtraData("byteStream");
        ConcolicByte retObject = (ConcolicByte) returnedObject;

        if (byteStreamObject == null) { return returnedObject; }

        int prevIndex = ((Integer)targetObject.getExtraData("prevIndex")).intValue();
        int currentIndex = ((Integer) targetObject.getExtraData("currentIndex")).intValue();

        if (Logger.compileLog) {
            Logger.DEBUG(String.format("[ByteBufferHook.getShort()] prev %d current %d", prevIndex, currentIndex));
        }
        // get each byte and build
        prevIndex = currentIndex;
        currentIndex += 1;
        targetObject.putExtraData("prevIndex", Integer.valueOf(prevIndex));
        targetObject.putExtraData("currentIndex", Integer.valueOf(currentIndex));

        ConcolicByte objectToReturn = (ConcolicByte) ConcolicObjectImpl.getField(byteStreamObject, prevIndex);
        return objectToReturn;
    }

    public static Object wrapGetInt(Object target_obj, Object[] args, String signature, Object returnedObject) {
        if (Logger.compileLog) {
            Logger.DEBUG("[ByteBufferHook] - virtual getInt(): " + signature);
            Logger.DEBUG("this - " + target_obj.toString());
            Logger.DEBUG("returnedObject - " + returnedObject.toString());
        }
        if (!(target_obj instanceof ConcolicObjectImpl)) {
            if (Logger.compileLog) {
                Logger.DEBUG("[ByteBufferHook.getInt()] target_obj class mismatch: " + target_obj.getClass().getName().toString());
            }
            return returnedObject;
        }
        if (!(returnedObject instanceof ConcolicInt)) {
            if (Logger.compileLog) {
                Logger.DEBUG("[ByteBufferHook.getInt()] returnedObject class mismatch: " + returnedObject.getClass().getName().toString());
            }
            return returnedObject;
        }


        ConcolicObjectImpl targetObject = (ConcolicObjectImpl) target_obj;
        ConcolicObjectImpl byteStreamObject = (ConcolicObjectImpl) targetObject.getExtraData("byteStream");
        ConcolicInt retObject = (ConcolicInt) returnedObject;

        if (byteStreamObject == null) { return returnedObject; }

        int prevIndex = ((Integer)targetObject.getExtraData("prevIndex")).intValue();
        int currentIndex = ((Integer) targetObject.getExtraData("currentIndex")).intValue();

        if (Logger.compileLog) {
            Logger.DEBUG(String.format("[ByteBufferHook.getInt()] prev %d current %d", prevIndex, currentIndex));
        }
        // get each byte and build
        prevIndex = currentIndex;
        currentIndex += 4;
        targetObject.putExtraData("prevIndex", Integer.valueOf(prevIndex));
        targetObject.putExtraData("currentIndex", Integer.valueOf(currentIndex));
        ConcolicByte[] byteArray = new ConcolicByte[4];
        for (int i=prevIndex; i < currentIndex; ++i) {
            ConcolicByte byteObject = (ConcolicByte) ConcolicObjectImpl.getField(byteStreamObject, i);
            if (Logger.compileLog) {
                Logger.DEBUG(String.format("[ByteBufferHook.getInt()] fetched object at %d: %s",
                                            i, byteObject.toString()));
            }
            byteArray[i - prevIndex] = byteObject;
        }

        ConcolicInt intObject = new ConcolicInt();
        BitVecExpr bvExpr = null;
        for (int i=0; i<4; ++i) {
            if (i == 1) {
                BitVecExpr expr0 = Z3Helper.mkExtract(7, 0, (BitVecExpr) byteArray[0].getExprWithInit());
                BitVecExpr expr1 = Z3Helper.mkExtract(7, 0, (BitVecExpr) byteArray[1].getExprWithInit());
                bvExpr = Z3Helper.mkConcat(expr0, expr1);
            } else if (i > 1) {
                BitVecExpr expr_i = Z3Helper.mkExtract(7, 0, (BitVecExpr) byteArray[i].getExprWithInit());
                bvExpr = Z3Helper.mkConcat(bvExpr, expr_i);
            }
        }

        intObject.setValueWithConstraints(retObject.getConcreteValue(), bvExpr);
        return intObject;
    }

    public static Object wrapGetShort(Object target_obj, Object[] args, String signature, Object returnedObject) {
        if (Logger.compileLog) {
            Logger.DEBUG("[ByteBufferHook] - virtual getShort(): " + signature);
            Logger.DEBUG("this - " + target_obj.toString());
            Logger.DEBUG("returnedObject - " + returnedObject.toString());
        }
        if (!(target_obj instanceof ConcolicObjectImpl)) {
            if (Logger.compileLog) {
                Logger.DEBUG("[ByteBufferHook.getShort()] target_obj class mismatch: " + target_obj.getClass().getName().toString());
            }
            return returnedObject;
        }
        if (!(returnedObject instanceof ConcolicShort)) {
            if (Logger.compileLog) {
                Logger.DEBUG("[ByteBufferHook.getShort()] returnedObject class mismatch: " + returnedObject.getClass().getName().toString());
            }
            return returnedObject;
        }

        ConcolicObjectImpl targetObject = (ConcolicObjectImpl) target_obj;
        ConcolicObjectImpl byteStreamObject = (ConcolicObjectImpl) targetObject.getExtraData("byteStream");
        ConcolicShort retObject = (ConcolicShort) returnedObject;

        if (byteStreamObject == null) { return returnedObject; }

        int prevIndex = ((Integer)targetObject.getExtraData("prevIndex")).intValue();
        int currentIndex = ((Integer) targetObject.getExtraData("currentIndex")).intValue();

        if (Logger.compileLog) {
            Logger.DEBUG(String.format("[ByteBufferHook.getShort()] prev %d current %d", prevIndex, currentIndex));
        }
        // get each byte and build
        prevIndex = currentIndex;
        currentIndex += 2;
        targetObject.putExtraData("prevIndex", Integer.valueOf(prevIndex));
        targetObject.putExtraData("currentIndex", Integer.valueOf(currentIndex));
        ConcolicByte[] byteArray = new ConcolicByte[2];
        for (int i=prevIndex; i < currentIndex; ++i) {
            ConcolicByte byteObject = (ConcolicByte) ConcolicObjectImpl.getField(byteStreamObject, i);
            if (Logger.compileLog) {
                Logger.DEBUG(String.format("[ByteBufferHook.getShort()] fetched object at %d: %s",
                                            i, byteObject.toString()));
            }
            byteArray[i - prevIndex] = byteObject;
        }

        ConcolicShort shortObject = new ConcolicShort();
        BitVecExpr expr0 = Z3Helper.mkExtract(7, 0, (BitVecExpr) byteArray[0].getExprWithInit());
        BitVecExpr expr1 = Z3Helper.mkExtract(7, 0, (BitVecExpr) byteArray[1].getExprWithInit());
        BitVecExpr bvExpr = Z3Helper.mkConcat(expr0, expr1);

        shortObject.setValueWithConstraints(retObject.getConcreteValue(), bvExpr);
        return shortObject;
    }

    public static Object wrapGetLong(Object target_obj, Object[] args, String signature, Object returnedObject) {
        if (Logger.compileLog) {
            Logger.DEBUG("[ByteBufferHook] - virtual getLong(): " + signature);
            Logger.DEBUG("this - " + target_obj.toString());
            Logger.DEBUG("returnedObject - " + returnedObject.toString());
        }
        if (!(target_obj instanceof ConcolicObjectImpl)) {
            if (Logger.compileLog) {
                Logger.DEBUG("[ByteBufferHook.getLong()] target_obj class mismatch: " + target_obj.getClass().getName().toString());
            }
            return returnedObject;
        }
        if (!(returnedObject instanceof ConcolicLong)) {
            if (Logger.compileLog) {
                Logger.DEBUG("[ByteBufferHook.getLong()] returnedObject class mismatch: " + returnedObject.getClass().getName().toString());
            }
            return returnedObject;
        }


        ConcolicObjectImpl targetObject = (ConcolicObjectImpl) target_obj;
        ConcolicObjectImpl byteStreamObject = (ConcolicObjectImpl) targetObject.getExtraData("byteStream");
        ConcolicLong retObject = (ConcolicLong) returnedObject;

        if (byteStreamObject == null) { return returnedObject; }

        int prevIndex = ((Integer)targetObject.getExtraData("prevIndex")).intValue();
        int currentIndex = ((Integer) targetObject.getExtraData("currentIndex")).intValue();

        if (Logger.compileLog) {
            Logger.DEBUG(String.format("[ByteBufferHook.getLong()] prev %d current %d", prevIndex, currentIndex));
        }
        // get each byte and build
        prevIndex = currentIndex;
        currentIndex += 8;
        targetObject.putExtraData("prevIndex", Integer.valueOf(prevIndex));
        targetObject.putExtraData("currentIndex", Integer.valueOf(currentIndex));
        ConcolicByte[] byteArray = new ConcolicByte[8];
        for (int i=prevIndex; i < currentIndex; ++i) {
            ConcolicByte byteObject = (ConcolicByte) ConcolicObjectImpl.getField(byteStreamObject, i);
            if (Logger.compileLog) {
                Logger.DEBUG(String.format("[ByteBufferHook.getLong()] fetched object at %d: %s",
                                            i, byteObject.toString()));
            }
            byteArray[i - prevIndex] = byteObject;
        }

        ConcolicLong longObject = new ConcolicLong();
        BitVecExpr bvExpr = null;
        for (int i=0; i<8; ++i) {
            if (i == 1) {
                BitVecExpr expr0 = Z3Helper.mkExtract(7, 0, (BitVecExpr) byteArray[0].getExprWithInit());
                BitVecExpr expr1 = Z3Helper.mkExtract(7, 0, (BitVecExpr) byteArray[1].getExprWithInit());
                bvExpr = Z3Helper.mkConcat(expr0, expr1);
            } else if (i > 1) {
                BitVecExpr expr_i = Z3Helper.mkExtract(7, 0, (BitVecExpr) byteArray[i].getExprWithInit());
                bvExpr = Z3Helper.mkConcat(bvExpr, expr_i);
            }
        }

        longObject.setValueWithConstraints(retObject.getConcreteValue(), bvExpr);
        return longObject;
    }


}
