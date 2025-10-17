package com.oracle.truffle.espresso.concolic;

import com.oracle.truffle.api.concolic.*;
import com.oracle.truffle.espresso.meta.Meta;
import com.oracle.truffle.espresso.runtime.staticobject.StaticObject;
import com.oracle.truffle.espresso.impl.Klass;
import com.microsoft.z3.*;
import java.util.*;

public class SeqSupport {
    public static ConcolicArrayObject getByteArray(ConcolicObjectImpl str) {
        return str.isString() ? (ConcolicArrayObject) str.getOrCreateField(0) : null;
    }

    public static SeqExpr<? extends Sort> createSeqExpr(ConcolicObjectImpl obj, int width) {
        if (obj == null) {
            return null;
        } else if (obj.isArray()) {
            Klass componentKlass = ((ConcolicArrayObject) obj).getComponentKlass();
            if (componentKlass.isPrimitive() || ConcolicObjectImpl.isBoxed(componentKlass)) {
                SeqExpr<BitVecSort> seq = null;
                for (ConcolicValueWrapper<?> e : obj.getFields()) {
                    SeqExpr<BitVecSort> bv = Z3Helper.mkUnit((BitVecExpr) e.getExprWithInit());
                    seq = seq == null ? bv : Z3Helper.mkConcat(seq, bv);
                }
                return seq;
            } else if (ConcolicObjectImpl.isString(componentKlass)) {
                SeqExpr<SeqSort<BitVecSort>> seq = null;
                for (ConcolicValueWrapper<?> e : obj.getFields()) {
                    SeqExpr<BitVecSort> seqExpr = (SeqExpr<BitVecSort>) e.getSeqExprWithInit();
                    int len = ((ConcolicObjectImpl) e).getConcreteStringValue().length();
                    if (seqExpr != null && (width < 0 || width == len)) {
                        SeqExpr<SeqSort<BitVecSort>> bv = Z3Helper.mkUnit(seqExpr);
                        seq = seq == null ? bv : Z3Helper.mkConcat(seq, bv);
                    }
                }
                return seq;
            }
        } else if (obj.isAbstractCollection()) {
            AbstractCollection<ConcolicValueWrapper<?>> collection = obj.getAbstractCollection();
            if (collection.size() == 0) {
                return null;
            } else if (collection.iterator().next().isBoxed()) {
                SeqExpr<BitVecSort> seq = null;
                for (ConcolicValueWrapper<?> e : collection) {
                    SeqExpr<BitVecSort> bv = Z3Helper.mkUnit((BitVecExpr) e.getExprWithInit());
                    seq = seq == null ? bv : Z3Helper.mkConcat(seq, bv);
                }
                return seq;
            } else if (collection.iterator().next().isString()) {
                SeqExpr<SeqSort<BitVecSort>> seq = null;
                for (ConcolicValueWrapper<?> e : collection) {
                    SeqExpr<BitVecSort> seqExpr = (SeqExpr<BitVecSort>) e.getSeqExprWithInit();
                    int len = ((ConcolicObjectImpl) e).getConcreteStringValue().length();
                    if (seqExpr != null && (width < 0 || width == len)) {
                        SeqExpr<SeqSort<BitVecSort>> bv = Z3Helper.mkUnit(seqExpr);
                        seq = seq == null ? bv : Z3Helper.mkConcat(seq, bv);
                    }
                }
                return seq;
            }
        }
        return null;
    }

    public static SeqExpr<BitVecSort> createStrSeqExpr(ConcolicObjectImpl str, int width) {
        if (!str.isString()) return null;
        return (SeqExpr<BitVecSort>) createSeqExpr(getByteArray(str), width);
    }
}
