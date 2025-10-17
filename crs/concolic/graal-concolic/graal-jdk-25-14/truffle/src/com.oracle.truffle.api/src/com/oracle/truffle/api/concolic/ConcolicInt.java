package com.oracle.truffle.api.concolic;

import com.microsoft.z3.*;
import com.oracle.truffle.api.concolic.ConcolicValueHelper;
public class ConcolicInt extends ConcolicValueWrapper<Integer> implements ConcolicValue {

    //private int passedHashCode;

    public static ConcolicInt createWithoutConstraints(int value) {
        ConcolicInt concolicInt = new ConcolicInt();
        concolicInt.setValueWithoutConstraints(value);
        return concolicInt;
    }

    public static ConcolicInt createNewSymbolicInt(int concreteValue) {
        String variableName = ConcolicValueHelper.getSymbolicIntegerName();
        ConcolicInt concolicInt = new ConcolicInt();
        BitVecExpr expr = Z3Helper.createIntVar(variableName);
        concolicInt.setValueWithConstraints(concreteValue, expr);
        return concolicInt;
    }

    public ConcolicInt() {
        super();
    }

    public boolean getPassedHashCode() {
        if (this.expr == Z3Helper.getInstance().hashCodeExpr) {
            return true;
        } else {
            return false;
        }
    }

    public void setPassedHashCode(boolean passed) {
        if (passed) {
            this.expr = Z3Helper.getInstance().hashCodeExpr;
        } else {
            // do nothing
        }
    }

    @Override
    protected void calculateExpr() {
        // TODO: Should change this type
        expr = Z3Helper.mkBV(this.getConcreteValue(), 32);
    }

    public ConcolicInt Add(ConcolicInt other) {
        int result = this.getConcreteValue() + other.getConcreteValue();
        ConcolicInt concolicInt = new ConcolicInt();
        if (ConcolicValueHelper.eitherSymbolic(this, other)) {
            concolicInt.setValueWithConstraints(result, getAddExpr(other));
        } else {
            if (Logger.compileLog) {
                Logger.DEBUG("[IADD] this: " + this.getConcreteValue() + " other: " + other.getConcreteValue() + " result: " + result);
            }
            concolicInt.setValueWithoutConstraints(result);
        }
        return concolicInt;
    }

    public ConcolicInt Subtract(ConcolicInt other) {
        int result = this.getConcreteValue() - other.getConcreteValue();
        ConcolicInt concolicInt = new ConcolicInt();
        if (ConcolicValueHelper.eitherSymbolic(this, other)) {
            concolicInt.setValueWithConstraints(result, getSubtractExpr(other));
        } else {
            if (Logger.compileLog) {
                Logger.DEBUG("[ISUB] this: " + this.getConcreteValue() + " other: " + other.getConcreteValue() + " result: " + result);
            }
            concolicInt.setValueWithoutConstraints(result);
        }
        return concolicInt;
    }

    public ConcolicInt Multiply(ConcolicInt other) {
        int result = this.getConcreteValue() * other.getConcreteValue();
        ConcolicInt concolicInt = new ConcolicInt();
        if (ConcolicValueHelper.eitherSymbolic(this, other)) {
            concolicInt.setValueWithConstraints(result, getMultiplyExpr(other));
        } else {
            if (Logger.compileLog) {
                Logger.DEBUG("[IMUL] this: " + this.getConcreteValue() + " other: " + other.getConcreteValue() + " result: " + result);
            }
            concolicInt.setValueWithoutConstraints(result);
        }
        return concolicInt;
    }

    public ConcolicInt Divide(ConcolicInt other) {
        int result = this.getConcreteValue() / other.getConcreteValue();
        ConcolicInt concolicInt = new ConcolicInt();
        if (ConcolicValueHelper.eitherSymbolic(this, other)) {
            concolicInt.setValueWithConstraints(result, getDivideExpr(other));
        } else {
            if (Logger.compileLog) {
                Logger.DEBUG("[IDIV] this: " + this.getConcreteValue() + " other: " + other.getConcreteValue() + " result: " + result);
            }
            concolicInt.setValueWithoutConstraints(result);
        }
        return concolicInt;
    }

    public ConcolicInt Modulo(ConcolicInt other) {
        int result = this.getConcreteValue() % other.getConcreteValue();
        ConcolicInt concolicInt = new ConcolicInt();
        if (ConcolicValueHelper.eitherSymbolic(this, other)) {
            concolicInt.setValueWithConstraints(result, getModuloExpr(other));
        } else {
            if (Logger.compileLog) {
                Logger.DEBUG("[IREM] this: " + this.getConcreteValue() + " other: " + other.getConcreteValue() + " result: " + result);
            }
            concolicInt.setValueWithoutConstraints(result);
        }
        return concolicInt;
    }

    public ConcolicInt Negate() {
        int result = -this.getConcreteValue();
        ConcolicInt concolicInt = new ConcolicInt();
        if (ConcolicValueHelper.eitherSymbolic(this)) {
            concolicInt.setValueWithConstraints(result, getNegateExpr());
        } else {
            if (Logger.compileLog) {
                Logger.DEBUG("[INEG] this: " + this.getConcreteValue() + " result: " + result);
            }
            concolicInt.setValueWithoutConstraints(result);
        }
        return concolicInt;
    }

    public ConcolicInt BitwiseAnd(ConcolicInt other) {
        int result = this.getConcreteValue() & other.getConcreteValue();
        ConcolicInt concolicInt = new ConcolicInt();
        if (ConcolicValueHelper.eitherSymbolic(this, other)) {
            concolicInt.setValueWithConstraints(result, getAndExpr(other));
        } else {
            if (Logger.compileLog) {
                Logger.DEBUG("[IAND] this: " + this.getConcreteValue() + " other: " + other.getConcreteValue() + " result: " + result);
            }
            concolicInt.setValueWithoutConstraints(result);
        }
        return concolicInt;
    }

    public ConcolicInt BitwiseOr(ConcolicInt other) {
        int result = this.getConcreteValue() | other.getConcreteValue();
        ConcolicInt concolicInt = new ConcolicInt();
        if (ConcolicValueHelper.eitherSymbolic(this, other)) {
            concolicInt.setValueWithConstraints(result, getORExpr(other));
        } else {
            if (Logger.compileLog) {
                Logger.DEBUG("[IOR] this: " + this.getConcreteValue() + " other: " + other.getConcreteValue() + " result: " + result);
            }
            concolicInt.setValueWithoutConstraints(result);
        }
        return concolicInt;
    }

    public ConcolicInt BitwiseXor(ConcolicInt other) {
        int result = this.getConcreteValue() ^ other.getConcreteValue();
        ConcolicInt concolicInt = new ConcolicInt();
        if (ConcolicValueHelper.eitherSymbolic(this, other)) {
            concolicInt.setValueWithConstraints(result, getXORExpr(other));
        } else {
            if (Logger.compileLog) {
                Logger.DEBUG("[IXOR] this: " + this.getConcreteValue() + " other: " + other.getConcreteValue() + " result: " + result);
            }
            concolicInt.setValueWithoutConstraints(result);
        }
        return concolicInt;
    }

    public ConcolicInt ShiftLeft(ConcolicInt other) {
        int result = this.getConcreteValue() << other.getConcreteValue();
        ConcolicInt concolicInt = new ConcolicInt();
        if (ConcolicValueHelper.eitherSymbolic(this, other)) {
            concolicInt.setValueWithConstraints(result, getShiftLeftExpr(other));
        } else {
            if (Logger.compileLog) {
                Logger.DEBUG("[ISHL] this: " + this.getConcreteValue() + " other: " + other.getConcreteValue() + " result: " + result);
            }
            concolicInt.setValueWithoutConstraints(result);
        }
        return concolicInt;
    }

    public ConcolicInt ShiftRight(ConcolicInt other) {
        int result = this.getConcreteValue() >> other.getConcreteValue();
        ConcolicInt concolicInt = new ConcolicInt();
        if (ConcolicValueHelper.eitherSymbolic(this, other)) {
            concolicInt.setValueWithConstraints(result, getShiftRightExpr(other));
        } else {
            if (Logger.compileLog) {
                Logger.DEBUG("[ISHR] this: " + this.getConcreteValue() + " other: " + other.getConcreteValue() + " result: " + result);
            }
            concolicInt.setValueWithoutConstraints(result);
        }
        return concolicInt;
    }

    public ConcolicInt ShiftRightUnsigned(ConcolicInt other) {
        int result = this.getConcreteValue() >>> other.getConcreteValue();
        ConcolicInt concolicInt = new ConcolicInt();
        if (ConcolicValueHelper.eitherSymbolic(this, other)) {
            concolicInt.setValueWithConstraints(result, getShiftRightUnsignedExpr(other));
        } else {
            if (Logger.compileLog) {
                Logger.DEBUG("[IUSHR] this: " + this.getConcreteValue() + " other: " + other.getConcreteValue() + " result: " + result);
            }
            concolicInt.setValueWithoutConstraints(result);
        }
        return concolicInt;
    }

    public ConcolicByte ToByteExpr() {
        return ToByte(true);
    }

    public ConcolicByte ToByte() {
        return ToByte(false);
    }

    public ConcolicByte ToByte(boolean extend) {
        byte result = this.getConcreteValue().byteValue();
        ConcolicByte concolicByte = new ConcolicByte();
        if (extend == false || this.expr == null) {
            concolicByte.setValueWithConstraints(result, this.expr);
        } else {
            BitVecExpr byteExpr = Z3Helper.convertBitVecWidth((BitVecExpr) this.expr, 8);
            BitVecExpr expr_32 = Z3Helper.convertBitVecWidth(byteExpr, 32);
            concolicByte.setValueWithConstraints(result, expr_32);
        }
        return concolicByte;
    }

    public ConcolicShort ToShortExpr() {
        return ToShort(true);
    }

    public ConcolicShort ToShort() {
        return ToShort(false);
    }

    public ConcolicShort ToShort(boolean extend) {
        short result = this.getConcreteValue().shortValue();
        ConcolicShort concolicShort = new ConcolicShort();
        if (extend == false || this.expr == null) {
            concolicShort.setValueWithConstraints(result, this.expr);
        } else {
            BitVecExpr shortExpr = Z3Helper.convertBitVecWidth((BitVecExpr) this.expr, 16);
            BitVecExpr expr_32 = Z3Helper.convertBitVecWidth(shortExpr, 32);
            concolicShort.setValueWithConstraints(result, expr_32);
        }
        return concolicShort;
    }

    public ConcolicInt ToIntExpr() {
        return this;
    }

    public ConcolicInt ToInt() {
        return this;
    }

    public ConcolicLong ToLongExpr() {
        return ToLong(true);
    }

    public ConcolicLong ToLong() {
        return ToLong(false);
    }

    public ConcolicLong ToLong(boolean extend) {
        long result = this.getConcreteValue().longValue();
        ConcolicLong concolicLong = new ConcolicLong();
        if (extend == false || this.expr == null) {
            concolicLong.setValueWithConstraints(result, this.expr);
        } else {
            BitVecExpr longExpr = Z3Helper.convertBitVecWidth((BitVecExpr) this.expr, 64);
            concolicLong.setValueWithConstraints(result, longExpr);
        }
        return concolicLong;
    }


    public ConcolicFloat ToFloatConversion() {
        float result = (float) this.getConcreteValue();
        ConcolicFloat cf = new ConcolicFloat();
        if (ConcolicValueHelper.eitherSymbolic(this)) {
            Expr<?> bitVecExpr = this.getExprWithInit();
            // always signed integer
            Expr<?> intExpr = Z3Helper.mkBV2Int((BitVecExpr) bitVecExpr, true);
            Expr<?> realExpr = Z3Helper.mkInt2Real((IntExpr) intExpr);
            cf.setValueWithConstraints(result, realExpr);
        } else {
            cf.setValueWithoutConstraints(result);
        }
        return cf;
    }

    public ConcolicDouble ToDoubleConversion() {
        double result = (double) this.getConcreteValue();
        ConcolicDouble cd = new ConcolicDouble();
        if (ConcolicValueHelper.eitherSymbolic(this)) {
            Expr<?> bitVecExpr = this.getExprWithInit();
            // always signed integer
            Expr<?> intExpr = Z3Helper.mkBV2Int((BitVecExpr) bitVecExpr, true);
            Expr<?> realExpr = Z3Helper.mkInt2Real((IntExpr) intExpr);
            cd.setValueWithConstraints(result, realExpr);
        } else {
            cd.setValueWithoutConstraints(result);
        }
        return cd;
    }

}
