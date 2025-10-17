package com.oracle.truffle.espresso.concolic.hook;

import com.oracle.truffle.api.concolic.*;
import com.oracle.truffle.espresso.concolic.*;
import com.oracle.truffle.espresso.meta.Meta;
import com.oracle.truffle.espresso.runtime.staticobject.StaticObject;
import com.oracle.truffle.espresso.descriptors.*;
import com.oracle.truffle.espresso.vm.InterpreterToVM;
import com.oracle.truffle.espresso.impl.*;
import com.oracle.truffle.espresso.classfile.descriptors.*;

import com.microsoft.z3.*;

import java.util.HashSet;
import java.util.Arrays;
import java.util.ArrayList;
import sun.misc.Unsafe;
import com.oracle.truffle.espresso.vm.UnsafeAccess;

public class StringMethodHook extends CompleteHook {
    static public HashSet<String> shouldNotTrackExpressions = new HashSet<>();
    static {
        shouldNotTrackExpressions.add("hashCode");
        shouldNotTrackExpressions.add("indexOf");
        shouldNotTrackExpressions.add("lastIndexOf");
    }

    private static final Unsafe UNSAFE = UnsafeAccess.get();
    static boolean host_compact;
    static {
        try {
            host_compact = UNSAFE.getBoolean(
                UNSAFE.staticFieldBase(String.class.getDeclaredField("COMPACT_STRINGS")),
                UNSAFE.staticFieldOffset(String.class.getDeclaredField("COMPACT_STRINGS"))
            );
        } catch (NoSuchFieldException e) {
            throw new RuntimeException("exception while trying to get Buffer.address via reflection:", e);
        }
    }

    public static Boolean isSymbolizedConcolicString(Object obj) {
        if (obj instanceof ConcolicObjectImpl concolicObject) {
            Field valueField = CompleteHook.calculateField(concolicObject, "value", "[B");
            Object accessed_value = CompleteHook.getField(concolicObject, valueField);
            if (accessed_value instanceof ConcolicArrayObject concolicArrayObject) {
                return concolicArrayObject.getExpr() != null || concolicArrayObject.isSymbolic();
            }
        }
        return false;
    }

    public static byte getCoder(ConcolicObjectImpl target_obj) {
        Field coderField = CompleteHook.calculateField(target_obj, "coder", "B");
        byte coder = (byte) ((ConcolicValueWrapper<?>) CompleteHook.getField(target_obj, coderField)).getConcreteValue();
        if (host_compact) {
            return coder;
        }
        return (byte) 1 /* UTF-16 */;
    }

    public static Expr<?> ConvertBoolExprToBitVecExpr(BoolExpr boolExpr) {
        BitVecExpr bvZeroExpr = Z3Helper.getInstance().zeroExpr;
        BitVecExpr bvOneExpr = Z3Helper.getInstance().oneExpr;
        return Z3Helper.mkITE(boolExpr, bvOneExpr, bvZeroExpr);
    }

    public static Object wrapMethod(String className,
                                    String methodName,
                                    Object target_obj,
                                    Object[] args,
                                    String signature,
                                    Object returnedObject) {
        if (!className.equals("java/lang/String")) {
            throw new RuntimeException("[StringMethodHook] bad className: " + className);
        }

        switch (methodName) {
            case "<init>": {
                return wrapInit(target_obj, args, signature, returnedObject);
            }
            case "charAt": {
                return wrapCharAt(target_obj, args, signature, returnedObject);
            }
            case "chars": {
                return wrapChars(target_obj, args, signature, returnedObject);
            }
            case "codePointAt": {
                return wrapCodePointAt(target_obj, args, signature, returnedObject);
            }
            case "codePointBefore": {
                return wrapCodePointBefore(target_obj, args, signature, returnedObject);
            }
            case "codePointCount": {
                return wrapCodePointCount(target_obj, args, signature, returnedObject);
            }
            case "codePoints": {
                return wrapCodePoints(target_obj, args, signature, returnedObject);
            }
            case "compareTo": {
                return wrapCompareTo(target_obj, args, signature, returnedObject);
            }
            case "compareToIgnoreCase": {
                return wrapCompareToIgnoreCase(target_obj, args, signature, returnedObject);
            }
            case "concat": {
                return wrapConcat(target_obj, args, signature, returnedObject);
            }
            case "contains": {
                return wrapContains((ConcolicObjectImpl) target_obj, args, signature, returnedObject);
            }
            case "contentEquals": {
                return wrapContentEquals(target_obj, args, signature, returnedObject);
            }
            case "describeConstable": {
                return wrapDescribeConstable(target_obj, args, signature, returnedObject);
            }
            case "endsWith": {
                return wrapEndsWith(target_obj, args, signature, returnedObject);
            }
            case "equals": {
                return wrapEquals(target_obj, args, signature, returnedObject);
            }
            case "equalsIgnoreCase": {
                return wrapEqualsIgnoreCase(target_obj, args, signature, returnedObject);
            }
            case "formatted": {
                return wrapFormatted(target_obj, args, signature, returnedObject);
            }
            case "getBytes": {
                return wrapGetBytes(target_obj, args, signature, returnedObject);
            }
            case "getChars": {
                return wrapGetChars(target_obj, args, signature, returnedObject);
            }
            case "hashCode": {
                return wrapHashCode(target_obj, args, signature, returnedObject);
            }
            case "indent": {
                return wrapIndent(target_obj, args, signature, returnedObject);
            }
            case "indexOf": {
                return wrapIndexOf(target_obj, args, signature, returnedObject);
            }
            case "intern": {
                return wrapIntern(target_obj, args, signature, returnedObject);
            }
            case "isBlank": {
                return wrapIsBlank(target_obj, args, signature, returnedObject);
            }
            case "isEmpty": {
                return wrapIsEmpty(target_obj, args, signature, returnedObject);
            }
            case "lastIndexOf": {
                return wrapLastIndexOf(target_obj, args, signature, returnedObject);
            }
            case "length": {
                return wrapLength(target_obj, args, signature, returnedObject);
            }
            case "lines": {
                return wrapLines(target_obj, args, signature, returnedObject);
            }
            case "matches": {
                return wrapMatches(target_obj, args, signature, returnedObject);
            }
            case "offsetByCodePoints": {
                return wrapOffsetByCodePoints(target_obj, args, signature, returnedObject);
            }
            case "regionMatches": {
                return wrapRegionMatches(target_obj, args, signature, returnedObject);
            }
            case "repeat": {
                return wrapRepeat(target_obj, args, signature, returnedObject);
            }
            case "replace": {
                return wrapReplace(target_obj, args, signature, returnedObject);
            }
            case "replaceAll": {
                return wrapReplaceAll(target_obj, args, signature, returnedObject);
            }
            case "replaceFirst": {
                return wrapReplaceFirst(target_obj, args, signature, returnedObject);
            }
            case "resolveConstantDesc": {
                return wrapResolveConstantDesc(target_obj, args, signature, returnedObject);
            }
            case "split": {
                return wrapSplit((ConcolicObjectImpl) target_obj, args, signature, returnedObject);
            }
            case "startsWith": {
                return wrapStartsWith(target_obj, args, signature, returnedObject);
            }
            case "strip": {
                return wrapStrip(target_obj, args, signature, returnedObject);
            }
            case "stripIndent": {
                return wrapStripIndent(target_obj, args, signature, returnedObject);
            }
            case "stripLeading": {
                return wrapStripLeading(target_obj, args, signature, returnedObject);
            }
            case "stripTrailing": {
                return wrapStripTrailing(target_obj, args, signature, returnedObject);
            }
            case "subSequence": {
                return wrapSubSequence(target_obj, args, signature, returnedObject);
            }
            case "substring": {
                return wrapSubstring(target_obj, args, signature, returnedObject);
            }
            case "toCharArray": {
                return wrapToCharArray(target_obj, args, signature, returnedObject);
            }
            case "toLowerCase": {
                return wrapToLowerCase(target_obj, args, signature, returnedObject);
            }
            case "toString": {
                return wrapToString(target_obj, args, signature, returnedObject);
            }
            case "toUpperCase": {
                return wrapToUpperCase(target_obj, args, signature, returnedObject);
            }
            case "transform": {
                return wrapTransform(target_obj, args, signature, returnedObject);
            }
            case "translateEscapes": {
                return wrapTranslateEscapes(target_obj, args, signature, returnedObject);
            }
            case "trim": {
                return wrapTrim(target_obj, args, signature, returnedObject);
            }
            default:
                break;
        }

        return returnedObject;
    }

    public static void prepareExprs(ConcolicObjectImpl targetObject) {
        if (targetObject.getExpr() != null) {
            return;
        }

        StaticObject staticObject = (StaticObject) targetObject.getConcreteValue();
        String concreteString = targetObject.getConcreteStringValue();
        targetObject.setValueWithConstraints(staticObject, Z3Helper.mkString(concreteString));
        ConcolicInt length = new ConcolicInt();
        int concreteLength = concreteString.length();
        BitVecExpr lengthExpr = Z3Helper.mkBV(concreteLength, 32);
        length.setValueWithConstraints(concreteLength, lengthExpr);
        targetObject.putExtraData("length", length);
        if (Logger.compileLog) {
            synchronized (Z3Helper.getInstance()) {
                Logger.DEBUG("[prepareExprs targetObject] " + targetObject.toString());
                Logger.DEBUG("[prepareExprs targetObjectClassName] " + targetObject.getTargetClassName());
                Logger.DEBUG("[prepareExprs concreteString] " + concreteString);
                Logger.DEBUG("[prepareExprs length] " + length.toString());
            }
        }
    }

    public static Object wrapInit(Object target_obj,
                                      Object[] args,
                                      String signature,
                                      Object returnedObject) {
        // DONE: we don't have to do anything for <init>
        // exprs will be lazily set in prepareExprs()
        if (returnedObject instanceof ConcolicValueWrapper<?> concolicObject) {
            // concolicObject.setExpr(null);
            return returnedObject;
        }
        return returnedObject;
    }

    public static Object wrapCharAt(Object target_obj,
                                     Object[] args,
                                     String signature,
                                     Object returnedObject) {
        // DONE: we don't have to do anything this method
        // it internally access .value field of String class so being tracked
        return returnedObject;
    }

    public static Object wrapChars(Object target_obj,
                                    Object[] args,
                                    String signature,
                                    Object returnedObject) {
        // IGNORE: Do not implement this method: 1) Hard to implement 2) Rarely used
        if (Logger.compileLog) {
            Logger.DEBUG("[StringMethodHook.chars]: Not implemented " + signature);
        }
        return returnedObject;
    }

    public static Object wrapCodePointAt(Object target_obj,
                                          Object[] args,
                                          String signature,
                                          Object returnedObject) {
        // DONE: we don't have to do anything this method
        // it internally access .value field of String class so being tracked
        return returnedObject;
    }

    public static Object wrapCodePointBefore(Object target_obj,
                                              Object[] args,
                                              String signature,
                                              Object returnedObject) {
        // DONE: we don't have to do anything this method
        // it internally access .value field of String class so being tracked
        return returnedObject;
    }

    public static Object wrapCodePointCount(Object target_obj,
                                             Object[] args,
                                             String signature,
                                             Object returnedObject) {
        // IGNORE: Do not implement this method: 1) Hard to implement 2) Rarely used
        // It internally access length field
        if (Logger.compileLog) {
            Logger.DEBUG("[StringMethodHook.codePointCount]: Not implemented " + signature);
        }
        return returnedObject;
    }

    public static Object wrapCodePoints(Object target_obj,
                                         Object[] args,
                                         String signature,
                                         Object returnedObject) {
        // IGNORE: Do not implement this method: 1) Hard to implement 2) Rarely used
        if (Logger.compileLog) {
            Logger.DEBUG("[StringMethodHook.codePoints]: Not implemented " + signature);
        }
        return returnedObject;
    }

    public static Object wrapCompareTo(Object target_obj,
                                        Object[] args,
                                        String signature,
                                        Object returnedObject) {
        // TODO: Implement this method
        if (Logger.compileLog) {
            Logger.DEBUG("[StringMethodHook.compareTo]: Not implemented " + signature);
        }
        return returnedObject;
    }

    public static Object wrapCompareToIgnoreCase(Object target_obj,
                                                  Object[] args,
                                                  String signature,
                                                  Object returnedObject) {
        // TODO: Implement this method
        if (Logger.compileLog) {
            Logger.DEBUG("[StringMethodHook.compareToIgnoreCase]: Not implemented " + signature);
        }
        return returnedObject;
    }

    public static Object wrapConcat(Object target_obj,
                                     Object[] args,
                                     String signature,
                                     Object returnedObject) {
        // DONE: we don't have to do anything this method
        // it internally access .value field of String class so being tracked
        return returnedObject;
    }

    public static Object wrapContains(ConcolicObjectImpl str,
                                       Object[] args,
                                       String signature,
                                       Object returnedObject) {
        if (Logger.compileLog) {
            Logger.DEBUG("[StringMethodHook.wrapContains] " + signature);
        }
        ConcolicObjectImpl arg1 = (ConcolicObjectImpl) args[1];
        if (!str.isString() || !arg1.isString()) return returnedObject;
        if (!ConcolicValueHelper.eitherSymbolic(str, arg1)) return returnedObject;

        byte this_coder = getCoder(str);
        byte other_coder = getCoder(arg1);
        if (this_coder != other_coder) {
            if (Logger.compileLog) {
                Logger.DEBUG("[String.wrapContains] Coder mismatch");
            }
            return returnedObject;
        }
        int strSize = ((ConcolicArrayObject) str.getOrCreateField(0)).getConcreteSize();
        int arg1Size = ((ConcolicArrayObject) arg1.getOrCreateField(0)).getConcreteSize();
        if (strSize <= 64 && arg1Size <= 64) {
            SeqExpr<BitVecSort> expr1 = (SeqExpr<BitVecSort>) str.getSeqExprWithInit();
            SeqExpr<BitVecSort> expr2 = (SeqExpr<BitVecSort>) arg1.getSeqExprWithInit();
            ConcolicBoolean ret = (ConcolicBoolean) ConcolicHelper.toConcolic(returnedObject);
            ret.setExpr(Z3Helper.mkContains(expr1, expr2));
            return ret;
        }
        return returnedObject;
    }

    public static Object wrapContentEquals(Object target_obj,
                                            Object[] args,
                                            String signature,
                                            Object returnedObject) {
        // DONE: Internally uses equals() when String is given
        return wrapEquals(target_obj, args, signature, returnedObject);
    }

    public static Object wrapDescribeConstable(Object target_obj,
                                                Object[] args,
                                                String signature,
                                                Object returnedObject) {
        // IGNORE: Do not implement this method: 1) Hard to implement 2) Rarely used
        if (Logger.compileLog) {
            Logger.DEBUG("[StringMethodHook.describeConstable]: Not implemented " + signature);
        }
        return returnedObject;
    }

    public static Object wrapEndsWith(Object target_obj,
                                       Object[] args,
                                       String signature,
                                       Object returnedObject) {
        // DONE: Internally uses startsWith()
        return returnedObject;
    }


    public static Object wrapEquals(Object target_obj,
                                      Object[] args,
                                      String signature,
                                      Object returnedObject) {
        boolean is_symbolic = false;
        if (!(target_obj instanceof ConcolicObjectImpl) || !(args[1] instanceof ConcolicObjectImpl)) {
            if (Logger.compileLog) {
                Logger.DEBUG("[wrapEquals] not ConcolicObjectImpl");
            }
            return returnedObject;
        }
        ConcolicObjectImpl targetObject = (ConcolicObjectImpl) target_obj;
        ConcolicObjectImpl otherObject = (ConcolicObjectImpl) args[1];

        // Check if the coders are the same
        try {
            byte this_coder = getCoder(targetObject);
            byte other_coder = getCoder(otherObject);
            if (this_coder != other_coder) {
                // don't have to do anything for different coders
                if (Logger.compileLog) {
                    Logger.DEBUG("[wrapEquals] Coder mismatch");
                }
                return returnedObject;
            }
        } catch (Exception e) {
            if (Logger.compileLog) {
                Logger.DEBUG("[wrapEquals] Coder exception");
                Logger.DEBUG(e.getMessage());
            }
            return returnedObject;
        }


        // Get the value field of the targetObject and otherObject
        Field valueField = CompleteHook.calculateField(targetObject, "value", "[B");
        ConcolicArrayObject this_concolicvalue = (ConcolicArrayObject) CompleteHook.getField(targetObject, valueField);
        ConcolicArrayObject other_concolicvalue = (ConcolicArrayObject) CompleteHook.getField(otherObject, valueField);
        if (this_concolicvalue == null || other_concolicvalue == null) {
            if (Logger.compileLog) {
                Logger.DEBUG("[wrapEquals] null concolicvalue");
            }
            return returnedObject;
        }
        BoolExpr ret_expr = Z3Helper.mkTrue();

        // Check if the size of the string is equal
        int this_value_size = this_concolicvalue.getSize().getConcreteValue();
        int other_value_size = other_concolicvalue.getSize().getConcreteValue();
        boolean is_size_equal = this_value_size == other_value_size;

        if (ConcolicValueHelper.eitherSymbolic(this_concolicvalue.getSize(), other_concolicvalue.getSize())) {
            is_symbolic = true;
            BoolExpr size_expr = Z3Helper.mkEq(
                this_concolicvalue.getSize().getExprWithInit(),
                other_concolicvalue.getSize().getExprWithInit()
            );
            ret_expr = Z3Helper.mkAnd(
                ret_expr,
                size_expr
            );
        }
        if (!is_size_equal) {
            returnedObject = new ConcolicBoolean();
            ((ConcolicBoolean) returnedObject).setValueWithConstraints(
                false,
                ConvertBoolExprToBitVecExpr(ret_expr)
            );
            if (Logger.compileLog) {
                Logger.DEBUG("[wrapEquals] size unequal");
            }
            return returnedObject;
        }

        // Check if the bytes are the same
        for (int i = 0; i < this_value_size; i++) {
            ConcolicByte this_byte = (ConcolicByte) this_concolicvalue.getElement(i);
            ConcolicByte other_byte = (ConcolicByte) other_concolicvalue.getElement(i);
            if (this_byte == null || other_byte == null) continue;
            if (ConcolicValueHelper.eitherSymbolic(this_byte, other_byte)) {
                ret_expr = Z3Helper.mkAnd(
                    ret_expr,
                    Z3Helper.mkEq(
                        this_byte.ToLong().getExprWithInitInWidth(32),
                        other_byte.ToLong().getExprWithInitInWidth(32)
                    )
                );
                is_symbolic = true;
            }
        }
        if (is_symbolic) {
            boolean concreteValue = (Boolean) ConcolicHelper.toConcrete(returnedObject);
            returnedObject = new ConcolicBoolean();
            ((ConcolicBoolean) returnedObject).setValueWithConstraints(concreteValue, ConvertBoolExprToBitVecExpr(ret_expr));
        } else {
            if (Logger.compileLog) {
                Logger.DEBUG("[wrapEquals] not symbolic");
            }
        }
        return returnedObject;
    }

    public static Object wrapEqualsIgnoreCase(Object target_obj,
                                                Object[] args,
                                                String signature,
                                                Object returnedObject) {
        // TODO: Implement this method
        if (Logger.compileLog) {
            Logger.DEBUG("[StringMethodHook.equalsIgnoreCase]: Not implemented " + signature);
        }
        return returnedObject;
    }

    public static Object wrapFormatted(Object target_obj,
                                        Object[] args,
                                        String signature,
                                        Object returnedObject) {
        // IGNORE: Do not implement this method: 1) Hard to implement
        if (Logger.compileLog) {
            Logger.DEBUG("[StringMethodHook.formatted]: Not implemented " + signature);
        }
        return returnedObject;
    }

    public static Object wrapGetBytes(Object target_obj,
                                       Object[] args,
                                       String signature,
                                       Object returnedObject) {
        // DONE: we don't have to do anything this method
        // it internally access .value field of String class so being tracked
        return returnedObject;
    }

    public static Object wrapGetChars(Object target_obj,
                                       Object[] args,
                                       String signature,
                                       Object returnedObject) {
        // DONE: we don't have to do anything this method
        // it internally access .value field of String class so being tracked
        return returnedObject;
    }

    public static Object wrapHashCode(Object target_obj,
                                       Object[] args,
                                       String signature,
                                       Object returnedObject) {
        // IGNORE: Do not implement this method: 1) Solving speed issue
        if (returnedObject instanceof ConcolicValueWrapper<?> concolicObject) {
            concolicObject.setNonSymbolic();
        }

        // XXX: YJ:
        // set to mark hashcode for string switch/case
        // the above is unused but we don't want to remove until
        // this will be finalized.
        if (returnedObject instanceof ConcolicInt concolicInt) {
            boolean is_symbolic = false;
            ConcolicObjectImpl targetObject = (ConcolicObjectImpl) target_obj;
            Field valueField = CompleteHook.calculateField(targetObject, "value", "[B");
            ConcolicArrayObject this_concolicvalue = (ConcolicArrayObject) CompleteHook.getField(targetObject, valueField);
            if (ConcolicValueHelper.eitherSymbolic(this_concolicvalue.getSize())) {
                is_symbolic = true;
            } else {
                int this_value_size = this_concolicvalue.getSize().getConcreteValue();
                for (int i = 0; i < this_value_size; i++) {
                    ConcolicByte this_byte = (ConcolicByte) this_concolicvalue.getElement(i);
                    if (this_byte == null) {
                        continue;
                    }
                    if (ConcolicValueHelper.eitherSymbolic(this_byte)) {
                        is_symbolic = true;
                        break;
                    }
                }
            }

            if (is_symbolic) {
                concolicInt.setPassedHashCode(true);
            }
        }

        return returnedObject;
    }

    public static Object wrapIndent(Object target_obj,
                                     Object[] args,
                                     String signature,
                                     Object returnedObject) {
        // IGNORE: Do not implement this method: 1) Hard to implement 2) Rarely used
        if (Logger.compileLog) {
            Logger.DEBUG("[StringMethodHook.indent]: Not implemented " + signature);
        }
        return returnedObject;
    }

    public static Object wrapIndexOf(Object target_obj,
                                      Object[] args,
                                      String signature,
                                      Object returnedObject) {
        // IGNORE: Do not implement this method: 1) Hard to implement
        if (Logger.compileLog) {
            Logger.DEBUG("[StringMethodHook.indexOf]: Not implemented " + signature);
        }
        return returnedObject;
    }

    public static Object wrapIntern(Object target_obj,
                                     Object[] args,
                                     String signature,
                                     Object returnedObject) {
        // IGNORE: Do not implement this method: 1) Hard to implement
        if (Logger.compileLog) {
            Logger.DEBUG("[StringMethodHook.intern]: Not implemented " + signature);
        }
        return returnedObject;
    }

    public static Object wrapIsBlank(Object target_obj,
                                      Object[] args,
                                      String signature,
                                      Object returnedObject) {
        // IGNORE: Do not implement this method: 1) Hard to implement
        if (Logger.compileLog) {
            Logger.DEBUG("[StringMethodHook.isBlank]: Not implemented " + signature);
        }
        return returnedObject;
    }

    public static Object wrapIsEmpty(Object target_obj,
                                      Object[] args,
                                      String signature,
                                      Object returnedObject) {
        // IGNORE: Do not implement this method: 1) Hard to implement
        if (Logger.compileLog) {
            Logger.DEBUG("[StringMethodHook.isEmpty]: Not implemented " + signature);
        }
        return returnedObject;
    }

    public static Object wrapLastIndexOf(Object target_obj,
                                          Object[] args,
                                          String signature,
                                          Object returnedObject) {
        // IGNORE: Do not implement this method: 1) Hard to implement
        if (Logger.compileLog) {
            Logger.DEBUG("[StringMethodHook.lastIndexOf]: Not implemented " + signature);
        }
        return returnedObject;
    }

    public static Object wrapLength(Object target_obj,
                                     Object[] args,
                                     String signature,
                                     Object returnedObject) {
        // IGNORE: Do not implement this method: 1) It doesn't track length right now
        if (Logger.compileLog) {
            Logger.DEBUG("[StringMethodHook.length]: Not implemented " + signature);
        }
        return returnedObject;
    }

    public static Object wrapLines(Object target_obj,
                                    Object[] args,
                                    String signature,
                                    Object returnedObject) {
        // IGNORE: Do not implement this method: 1) Hard to implement 2) Rarely used
        if (Logger.compileLog) {
            Logger.DEBUG("[StringMethodHook.lines]: Not implemented " + signature);
        }
        return returnedObject;
    }

    public static Object wrapMatches(Object target_obj,
                                      Object[] args,
                                      String signature,
                                      Object returnedObject) {
        // IGNORE: Do not implement this method: 1) Hard to implement 2) Rarely used
        if (Logger.compileLog) {
            Logger.DEBUG("[StringMethodHook.matches]: Not implemented " + signature);
        }
        return returnedObject;
    }

    public static Object wrapOffsetByCodePoints(Object target_obj,
                                                 Object[] args,
                                                 String signature,
                                                 Object returnedObject) {
        // IGNORE: Do not implement this method: 1) Hard to implement 2) Rarely used
        if (Logger.compileLog) {
            Logger.DEBUG("[StringMethodHook.offsetByCodePoints]: Not implemented " + signature);
        }
        return returnedObject;
    }

    public static Object wrapRegionMatches(Object target_obj,
                                            Object[] args,
                                            String signature,
                                            Object returnedObject) {
        // IGNORE: Do not implement this method: 1) Hard to implement 2) Rarely used
        if (Logger.compileLog) {
            Logger.DEBUG("[StringMethodHook.regionMatches]: Not implemented " + signature);
        }
        return returnedObject;
    }

    public static Object wrapRepeat(Object target_obj,
                                     Object[] args,
                                     String signature,
                                     Object returnedObject) {
        // DONE: we don't have to do anything this method
        // it internally access .value field of String class so being tracked
        return returnedObject;
    }

    public static Object wrapReplace(Object target_obj,
                                      Object[] args,
                                      String signature,
                                      Object returnedObject) {
        // IGNORE: Do not implement this method: 1) Hard to implement
        if (Logger.compileLog) {
            Logger.DEBUG("[StringMethodHook.replace]: Not implemented " + signature);
        }
        return returnedObject;
    }

    public static Object wrapReplaceAll(Object target_obj,
                                         Object[] args,
                                         String signature,
                                         Object returnedObject) {
        // IGNORE: Do not implement this method: 1) Hard to implement
        if (Logger.compileLog) {
            Logger.DEBUG("[StringMethodHook.replaceAll]: Not implemented " + signature);
        }
        return returnedObject;
    }

    public static Object wrapReplaceFirst(Object target_obj,
                                           Object[] args,
                                           String signature,
                                           Object returnedObject) {
        // IGNORE: Do not implement this method: 1) Hard to implement
        if (Logger.compileLog) {
            Logger.DEBUG("[StringMethodHook.replaceFirst]: Not implemented " + signature);
        }
        return returnedObject;
    }

    public static Object wrapResolveConstantDesc(Object target_obj,
                                                  Object[] args,
                                                  String signature,
                                                  Object returnedObject) {
        // DONE: It just returns 'this'
        return returnedObject;
    }

    public static Object wrapSplit(ConcolicObjectImpl str,
                                    Object[] args,
                                    String signature,
                                    Object returnedObject) {
        // DONE: we don't have to do anything this method
        // it internally access .value field of String class so being tracked
        return returnedObject;
    }

    public static Object wrapStartsWith(Object target_obj,
                                         Object[] args,
                                         String signature,
                                         Object returnedObject) {
        switch (signature) {
            case "(Ljava/lang/String;I)Z":
                if (!(target_obj instanceof ConcolicObjectImpl) || !(args[1] instanceof ConcolicObjectImpl)) {
                    return returnedObject;
                }
                ConcolicObjectImpl targetObject = (ConcolicObjectImpl) target_obj;
                ConcolicObjectImpl otherObject = (ConcolicObjectImpl) args[1];

                Field valueField = CompleteHook.calculateField(targetObject, "value", "[B");
                ConcolicArrayObject this_concolicvalue = (ConcolicArrayObject) CompleteHook.getField(targetObject, valueField);
                ConcolicArrayObject other_concolicvalue = (ConcolicArrayObject) CompleteHook.getField(otherObject, valueField);
                if (this_concolicvalue == null || other_concolicvalue == null) {
                    return returnedObject;
                }

                ConcolicInt start_offset = (ConcolicInt) args[2];

                int this_value_size = this_concolicvalue.getSize().getConcreteValue();
                int other_value_size = other_concolicvalue.getSize().getConcreteValue();
                byte this_coder = getCoder(targetObject);
                byte other_coder = getCoder(otherObject);
                int this_string_len = this_value_size >>> this_coder;
                int other_string_len = other_value_size >>> other_coder;

                int toffset = start_offset.getConcreteValue();
                if (toffset < 0 || toffset + other_string_len > this_string_len) {
                    // false. return immediately
                    // NOTE: Should we inject constraints here?
                    return returnedObject;
                }

                if (this_coder == other_coder) {
                    // Same coder
                    if (this_coder == 1 /* UTF-16 */) {
                        toffset = toffset << 1;
                    }
                    BitVecExpr bvZeroExpr = Z3Helper.getInstance().zeroExpr;
                    BitVecExpr bvOneExpr = Z3Helper.getInstance().oneExpr;
                    BoolExpr eqs = Z3Helper.mkTrue();
                    boolean is_symbolic = false;
                    for (int i = 0; i < other_value_size; i++) {
                        ConcolicByte this_byte = (ConcolicByte) this_concolicvalue.getElement(toffset + i);
                        ConcolicByte other_byte = (ConcolicByte) other_concolicvalue.getElement(i);
                        if (this_byte == null || other_byte == null) continue;
                        if (ConcolicValueHelper.eitherSymbolic(this_byte, other_byte)) {
                            eqs = Z3Helper.mkAnd(
                                eqs,
                                Z3Helper.mkEq(
                                    this_byte.ToLong().getExprWithInitInWidth(32),
                                    other_byte.ToLong().getExprWithInitInWidth(32)
                                )
                            );
                            is_symbolic = true;
                        }
                    }
                    if (is_symbolic) {
                        boolean concreteValue = (Boolean) ConcolicHelper.toConcrete(returnedObject);
                        returnedObject = new ConcolicBoolean();
                        ((ConcolicBoolean) returnedObject).setValueWithConstraints(concreteValue, Z3Helper.mkITE(eqs, bvOneExpr, bvZeroExpr));
                    }
                    return returnedObject;
                }
                else {
                    // Different coders
                    if (this_coder == 0 /* LATIN1 */) {
                        // this_coder == LATIN1 and other_coder == UTF-16
                        // false. return immediately
                        // NOTE: Should we inject constraints here?
                        return returnedObject;
                    }
                    // this_coder == UTF-16 and other_coder == LATIN1
                    BitVecExpr bvZeroExpr = Z3Helper.getInstance().zeroExpr;
                    BitVecExpr bvOneExpr = Z3Helper.getInstance().oneExpr;
                    BoolExpr eqs = Z3Helper.mkTrue();
                    boolean is_symbolic = false;
                    ConcolicChar this_char = null;
                    for (int i = 0; i < other_value_size; i++) {
                        // Must have to type conversion
                        ConcolicByte b0 = (ConcolicByte) this_concolicvalue.getElement(toffset + i * 2 + 0);
                        ConcolicByte b1 = (ConcolicByte) this_concolicvalue.getElement(toffset + i * 2 + 1);

                        // Merge two bytes into one char
                        if (ConcolicValueHelper.eitherSymbolic(b0, b1)) {
                            ConcolicLong new_b_long = new ConcolicLong();
                            new_b_long.setValueWithConstraints((long)(b0.getConcreteValue()), b0.getExpr());
                            new_b_long.ShiftLeft(ConcolicLong.createWithoutConstraints(8));
                            new_b_long.BitwiseOr(b1.ToLong());
                            this_char = new_b_long.ToChar();
                        }
                        else {
                            this_char = new ConcolicChar();
                            this_char.setValueWithConstraints((char)(((long)(b0.getConcreteValue()) << 8) | (long)(b1.getConcreteValue())), null);
                        }
                        ConcolicByte other_byte = (ConcolicByte) other_concolicvalue.getElement(i);
                        if (b0 == null || b1 == null || other_byte == null) continue;
                        // ConcolicChar other_char = new ConcolicChar();
                        // other_char.setValueWithConstraints((char)(other_byte.getConcreteValue() & 0xFF), other_byte.getExpr());
                        ConcolicChar other_char = other_byte.ToLong().ToChar();
                        if (ConcolicValueHelper.eitherSymbolic(this_char, other_char)) {
                            eqs = Z3Helper.mkAnd(
                                eqs,
                                Z3Helper.mkEq(
                                    this_char.ToLong().getExprWithInitInWidth(32),
                                    other_char.ToLong().getExprWithInitInWidth(32)
                                )
                            );
                            is_symbolic = true;
                        }
                    }
                    if (is_symbolic) {
                        boolean concreteValue = (Boolean) ConcolicHelper.toConcrete(returnedObject);
                        returnedObject = new ConcolicBoolean();
                        ((ConcolicBoolean) returnedObject).setValueWithConstraints(concreteValue, Z3Helper.mkITE(eqs, bvOneExpr, bvZeroExpr));
                    }
                }
                break;
            default:
                return returnedObject;
        }
        return returnedObject;
    }

    public static Object wrapStrip(Object target_obj,
                                    Object[] args,
                                    String signature,
                                    Object returnedObject) {
        // DONE: we don't have to do anything this method
        // it internally access .value field of String class so being tracked
        return returnedObject;
    }

    public static Object wrapStripIndent(Object target_obj,
                                          Object[] args,
                                          String signature,
                                          Object returnedObject) {
        // IGNORE: Do not implement this method: 1) Hard to implement
        if (Logger.compileLog) {
            Logger.DEBUG("[StringMethodHook.stripIndent]: Not implemented " + signature);
        }
        return returnedObject;
    }

    public static Object wrapStripLeading(Object target_obj,
                                           Object[] args,
                                           String signature,
                                           Object returnedObject) {
        // IGNORE: Do not implement this method: 1) Hard to implement
        if (Logger.compileLog) {
            Logger.DEBUG("[StringMethodHook.stripLeading]: Not implemented " + signature);
        }
        return returnedObject;
    }

    public static Object wrapStripTrailing(Object target_obj,
                                            Object[] args,
                                            String signature,
                                            Object returnedObject) {
        // IGNORE: Do not implement this method: 1) Hard to implement
        if (Logger.compileLog) {
            Logger.DEBUG("[StringMethodHook.stripTrailing]: Not implemented " + signature);
        }
        return returnedObject;
    }

    public static Object wrapSubSequence(Object target_obj,
                                          Object[] args,
                                          String signature,
                                          Object returnedObject) {
        // IGNORE: It internally call .substring()
        if (Logger.compileLog) {
            Logger.DEBUG("[StringMethodHook.subSequence]: Not implemented " + signature);
        }
        return returnedObject;
    }

    public static Object wrapSubstring(Object target_obj,
                                        Object[] args,
                                        String signature,
                                        Object returnedObject) {
        // DONE: we don't have to do anything this method
        // it internally access .value field of String class so being tracked
        return returnedObject;
    }

    public static Object wrapToCharArray(Object target_obj,
                                          Object[] args,
                                          String signature,
                                          Object returnedObject) {
        // DONE: It's wrapper of toChars()
        return returnedObject;
    }

    public static Object wrapToLowerCase(Object target_obj,
                                          Object[] args,
                                          String signature,
                                          Object returnedObject) {
        // IGNORE: Do not implement this method: 1) Hard to implement
        if (Logger.compileLog) {
            Logger.DEBUG("[StringMethodHook.toLowerCase]: Not implemented " + signature);
        }
        return returnedObject;
    }

    public static Object wrapToString(Object target_obj,
                                       Object[] args,
                                       String signature,
                                       Object returnedObject) {
        // DONE: It just returns 'this'
        return returnedObject;
    }

    public static Object wrapToUpperCase(Object target_obj,
                                          Object[] args,
                                          String signature,
                                          Object returnedObject) {
        // IGNORE: Do not implement this method: 1) Hard to implement
        if (Logger.compileLog) {
            Logger.DEBUG("[StringMethodHook.toUpperCase]: Not implemented " + signature);
        }
        return returnedObject;
    }

    public static Object wrapTransform(Object target_obj,
                                        Object[] args,
                                        String signature,
                                        Object returnedObject) {
        // IGNORE: Do not implement this method: 1) Hard to implement 2) Rarely used
        if (Logger.compileLog) {
            Logger.DEBUG("[StringMethodHook.transform]: Not implemented " + signature);
        }
        return returnedObject;
    }

    public static Object wrapTranslateEscapes(Object target_obj,
                                               Object[] args,
                                               String signature,
                                               Object returnedObject) {
        // IGNORE: Do not implement this method: 1) Hard to implement 2) Rarely used
        if (Logger.compileLog) {
            Logger.DEBUG("[StringMethodHook.translateEscapes]: Not implemented " + signature);
        }
        return returnedObject;
    }

    public static Object wrapTrim(Object target_obj,
                                   Object[] args,
                                   String signature,
                                   Object returnedObject) {
        // DONE: we don't have to do anything this method
        // it internally access .value field of String class so being tracked
        return returnedObject;
    }
}
