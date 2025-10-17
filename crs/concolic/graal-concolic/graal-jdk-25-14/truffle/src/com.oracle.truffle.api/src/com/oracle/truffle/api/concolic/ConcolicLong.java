package com.oracle.truffle.api.concolic;

import com.microsoft.z3.*;
import com.oracle.truffle.api.concolic.ConcolicValueHelper;

public class ConcolicLong extends ConcolicValueWrapper<Long> implements ConcolicValue {
    public ConcolicLong() {
        super();
    }

    public static ConcolicLong createWithoutConstraints(long value) {
        ConcolicLong ConcolicLong = new ConcolicLong();
        ConcolicLong.setValueWithoutConstraints(value);
        return ConcolicLong;
    }

    public static ConcolicLong createNewSymbolicLong(long concreteValue) {
        String variableName = ConcolicValueHelper.getSymbolicLongName();
        ConcolicLong concolicLong = new ConcolicLong();
        Expr<?> expr = Z3Helper.createLongVar(variableName);
        concolicLong.setValueWithConstraints(concreteValue, expr);
        return concolicLong;
    }

    @Override
    protected void calculateExpr() {
        // TODO: Should change this type
        expr = Z3Helper.mkBV(this.getConcreteValue(), 64);
    }

    public ConcolicLong Add(ConcolicLong other) {
        long result = this.getConcreteValue() + other.getConcreteValue();
        ConcolicLong concolicLong = new ConcolicLong();

        if (ConcolicValueHelper.eitherSymbolic(this, other)) {
            Expr<?> this_expr = this.getExprWithInitInWidth(64);
            Expr<?> other_expr = other.getExprWithInitInWidth(64);
            Expr<?> result_expr = Z3Helper.mkBVAdd((BitVecExpr) this_expr, (BitVecExpr) other_expr);
            if (Logger.compileLog) {
                Logger.DEBUG("[LADD Symbolic] this: " + this_expr + " other: " + other_expr + " result: " + result_expr);
            }
            concolicLong.setValueWithConstraints(result, result_expr);
        } else {
            if (Logger.compileLog) {
                Logger.DEBUG("[LADD] this: " + this.getConcreteValue() + " other: " + other.getConcreteValue() + " result: " + result);
            }
            concolicLong.setValueWithoutConstraints(result);
        }
        return concolicLong;
    }

    public ConcolicLong Subtract(ConcolicLong other) {
        long result = this.getConcreteValue() - other.getConcreteValue();
        ConcolicLong concolicLong = new ConcolicLong();

        if (ConcolicValueHelper.eitherSymbolic(this, other)) {
            Expr<?> this_expr = this.getExprWithInit();
            Expr<?> other_expr = other.getExprWithInit();
            Expr<?> result_expr = Z3Helper.mkBVSub((BitVecExpr) this_expr, (BitVecExpr) other_expr);
            if (Logger.compileLog) {
                Logger.DEBUG("[LSUB Symbolic] this: " + this_expr + " other: " + other_expr + " result: " + result_expr);
            }
            concolicLong.setValueWithConstraints(result, result_expr);
        } else {
            if (Logger.compileLog) {
                Logger.DEBUG("[LSUB] this: " + this.getConcreteValue() + " other: " + other.getConcreteValue() + " result: " + result);
            }
            concolicLong.setValueWithoutConstraints(result);
        }
        return concolicLong;
    }

    public ConcolicLong Multiply(ConcolicLong other) {
        long result = this.getConcreteValue() * other.getConcreteValue();
        ConcolicLong concolicLong = new ConcolicLong();

        if (ConcolicValueHelper.eitherSymbolic(this, other)) {
            Expr<?> this_expr = this.getExprWithInit();
            Expr<?> other_expr = other.getExprWithInit();
            Expr<?> result_expr = Z3Helper.mkBVMul((BitVecExpr) this_expr, (BitVecExpr) other_expr);
            if (Logger.compileLog) {
                Logger.DEBUG("[LMUL Symbolic] this: " + this_expr + " other: " + other_expr + " result: " + result_expr);
            }
            concolicLong.setValueWithConstraints(result, result_expr);
        } else {
            if (Logger.compileLog) {
                Logger.DEBUG("[LMUL] this: " + this.getConcreteValue() + " other: " + other.getConcreteValue() + " result: " + result);
            }
            concolicLong.setValueWithoutConstraints(result);
        }
        return concolicLong;
    }

    public ConcolicLong Divide(ConcolicLong other) {
        long result = this.getConcreteValue() / other.getConcreteValue();
        ConcolicLong concolicLong = new ConcolicLong();

        if (ConcolicValueHelper.eitherSymbolic(this, other)) {
            Expr<?> this_expr = this.getExprWithInit();
            Expr<?> other_expr = other.getExprWithInit();
            Expr<?> result_expr = Z3Helper.mkBVSDiv((BitVecExpr) this_expr, (BitVecExpr) other_expr);
            if (Logger.compileLog) {
                Logger.DEBUG("[LDIV Symbolic] this: " + this_expr + " other: " + other_expr + " result: " + result_expr);
            }
            concolicLong.setValueWithConstraints(result, result_expr);
        } else {
            if (Logger.compileLog) {
                Logger.DEBUG("[LDIV] this: " + this.getConcreteValue() + " other: " + other.getConcreteValue() + " result: " + result);
            }
            concolicLong.setValueWithoutConstraints(result);
        }
        return concolicLong;
    }

    public ConcolicLong Modulo(ConcolicLong other) {
        long result = this.getConcreteValue() % other.getConcreteValue();
        ConcolicLong concolicLong = new ConcolicLong();

        if (ConcolicValueHelper.eitherSymbolic(this, other)) {
            Expr<?> this_expr = this.getExprWithInitInWidth(64);
            Expr<?> other_expr = other.getExprWithInitInWidth(64);
            Expr<?> result_expr = Z3Helper.mkBVSRem((BitVecExpr) this_expr, (BitVecExpr) other_expr);
            if (Logger.compileLog) {
                Logger.DEBUG("[LREM Symbolic] this: " + this_expr + " other: " + other_expr + " result: " + result_expr);
            }
            concolicLong.setValueWithConstraints(result, result_expr);
        } else {
            if (Logger.compileLog) {
                Logger.DEBUG("[LREM] this: " + this.getConcreteValue() + " other: " + other.getConcreteValue() + " result: " + result);
            }
            concolicLong.setValueWithoutConstraints(result);
        }
        return concolicLong;
    }

    public ConcolicLong Negate() {
        long result = -this.getConcreteValue();
        ConcolicLong concolicLong = new ConcolicLong();
        if (ConcolicValueHelper.eitherSymbolic(this)) {
            Expr<?> this_expr = this.getExprWithInit();
            Expr<?> result_expr = Z3Helper.mkBVNeg((BitVecExpr) this_expr);
            if (Logger.compileLog) {
                Logger.DEBUG("[LNEG Symbolic] this: " + this_expr + " result: " + result_expr);
            }
            concolicLong.setValueWithConstraints(result, result_expr);

        } else {
            if (Logger.compileLog) {
                Logger.DEBUG("[LNEG] this: " + this.getConcreteValue() + " result: " + result);
            }
            concolicLong.setValueWithoutConstraints(result);
        }
        return concolicLong;
    }

    // YJ: JVM does not have bitwise NOT. What it will do is -1 ^ target.
    /*
    public ConcolicLong Not() {
        int result = ~this.getConcreteValue();
        ConcolicLong concolicLong = new ConcolicLong();
        concolicLong.setValueWithoutConstraints(result);
        return concolicLong;
    }
    */

    public ConcolicLong BitwiseAnd(ConcolicLong other) {
        long result = this.getConcreteValue() & other.getConcreteValue();
        ConcolicLong concolicLong = new ConcolicLong();

        if (ConcolicValueHelper.eitherSymbolic(this, other)) {
            Expr<?> this_expr = this.getExprWithInit();
            Expr<?> other_expr = other.getExprWithInit();
            Expr<?> result_expr = Z3Helper.mkBVAND((BitVecExpr) this_expr, (BitVecExpr) other_expr);
            if (Logger.compileLog) {
                Logger.DEBUG("[LAND Symbolic] this: " + this_expr + " other: " + other_expr + " result: " + result_expr);
            }
            concolicLong.setValueWithConstraints(result, result_expr);
        } else {
            if (Logger.compileLog) {
                Logger.DEBUG("[LAND] this: " + this.getConcreteValue() + " other: " + other.getConcreteValue() + " result: " + result);
            }
            concolicLong.setValueWithoutConstraints(result);
        }
        return concolicLong;
    }

    public ConcolicLong BitwiseOr(ConcolicLong other) {
        long result = this.getConcreteValue() | other.getConcreteValue();
        ConcolicLong concolicLong = new ConcolicLong();

        if (ConcolicValueHelper.eitherSymbolic(this, other)) {
            Expr<?> this_expr = this.getExprWithInit();
            Expr<?> other_expr = other.getExprWithInit();
            Expr<?> result_expr = Z3Helper.mkBVOR((BitVecExpr) this_expr, (BitVecExpr) other_expr);
            if (Logger.compileLog) {
                Logger.DEBUG("[LOR Symbolic] this: " + this_expr + " other: " + other_expr + " result: " + result_expr);
            }
            concolicLong.setValueWithConstraints(result, result_expr);
        } else {
            if (Logger.compileLog) {
                Logger.DEBUG("[LOR] this: " + this.getConcreteValue() + " other: " + other.getConcreteValue() + " result: " + result);
            }
            concolicLong.setValueWithoutConstraints(result);
        }
        return concolicLong;
    }

    public ConcolicLong BitwiseXor(ConcolicLong other) {
        long result = this.getConcreteValue() ^ other.getConcreteValue();
        ConcolicLong concolicLong = new ConcolicLong();

        if (ConcolicValueHelper.eitherSymbolic(this, other)) {
            Expr<?> this_expr = this.getExprWithInit();
            Expr<?> other_expr = other.getExprWithInit();
            Expr<?> result_expr = Z3Helper.mkBVXOR((BitVecExpr) this_expr, (BitVecExpr) other_expr);
            if (Logger.compileLog) {
                Logger.DEBUG("[LXOR Symbolic] this: " + this_expr + " other: " + other_expr + " result: " + result_expr);
            }
            concolicLong.setValueWithConstraints(result, result_expr);
        } else {
            if (Logger.compileLog) {
                Logger.DEBUG("[LXOR] this: " + this.getConcreteValue() + " other: " + other.getConcreteValue() + " result: " + result);
            }
            concolicLong.setValueWithoutConstraints(result);
        }
        return concolicLong;
    }

    public ConcolicLong ShiftLeft(ConcolicLong other) {
        long result = this.getConcreteValue() << other.getConcreteValue();
        ConcolicLong concolicLong = new ConcolicLong();

        if (ConcolicValueHelper.eitherSymbolic(this, other)) {
            BitVecExpr this_expr = (BitVecExpr) this.getExprWithInit();
            BitVecExpr other_expr = (BitVecExpr) other.getExprWithInit();
            this_expr = Z3Helper.convertBitVecWidth(this_expr, 64);
            other_expr = Z3Helper.convertBitVecWidth(other_expr, 64);
            BitVecExpr result_expr = Z3Helper.mkBVSHL(this_expr, other_expr);
            if (Logger.compileLog) {
                Logger.DEBUG("[LSHL Symbolic] this: " + this_expr + " other: " + other_expr + " result: " + result_expr);
            }
            concolicLong.setValueWithConstraints(result, result_expr);
        } else {
            if (Logger.compileLog) {
                Logger.DEBUG("[LSHL] this: " + this.getConcreteValue() + " other: " + other.getConcreteValue() + " result: " + result);
            }
            concolicLong.setValueWithoutConstraints(result);
        }
        return concolicLong;

    }

    public ConcolicLong ShiftRight(ConcolicLong other) {
        long result = this.getConcreteValue() >> other.getConcreteValue();
        ConcolicLong concolicLong = new ConcolicLong();

        if (ConcolicValueHelper.eitherSymbolic(this, other)) {
            BitVecExpr this_expr = (BitVecExpr) this.getExprWithInit();
            BitVecExpr other_expr = (BitVecExpr) other.getExprWithInit();
            this_expr = Z3Helper.convertBitVecWidth(this_expr, 64);
            other_expr = Z3Helper.convertBitVecWidth(other_expr, 64);
            // arithmetic; signed
            Expr<?> result_expr = Z3Helper.mkBVASHR(this_expr, other_expr);
            if (Logger.compileLog) {
                Logger.DEBUG("[LSHR Symbolic] this: " + this_expr + " other: " + other_expr + " result: " + result_expr);
            }
            concolicLong.setValueWithConstraints(result, result_expr);
        } else {
            if (Logger.compileLog) {
                Logger.DEBUG("[LSHR] this: " + this.getConcreteValue() + " other: " + other.getConcreteValue() + " result: " + result);
            }
            concolicLong.setValueWithoutConstraints(result);
        }
        return concolicLong;

    }

    public ConcolicLong ShiftRightUnsigned(ConcolicLong other) {
        long result = this.getConcreteValue() >>> other.getConcreteValue();
        ConcolicLong concolicLong = new ConcolicLong();

        if (ConcolicValueHelper.eitherSymbolic(this, other)) {
            BitVecExpr this_expr = (BitVecExpr) this.getExprWithInit();
            BitVecExpr other_expr = (BitVecExpr) other.getExprWithInit();
            this_expr = Z3Helper.convertBitVecWidth(this_expr, 64);
            other_expr = Z3Helper.convertBitVecWidth(other_expr, 64);
            // logical; unsigned
            Expr<?> result_expr = Z3Helper.mkBVLSHR(this_expr, other_expr);
            if (Logger.compileLog) {
                Logger.DEBUG("[LUSHR Symbolic] this: " + this_expr + " other: " + other_expr + " result: " + result_expr);
            }
            concolicLong.setValueWithConstraints(result, result_expr);
        } else {
            if (Logger.compileLog) {
                Logger.DEBUG("[LUSHR] this: " + this.getConcreteValue() + " other: " + other.getConcreteValue() + " result: " + result);
            }
            concolicLong.setValueWithoutConstraints(result);
        }
        return concolicLong;

    }

    public ConcolicInt Compare(ConcolicLong other) {
        int concreteResult = Long.compare(this.getConcreteValue(), other.getConcreteValue());
        ConcolicInt returnInt = new ConcolicInt();

        if (ConcolicValueHelper.eitherSymbolic(this, other)) {
            BitVecExpr bvZeroExpr = Z3Helper.getInstance().zeroExpr64;
            BitVecExpr bvOneExpr = Z3Helper.getInstance().oneExpr64;
            BitVecExpr bvMOneExpr = Z3Helper.getInstance().mOneExpr64;

            BitVecExpr subtractExpr = Z3Helper.mkBVSub(
                    (BitVecExpr) this.getExprWithInit(),
                    (BitVecExpr) other.getExprWithInit());

            BoolExpr eqZero = Z3Helper.mkEq(bvZeroExpr, subtractExpr);
            BoolExpr gtZero = Z3Helper.mkBVSGT(subtractExpr, bvZeroExpr);
            Expr<?> ifGtZero = Z3Helper.mkITE(gtZero, bvOneExpr, bvMOneExpr);
            Expr<?> ifEqZero = Z3Helper.mkITE(eqZero, bvZeroExpr, ifGtZero);
            returnInt.setValueWithConstraints(concreteResult, ifEqZero);

        } else {
            returnInt.setValueWithoutConstraints(concreteResult);
        }
        return returnInt;
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
            Expr<?> byteExpr = getExprWithInitInWidth(8);
            concolicByte.setValueWithConstraints(result, byteExpr);
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
            Expr<?> shortExpr = getExprWithInitInWidth(16);
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
            Expr<?> intExpr = getExprWithInitInWidth(32);
            concolicInt.setValueWithConstraints(result, intExpr);
        }
        return concolicInt;
    }

    public ConcolicLong ToLongExpr() {
        return this;
    }

    public ConcolicLong ToLong() {
        return this;
    }

    public ConcolicDouble ToDouble() {
        double result = Double.longBitsToDouble(this.getConcreteValue().longValue());
        ConcolicDouble concolicDouble = new ConcolicDouble();
        concolicDouble.setValueWithConstraints(result, this.getExpr());
        return concolicDouble;
    }

    public ConcolicFloat ToFloat() {
        float result = Float.intBitsToFloat(this.getConcreteValue().intValue());
        ConcolicFloat concolicFloat = new ConcolicFloat();
        concolicFloat.setValueWithConstraints(result, this.getExpr());
        return concolicFloat;
    }

    public ConcolicBoolean ToBoolean() {
        boolean result = this.getConcreteValue() != 0;
        ConcolicBoolean concolicBoolean = new ConcolicBoolean();
        concolicBoolean.setValueWithConstraints(result, this.getExpr());
        return concolicBoolean;
    }

    public ConcolicChar ToCharExpr() {
        return ToChar(true);
    }

    public ConcolicChar ToChar() {
        return ToChar(false);
    }

    public ConcolicChar ToChar(boolean extend) {
        char result = (char) this.getConcreteValue().intValue();
        ConcolicChar concolicChar = new ConcolicChar();
        if (extend == false || this.expr == null) {
            concolicChar.setValueWithConstraints(result, this.expr);
        } else {
            Expr<?> charExpr = getExprWithInitInWidthUnsigned(16);
            concolicChar.setValueWithConstraints(result, charExpr);
        }
        return concolicChar;
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
