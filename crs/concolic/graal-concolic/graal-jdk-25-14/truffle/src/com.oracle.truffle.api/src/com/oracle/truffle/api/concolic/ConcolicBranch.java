package com.oracle.truffle.api.concolic;

import static com.oracle.truffle.api.concolic.Opcodes.*;

import java.util.*;
import com.microsoft.z3.*;

public class ConcolicBranch {
    private static class LL {
        private ConcolicBranch branch;
        private LL next;
        private LL prev;

        public LL(ConcolicBranch branch) {
            this.branch = branch;
            this.next = null;
            this.prev = null;
        }

        public void remove() {
            if (this.prev != null) {
                this.prev.next = this.next;
            }
            if (this.next != null) {
                this.next.prev = this.prev;
            }
        }
    }
    private static class LLManager {
        LL head;
        LL tail;
        HashMap<String, LinkedList<LL>> hashMap;
        private int singleLLSize = 5;

        public LLManager() {
            this.head = new LL(null);
            this.tail = new LL(null);
            this.head.next = this.tail;
            this.tail.prev = this.head;
            this.hashMap = new HashMap<String, LinkedList<LL>>();
        }

        private String getBranchStr(ConcolicBranch b) {
            return b.getClassName() + "." + b.getMethodName() + ":" + b.getBytecodeOffset();
        }

        public LL add(ConcolicBranch b) {
            LL newLL = new LL(b);
            newLL.next = this.head.next;
            newLL.prev = this.head;
            this.head.next.prev = newLL;
            this.head.next = newLL;

            String branch_str = getBranchStr(b);

            if (!this.hashMap.containsKey(branch_str)) {
                this.hashMap.put(branch_str, new LinkedList<LL>());
            }
            this.hashMap.get(branch_str).add(newLL);

            return newLL;
        }

        public void clear() {
            this.head.next = this.tail;
            this.tail.prev = this.head;
            this.hashMap.clear();
        }

        public void removeTooManyLL(LL ll) {
            String branch_str = getBranchStr(ll.branch);
            if (!this.hashMap.containsKey(branch_str)) {
                return;
            }
            LinkedList<LL> list = this.hashMap.get(branch_str);
            if (list.size() > this.singleLLSize) {
                LL toRemove = list.removeFirst();
                toRemove.remove();
                if (list.size() == 0) {
                    this.hashMap.remove(branch_str);
                }
            }
        }
    }

    private static boolean isLoggingEnabled;
    private String backtrace = "";
    private static boolean isDirty = true;
    private static ArrayList<ConcolicBranch> branchList = new ArrayList<ConcolicBranch>(8192);
    private static LLManager tempBranchList = new LLManager();

    static {
        isLoggingEnabled = false;
    }

    public static void enableLogging() {
        isLoggingEnabled = true;
    }

    public static void disableLogging() {
        isLoggingEnabled = false;
    }

    private static synchronized void buildBranchList() {
        branchList.clear();

        LL current = tempBranchList.head.next;
        while (current != tempBranchList.tail) {
            branchList.add(current.branch);
            current = current.next;
        }
        Collections.reverse(branchList);
    }

    public static synchronized ArrayList<ConcolicBranch> getBranchList() {
        if (isDirty) {
            buildBranchList();
            isDirty = false;
        }
        return branchList;
    }

    public static synchronized void clearBranchList() {
        isDirty = true;
        branchList.clear();
        tempBranchList.clear();
    }

    public static synchronized void addBranch(ConcolicBranch b) {
        if (!isLoggingEnabled) {
            return;
        }

        isDirty = true;
        // if (!branchList.isEmpty()) {
        //     // get parent and add itself as a child
        //     ConcolicBranch lastItem = branchList.get(branchList.size()-1);
        //     lastItem.addChild(b);
        // }
        LL ll = tempBranchList.add(b);
        tempBranchList.removeTooManyLL(ll);
    }

    private boolean _isTaken;
    private ArrayList<BoolExpr> pathConstraintExprs;
    private String branchIdentifier;        // Class.method:bytecodeOffset
    private String className;
    private String methodName;
    private int bytecodeOffset;
    private boolean multiExpr;

    public void setMultiExpr() {
        multiExpr = true;
    }

    public boolean isMultiExpr() {
        return multiExpr;
    }

    public String getClassName() {
        return this.className;
    }
    public String getMethodName() {
        return this.methodName;
    }
    public String getClassAndMethodName() {
        return this.className + "." + this.methodName;
    }
    public int getBytecodeOffset() {
        return this.bytecodeOffset;
    }

    private ConcolicBranch parent;
    private ConcolicBranch takenChild;
    private ConcolicBranch untakenChild;

    public ConcolicBranch() {
        this._isTaken = false;
        this.pathConstraintExprs = null;
        this.branchIdentifier = null;
        this.className = null;
        this.methodName = null;
        this.bytecodeOffset = -1;
        this.parent = null;
        this.takenChild = null;
        this.untakenChild = null;
        this.multiExpr = false;
    }

    public boolean isTaken() {
        return this._isTaken;
    }

    public BoolExpr getExpr() {
        if (this.multiExpr) {
            throw new RuntimeException("[ConcolicBranch] getExpr called for multiExpr branch");
        }
        if (this.pathConstraintExprs == null) {
            return null;
        }
        if (this.pathConstraintExprs.size() == 0) {
            return null;
        } else {
            return this.pathConstraintExprs.get(0);
        }
    }

    public BoolExpr getAllAndExpr() {
        if (this.multiExpr == false) {
            throw new RuntimeException("[ConcolicBranch] getAllAndExpr() called for non-multiExpr branch!");
        }
        BoolExpr combinedExpr = Z3Helper.getInstance().trueExpr;
        for (BoolExpr boolExpr : this.pathConstraintExprs) {
            combinedExpr = Z3Helper.mkAnd(combinedExpr, boolExpr);
        }
        return combinedExpr;
    }

    public BoolExpr getExpr(int index) {
        if (this.multiExpr == false) {
            throw new RuntimeException("[ConcolicBranch] getExpr(index) called for non-multiExpr branch!");
        }
        return this.pathConstraintExprs.get(index);
    }

    public BoolExpr getFlippedExpr() {
        if (this.multiExpr) {
            throw new RuntimeException("[ConcolicBranch] getFlippedExpr called for multiExpr branch");
        }
        return Z3Helper.mkNot(pathConstraintExprs.get(0));
    }

    public BoolExpr getFlippedExpr(int index) {
        if (this.multiExpr == false) {
            throw new RuntimeException("[ConcolicBranch] getFlippedExpr(index) called for non-multi Expr branch");
        }
        return Z3Helper.mkNot(pathConstraintExprs.get(index));
    }

    public int getExprArrayLength() {
        if (this.pathConstraintExprs == null) {
            return 0;
        }
        return this.pathConstraintExprs.size();
    }

    public void setExpr(BoolExpr constraint, boolean is_taken) {
        /*
        Params params = Z3Helper.getContext().mkParams();
        params.add("bv_extract_prop", true);
        params.add("elim_and", true);
        params.add("elim_or", true);
        params.add("elim_ite", true);
        params.add("elim_sign_ext", true);
        params.add("pull_cheap_ite", true);
        params.add("mul_to_power", true);
        BoolExpr simplifiedExpr = (BoolExpr) constraint.simplify(params);
        */
        // Create tactic (simplify):
        /*
        Logger.ALWAYS("Before simplication: " + constraint);
        Context ctx = Z3Helper.getContext();
        Tactic combined = ctx.then(
                ctx.mkTactic("simplify"),
                ctx.mkTactic("propagate-values"),
                ctx.mkTactic("ctx-simplify"),
                ctx.mkTactic("dom-simplify"),
                ctx.mkTactic("propagate-ineqs"),
                ctx.mkTactic("simplify")
                );

        // Set up goal and add expression:
        Goal goal = ctx.mkGoal(true, false, false);
        goal.add(constraint);

        // Apply tactic:
        ApplyResult ar = combined.apply(goal);

        // Get simplified result:
        Goal[] subGoals = ar.getSubgoals();
        Expr<?> simplified = subGoals[0].getFormulas()[0];
        BoolExpr simplifiedExpr = (BoolExpr) simplified;
        this.pathConstraintExpr = simplifiedExpr;
        */
        BoolExpr constraintToAdd = constraint;
        if (is_taken == false) {
            constraintToAdd = Z3Helper.mkNot(constraint);
        }
        this.pathConstraintExprs = new ArrayList<BoolExpr>();
        this.pathConstraintExprs.add(constraintToAdd);
        this._isTaken = is_taken;

        // Update backtrace
        updateBacktrace();
    }

    public String getBacktrace() {
        return this.backtrace;
    }

    public void updateBacktrace() {
        String backtrace = "";
        StackTraceElement[] stackTrace = Thread.currentThread().getStackTrace();
        for (StackTraceElement element : stackTrace) {
            backtrace += "    " + element.toString() + "\n";
        }
        this.backtrace = backtrace;
    }

    public int backtraceHash() {
        return this.backtrace.hashCode();
    }

    public String getIdentifier() {
        return this.branchIdentifier;
    }

    public String getDotIdentifier() {
        return this.branchIdentifier.replace("/", ".");
    }

    public void setIdentifier(String[] ids) {
        this.className = ids[0];
        this.methodName = ids[1];
        this.bytecodeOffset = Integer.valueOf(ids[2]).intValue();
        this.branchIdentifier = className + "." + methodName + ":" + bytecodeOffset;
    }

    // public void addChild(ConcolicBranch b) {
    //     if (this.isTaken()) {
    //         takenChild = b;
    //     } else {
    //         untakenChild = b;
    //     }
    // }

    public void addSwitch(ConcolicInt lookupValue, int compareValue, boolean branchTaken) {
        if (this.pathConstraintExprs == null) {
            this.pathConstraintExprs = new ArrayList<BoolExpr>();
        }
        ConcolicInt concolic_compareValue = new ConcolicInt();
        concolic_compareValue.setValueWithoutConstraints(compareValue);
        BitVecExpr expr1 = (BitVecExpr) lookupValue.getExprWithInitInWidth(32);
        BitVecExpr expr2 = (BitVecExpr) concolic_compareValue.getExprWithInitInWidth(32);
        BoolExpr switchConstraint = Z3Helper.mkEq(expr1, expr2);
        if (branchTaken == false) {
            switchConstraint = Z3Helper.mkNot(switchConstraint);
        }
        this.pathConstraintExprs.add(switchConstraint);
        if (this.multiExpr == false) {
            if (this.pathConstraintExprs.size() > 1) {
                this.setMultiExpr();
            }
        }
    }

    public void addStringSwitch(BoolExpr expr,
                                boolean branchTaken) {
        if (this.pathConstraintExprs == null) {
            this.pathConstraintExprs = new ArrayList<BoolExpr>();
        }
        BoolExpr switchConstraint = expr;
        if (branchTaken == false) {
            switchConstraint = Z3Helper.mkNot(switchConstraint);
        }
        this.pathConstraintExprs.add(switchConstraint);
        if (this.multiExpr == false) {
            if (this.pathConstraintExprs.size() > 1) {
                this.setMultiExpr();
            }
        }
    }

    public boolean setICMP(int opcode, ConcolicInt operand1, ConcolicInt operand2, boolean is_taken) {
        if (Logger.compileLog) {
            Logger.DEBUG("[setICMP] Entering");
        }
        BitVecExpr expr1 = (BitVecExpr) operand1.getExprWithInitInWidth(32);
        BitVecExpr expr2 = (BitVecExpr) operand2.getExprWithInitInWidth(32);
        if (Logger.compileLog) {
            Logger.DEBUG("EXPR1: " + expr1);
            Logger.DEBUG("EXPR2: " + expr2);
        }
        BoolExpr pathConstraint = null;
        if (!ConcolicValueHelper.eitherSymbolic(operand1, operand2)) {
            if (Logger.compileLog) {
                Logger.WARNING("NOT SYMBOLIC");
            }
            return false;
        }

        if (!ConcolicValueHelper.eitherSymbolicExpr(operand1.getExpr(), operand2.getExpr())) {
            if (Logger.compileLog) {
                Logger.WARNING("NOT SYMBOLIC EXPR");
            }
            operand1.setValueWithoutConstraints(operand1.getConcreteValue());
            operand2.setValueWithoutConstraints(operand2.getConcreteValue());
            return false;
        }

        switch (opcode) {
            case IF_ICMPEQ: {
                pathConstraint = Z3Helper.mkEq(expr2, expr1);
                break;
            }
            case IF_ICMPNE: {
                pathConstraint = Z3Helper.mkNot(Z3Helper.mkEq(expr2, expr1));
                break;
            }
            case IF_ICMPLT: {
                pathConstraint = Z3Helper.mkBVSLT(expr2, expr1);
                break;
            }
            case IF_ICMPGE: {
                pathConstraint = Z3Helper.mkBVSGE(expr2, expr1);
                break;
            }
            case IF_ICMPGT: {
                pathConstraint = Z3Helper.mkBVSGT(expr2, expr1);
                break;
            }
            case IF_ICMPLE: {
                pathConstraint = Z3Helper.mkBVSLE(expr2, expr1);
                break;
            }
            default:
                break;
        }
        this.setExpr(pathConstraint, is_taken);
        if (Logger.compileLog) {
            Logger.DEBUG("ICMP constraint: " + pathConstraint);
            Logger.DEBUG("[setICMP] Exiting");
        }
        return true;
    }

    public boolean setIF(int opcode, ConcolicInt condition, boolean is_taken) {
        if (!ConcolicValueHelper.eitherSymbolic(condition)) {
            return false;
        }
        if (!ConcolicValueHelper.eitherSymbolicExpr(condition.getExpr())) {
            condition.setValueWithoutConstraints(condition.getConcreteValue());
            return false;
        }

        BitVecExpr exprCondition = (BitVecExpr) condition.getExprWithInitInWidth(32);
        BoolExpr pathConstraint = null;

        BitVecExpr zeroExpr = Z3Helper.getInstance().zeroExpr;
        switch (opcode) {
            case IFEQ: {
                pathConstraint = Z3Helper.mkEq(exprCondition, zeroExpr);
                break;
            }
            case IFNE: {
                pathConstraint = Z3Helper.mkNot(Z3Helper.mkEq(exprCondition, zeroExpr));
                break;
            }
            case IFLT: {
                pathConstraint = Z3Helper.mkBVSLT(exprCondition, zeroExpr);
                break;
            }
            case IFGE: {
                pathConstraint = Z3Helper.mkBVSGE(exprCondition, zeroExpr);
                break;
            }
            case IFGT: {
                pathConstraint = Z3Helper.mkBVSGT(exprCondition, zeroExpr);
                break;
            }
            case IFLE: {
                pathConstraint = Z3Helper.mkBVSLE(exprCondition, zeroExpr);
                break;
            }
            default:
                break;
        }

        this.setExpr(pathConstraint, is_taken);
        return true;
    }
}
