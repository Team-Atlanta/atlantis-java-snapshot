package com.oracle.truffle.api.concolic;

import com.microsoft.z3.*;

public class Z3Helper {
    private static Z3Helper instance;
    private Context z3Context;

    public BoolExpr trueExpr;
    public BoolExpr falseExpr;

    public BitVecExpr zeroExpr;
    public BitVecExpr oneExpr;
    public BitVecExpr mOneExpr;
    public BitVecExpr byteMinExpr;
    public BitVecExpr byteMaxExpr;
    public BitVecExpr shortMinExpr;
    public BitVecExpr shortMaxExpr;
    public BitVecExpr intMinExpr;
    public BitVecExpr intMaxExpr;

    public BitVecExpr hashCodeExpr;

    public BitVecExpr zeroExpr64;
    public BitVecExpr oneExpr64;
    public BitVecExpr mOneExpr64;
    public BitVecExpr byteMinExpr64;
    public BitVecExpr byteMaxExpr64;
    public BitVecExpr shortMinExpr64;
    public BitVecExpr shortMaxExpr64;
    public BitVecExpr intMinExpr64;
    public BitVecExpr intMaxExpr64;
    public BitVecExpr longMinExpr64;
    public BitVecExpr longMaxExpr64;

    private Z3Helper() {
        synchronized(this) {
            z3Context = new Context();
            trueExpr = z3Context.mkBool(true);
            falseExpr = z3Context.mkBool(false);

            zeroExpr = (BitVecExpr) z3Context.mkBV(0, 32);
            oneExpr = (BitVecExpr) z3Context.mkBV(1, 32);
            mOneExpr = (BitVecExpr) z3Context.mkBV(-1, 32);
            byteMinExpr = (BitVecExpr) z3Context.mkBV(Byte.MIN_VALUE, 32);
            byteMaxExpr = (BitVecExpr) z3Context.mkBV(Byte.MAX_VALUE, 32);
            shortMinExpr = (BitVecExpr) z3Context.mkBV(Short.MIN_VALUE, 32);
            shortMaxExpr = (BitVecExpr) z3Context.mkBV(Short.MAX_VALUE, 32);
            intMinExpr = (BitVecExpr) z3Context.mkBV(Integer.MIN_VALUE, 32);
            intMaxExpr = (BitVecExpr) z3Context.mkBV(Integer.MAX_VALUE, 32);

            zeroExpr64 = (BitVecExpr) z3Context.mkBV(0, 64);
            oneExpr64 = (BitVecExpr) z3Context.mkBV(1, 64);
            mOneExpr64 = (BitVecExpr) z3Context.mkBV(-1, 64);
            byteMinExpr64 = (BitVecExpr) z3Context.mkBV(Byte.MIN_VALUE, 64);
            byteMaxExpr64 = (BitVecExpr) z3Context.mkBV(Byte.MAX_VALUE, 64);
            shortMinExpr64 = (BitVecExpr) z3Context.mkBV(Short.MIN_VALUE, 32);
            shortMaxExpr64 = (BitVecExpr) z3Context.mkBV(Short.MAX_VALUE, 64);
            intMinExpr64 = (BitVecExpr) z3Context.mkBV(Integer.MIN_VALUE, 64);
            intMaxExpr64 = (BitVecExpr) z3Context.mkBV(Integer.MAX_VALUE, 64);
            longMinExpr64 = (BitVecExpr) z3Context.mkBV(Long.MIN_VALUE, 64);
            longMaxExpr64 = (BitVecExpr) z3Context.mkBV(Long.MAX_VALUE, 64);
            hashCodeExpr = (BitVecExpr) z3Context.mkBVConst("hashCode", 32);
        }
    }

    public static Z3Helper getInstance() {
        if (Z3Helper.instance == null) {
            Z3Helper.instance = new Z3Helper();
        }
        return Z3Helper.instance;
    }

    public static void resetInstance() {
        if (Z3Helper.instance != null) {
            //System.out.println("[Z3Helper.resetInstance()] context closing!");
            Z3Helper.getContext().close();
            Z3Helper.instance = new Z3Helper();
        }
    }

    private static Context getContext() {
        return getInstance().z3Context;
    }

    public static void resetContext() {
        resetInstance();
    }

    public static BitVecExpr createByteVar(String name) {
        synchronized (getInstance()) {
            return getContext().mkBVConst(name, 8);
        }
    }

    public static BitVecExpr createShortVar(String name) {
        synchronized (getInstance()) {
            return getContext().mkBVConst(name, 16);
        }
    }

    public static BitVecExpr createIntVar(String name) {
        synchronized (getInstance()) {
            return getContext().mkBVConst(name, 32);
        }
    }

    public static BitVecExpr createLongVar(String name) {
        synchronized(getInstance()) {
            return getContext().mkBVConst(name, 64);
        }
    }

    public static BitVecExpr convertBitVecWidth(BitVecExpr expr, int newWidth) {
        synchronized(getInstance()) {
            int currentWidth = expr.getSortSize();
            if (currentWidth == newWidth) {
                return expr;
            } else if (currentWidth > newWidth) {
                return getContext().mkExtract(newWidth-1, 0, expr);
            } else {
                return getContext().mkSignExt(newWidth - currentWidth, expr);
            }
        }
    }

    public static BitVecExpr convertBitVecWidthUnsigned(BitVecExpr expr, int newWidth) {
        synchronized(getInstance()) {
            int currentWidth = expr.getSortSize();
            if (currentWidth == newWidth) {
                return expr;
            } else if (currentWidth > newWidth) {
                return getContext().mkExtract(newWidth-1, 0, expr);
            } else {
                return getContext().mkZeroExt(newWidth - currentWidth, expr);
            }
        }
    }

    public static BitVecExpr mkExtract(int high, int low, BitVecExpr expr) {
        synchronized(getInstance()) {
            return getContext().mkExtract(high, low, expr);
        }
    }

    public static BitVecExpr mkSignExt(int width, BitVecExpr expr) {
        synchronized(getInstance()) {
            return getContext().mkSignExt(width, expr);
        }
    }

    public static BitVecExpr mkZeroExt(int width, BitVecExpr expr) {
        synchronized(getInstance()) {
            return getContext().mkZeroExt(width, expr);
        }
    }

    public static Expr<?> mkAdd(RealExpr expr1, RealExpr expr2) {
        synchronized(getInstance()) {
            return getContext().mkAdd(expr1, expr2);
        }
    }

    public static BitVecExpr mkBV(long value, int width) {
        synchronized(getInstance()) {
            return getContext().mkBV(value, width);
        }
    }

    public static BitVecExpr mkBVAdd(BitVecExpr expr1, BitVecExpr expr2) {
        synchronized(getInstance()) {
            return getContext().mkBVAdd(expr1, expr2);
        }
    }

    public static BitVecExpr mkBVSub(BitVecExpr expr1, BitVecExpr expr2) {
        synchronized(getInstance()) {
            return getContext().mkBVSub(expr1, expr2);
        }
    }

    public static Expr<?> mkSub(RealExpr expr1, RealExpr expr2) {
        synchronized(getInstance()) {
            return getContext().mkSub(expr1, expr2);
        }
    }

    public static BitVecExpr mkBVMul(BitVecExpr expr1, BitVecExpr expr2) {
        synchronized(getInstance()) {
            return getContext().mkBVMul(expr1, expr2);
        }
    }

    public static Expr<?> mkMul(RealExpr expr1, RealExpr expr2) {
        synchronized(getInstance()) {
            return getContext().mkMul(expr1, expr2);
        }
    }

    public static BitVecExpr mkBVSDiv(BitVecExpr expr1, BitVecExpr expr2) {
        synchronized(getInstance()) {
            return getContext().mkBVSDiv(expr1, expr2);
        }
    }

    public static Expr<?> mkDiv(RealExpr expr1, RealExpr expr2) {
        synchronized(getInstance()) {
            return getContext().mkDiv(expr1, expr2);
        }
    }

    public static BitVecExpr mkBVSRem(BitVecExpr expr1, BitVecExpr expr2) {
        synchronized(getInstance()) {
            return getContext().mkBVSRem(expr1, expr2);
        }
    }

    public static IntExpr mkReal2Int(RealExpr expr) {
        synchronized(getInstance()) {
            return getContext().mkReal2Int(expr);
        }
    }

    public static RealExpr mkInt2Real(IntExpr expr) {
        synchronized(getInstance()) {
            return getContext().mkInt2Real(expr);
        }
    }

    public static BitVecExpr mkBVNeg(BitVecExpr expr) {
        synchronized(getInstance()) {
            return getContext().mkBVNeg(expr);
        }
    }

    public static Expr<?> mkUnaryMinus(RealExpr expr) {
        synchronized(getInstance()) {
            return getContext().mkUnaryMinus(expr);
        }
    }

    public static BitVecExpr mkBVAND(BitVecExpr expr1, BitVecExpr expr2) {
        synchronized(getInstance()) {
            return getContext().mkBVAND(expr1, expr2);
        }
    }

    public static BitVecExpr mkBVOR(BitVecExpr expr1, BitVecExpr expr2) {
        synchronized(getInstance()) {
            return getContext().mkBVOR(expr1, expr2);
        }
    }

    public static BitVecExpr mkBVXOR(BitVecExpr expr1, BitVecExpr expr2) {
        synchronized(getInstance()) {
            return getContext().mkBVXOR(expr1, expr2);
        }
    }

    public static BitVecExpr mkBVSHL(BitVecExpr expr1, BitVecExpr expr2) {
        synchronized(getInstance()) {
            return getContext().mkBVSHL(expr1, expr2);
        }
    }

    public static BitVecExpr mkBVASHR(BitVecExpr expr1, BitVecExpr expr2) {
        synchronized(getInstance()) {
            return getContext().mkBVASHR(expr1, expr2);
        }
    }

    public static BitVecExpr mkBVLSHR(BitVecExpr expr1, BitVecExpr expr2) {
        synchronized(getInstance()) {
            return getContext().mkBVLSHR(expr1, expr2);
        }
    }

    public static BoolExpr mkEq(Expr<?> expr1, Expr<?> expr2) {
        synchronized(getInstance()) {
            return getContext().mkEq(expr1, expr2);
        }
    }

    public static BoolExpr mkBVSGT(Expr<?> expr1, Expr<?> expr2) {
        synchronized(getInstance()) {
            return getContext().mkBVSGT((BitVecExpr) expr1, (BitVecExpr) expr2);
        }
    }

    public static BoolExpr mkBVSGE(Expr<?> expr1, Expr<?> expr2) {
        synchronized(getInstance()) {
            return getContext().mkBVSGE((BitVecExpr) expr1, (BitVecExpr) expr2);
        }
    }

    public static BoolExpr mkBVSLT(Expr<?> expr1, Expr<?> expr2) {
        synchronized(getInstance()) {
            return getContext().mkBVSLT((BitVecExpr) expr1, (BitVecExpr) expr2);
        }
    }

    public static BoolExpr mkBVSLE(BitVecExpr expr1, BitVecExpr expr2) {
        synchronized(getInstance()) {
            return getContext().mkBVSLE(expr1, expr2);
        }
    }

    public static Expr<?> mkITE(BoolExpr boolExpr, Expr<?> expr1, Expr<?> expr2) {
        synchronized(getInstance()) {
            return getContext().mkITE(boolExpr, expr1, expr2);
        }
    }

    public static IntExpr mkBV2Int(BitVecExpr expr, boolean signed) {
        synchronized(getInstance()) {
            return getContext().mkBV2Int(expr, signed);
        }
    }

    public static RealExpr mkReal(String value) {
        synchronized(getInstance()) {
            return getContext().mkReal(value);
        }
    }

    public static BitVecExpr mkInt2BV(int width, IntExpr expr) {
        synchronized(getInstance()) {
            return getContext().mkInt2BV(width, expr);
        }
    }

    public static BoolExpr mkGt(Expr<?> expr1, Expr<?> expr2) {
        synchronized(getInstance()) {
            return getContext().mkGt((RealExpr)expr1, (RealExpr)expr2);
        }
    }

    public static BoolExpr mkBool(boolean value) {
        synchronized(getInstance()) {
            return getContext().mkBool(value);
        }
    }

    public static BoolExpr mkAnd(BoolExpr expr1, BoolExpr expr2) {
        synchronized(getInstance()) {
            return getContext().mkAnd(expr1, expr2);
        }
    }

    public static BoolExpr mkNot(BoolExpr expr) {
        synchronized(getInstance()) {
            return getContext().mkNot(expr);
        }
    }

    public static BitVecExpr mkConcat(BitVecExpr expr1, BitVecExpr expr2) {
        synchronized(getInstance()) {
            return getContext().mkConcat(expr1, expr2);
        }
    }

    public static BoolExpr mkTrue() {
        synchronized(getInstance()) {
            return getContext().mkTrue();
        }
    }

    public static SeqExpr<CharSort> mkString(String value) {
        synchronized(getInstance()) {
            return getContext().mkString(value);
        }
    }

    public static BoolExpr mkContains(SeqExpr<BitVecSort> expr1, SeqExpr<BitVecSort> expr2) {
        synchronized(getInstance()) {
            return getContext().mkContains(expr1, expr2);
        }
    }

    public static <R extends Sort> BoolExpr mkContains(Expr<SeqSort<R>> expr1, Expr<SeqSort<R>> expr2) {
        synchronized(getInstance()) {
            return getContext().mkContains(expr1, expr2);
        }
    }

    public static <R extends Sort> SeqExpr<R> mkUnit(Expr<R> elem) {
        synchronized(getInstance()) {
            return getContext().mkUnit(elem);
        }
    }

    public static BitVecExpr mkConcat(Expr<BitVecSort> expr1, Expr<BitVecSort> expr2) {
        synchronized(getInstance()) {
            return getContext().mkConcat(expr1, expr2);
        }
    }

    public static <R extends Sort> SeqExpr<R> mkConcat(SeqExpr<R> expr1, SeqExpr<R> expr2) {
        synchronized(getInstance()) {
            return getContext().mkConcat(expr1, expr2);
        }
    }

    public static IntExpr mkInt(int i) {
        synchronized(getInstance()) {
            return getContext().mkInt(i);
        }
    }

    public static <D extends Sort, R extends Sort> ArrayExpr<D, R> mkStore(Expr<ArraySort<D, R>> a, Expr<D> i, Expr<R> v) {
        synchronized(getInstance()) {
            return getContext().mkStore(a, i, v);
        }
    }

    public static <R extends Sort> IntExpr mkIndexOf(Expr<SeqSort<R>> s, Expr<SeqSort<R>> substr, Expr<IntSort> offset) {
        synchronized(getInstance()) {
            return getContext().mkIndexOf(s, substr, offset);
        }
    }

    public static <R extends Sort> SeqExpr<R> mkAt(Expr<SeqSort<R>> s, Expr<IntSort> index) {
        synchronized(getInstance()) {
            return getContext().mkAt(s, index);
        }
    }

    public static <D extends Sort, R extends Sort> Expr<R> mkSelect(Expr<ArraySort<D, R>> a, Expr<D> i) {
        synchronized(getInstance()) {
            return getContext().mkSelect(a, i);
        }
    }

    public static < D extends Sort, R extends Sort > ArrayExpr< D, R > mkArrayConst(String name, D domain, R range) {
        synchronized(getInstance()) {
            return getContext().mkArrayConst(name, domain, range);
        }
    }

    public static < D extends Sort, R extends Sort > ArrayExpr< D, R > mkConstArray(D domain, Expr<R> v) {
        synchronized(getInstance()) {
            return getContext().mkConstArray(domain, v);
        }
    }

    public static BitVecSort mkBitVecSort (int size)   {
        synchronized(getInstance()) {
            return getContext().mkBitVecSort(size);
        }
    }

    public static <R extends Sort> SeqSort<R> mkSeqSort(R s) {
        synchronized(getInstance()) {
            return getContext().mkSeqSort(s);
        }
    }

    public static Solver mkSolver () {
        synchronized(getInstance()) {
            return getContext().mkSolver();
        }
    }

    public static Params mkParams() {
        synchronized(getInstance()) {
            return getContext().mkParams();
        }
    }

    public static Optimize mkOptimize() {
        synchronized(getInstance()) {
            return getContext().mkOptimize();
        }
    }
}
