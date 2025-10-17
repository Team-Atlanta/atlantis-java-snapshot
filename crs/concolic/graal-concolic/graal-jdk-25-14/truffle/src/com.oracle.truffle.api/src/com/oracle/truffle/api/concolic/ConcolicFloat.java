package com.oracle.truffle.api.concolic;

import com.microsoft.z3.*;

public class ConcolicFloat extends ConcolicValueWrapper<Float> implements ConcolicValue {
    public ConcolicFloat() {
        super();
    }

    private static final long INT_MASK = 0xFFFFFFFFL;
    private static long extend(int value) {
        return value & INT_MASK;
    }

    public static ConcolicFloat createWithoutConstraints(float value) {
        ConcolicFloat concolicFloat = new ConcolicFloat();
        concolicFloat.setValueWithoutConstraints(value);
        return concolicFloat;
    }

    @Override
    protected void calculateExpr() {
        // TODO: Should change this type
        expr = Z3Helper.mkReal(Float.toString(this.getConcreteValue()));
    }

    public ConcolicFloat Add(ConcolicFloat other) {
        float result = this.getConcreteValue() + other.getConcreteValue();
        ConcolicFloat concolicFloat = new ConcolicFloat();
        if (ConcolicValueHelper.eitherSymbolic(this, other)) {
            concolicFloat.setValueWithConstraints(result, getAddExprReal(other));
        } else {
            concolicFloat.setValueWithoutConstraints(result);
        }
        return concolicFloat;
    }

    public ConcolicFloat Subtract(ConcolicFloat other) {
        float result = this.getConcreteValue() - other.getConcreteValue();
        ConcolicFloat concolicFloat = new ConcolicFloat();
        if (ConcolicValueHelper.eitherSymbolic(this, other)) {
            concolicFloat.setValueWithConstraints(result, getSubtractExprReal(other));
        } else {
            concolicFloat.setValueWithoutConstraints(result);
        }
        return concolicFloat;
    }

    public ConcolicFloat Multiply(ConcolicFloat other) {
        float result = this.getConcreteValue() * other.getConcreteValue();
        ConcolicFloat concolicFloat = new ConcolicFloat();
        if (ConcolicValueHelper.eitherSymbolic(this, other)) {
            concolicFloat.setValueWithConstraints(result, getMultiplyExprReal(other));
        } else {
            concolicFloat.setValueWithoutConstraints(result);
        }
        return concolicFloat;
    }

    public ConcolicFloat Divide(ConcolicFloat other) {
        float result = this.getConcreteValue() / other.getConcreteValue();
        ConcolicFloat concolicFloat = new ConcolicFloat();
        if (ConcolicValueHelper.eitherSymbolic(this, other)) {
            concolicFloat.setValueWithConstraints(result, getDivideExprReal(other));
        } else {
            concolicFloat.setValueWithoutConstraints(result);
        }
        return concolicFloat;
    }

    public ConcolicFloat Modulo(ConcolicFloat other) {
        float result = this.getConcreteValue() % other.getConcreteValue();
        ConcolicFloat concolicFloat = new ConcolicFloat();
        if (ConcolicValueHelper.eitherSymbolic(this, other)) {
            concolicFloat.setValueWithConstraints(result, getModuloExprReal(other));
        } else {
            concolicFloat.setValueWithoutConstraints(result);
        }
        return concolicFloat;
    }

    public ConcolicFloat Negate() {
        float result = -this.getConcreteValue();
        ConcolicFloat concolicFloat = new ConcolicFloat();
        if (ConcolicValueHelper.eitherSymbolic(this)) {
            concolicFloat.setValueWithConstraints(result, getNegateExprReal());
        } else {
            concolicFloat.setValueWithoutConstraints(result);
        }
        return concolicFloat;
    }

    // Bitwise operations are not applicable for float, so they are omitted.
    //
    public ConcolicInt Compare(ConcolicFloat other) {
        int concreteResult = Float.compare(this.getConcreteValue(), other.getConcreteValue());

        ConcolicInt returnInt = new ConcolicInt();

        if (ConcolicValueHelper.eitherSymbolic(this, other)) {
            BitVecExpr bvZeroExpr = Z3Helper.getInstance().zeroExpr;
            BitVecExpr bvOneExpr = Z3Helper.getInstance().oneExpr;
            BitVecExpr bvMOneExpr = Z3Helper.getInstance().mOneExpr;

            // equality test
            BoolExpr eq = Z3Helper.mkEq(
                                (RealExpr) this.getExprWithInit(),
                                (RealExpr) other.getExprWithInit());

            // greater than teest
            BoolExpr gt = Z3Helper.mkGt(
                                (RealExpr) this.getExprWithInit(),
                                (RealExpr) other.getExprWithInit());

            // 2nd if, if equal, return 0; otherwise, return -1 (less than)
            Expr<?> ifeq = Z3Helper.mkITE(eq, bvZeroExpr, bvMOneExpr);
            // 1st if, if greater than, return 1; otherwise, return 2nd if result
            Expr<?> ifGt = Z3Helper.mkITE(gt, bvOneExpr, ifeq);

            returnInt.setValueWithConstraints(concreteResult, ifGt);

        } else {
            returnInt.setValueWithoutConstraints(concreteResult);
        }
        return returnInt;
    }

    public ConcolicLong ToLong() {
        long result = extend(Float.floatToRawIntBits(this.getConcreteValue()));
        ConcolicLong concolicLong = new ConcolicLong();
        concolicLong.setValueWithConstraints(result, this.getExpr());
        return concolicLong;
    }

    public ConcolicInt ToIntConversion() {
        int result = this.getConcreteValue().intValue();
        ConcolicInt ci = new ConcolicInt();
        if (ConcolicValueHelper.eitherSymbolic(this)) {
            Expr<?> intExpr = Z3Helper.mkReal2Int(
                                        (RealExpr) this.getExprWithInit());
            Expr<?> resultExpr = Z3Helper.mkInt2BV(32, (IntExpr) intExpr);
            ci.setValueWithConstraints(result, resultExpr);
        } else {
            ci.setValueWithoutConstraints(result);
        }
        return ci;
    }

    public ConcolicLong ToLongConversion() {
        long result = this.getConcreteValue().longValue();
        ConcolicLong cl = new ConcolicLong();
        if (ConcolicValueHelper.eitherSymbolic(this)) {
            Expr<?> intExpr = Z3Helper.mkReal2Int(
                                        (RealExpr) this.getExprWithInit());
            Expr<?> resultExpr = Z3Helper.mkInt2BV(64, (IntExpr) intExpr);
            cl.setValueWithConstraints(result, resultExpr);
        } else {
            cl.setValueWithoutConstraints(result);
        }
        return cl;
    }

    public ConcolicDouble ToDoubleConversion() {
        double result = this.getConcreteValue().doubleValue();
        ConcolicDouble cd = new ConcolicDouble();
        if (ConcolicValueHelper.eitherSymbolic(this)) {
            cd.setValueWithConstraints(result, this.getExprWithInit());
        } else {
            cd.setValueWithoutConstraints(result);
        }
        return cd;
    }

}
