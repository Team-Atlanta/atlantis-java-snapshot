package com.oracle.truffle.api.concolic;

import com.microsoft.z3.*;
import com.oracle.truffle.api.concolic.ConcolicValueHelper;

public class ConcolicShort extends ConcolicValueWrapper<Short> implements ConcolicValue {
    public ConcolicShort() {
        super();
    }

    public static ConcolicShort createWithoutConstraints(short value) {
        ConcolicShort concolicShort = new ConcolicShort();
        concolicShort.setValueWithoutConstraints(value);
        return concolicShort;
    }

    public static ConcolicShort createNewSymbolicShort(short concreteValue) {
        String variableName = ConcolicValueHelper.getSymbolicShortName();
        ConcolicShort concolicShort = new ConcolicShort();
        BitVecExpr expr = Z3Helper.createShortVar(variableName);
        BitVecExpr expr_32 = Z3Helper.convertBitVecWidth(expr, 32);
        concolicShort.setValueWithConstraints(concreteValue, expr_32);
        return concolicShort;
    }

    @Override
    protected void calculateExpr() {
        // TODO: Should change this type
        expr = Z3Helper.mkBV(this.getConcreteValue(), 32);
    }

    public ConcolicShort Add(ConcolicShort other) {
        int concreteResult = this.getConcreteValue() + other.getConcreteValue();
        short result = (short) (concreteResult & 0xffff);
        ConcolicShort concolicShort = new ConcolicShort();
        if (ConcolicValueHelper.eitherSymbolic(this, other)) {
            concolicShort.setValueWithConstraints(result, getAddExpr(other));
        } else {
            if (Logger.compileLog) {
                Logger.DEBUG("[SHORT_IADD] this: " + this.getConcreteValue() + " other: " + other.getConcreteValue() + " result: " + result);
            }
            concolicShort.setValueWithoutConstraints(result);
        }
        return concolicShort;
    }

    public ConcolicShort Subtract(ConcolicShort other) {
        int concreteResult = this.getConcreteValue() - other.getConcreteValue();
        short result = (short) (concreteResult & 0xffff);
        ConcolicShort concolicShort = new ConcolicShort();
        if (ConcolicValueHelper.eitherSymbolic(this, other)) {
            concolicShort.setValueWithConstraints(result, getSubtractExpr(other));
        } else {
            if (Logger.compileLog) {
                Logger.DEBUG("[SHORT_ISUB] this: " + this.getConcreteValue() + " other: " + other.getConcreteValue() + " result: " + result);
            }
            concolicShort.setValueWithoutConstraints(result);
        }
        return concolicShort;
    }

    public ConcolicShort Multiply(ConcolicShort other) {
        int concreteResult = this.getConcreteValue() * other.getConcreteValue();
        short result = (short) (concreteResult & 0xffff);
        ConcolicShort concolicShort = new ConcolicShort();
        if (ConcolicValueHelper.eitherSymbolic(this, other)) {
            concolicShort.setValueWithConstraints(result, getMultiplyExpr(other));
        } else {
            if (Logger.compileLog) {
                Logger.DEBUG("[SHORT_IMUL] this: " + this.getConcreteValue() + " other: " + other.getConcreteValue() + " result: " + result);
            }
            concolicShort.setValueWithoutConstraints(result);
        }
        return concolicShort;
    }

    public ConcolicShort Divide(ConcolicShort other) {
        int concreteResult = this.getConcreteValue() / other.getConcreteValue();
        short result = (short) (concreteResult & 0xffff);
        ConcolicShort concolicShort = new ConcolicShort();
        if (ConcolicValueHelper.eitherSymbolic(this, other)) {
            concolicShort.setValueWithConstraints(result, getDivideExpr(other));
        } else {
            if (Logger.compileLog) {
                Logger.DEBUG("[SHORT_IDIV] this: " + this.getConcreteValue() + " other: " + other.getConcreteValue() + " result: " + result);
            }
            concolicShort.setValueWithoutConstraints(result);
        }
        return concolicShort;
    }

    public ConcolicShort Modulo(ConcolicShort other) {
        int concreteResult = this.getConcreteValue() % other.getConcreteValue();
        short result = (short) (concreteResult & 0xffff);
        ConcolicShort concolicShort = new ConcolicShort();
        if (ConcolicValueHelper.eitherSymbolic(this, other)) {
            concolicShort.setValueWithConstraints(result, getModuloExpr(other));
        } else {
            if (Logger.compileLog) {
                Logger.DEBUG("[SHORT_IREM] this: " + this.getConcreteValue() + " other: " + other.getConcreteValue() + " result: " + result);
            }
            concolicShort.setValueWithoutConstraints(result);
        }
        return concolicShort;
    }

    public ConcolicShort Negate() {
        int concreteResult = -this.getConcreteValue();
        short result = (short) (concreteResult & 0xffff);
        ConcolicShort concolicShort = new ConcolicShort();
        if (ConcolicValueHelper.eitherSymbolic(this)) {
            concolicShort.setValueWithConstraints(result, getNegateExpr());
        } else {
            if (Logger.compileLog) {
                Logger.DEBUG("[SHORT_INEG] this: " + this.getConcreteValue() + " result: " + result);
            }
            concolicShort.setValueWithoutConstraints(result);
        }
        return concolicShort;
    }

    public ConcolicShort BitwiseAnd(ConcolicShort other) {
        int concreteResult = this.getConcreteValue() & other.getConcreteValue();
        short result = (short) (concreteResult & 0xffff);
        ConcolicShort concolicShort = new ConcolicShort();
        if (ConcolicValueHelper.eitherSymbolic(this, other)) {
            concolicShort.setValueWithConstraints(result, getAndExpr(other));
        } else {
            if (Logger.compileLog) {
                Logger.DEBUG("[SHORT_IAND] this: " + this.getConcreteValue() + " other: " + other.getConcreteValue() + " result: " + result);
            }
            concolicShort.setValueWithoutConstraints(result);
        }
        return concolicShort;
    }

    public ConcolicShort BitwiseOr(ConcolicShort other) {
        int concreteResult = this.getConcreteValue() | other.getConcreteValue();
        short result = (short) (concreteResult & 0xffff);
        ConcolicShort concolicShort = new ConcolicShort();
        if (ConcolicValueHelper.eitherSymbolic(this, other)) {
            concolicShort.setValueWithConstraints(result, getORExpr(other));
        } else {
            if (Logger.compileLog) {
                Logger.DEBUG("[SHORT_IOR] this: " + this.getConcreteValue() + " other: " + other.getConcreteValue() + " result: " + result);
            }
            concolicShort.setValueWithoutConstraints(result);
        }
        return concolicShort;
    }

    public ConcolicShort BitwiseXor(ConcolicShort other) {
        int concreteResult = this.getConcreteValue() ^ other.getConcreteValue();
        short result = (short) (concreteResult & 0xffff);
        ConcolicShort concolicShort = new ConcolicShort();
        if (ConcolicValueHelper.eitherSymbolic(this, other)) {
            concolicShort.setValueWithConstraints(result, getXORExpr(other));
        } else {
            if (Logger.compileLog) {
                Logger.DEBUG("[SHORT_IXOR] this: " + this.getConcreteValue() + " other: " + other.getConcreteValue() + " result: " + result);
            }
            concolicShort.setValueWithoutConstraints(result);
        }
        return concolicShort;
    }

    public ConcolicShort ShiftLeft(ConcolicShort other) {
        int concreteResult = this.getConcreteValue() << other.getConcreteValue();
        short result = (short) (concreteResult & 0xffff);
        ConcolicShort concolicShort = new ConcolicShort();
        if (ConcolicValueHelper.eitherSymbolic(this, other)) {
            concolicShort.setValueWithConstraints(result, getShiftLeftExpr(other));
        } else {
            if (Logger.compileLog) {
                Logger.DEBUG("[SHORT_ISHL] this: " + this.getConcreteValue() + " other: " + other.getConcreteValue() + " result: " + result);
            }
            concolicShort.setValueWithoutConstraints(result);
        }
        return concolicShort;
    }

    public ConcolicShort ShiftRight(ConcolicShort other) {
        int concreteResult = this.getConcreteValue() >> other.getConcreteValue();
        short result = (short) (concreteResult & 0xffff);
        ConcolicShort concolicShort = new ConcolicShort();
        if (ConcolicValueHelper.eitherSymbolic(this, other)) {
            concolicShort.setValueWithConstraints(result, getShiftRightExpr(other));
        } else {
            if (Logger.compileLog) {
                Logger.DEBUG("[SHORT_ISHR] this: " + this.getConcreteValue() + " other: " + other.getConcreteValue() + " result: " + result);
            }
            concolicShort.setValueWithoutConstraints(result);
        }
        return concolicShort;
    }

    public ConcolicShort ShiftRightUnsigned(ConcolicShort other) {
        int concreteResult = this.getConcreteValue() >>> other.getConcreteValue();
        short result = (short) (concreteResult & 0xffff);
        ConcolicShort concolicShort = new ConcolicShort();
        if (ConcolicValueHelper.eitherSymbolic(this, other)) {
            concolicShort.setValueWithConstraints(result, getShiftRightUnsignedExpr(other));
        } else {
            if (Logger.compileLog) {
                Logger.DEBUG("[SHORT_IUSHR] this: " + this.getConcreteValue() + " other: " + other.getConcreteValue() + " result: " + result);
            }
            concolicShort.setValueWithoutConstraints(result);
        }
        return concolicShort;
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
        return this;
    }

    public ConcolicShort ToShort() {
        return this;
    }

    public ConcolicInt ToIntExpr() {
        return ToInt(true);
    }

    public ConcolicInt ToInt() {
        return ToInt(false);
    }

    public ConcolicInt ToInt(boolean extend) {
        int result = this.getConcreteValue().intValue();
        ConcolicInt concolicInt = new ConcolicInt();
        if (extend == false || this.expr == null) {
            concolicInt.setValueWithConstraints(result, this.expr);
        } else {
            BitVecExpr intExpr = Z3Helper.convertBitVecWidth((BitVecExpr) this.expr, 32);
            concolicInt.setValueWithConstraints(result, intExpr);
        }
        return concolicInt;
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
            Expr<?> longExpr = Z3Helper.convertBitVecWidth((BitVecExpr) this.expr, 64);
            concolicLong.setValueWithConstraints(result, longExpr);
        }
        return concolicLong;
    }
}
