package com.oracle.truffle.api.concolic;

import com.microsoft.z3.*;
import com.oracle.truffle.api.concolic.ConcolicValueHelper;

public class ConcolicByte extends ConcolicValueWrapper<Byte> implements ConcolicValue {
    public ConcolicByte() {
        super();
    }

    public static ConcolicByte createWithoutConstraints(byte value) {
        ConcolicByte concolicByte = new ConcolicByte();
        concolicByte.setValueWithoutConstraints(value);
        return concolicByte;
    }

    public static ConcolicByte createNewSymbolicByte(byte concreteValue) {
        String variableName = ConcolicValueHelper.getSymbolicByteName();
        ConcolicByte concolicByte = new ConcolicByte();
        BitVecExpr expr = Z3Helper.createByteVar(variableName);
        BitVecExpr expr_32 = Z3Helper.convertBitVecWidth(expr, 32);
        concolicByte.setValueWithConstraints(concreteValue, expr_32);
        return concolicByte;
    }

    public static ConcolicByte createNewSymbolicByte(byte concreteValue, int blobPosition) {
        String variableName = ConcolicValueHelper.getSymbolicByteName();
        ConcolicByte concolicByte = new ConcolicByte();
        BitVecExpr expr = Z3Helper.createByteVar(variableName);
        BitVecExpr expr_32 = Z3Helper.convertBitVecWidth(expr, 32);
        concolicByte.setValueWithConstraints(concreteValue, expr_32);
        ConcolicVariableInfo info = new ConcolicVariableInfo(variableName,
                                                blobPosition, blobPosition + 1);
        ConcolicVariableInfo.setVariableInfo(variableName, info);
        return concolicByte;
    }


    @Override
    protected void calculateExpr() {
        // TODO: Should change this type
        expr = Z3Helper.mkBV(this.getConcreteValue(), 32);
    }

    public ConcolicByte Add(ConcolicByte other) {
        int concreteResult = this.getConcreteValue() + other.getConcreteValue();
        byte result = (byte) (concreteResult & 0xff);
        ConcolicByte concolicByte = new ConcolicByte();
        if (ConcolicValueHelper.eitherSymbolic(this, other)) {
            concolicByte.setValueWithConstraints(result, getAddExpr(other));
        } else {
            if (Logger.compileLog) {
                Logger.DEBUG("[BYTE_IADD] this: " + this.getConcreteValue() + " other: " + other.getConcreteValue() + " result: " + result);
            }
            concolicByte.setValueWithoutConstraints(result);
        }
        return concolicByte;
    }

    public ConcolicByte Subtract(ConcolicByte other) {
        int concreteResult = this.getConcreteValue() - other.getConcreteValue();
        byte result = (byte) (concreteResult & 0xff);
        ConcolicByte concolicByte = new ConcolicByte();
        if (ConcolicValueHelper.eitherSymbolic(this, other)) {
            concolicByte.setValueWithConstraints(result, getSubtractExpr(other));
        } else {
            if (Logger.compileLog) {
                Logger.DEBUG("[BYTE_ISUB] this: " + this.getConcreteValue() + " other: " + other.getConcreteValue() + " result: " + result);
            }
            concolicByte.setValueWithoutConstraints(result);
        }
        return concolicByte;
    }

    public ConcolicByte Multiply(ConcolicByte other) {
        int concreteResult = this.getConcreteValue() * other.getConcreteValue();
        byte result = (byte) (concreteResult & 0xff);
        ConcolicByte concolicByte = new ConcolicByte();
        if (ConcolicValueHelper.eitherSymbolic(this, other)) {
            concolicByte.setValueWithConstraints(result, getMultiplyExpr(other));
        } else {
            if (Logger.compileLog) {
                Logger.DEBUG("[BYTE_IMUL] this: " + this.getConcreteValue() + " other: " + other.getConcreteValue() + " result: " + result);
            }
            concolicByte.setValueWithoutConstraints(result);
        }
        return concolicByte;
    }

    public ConcolicByte Divide(ConcolicByte other) {
        int concreteResult = this.getConcreteValue() / other.getConcreteValue();
        byte result = (byte) (concreteResult & 0xff);
        ConcolicByte concolicByte = new ConcolicByte();
        if (ConcolicValueHelper.eitherSymbolic(this, other)) {
            concolicByte.setValueWithConstraints(result, getDivideExpr(other));
        } else {
            if (Logger.compileLog) {
                Logger.DEBUG("[BYTE_IDIV] this: " + this.getConcreteValue() + " other: " + other.getConcreteValue() + " result: " + result);
            }
            concolicByte.setValueWithoutConstraints(result);
        }
        return concolicByte;
    }

    public ConcolicByte Modulo(ConcolicByte other) {
        int concreteResult = this.getConcreteValue() % other.getConcreteValue();
        byte result = (byte) (concreteResult & 0xff);
        ConcolicByte concolicByte = new ConcolicByte();
        if (ConcolicValueHelper.eitherSymbolic(this, other)) {
            concolicByte.setValueWithConstraints(result, getModuloExpr(other));
        } else {
            if (Logger.compileLog) {
                Logger.DEBUG("[BYTE_IREM] this: " + this.getConcreteValue() + " other: " + other.getConcreteValue() + " result: " + result);
            }
            concolicByte.setValueWithoutConstraints(result);
        }
        return concolicByte;
    }

    public ConcolicByte Negate() {
        int concreteResult = -this.getConcreteValue();
        byte result = (byte) (concreteResult & 0xff);
        ConcolicByte concolicByte = new ConcolicByte();
        if (ConcolicValueHelper.eitherSymbolic(this)) {
            concolicByte.setValueWithConstraints(result, getNegateExpr());
        } else {
            if (Logger.compileLog) {
                Logger.DEBUG("[BYTE_INEG] this: " + this.getConcreteValue() + " result: " + result);
            }
            concolicByte.setValueWithoutConstraints(result);
        }
        return concolicByte;
    }

    public ConcolicByte BitwiseAnd(ConcolicByte other) {
        int concreteResult = this.getConcreteValue() & other.getConcreteValue();
        byte result = (byte) (concreteResult & 0xff);
        ConcolicByte concolicByte = new ConcolicByte();
        if (ConcolicValueHelper.eitherSymbolic(this, other)) {
            concolicByte.setValueWithConstraints(result, getAndExpr(other));
        } else {
            if (Logger.compileLog) {
                Logger.DEBUG("[BYTE_IAND] this: " + this.getConcreteValue() + " other: " + other.getConcreteValue() + " result: " + result);
            }
            concolicByte.setValueWithoutConstraints(result);
        }
        return concolicByte;
    }

    public ConcolicByte BitwiseOr(ConcolicByte other) {
        int concreteResult = this.getConcreteValue() | other.getConcreteValue();
        byte result = (byte) (concreteResult & 0xff);
        ConcolicByte concolicByte = new ConcolicByte();
        if (ConcolicValueHelper.eitherSymbolic(this, other)) {
            concolicByte.setValueWithConstraints(result, getORExpr(other));
        } else {
            if (Logger.compileLog) {
                Logger.DEBUG("[BYTE_IOR] this: " + this.getConcreteValue() + " other: " + other.getConcreteValue() + " result: " + result);
            }
            concolicByte.setValueWithoutConstraints(result);
        }
        return concolicByte;
    }

    public ConcolicByte BitwiseXor(ConcolicByte other) {
        int concreteResult = this.getConcreteValue() ^ other.getConcreteValue();
        byte result = (byte) (concreteResult & 0xff);
        ConcolicByte concolicByte = new ConcolicByte();
        if (ConcolicValueHelper.eitherSymbolic(this, other)) {
            concolicByte.setValueWithConstraints(result, getXORExpr(other));
        } else {
            if (Logger.compileLog) {
                Logger.DEBUG("[BYTE_IXOR] this: " + this.getConcreteValue() + " other: " + other.getConcreteValue() + " result: " + result);
            }
            concolicByte.setValueWithoutConstraints(result);
        }
        return concolicByte;
    }

    public ConcolicByte ShiftLeft(ConcolicByte other) {
        int concreteResult = this.getConcreteValue() << other.getConcreteValue();
        byte result = (byte) (concreteResult & 0xff);
        ConcolicByte concolicByte = new ConcolicByte();
        if (ConcolicValueHelper.eitherSymbolic(this, other)) {
            concolicByte.setValueWithConstraints(result, getShiftLeftExpr(other));
        } else {
            if (Logger.compileLog) {
                Logger.DEBUG("[BYTE_ISHL] this: " + this.getConcreteValue() + " other: " + other.getConcreteValue() + " result: " + result);
            }
            concolicByte.setValueWithoutConstraints(result);
        }
        return concolicByte;
    }

    public ConcolicByte ShiftRight(ConcolicByte other) {
        int concreteResult = this.getConcreteValue() >> other.getConcreteValue();
        byte result = (byte) (concreteResult & 0xff);
        ConcolicByte concolicByte = new ConcolicByte();
        if (ConcolicValueHelper.eitherSymbolic(this, other)) {
            concolicByte.setValueWithConstraints(result, getShiftRightExpr(other));
        } else {
            if (Logger.compileLog) {
                Logger.DEBUG("[BYTE_ISHR] this: " + this.getConcreteValue() + " other: " + other.getConcreteValue() + " result: " + result);
            }
            concolicByte.setValueWithoutConstraints(result);
        }
        return concolicByte;
    }

    public ConcolicByte ShiftRightUnsigned(ConcolicByte other) {
        int concreteResult = this.getConcreteValue() >>> other.getConcreteValue();
        byte result = (byte) (concreteResult & 0xff);
        ConcolicByte concolicByte = new ConcolicByte();
        if (ConcolicValueHelper.eitherSymbolic(this, other)) {
            concolicByte.setValueWithConstraints(result, getShiftRightUnsignedExpr(other));
        } else {
            if (Logger.compileLog) {
                Logger.DEBUG("[BYTE_IUSHR] this: " + this.getConcreteValue() + " other: " + other.getConcreteValue() + " result: " + result);
            }
            concolicByte.setValueWithoutConstraints(result);
        }
        return concolicByte;
    }

    public ConcolicByte ToByteExpr() {
        return ToByte(true);
    }

    public ConcolicByte ToByte() {
        return ToByte(false);
    }

    public ConcolicByte ToByte(boolean extend) {
        if (extend == false || this.expr == null) {
            return this;
        }
        byte result = this.getConcreteValue();
        ConcolicByte concolicByte = new ConcolicByte();
        BitVecExpr byteExpr = Z3Helper.convertBitVecWidth((BitVecExpr) this.expr, 8);
        concolicByte.setValueWithConstraints(result, byteExpr);
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
            concolicShort.setValueWithConstraints(result, shortExpr);
        }
        return concolicShort;
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
            BitVecExpr longExpr = Z3Helper.convertBitVecWidth((BitVecExpr) this.expr, 64);
            concolicLong.setValueWithConstraints(result, longExpr);
        }
        return concolicLong;
    }

}
