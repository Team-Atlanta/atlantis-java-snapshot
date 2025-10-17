package com.oracle.truffle.api.concolic;

import com.microsoft.z3.*;

public class ConcolicDouble extends ConcolicValueWrapper<Double> implements ConcolicValue {
    public ConcolicDouble() {
        super();
    }

    public static ConcolicDouble createWithoutConstraints(double value) {
        ConcolicDouble concolicDouble = new ConcolicDouble();
        concolicDouble.setValueWithoutConstraints(value);
        return concolicDouble;
    }

    @Override
    protected void calculateExpr() {
        // TODO: Should change this type
        expr = Z3Helper.mkReal(Double.toString(this.getConcreteValue()));
    }

    public ConcolicDouble Add(ConcolicDouble other) {
        double result = this.getConcreteValue() + other.getConcreteValue();
        ConcolicDouble concolicDouble = new ConcolicDouble();
        if (ConcolicValueHelper.eitherSymbolic(this, other)) {
            concolicDouble.setValueWithConstraints(result, getAddExprReal(other));
        } else {
            concolicDouble.setValueWithoutConstraints(result);
        }
        return concolicDouble;
    }

    public ConcolicDouble Subtract(ConcolicDouble other) {
        double result = this.getConcreteValue() - other.getConcreteValue();
        ConcolicDouble concolicDouble = new ConcolicDouble();
        if (ConcolicValueHelper.eitherSymbolic(this, other)) {
            concolicDouble.setValueWithConstraints(result, getSubtractExprReal(other));
        } else {
            concolicDouble.setValueWithoutConstraints(result);
        }
        return concolicDouble;
    }

    public ConcolicDouble Multiply(ConcolicDouble other) {
        double result = this.getConcreteValue() * other.getConcreteValue();
        ConcolicDouble concolicDouble = new ConcolicDouble();
        if (ConcolicValueHelper.eitherSymbolic(this, other)) {
            concolicDouble.setValueWithConstraints(result, getMultiplyExprReal(other));
        } else {
            concolicDouble.setValueWithoutConstraints(result);
        }
        return concolicDouble;
    }

    public ConcolicDouble Divide(ConcolicDouble other) {
        double result = this.getConcreteValue() / other.getConcreteValue();
        ConcolicDouble concolicDouble = new ConcolicDouble();
        if (ConcolicValueHelper.eitherSymbolic(this, other)) {
            concolicDouble.setValueWithConstraints(result, getDivideExprReal(other));
        } else {
            concolicDouble.setValueWithoutConstraints(result);
        }
        return concolicDouble;
    }

    public ConcolicDouble Modulo(ConcolicDouble other) {
        double result = this.getConcreteValue() % other.getConcreteValue();
        ConcolicDouble concolicDouble = new ConcolicDouble();
        if (ConcolicValueHelper.eitherSymbolic(this, other)) {
            concolicDouble.setValueWithConstraints(result, getModuloExprReal(other));
        } else {
            concolicDouble.setValueWithoutConstraints(result);
        }
        return concolicDouble;
    }

    public ConcolicDouble Negate() {
        double result = -this.getConcreteValue();
        ConcolicDouble concolicDouble = new ConcolicDouble();
        if (ConcolicValueHelper.eitherSymbolic(this)) {
            concolicDouble.setValueWithConstraints(result, getNegateExprReal());
        } else {
            concolicDouble.setValueWithoutConstraints(result);
        }
        return concolicDouble;
    }

    // Bitwise operations are not applicable for double, so they are omitted.
    public ConcolicInt Compare(ConcolicDouble other) {
        int concreteResult = Double.compare(this.getConcreteValue(), other.getConcreteValue());

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
        long result = Double.doubleToRawLongBits(this.getConcreteValue());
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

    public ConcolicFloat ToFloatConversion() {
        float result = this.getConcreteValue().floatValue();
        ConcolicFloat cf = new ConcolicFloat();
        if (ConcolicValueHelper.eitherSymbolic(this)) {
            cf.setValueWithConstraints(result, this.getExprWithInit());
        } else {
            cf.setValueWithoutConstraints(result);
        }
        return cf;
    }

}
