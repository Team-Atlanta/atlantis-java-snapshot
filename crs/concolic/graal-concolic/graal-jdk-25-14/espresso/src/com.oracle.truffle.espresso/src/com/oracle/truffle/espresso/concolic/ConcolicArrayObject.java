package com.oracle.truffle.espresso.concolic;

import com.oracle.truffle.api.concolic.*;
import com.oracle.truffle.espresso.classfile.JavaKind;
import com.oracle.truffle.espresso.impl.Klass;
import com.oracle.truffle.espresso.impl.ArrayKlass;
import com.microsoft.z3.*;

public class ConcolicArrayObject extends ConcolicObjectImpl {

    private ConcolicInt size = null;

    public ConcolicArrayObject(Object value, ConcolicInt size) {
        super();
        setValueWithoutConstraints(value);
        this.size = size;
    }

    public final ConcolicValueWrapper<?> getElement(int index) {
        return getField(index);
    }

    public final void setElement(int index, ConcolicValueWrapper<?> value) {
        putField(index, value);
    }

    public ConcolicInt getSize() {
        return size;
    }

    @Override
    public ConcolicValueWrapper<?> getAs(JavaKind kind, int index) {
        int valueSize = (kind.equals(JavaKind.Object)) ? 4 : kind.getByteCount();
        int fieldSize = getFieldSize();
        if (Logger.compileLog) {
            Logger.DEBUG("getAs(" + kind + ", " + index + ") concreteSize: " + getConcreteSize() + ", fieldSize: " + fieldSize);
        }
        if (getField(index) == null || valueSize / fieldSize > getConcreteSize() - index) {
            if (Logger.compileLog) {
                Logger.WARNING("Invalid!");
            }
            return null;
        }

        long concrete = 0L;
        BitVecExpr expr = null;
        if (valueSize <= fieldSize) {
            ConcolicValueWrapper<?> field = getField(index);
            if (field.getConcreteValue() instanceof Number num) {
                concrete = num.longValue();
            } else {
                concrete = (long) field.getConcreteValue();
            }
            if (field.isSymbolic()) {
                expr = (BitVecExpr) field.getExprWithInitInWidthUnsigned(8 * valueSize);
            }
        } else {
            boolean eitherSymbolic = false;
            int fieldBits = 8 * fieldSize;
            for (int i = 0; i < valueSize / fieldSize; i++) {
                ConcolicValueWrapper<?> field = getField(index + i);
                long mask = (1L << fieldBits) - 1;
                concrete |= ((((Number) field.getConcreteValue()).longValue() & mask) << (fieldBits * i));
                if (eitherSymbolic || field.isSymbolic()) {
                    eitherSymbolic = true;
                    BitVecExpr fieldExpr = (BitVecExpr) field.getExprWithInitInWidthUnsigned(fieldBits);
                    expr = (i == 0) ? fieldExpr : Z3Helper.mkConcat(fieldExpr, expr);  // little-endian
                }
            }
        }
        switch(kind) {
            case Boolean: {
                ConcolicBoolean ret = new ConcolicBoolean();
                ret.setValueWithConstraints(concrete != 0, expr);
                return ret;
            }
            case Byte: {
                ConcolicByte ret = new ConcolicByte();
                ret.setValueWithConstraints((byte) concrete, expr);
                return ret;
            }
            case Char: {
                ConcolicChar ret = new ConcolicChar();
                ret.setValueWithConstraints((char) concrete, expr);
                return ret;
            }
            case Int: {
                ConcolicInt ret = new ConcolicInt();
                ret.setValueWithConstraints((int) concrete, expr);
                return ret;
            }
            case Long: {
                ConcolicLong ret = new ConcolicLong();
                ret.setValueWithConstraints(concrete, expr);
                return ret;
            }
            case Float: {
                ConcolicFloat ret = new ConcolicFloat();
                ret.setValueWithConstraints(Float.intBitsToFloat((int) concrete), expr);
                return ret;
            }
            case Double: {
                ConcolicDouble ret = new ConcolicDouble();
                ret.setValueWithConstraints(Double.longBitsToDouble(concrete), expr);
                return ret;
            }
            case Short: {
                ConcolicShort ret = new ConcolicShort();
                ret.setValueWithConstraints((short) concrete, expr);
                return ret;
            }
            default:
                throw new RuntimeException("Unknown getAs(" + kind + ", " + index + ")");
        }
    }

    @Override
    public void putAs(JavaKind kind, int index, ConcolicValueWrapper<?> v) {
        if (Logger.compileLog) {
            synchronized (Z3Helper.getInstance()) {
                Logger.DEBUG("putAs(" + kind + ", " + index + ", " + v + ") concreteSize: " + getConcreteSize() + ", fieldSize: " + getFieldSize());
            }
        }
        JavaKind fieldKind = this.getFieldKind(index);
        if (fieldKind == null) {
            if (Logger.compileLog) {
                Logger.WARNING("putAs: fieldKind isNull");
            }
            return;
        }
        if (fieldKind.equals(kind)) {
            putField(index, v);
            return;
        }

        int valueSize = (kind.equals(JavaKind.Object)) ? 4 : kind.getByteCount();
        int fieldSize = getFieldSize();
        if (valueSize / fieldSize > getConcreteSize() - index) {
            if (Logger.compileLog) {
                Logger.WARNING("Invalid!");
            }
            return;
        }

        if (valueSize <= fieldSize) {
            switch(fieldKind) {
                case Boolean: putField(index, v.ToLong().ToBoolean());  return;
                case Byte:    putField(index, v.ToLong().ToByte());     return;
                case Char:    putField(index, v.ToLong().ToChar());     return;
                case Int:     putField(index, v.ToLong().ToInt());      return;
                case Long:    putField(index, v.ToLong());              return;
                case Float:   putField(index, v.ToLong().ToFloat());    return;
                case Double:  putField(index, v.ToLong().ToDouble());   return;
                case Short:   putField(index, v.ToLong().ToShort());    return;
                default:
                    throw new RuntimeException("Unknown getAs(" + kind + ", " + index + ")");
            }
        } else {
            long bits = v.ToLong().getConcreteValue();
            int fieldBits = 8 * fieldSize;
            int numFields = valueSize / fieldSize;
            for (int i = 0; i < numFields; i++) {
                long partialBits = (bits >>> (fieldBits * i)) & ((1L << fieldBits) - 1L);
                BitVecExpr partialExpr = null;
                if (v.isSymbolic()) {
                    int hi = fieldBits * (i + 1) - 1;
                    int lo = fieldBits * i;
                    partialExpr = Z3Helper.mkExtract(hi, lo, (BitVecExpr) v.getExprWithInit());
                }
                switch (fieldKind) {
                    case Boolean: {
                        ConcolicBoolean x = new ConcolicBoolean();
                        x.setValueWithConstraints(partialBits != 0, partialExpr);
                        putField(index + i, x);
                        break;
                    }
                    case Byte: {
                        ConcolicByte x = new ConcolicByte();
                        x.setValueWithConstraints((byte) partialBits, partialExpr);
                        putField(index + i, x);
                        break;
                    }
                    case Char: {
                        ConcolicChar x = new ConcolicChar();
                        x.setValueWithConstraints((char) partialBits, partialExpr);
                        putField(index + i, x);
                        break;
                    }
                    case Int: {
                        ConcolicInt x = new ConcolicInt();
                        x.setValueWithConstraints((int) partialBits, partialExpr);
                        putField(index + i, x);
                        break;
                    }
                    case Long: {
                        ConcolicLong x = new ConcolicLong();
                        x.setValueWithConstraints(partialBits, partialExpr);
                        putField(index + i, x);
                        break;
                    }
                    case Float: {
                        ConcolicFloat x = new ConcolicFloat();
                        x.setValueWithConstraints((float) partialBits, partialExpr);
                        putField(index + i, x);
                        break;
                    }
                    case Double: {
                        ConcolicDouble x = new ConcolicDouble();
                        x.setValueWithConstraints((double) partialBits, partialExpr);
                        putField(index + i, x);
                        break;
                    }
                    case Short: {
                        ConcolicShort x = new ConcolicShort();
                        x.setValueWithConstraints((short) partialBits, partialExpr);
                        putField(index + i, x);
                        break;
                    }
                    default:
                        throw new RuntimeException("Unsupported fieldSize=" + fieldSize + " in multi-field putAs");
                }
            }
        }
    }

    public Klass getComponentKlass() {
        return isArray() ? ((ArrayKlass) getConcreteObject().getKlass()).getComponentType() : null;
    }

    public final JavaKind getFieldKind() {
        return this.kinds[0];
    }

    public final int getFieldSize() {
        JavaKind kind = getFieldKind();
        return (kind.equals(JavaKind.Object)) ? 4 : kind.getByteCount();
    }
}
