package com.oracle.truffle.api.concolic;

import com.microsoft.z3.*;
import java.util.ArrayList;

public abstract class ConcolicValueWrapper<T> {

    protected T concrete_value;
    protected Expr<?> expr = null;
    protected ArrayList<ConcolicVariableInfo> infoList;
    protected ConcolicObject parent;
    protected int parentElementIdx;

    public ConcolicValueWrapper() {
        this.concrete_value = null;
        this.expr = null;
        this.parent = null;
        this.parentElementIdx = -1;
        this.infoList = new ArrayList<ConcolicVariableInfo>();
    }

    // TODO: add method for creating a ConcolicValueWrapper with a constraint

    public void setValueWithoutConstraints(T value) {
        this.concrete_value = value;
        this.expr = null;
    }

    public void setValueWithConstraints(Object value, Expr<?> expr) {
        this.concrete_value = (T) value;
        this.setExpr(expr);
    }

    public T getConcreteValue() {
        return concrete_value;
    }

    public Expr<?> getExpr() {
        // Use this method in most cases. See getExprWithInit() for more details.
        return expr;
    }

    public void setParent(ConcolicObject parent, int parentElementIdx) {
        this.parent = parent;
        this.parentElementIdx = parentElementIdx;
    }

    public void setExpr(Expr<?> expr) {
        boolean beforeSymbolic = isSymbolic();
        this.expr = expr;
        boolean afterSymbolic = isSymbolic();
        if (parent != null && beforeSymbolic != afterSymbolic) {
            parent.updateSymbolic(afterSymbolic, parentElementIdx);
        }
    }

    public SeqExpr<?> getSeqExprWithInit() {
        throw new UnsupportedOperationException("This method should be overridden by subclasses");
    }

    public Expr<?> getExprWithInit() {
        // If you need to get expr with valid default value, call this method
        // Otherwise, you should call getExpr() instead.
        // Beacuse too many exprs can cause Z3 memory corruption.
        if (expr == null) {
            calculateExpr();
        }
        return expr;
    }

    abstract protected void calculateExpr();

    public boolean isSymbolic() {
        return expr != null;
    }

    public void setNonSymbolic() {
        this.expr = null;
    }

    public boolean isString() {
        return false;
    }

    public boolean isBoxed() {
        return false;
    }

    public ConcolicLong ToLong() {
        throw new UnsupportedOperationException("This method should be overridden by subclasses");
    }

    public String toString() {
        String clsName = getClass() != null ? getClass().getName() : "null";
        synchronized (Z3Helper.getInstance()) {
            return clsName + "(" + concrete_value + "@" + Integer.toHexString(System.identityHashCode(this)) + ", " + this.getExpr() + ")";
        }
    }

    public Expr<?> getExprWithInitInWidth(int bitvecWidth) {
        synchronized (Z3Helper.getInstance()) {
            BitVecExpr myExpr = (BitVecExpr) this.getExprWithInit();
            int myWidth = myExpr.getSortSize();
            if (myWidth > bitvecWidth) {
                myExpr = Z3Helper.mkExtract(bitvecWidth-1, 0, myExpr);
            } else if (myWidth < bitvecWidth) {
                myExpr = Z3Helper.mkSignExt(bitvecWidth - myWidth, myExpr);
            }
            return myExpr;
        }
    }

    public Expr<?> getExprWithInitInWidthUnsigned(int bitvecWidth) {
        synchronized (Z3Helper.getInstance()) {
            BitVecExpr myExpr = (BitVecExpr) this.getExprWithInit();
            int myWidth = myExpr.getSortSize();
            if (myWidth > bitvecWidth) {
                myExpr = Z3Helper.mkExtract(bitvecWidth-1, 0, myExpr);
            } else if (myWidth < bitvecWidth) {
                myExpr = Z3Helper.mkZeroExt(bitvecWidth - myWidth, myExpr);
            }
            return myExpr;
        }
    }


    public Expr<?> matchBitVectorWidthByType(ConcolicValueWrapper<?> other) {
        synchronized (Z3Helper.getInstance()) {
            BitVecExpr myExpr = (BitVecExpr) this.getExprWithInit();
            BitVecExpr expr = (BitVecExpr) other.getExprWithInit();
            int myWidth = myExpr.getSortSize();
            int otherWidth = expr.getSortSize();

            if (myWidth > otherWidth) {
                // extend
                Expr<?> extendedExpr = Z3Helper.mkSignExt(myWidth - otherWidth, expr);
                return extendedExpr;
            } else if (myWidth < otherWidth) {
                // shrink
                Expr<?> extractedExpr =Z3Helper.mkExtract(myWidth - 1, 0, expr);
                return extractedExpr;
            } else {
                return other.getExprWithInit();
            }
        }
    }

    public Expr<?> getAddExpr(ConcolicValueWrapper<?> other) {
        synchronized (Z3Helper.getInstance()) {
            Expr<?> thisExpr = this.getExprWithInit();
            Expr<?> otherExpr = matchBitVectorWidthByType(other);
            Expr<?> resultExpr = Z3Helper.mkBVAdd((BitVecExpr) thisExpr, (BitVecExpr) otherExpr);
            if (Logger.compileLog) {
                Logger.DEBUG("[IADD] this: " + thisExpr + " other: " + otherExpr +
                        " result: " + resultExpr);
            }
            return resultExpr;
        }
    }

    public Expr<?> getAddExprReal(ConcolicValueWrapper<?> other) {
        synchronized (Z3Helper.getInstance()) {
            Expr<?> thisExpr = this.getExprWithInit();
            Expr<?> otherExpr = other.getExprWithInit();
            Expr<?> resultExpr = Z3Helper.mkAdd((RealExpr)thisExpr, (RealExpr)otherExpr);
            if (Logger.compileLog) {
                Logger.DEBUG("[RADD] this: " + thisExpr + " other: " + otherExpr + " result: " + resultExpr);
            }
            return resultExpr;
        }
    }

    public Expr<?> getSubtractExpr(ConcolicValueWrapper<?> other) {
        synchronized (Z3Helper.getInstance()) {
            Expr<?> thisExpr = this.getExprWithInit();
            Expr<?> otherExpr = matchBitVectorWidthByType(other);
            Expr<?> resultExpr = Z3Helper.mkBVSub((BitVecExpr) thisExpr, (BitVecExpr) otherExpr);
            if (Logger.compileLog) {
                Logger.DEBUG("[ISUB] this: " + thisExpr + " other: " + otherExpr +
                        " result: " + resultExpr);
            }
            return resultExpr;
        }
    }

    public Expr<?> getSubtractExprReal(ConcolicValueWrapper<?> other) {
        synchronized (Z3Helper.getInstance()) {
            Expr<?> thisExpr = this.getExprWithInit();
            Expr<?> otherExpr = other.getExprWithInit();
            Expr<?> resultExpr = Z3Helper.mkSub((RealExpr) thisExpr, (RealExpr) otherExpr);
            if (Logger.compileLog) {
                Logger.DEBUG("[RSUB] this: " + thisExpr + " other: " + otherExpr + " result: " + resultExpr);
            }
            return resultExpr;
        }
    }

    public Expr<?> getMultiplyExpr(ConcolicValueWrapper<?> other) {
        synchronized (Z3Helper.getInstance()) {
            Expr<?> thisExpr = this.getExprWithInit();
            Expr<?> otherExpr = matchBitVectorWidthByType(other);
            Expr<?> resultExpr = Z3Helper.mkBVMul((BitVecExpr) thisExpr, (BitVecExpr) otherExpr);
            if (Logger.compileLog) {
                Logger.DEBUG("[IMUL] this: " + thisExpr + " other: " + otherExpr +
                        " result: " + resultExpr);
            }
            return resultExpr;
        }
    }

    public Expr<?> getMultiplyExprReal(ConcolicValueWrapper<?> other) {
        synchronized (Z3Helper.getInstance()) {
            Expr<?> thisExpr = this.getExprWithInit();
            Expr<?> otherExpr = other.getExprWithInit();
            Expr<?> resultExpr = Z3Helper.mkMul((RealExpr) thisExpr, (RealExpr) otherExpr);
            if (Logger.compileLog) {
                Logger.DEBUG("[RMUL] this: " + thisExpr + " other: " + otherExpr + " result: " + resultExpr);
            }
            return resultExpr;
        }
    }

    public Expr<?> getDivideExpr(ConcolicValueWrapper<?> other) {
        synchronized (Z3Helper.getInstance()) {
            Expr<?> thisExpr = this.getExprWithInit();
            Expr<?> otherExpr = matchBitVectorWidthByType(other);
            Expr<?> resultExpr = Z3Helper.mkBVSDiv((BitVecExpr) thisExpr, (BitVecExpr) otherExpr);
            if (Logger.compileLog) {
                Logger.DEBUG("[IDIV] this: " + thisExpr + " other: " + otherExpr +
                        " result: " + resultExpr);
            }
            return resultExpr;
        }
    }

    public Expr<?> getDivideExprReal(ConcolicValueWrapper<?> other) {
        synchronized (Z3Helper.getInstance()) {
            Expr<?> thisExpr = this.getExprWithInit();
            Expr<?> otherExpr = other.getExprWithInit();
            Expr<?> resultExpr = Z3Helper.mkDiv((RealExpr) thisExpr, (RealExpr) otherExpr);
            if (Logger.compileLog) {
                Logger.DEBUG("[RDIV] this: " + thisExpr + " other: " + otherExpr + " result: " + resultExpr);
            }
            return resultExpr;
        }
    }

    public Expr<?> getModuloExpr(ConcolicValueWrapper<?> other) {
        synchronized (Z3Helper.getInstance()) {
            Expr<?> thisExpr = this.getExprWithInit();
            Expr<?> otherExpr = matchBitVectorWidthByType(other);
            Expr<?> resultExpr = Z3Helper.mkBVSRem((BitVecExpr) thisExpr, (BitVecExpr) otherExpr);
            if (Logger.compileLog) {
                Logger.DEBUG("[IREM] this: " + thisExpr + " other: " + otherExpr +
                        " result: " + resultExpr);
            }
            return resultExpr;
        }
    }

    public Expr<?> getModuloExprReal(ConcolicValueWrapper<?> other) {
        synchronized (Z3Helper.getInstance()) {
            Expr<?> thisExpr = this.getExprWithInit();
            Expr<?> otherExpr = other.getExprWithInit();

            // calculate rem. for this and other,
            // rem = this - ((int) (this/other)) * other;
            // Q = (float/double)((int) (this / other))
            // rem = this - Q * other

            // this / other
            Expr<?> divExpr = Z3Helper.mkDiv((RealExpr) thisExpr, (RealExpr) otherExpr);
            // ((int) (this / other))
            Expr<?> divIntExpr = Z3Helper.mkReal2Int((RealExpr)divExpr);
            // ((float/double) ((int) (this / other))) = Q
            Expr<?> divIntRealExpr = Z3Helper.mkInt2Real((IntExpr)divIntExpr);
            // Q * other
            Expr<?> mulExpr = Z3Helper.mkMul((RealExpr) divIntRealExpr, (RealExpr) otherExpr);
            // this - (Q * other)
            Expr<?> resultExpr = Z3Helper.mkSub((RealExpr) thisExpr, (RealExpr) mulExpr);
            if (Logger.compileLog) {
                Logger.DEBUG("[RREM] this: " + thisExpr + " other: " + otherExpr + " result: " + resultExpr);
            }
            return resultExpr;
        }
    }

    public Expr<?> getNegateExpr() {
        synchronized (Z3Helper.getInstance()) {
            Expr<?> thisExpr = this.getExprWithInit();
            Expr<?> resultExpr = Z3Helper.mkBVNeg((BitVecExpr) thisExpr);
            if (Logger.compileLog) {
                Logger.DEBUG("[INEG] this: " + thisExpr + " result: " + resultExpr);
            }
            return resultExpr;
        }
    }

    public Expr<?> getNegateExprReal() {
        synchronized (Z3Helper.getInstance()) {
            Expr<?> thisExpr = this.getExprWithInit();
            Expr<?> resultExpr = Z3Helper.mkUnaryMinus((RealExpr) thisExpr);
            if (Logger.compileLog) {
                Logger.DEBUG("[RNEG] this: " + thisExpr + " result: " + resultExpr);
            }
            return resultExpr;
        }
    }

    public Expr<?> getAndExpr(ConcolicValueWrapper<?> other) {
        synchronized (Z3Helper.getInstance()) {
            Expr<?> thisExpr = this.getExprWithInit();
            Expr<?> otherExpr = matchBitVectorWidthByType(other);
            Expr<?> resultExpr = Z3Helper.mkBVAND((BitVecExpr) thisExpr, (BitVecExpr) otherExpr);
            if (Logger.compileLog) {
                Logger.DEBUG("[IAND] this: " + thisExpr + " other: " + otherExpr +
                        " result: " + resultExpr);
            }
            return resultExpr;
        }
    }

    public Expr<?> getORExpr(ConcolicValueWrapper<?> other) {
        synchronized (Z3Helper.getInstance()) {
            Expr<?> thisExpr = this.getExprWithInit();
            Expr<?> otherExpr = matchBitVectorWidthByType(other);
            Expr<?> resultExpr = Z3Helper.mkBVOR((BitVecExpr) thisExpr, (BitVecExpr) otherExpr);
            if (Logger.compileLog) {
                Logger.DEBUG("[IOR] this: " + thisExpr + " other: " + otherExpr +
                        " result: " + resultExpr);
            }
            return resultExpr;
        }
    }

    public Expr<?> getXORExpr(ConcolicValueWrapper<?> other) {
        synchronized (Z3Helper.getInstance()) {
            Expr<?> thisExpr = this.getExprWithInit();
            Expr<?> otherExpr = matchBitVectorWidthByType(other);
            Expr<?> resultExpr = Z3Helper.mkBVXOR((BitVecExpr) thisExpr, (BitVecExpr) otherExpr);
            if (Logger.compileLog) {
                Logger.DEBUG("[IXOR] this: " + thisExpr + " other: " + otherExpr +
                        " result: " + resultExpr);
            }
            return resultExpr;
        }
    }

    public Expr<?> getShiftLeftExpr(ConcolicValueWrapper<?> other) {
        synchronized (Z3Helper.getInstance()) {
            Expr<?> thisExpr = this.getExprWithInit();
            Expr<?> otherExpr = matchBitVectorWidthByType(other);
            Expr<?> resultExpr = Z3Helper.mkBVSHL((BitVecExpr) thisExpr, (BitVecExpr) otherExpr);
            if (Logger.compileLog) {
                Logger.DEBUG("[ISHL] this: " + thisExpr + " other: " + otherExpr +
                        " result: " + resultExpr);
            }
            return resultExpr;
        }
    }

    public Expr<?> getShiftRightExpr(ConcolicValueWrapper<?> other) {
        synchronized (Z3Helper.getInstance()) {
            Expr<?> thisExpr = this.getExprWithInit();
            Expr<?> otherExpr = matchBitVectorWidthByType(other);
            Expr<?> resultExpr = Z3Helper.mkBVASHR((BitVecExpr) thisExpr, (BitVecExpr) otherExpr);
            if (Logger.compileLog) {
                Logger.DEBUG("[ISHR] this: " + thisExpr + " other: " + otherExpr +
                        " result: " + resultExpr);
            }
            return resultExpr;
        }
    }

    public Expr<?> getShiftRightUnsignedExpr(ConcolicValueWrapper<?> other) {
        synchronized (Z3Helper.getInstance()) {
            Expr<?> thisExpr = this.getExprWithInit();
            Expr<?> otherExpr = matchBitVectorWidthByType(other);
            Expr<?> resultExpr = Z3Helper.mkBVASHR((BitVecExpr) thisExpr, (BitVecExpr) otherExpr);
            if (Logger.compileLog) {
                Logger.DEBUG("[IUSHR] this: " + thisExpr + " other: " + otherExpr +
                        " result: " + resultExpr);
            }
            return resultExpr;
        }
    }

    public ArrayList<ConcolicVariableInfo> getInfoList() {
        return this.infoList;
    }

    public void setInfoList(ArrayList<ConcolicVariableInfo> list) {
        this.infoList = list;
    }

}
