package com.oracle.truffle.api.concolic;

import com.microsoft.z3.*;

public class ConcolicBoolean extends ConcolicValueWrapper<Boolean> implements ConcolicValue {
    public ConcolicBoolean() {
        super();
    }

    public static ConcolicBoolean createWithoutConstraints(boolean value) {
        ConcolicBoolean concolicBoolean = new ConcolicBoolean();
        concolicBoolean.setValueWithoutConstraints(value);
        return concolicBoolean;
    }

    @Override
    protected void calculateExpr() {
        expr = Z3Helper.mkBool(this.getConcreteValue());
    }

    @Override
    public void setExpr(Expr<?> expr) {
        if (expr instanceof BoolExpr boolExpr) {
            BitVecExpr bv1 = Z3Helper.getInstance().oneExpr;
            BitVecExpr bv0 = Z3Helper.getInstance().zeroExpr;
            expr = (BitVecExpr) Z3Helper.mkITE(boolExpr, bv1, bv0);
        }
        super.setExpr(expr);
    }

    public ConcolicBoolean And(ConcolicBoolean other) {
        boolean result = this.getConcreteValue() && other.getConcreteValue();
        ConcolicBoolean concolicBoolean = new ConcolicBoolean();
        concolicBoolean.setValueWithoutConstraints(result);
        return concolicBoolean;
    }

    public ConcolicBoolean Or(ConcolicBoolean other) {
        boolean result = this.getConcreteValue() || other.getConcreteValue();
        ConcolicBoolean concolicBoolean = new ConcolicBoolean();
        concolicBoolean.setValueWithoutConstraints(result);
        return concolicBoolean;
    }

    public ConcolicBoolean Xor(ConcolicBoolean other) {
        boolean result = this.getConcreteValue() ^ other.getConcreteValue();
        ConcolicBoolean concolicBoolean = new ConcolicBoolean();
        concolicBoolean.setValueWithoutConstraints(result);
        return concolicBoolean;
    }

    public ConcolicBoolean Not() {
        boolean result = !this.getConcreteValue();
        ConcolicBoolean concolicBoolean = new ConcolicBoolean();
        concolicBoolean.setValueWithoutConstraints(result);
        return concolicBoolean;
    }

    public ConcolicBoolean ToBoolean() {
        return this;
    }

    public ConcolicLong ToLong() {
        long result = this.getConcreteValue() ? 1L : 0L;
        ConcolicLong concolicLong = new ConcolicLong();
        concolicLong.setValueWithConstraints(result, this.getExpr());
        return concolicLong;
    }
}
