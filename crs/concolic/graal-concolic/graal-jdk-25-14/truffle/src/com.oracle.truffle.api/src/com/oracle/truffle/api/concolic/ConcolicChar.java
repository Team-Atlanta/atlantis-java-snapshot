package com.oracle.truffle.api.concolic;

import com.microsoft.z3.*;
import com.oracle.truffle.api.concolic.ConcolicValueHelper;

public class ConcolicChar extends ConcolicValueWrapper<Character> implements ConcolicValue {
    public ConcolicChar() {
        super();
    }

    public static ConcolicChar createWithoutConstraints(char value) {
        ConcolicChar concolicChar = new ConcolicChar();
        concolicChar.setValueWithoutConstraints(value);
        return concolicChar;
    }

    @Override
    protected void calculateExpr() {
        // TODO: Should change this type
        expr = Z3Helper.mkInt(this.getConcreteValue());
    }

    public ConcolicChar Add(ConcolicChar other) {
        char result = (char) (this.getConcreteValue() + other.getConcreteValue());
        ConcolicChar concolicChar = new ConcolicChar();
        concolicChar.setValueWithoutConstraints(result);
        return concolicChar;
    }

    public ConcolicChar Subtract(ConcolicChar other) {
        char result = (char) (this.getConcreteValue() - other.getConcreteValue());
        ConcolicChar concolicChar = new ConcolicChar();
        concolicChar.setValueWithoutConstraints(result);
        return concolicChar;
    }

    public ConcolicChar Multiply(ConcolicChar other) {
        char result = (char) (this.getConcreteValue() * other.getConcreteValue());
        ConcolicChar concolicChar = new ConcolicChar();
        concolicChar.setValueWithoutConstraints(result);
        return concolicChar;
    }

    public ConcolicChar Divide(ConcolicChar other) {
        char result = (char) (this.getConcreteValue() / other.getConcreteValue());
        ConcolicChar concolicChar = new ConcolicChar();
        concolicChar.setValueWithoutConstraints(result);
        return concolicChar;
    }

    public ConcolicChar Modulo(ConcolicChar other) {
        char result = (char) (this.getConcreteValue() % other.getConcreteValue());
        ConcolicChar concolicChar = new ConcolicChar();
        concolicChar.setValueWithoutConstraints(result);
        return concolicChar;
    }

    public ConcolicChar Negate() {
        char result = (char) -this.getConcreteValue();
        ConcolicChar concolicChar = new ConcolicChar();
        concolicChar.setValueWithoutConstraints(result);
        return concolicChar;
    }

    // Bitwise operations are not applicable for char, so they are omitted.

    public ConcolicLong ToLongExpr() {
        return ToLong(true);
    }

    public ConcolicLong ToLong() {
        return ToLong(false);
    }

    public ConcolicLong ToLong(boolean extend) {
        long result = (long) this.getConcreteValue().charValue();
        ConcolicLong concolicLong = new ConcolicLong();
        if (extend == false || this.expr == null) {
            concolicLong.setValueWithConstraints(result, this.expr);
        } else {
            BitVecExpr longExpr = Z3Helper.convertBitVecWidthUnsigned((BitVecExpr) this.expr, 64);
            concolicLong.setValueWithConstraints(result, longExpr);
        }
        return concolicLong;
    }
}
