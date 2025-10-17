package com.oracle.truffle.espresso.concolic.hook;

import com.oracle.truffle.api.concolic.*;
import com.oracle.truffle.espresso.EspressoLanguage;
import com.oracle.truffle.espresso.concolic.*;
import com.oracle.truffle.espresso.meta.Meta;
import com.oracle.truffle.espresso.runtime.staticobject.StaticObject;
import com.oracle.truffle.espresso.impl.*;
import com.microsoft.z3.*;
import java.util.*;

public class CollectionHook {
    public static boolean isSupported(Object o) {
        if (o instanceof ConcolicObject obj) {
            return obj.isInitialized() && (obj.isBoxed() || obj.isString());
        }
        return false;
    }

    public static Object wrapMapMethod(ConcolicObjectImpl receiver,
                                       String methodName,
                                       Object[] args,
                                       String signature,
                                       ConcolicValueWrapper<?> ret) {
        AbstractMap<ConcolicValueWrapper<?>, ConcolicValueWrapper<?>> collection = receiver.getMap();
        if (collection == null) {
            if (Logger.compileLog) {
                Logger.WARNING("[CollectionHook] Invalid");
            }
            return ret;
        }
        switch (methodName) {
            case "clear":
                collection.clear();
                receiver.setNonSymbolic();
                break;
            case "containsKey": {
                ConcolicValueWrapper<?> arg1 = ConcolicHelper.toConcolic(args[1]);
                if (ConcolicValueHelper.eitherSymbolic(receiver, arg1)) {
                    if (arg1.isBoxed()) {
                        ret.setExpr(Z3Helper.mkSelect(
                            (ArrayExpr<BitVecSort, BoolSort>) receiver.getExistExprWithInit(arg1),
                            (BitVecExpr) arg1.getExprWithInit())
                        );
                    } else if (arg1.isString()) {
                        SeqExpr<BitVecSort> strExpr = (SeqExpr<BitVecSort>) arg1.getSeqExprWithInit();
                        if (strExpr != null) {
                            ret.setExpr(Z3Helper.mkSelect(
                                (ArrayExpr<SeqSort<BitVecSort>, BoolSort>) receiver.getExistExprWithInit(arg1),
                                strExpr
                            ));
                        }
                    } else {
                        if (Logger.compileLog) {
                            Logger.DEBUG("[CollectionHook] Unsupported: " + args[1]);
                        }
                    }
                }
                break;
            }
            // case "containsValue": TODO
            case "put": {
                ConcolicValueWrapper<?> arg1 = ConcolicHelper.toConcolic(args[1]);
                ConcolicValueWrapper<?> arg2 = ConcolicHelper.toConcolic(args[2]);
                collection.put(arg1, arg2);
                if (ConcolicValueHelper.eitherSymbolic(receiver, arg1, arg2)) {
                    if (arg1.isBoxed()) {
                        receiver.setExistExpr(Z3Helper.mkStore(
                                (ArrayExpr<BitVecSort, BoolSort>) receiver.getExistExprWithInit(arg1),
                                (BitVecExpr) arg1.getExprWithInit(),
                                Z3Helper.mkBool(true)));
                        if (arg2.isBoxed()) {
                            receiver.setExpr(Z3Helper.mkStore(
                                    (ArrayExpr<BitVecSort, BitVecSort>) receiver.getMapExprWithInit(
                                        ConcolicObjectImpl.getSort(arg1), ConcolicObjectImpl.getSort(arg2)),
                                    (BitVecExpr) arg1.getExprWithInit(),
                                    (BitVecExpr) arg2.getExprWithInit()));
                        } else if (arg2.isString()) {
                            receiver.setExpr(Z3Helper.mkStore(
                                    (ArrayExpr<BitVecSort, SeqSort<BitVecSort>>) receiver.getMapExprWithInit(
                                        ConcolicObjectImpl.getSort(arg1), ConcolicObjectImpl.getSort(arg2)),
                                    (BitVecExpr) arg1.getExprWithInit(),
                                    (SeqExpr<BitVecSort>) arg2.getExprWithInit()));
                        }
                    } else if (arg1.isString()) {
                        receiver.setExistExpr(Z3Helper.mkStore(
                                (ArrayExpr<SeqSort<BitVecSort>, BoolSort>) receiver.getExistExprWithInit(arg1),
                                (SeqExpr<BitVecSort>) arg1.getExprWithInit(),
                                Z3Helper.mkBool(true)));
                        if (arg2.isBoxed()) {
                            if (arg1.getSeqExprWithInit() != null) {
                                receiver.setExpr(Z3Helper.mkStore(
                                        (ArrayExpr<SeqSort<BitVecSort>, BitVecSort>) receiver.getMapExprWithInit(
                                            ConcolicObjectImpl.getSort(arg1), ConcolicObjectImpl.getSort(arg2)),
                                        (SeqExpr<BitVecSort>) arg1.getSeqExprWithInit(),
                                        (BitVecExpr) arg2.getExprWithInit()));
                            }
                        } else if (arg2.isString()) {
                            if (arg1.getSeqExprWithInit() != null && arg2.getSeqExprWithInit() != null) {
                                receiver.setExpr(Z3Helper.mkStore(
                                        (ArrayExpr<SeqSort<BitVecSort>, SeqSort<BitVecSort>>) receiver.getMapExprWithInit(
                                            ConcolicObjectImpl.getSort(arg1), ConcolicObjectImpl.getSort(arg2)),
                                        (SeqExpr<BitVecSort>) arg1.getSeqExprWithInit(),
                                        (SeqExpr<BitVecSort>) arg2.getSeqExprWithInit()));
                            }
                        }
                    } else {
                        if (Logger.compileLog) {
                            Logger.DEBUG("[CollectionHook] Unsupported: " + args[1] + ", " + args[2]);
                        }
                    }
                }
                break;
            }
            case "getOrDefault":
            case "get": {
                ConcolicValueWrapper<?> arg1 = ConcolicHelper.toConcolic(args[1]);
                if (ConcolicValueHelper.eitherSymbolic(receiver, arg1)) {
                    if (collection.isEmpty()) {
                        return ret;
                    } else if (arg1.isBoxed()) {
                        Sort valSort = ConcolicObjectImpl.getSort(collection.values().iterator().next());
                        ret.setExpr(Z3Helper.mkSelect(
                            (ArrayExpr<BitVecSort, ?>) receiver.getMapExprWithInit(ConcolicObjectImpl.getSort(arg1), valSort),
                            (BitVecExpr) arg1.getExprWithInit())
                        );
                    } else if (arg1.isString()) {
                        if (arg1.getSeqExprWithInit() != null) {
                            Sort valSort = ConcolicObjectImpl.getSort(collection.values().iterator().next());
                            ret.setExpr(Z3Helper.mkSelect(
                                (ArrayExpr<SeqSort<BitVecSort>, ?>) receiver.getMapExprWithInit(ConcolicObjectImpl.getSort(arg1), valSort),
                                (SeqExpr<BitVecSort>) arg1.getSeqExprWithInit())
                            );
                        }
                    }
                }
                break;
            }
            // case "entrySet": HashMap works, need check ConcurrentHashMap
            case "putIfAbsent":
                collection.putIfAbsent(ConcolicHelper.toConcolic(args[1]), ConcolicHelper.toConcolic(args[2]));
                break;
            case "remove":
                if (args.length < 3) {
                    collection.remove(ConcolicHelper.toConcolic(args[1]));
                } else {
                    collection.remove(ConcolicHelper.toConcolic(args[1]), ConcolicHelper.toConcolic(args[2]));
                }
                break;
            case "replace":
                if (args.length < 4) {
                    collection.replace(ConcolicHelper.toConcolic(args[1]), ConcolicHelper.toConcolic(args[2]));
                } else {
                    collection.replace(ConcolicHelper.toConcolic(args[1]), ConcolicHelper.toConcolic(args[2]), ConcolicHelper.toConcolic(args[3]));
                }
                break;
        }
        return ret;
    }

    public static Object wrapMethod(String className,
                                    String methodName,
                                    Object[] args,
                                    String signature,
                                    Object returnedObject) {
        if (args.length == 0 || !(args[0] instanceof ConcolicObjectImpl)) {
            throw new RuntimeException("[CollectionHook] arg0 should be ConcolicObjectImpl: " + args[0]);
        }
        ConcolicObjectImpl receiver = (ConcolicObjectImpl) args[0];
        ConcolicValueWrapper<?> ret = ConcolicHelper.toConcolic(returnedObject);
        if (Logger.compileLog) {
            Logger.DEBUG("[CollectionHook] " + receiver + "." + methodName + signature);
        }
        if (receiver.isMap()) {
            return wrapMapMethod(receiver, methodName, args, signature, ret);
        }

        AbstractCollection<ConcolicValueWrapper<?>> collection = receiver.getAbstractCollection();
        if (collection == null) {
            if (Logger.compileLog) {
                Logger.WARNING("[CollectionHook] Invalid");
            }
            return ret;
        }
        switch (methodName) {
            case "add":
                switch (args.length) {
                    case 2:
                        collection.add(ConcolicHelper.toConcolic(args[1]));
                        break;
                    case 3:
                        if (collection instanceof List<ConcolicValueWrapper<?>> list) {
                            list.add((int) ConcolicHelper.toConcrete(args[1]), ConcolicHelper.toConcolic(args[2]));
                        }
                        break;
                }
                break;
            case "addAll":
                switch (args.length) {
                    case 2:
                        if (args[1] instanceof ConcolicObjectImpl arg1) {
                            if (arg1.isAbstractCollection()) {
                                collection.addAll(arg1.getAbstractCollection());
                            }
                        }
                        break;
                    case 3:
                        if (collection instanceof List<ConcolicValueWrapper<?>> list) {
                            if (args[2] instanceof ConcolicObjectImpl arg2) {
                                if (arg2.isAbstractCollection()) {
                                    list.addAll((int) ConcolicHelper.toConcrete(args[1]), arg2.getAbstractCollection());
                                }
                            }
                        }
                        break;
                }
                break;
            case "clear":
                collection.clear();
                break;
            case "remove":
                switch (args.length) {
                    case 1:
                        if (collection instanceof Queue<ConcolicValueWrapper<?>> queue) {
                            queue.remove();
                        }
                        break;
                    case 2:
                        if (collection instanceof List<ConcolicValueWrapper<?>> list) {
                            list.remove(ConcolicHelper.toConcrete(args[1]));
                        }
                        break;
                }
                break;
            case "removeAll":
                if (collection instanceof List<ConcolicValueWrapper<?>> list) {
                    if (args[1] instanceof ConcolicObjectImpl arg1) {
                        if (arg1.isAbstractCollection()) {
                            list.removeAll(arg1.getAbstractCollection());
                        }
                    }
                }
                break;
            case "set":
                if (collection instanceof List<ConcolicValueWrapper<?>> list) {
                    list.set((int) ConcolicHelper.toConcrete(args[1]), ConcolicHelper.toConcolic(args[2]));
                }
                break;
            case "poll":
                if (collection instanceof Queue<ConcolicValueWrapper<?>> queue) {
                    queue.poll();
                }
                break;
            case "get":
                if (collection.isEmpty()) {
                    return ret;
                } else if (collection instanceof List<ConcolicValueWrapper<?>> list) {
                    ConcolicValueWrapper<?> concolic = ConcolicHelper.toConcolic(args[1]);
                    if (ConcolicValueHelper.eitherSymbolic(receiver, concolic)) {
                        if (!isSupported(concolic)) {
                            if (Logger.compileLog) {
                                Logger.DEBUG("[CollectionHook] Unsupported: " + args[1]);
                            }
                            return ret;
                        }
                        SeqExpr<?> expr1 = receiver.getSeqExprWithInit();
                        if (expr1 != null) {
                            IntExpr expr2 = Z3Helper.mkBV2Int((BitVecExpr) concolic.getExprWithInit(), true);
                            ret.setExpr(Z3Helper.mkAt(expr1, expr2));
                        }
                    }
                }
                break;
            case "indexOf":
                if (collection.isEmpty()) {
                    return ret;
                } else if (collection instanceof List<ConcolicValueWrapper<?>> list) {
                    ConcolicValueWrapper<?> concolic = ConcolicHelper.toConcolic(args[1]);
                    if (ConcolicValueHelper.eitherSymbolic(receiver, concolic)) {
                        if (concolic.isBoxed()) {
                            SeqExpr<BitVecSort> expr1 = (SeqExpr<BitVecSort>) receiver.getSeqExprWithInit();
                            SeqExpr<BitVecSort> expr2 = Z3Helper.mkUnit((BitVecExpr) concolic.getExprWithInit());
                            if (expr1 != null) {
                                ret.setExpr(Z3Helper.mkInt2BV(32,
                                    Z3Helper.mkIndexOf(expr1, expr2, Z3Helper.mkInt(0))));
                            }
                        } else if (concolic.isString()) {
                            int len = ((ConcolicObjectImpl) concolic).getConcreteStringValue().length();
                            SeqExpr<SeqSort<BitVecSort>> expr1 = (SeqExpr<SeqSort<BitVecSort>>) SeqSupport.createSeqExpr(receiver, len);
                            SeqExpr<SeqSort<BitVecSort>> expr2 = Z3Helper.mkUnit((SeqExpr<BitVecSort>) concolic.getSeqExprWithInit());
                            if (expr1 != null && expr2 != null) {
                                ret.setExpr(Z3Helper.mkInt2BV(32,
                                    Z3Helper.mkIndexOf(expr1, expr2, Z3Helper.mkInt(0))));
                            }
                        } else {
                            if (Logger.compileLog) {
                                Logger.DEBUG("[CollectionHook] Unsupported: " + args[1]);
                            }
                            return ret;
                        }
                    }
                }
                break;
            case "contains": {
                if (collection.isEmpty()) {
                    return ret;
                }
                ConcolicValueWrapper<?> concolic = ConcolicHelper.toConcolic(args[1]);
                if (ConcolicValueHelper.eitherSymbolic(receiver, concolic)) {
                    if (concolic.isBoxed()) {
                        SeqExpr<BitVecSort> expr1 = (SeqExpr<BitVecSort>) receiver.getSeqExprWithInit();
                        SeqExpr<BitVecSort> expr2 = Z3Helper.mkUnit((BitVecExpr) concolic.getExprWithInit());
                        if (expr1 != null) {
                            ret.setExpr(Z3Helper.mkContains(expr1, expr2));
                        }
                    } else if (concolic.isString()) {
                        int len = ((ConcolicObjectImpl) concolic).getConcreteStringValue().length();
                        SeqExpr<SeqSort<BitVecSort>> expr1 = (SeqExpr<SeqSort<BitVecSort>>) SeqSupport.createSeqExpr(receiver, len);
                        SeqExpr<SeqSort<BitVecSort>> expr2 = Z3Helper.mkUnit((SeqExpr<BitVecSort>) concolic.getSeqExprWithInit());
                        if (expr1 != null && expr2 != null) {
                            ret.setExpr(Z3Helper.mkContains(expr1, expr2));
                        }
                    } else {
                        if (Logger.compileLog) {
                            Logger.DEBUG("[CollectionHook] Unsupported: " + args[1]);
                        }
                        return ret;
                    }
                }
            }
        }
        return ret;
    }
}
