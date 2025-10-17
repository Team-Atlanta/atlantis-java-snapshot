package com.oracle.truffle.espresso.concolic.hook;

import com.oracle.truffle.api.concolic.*;
import com.oracle.truffle.espresso.EspressoLanguage;
import com.oracle.truffle.espresso.classfile.JavaKind;
import com.oracle.truffle.espresso.concolic.*;
import com.oracle.truffle.espresso.meta.Meta;
import com.oracle.truffle.espresso.runtime.staticobject.StaticObject;
import com.oracle.truffle.espresso.descriptors.*;
import com.oracle.truffle.espresso.vm.InterpreterToVM;
import com.oracle.truffle.espresso.vm.UnsafeAccess;
import com.oracle.truffle.espresso.impl.*;
import java.lang.reflect.Array;
import sun.misc.Unsafe;

public class UnsafeHook {
    public static final Unsafe UNSAFE = UnsafeAccess.get();

    private static int getSlot(ConcolicObject obj, long offset) {
        StaticObject concrete = (StaticObject) obj.getConcreteValue();
        Klass klass = concrete.getKlass();
        if (klass == null) {
            if (Logger.compileLog) {
                Logger.DEBUG("Klass not found in " + obj);
            }
            return -1;
        }
        if (!concrete.isArray()) {
            return klass.getMeta().getLanguage().getGuestFieldOffsetStrategy().guestOffsetToSlot(offset);
        } else if (((ArrayKlass) klass).getComponentType().isPrimitive()) {
            Class<?> hostPrimitive = ((ArrayKlass) klass).getComponentType().getJavaKind().toJavaClass();
            Class<?> hostArray = Array.newInstance(hostPrimitive, 0).getClass();
            return ((int) (offset - (long) UNSAFE.arrayBaseOffset(hostArray)) / UNSAFE.arrayIndexScale(hostArray));
        } else {
            return ((int) (offset - (long) UNSAFE.arrayBaseOffset(Object[].class)) / UNSAFE.arrayIndexScale(Object[].class));
        }
    }

    public static Object wrapMethod(String className,
                                    String methodName,
                                    Object[] args,
                                    String signature,
                                    Object returnedObject) {
        if (!className.equals("jdk/internal/misc/Unsafe")) {
            throw new RuntimeException("[UnsafeHook] bad className: " + className);
        }
        if (Logger.compileLog) {
            Logger.DEBUG("[UnsafeHook] " + methodName + signature);
        }
        switch (methodName) {
            // case "allocateMemory0":
            //     if (Logger.compileLog) {
            //         Logger.DEBUG("[UnsafeHook] " + methodName + signature);
            //     }
            //     if (signature.equals("(J)J")) {
            //         long offset = (long) ConcolicHelper.toConcrete(returnedObject);
            //         long length = (long) ConcolicHelper.toConcrete(args[1]);
            //         long idx = 0;
            //         while (idx < length) {
            //             ConcolicHelper.allocMap.put(offset + idx++, ConcolicByte.createWithoutConstraints(0));
            //         }
            //     }
            //     break;
            case "copyMemory0":
                if (signature.equals("(Ljava/lang/Object;JLjava/lang/Object;JJ)V")) {
                    ConcolicObjectImpl src = (ConcolicObjectImpl) ConcolicHelper.toConcolic(args[1]);
                    ConcolicObjectImpl dst = (ConcolicObjectImpl) ConcolicHelper.toConcolic(args[3]);
                    if ((src.isArray() && !((ConcolicArrayObject) src).getFieldKind().equals(JavaKind.Byte))
                            || (dst.isArray() && !((ConcolicArrayObject) dst).getFieldKind().equals(JavaKind.Byte))) {
                        if (Logger.compileLog) {
                            Logger.WARNING("[UnsafeHook] Not implemented yet");
                        }
                        return returnedObject;
                    }
                    StaticObject srcConcrete = src.getConcreteObject();
                    StaticObject dstConcrete = dst.getConcreteObject();
                    long srcOffset = (long) ConcolicHelper.toConcrete(args[2]);
                    long dstOffset = (long) ConcolicHelper.toConcrete(args[4]);
                    long bytes = (long) ConcolicHelper.toConcrete(args[5]);
                    if (StaticObject.isNull(dstConcrete)) {
                        ConcolicHelper.allocSizeMap.put(dstOffset, bytes);
                    }
                    long srcStartIdx = StaticObject.isNull(srcConcrete) ? srcOffset : getSlot(src, srcOffset);
                    long dstStartIdx = StaticObject.isNull(dstConcrete) ? dstOffset : getSlot(dst, dstOffset);
                    for (int i = 0; i < (int) bytes; i++) {
                        long srcIdx = srcStartIdx + i;
                        long dstIdx = dstStartIdx + i;
                        if ((StaticObject.notNull(srcConcrete) && i >= src.getConcreteSize())
                                || (StaticObject.notNull(dstConcrete) && i >= dst.getConcreteSize())) {
                            if (Logger.compileLog) {
                                Logger.WARNING("[UnsafeHook] Invalid Idx");
                            }
                            return returnedObject;
                        }
                        if ((StaticObject.isNull(srcConcrete) && !ConcolicHelper.allocMap.containsKey(srcIdx))) {
                            if (Logger.compileLog) {
                                Logger.WARNING("[UnsafeHook] concolic in heap not found");
                            }
                            return returnedObject;
                        }
                        byte concrete;
                        if (StaticObject.isNull(dstConcrete)) {
                            concrete = UnsafeHook.UNSAFE.getByte(dstIdx);
                        } else {
                            Klass klass = dstConcrete.getKlass();
                            EspressoLanguage language = klass.getMeta().getLanguage();
                            concrete = klass.getContext().getInterpreterToVM().getArrayByte(language, (int) dstIdx, dstConcrete);
                        }
                        ConcolicByte srcByte = StaticObject.isNull(srcConcrete)
                            ? (ConcolicByte) ConcolicHelper.allocMap.get(srcIdx)
                            : (ConcolicByte) src.getOrCreateField((int) srcIdx);
                        ConcolicByte dstByte = null;
                        if (StaticObject.isNull(dstConcrete) || srcByte.getConcreteValue() != concrete) {
                            if (Logger.compileLog && srcByte.getConcreteValue() != concrete && srcByte.isSymbolic()) {
                                synchronized (Z3Helper.getInstance()) {
                                    Logger.WARNING("[UnsafeHook] copyMemory0: Mismatch concolic: " + srcByte + ", concrete: " + concrete);
                                }
                            }
                            dstByte = (ConcolicByte) ConcolicByte.createWithoutConstraints(concrete);
                            ConcolicHelper.allocMap.put(dstIdx, dstByte);
                        } else {
                            dstByte = (ConcolicByte) dst.getOrCreateField((int) dstIdx);
                        }
                        if (srcByte.getConcreteValue() != concrete && srcByte.getConcreteValue() != 0) {
                            dstByte.setValueWithConstraints(concrete, null);
                        } else {
                            dstByte.setValueWithConstraints(concrete, srcByte.getExpr());
                        }
                        if (Logger.compileLog) {
                            synchronized (Z3Helper.getInstance()) {
                                Logger.DEBUG("[UnsafeHook] copyMemory0 " + (StaticObject.isNull(dstConcrete) ? "to heap " : "to obj ") + dstByte);
                            }
                        }
                    }
                    return returnedObject;
                }
                break;
            case "freeMemory0":
                if (signature.equals("(J)V")) {
                    long heapOffset = (long) ConcolicHelper.toConcrete(args[1]);
                    if (!ConcolicHelper.allocMap.containsKey(heapOffset)) {
                        return returnedObject;
                    }
                    if (ConcolicHelper.allocSizeMap.containsKey(heapOffset)) {
                        Long allocSize = ConcolicHelper.allocSizeMap.remove(heapOffset);
                        for (int i = 0; i < allocSize; i++) {
                            long curHeapOffset = heapOffset + i;
                            ConcolicValueWrapper<?> e = ConcolicHelper.allocMap.remove(curHeapOffset);
                            if (e == null) {
                                break;
                            }
                            if (Logger.compileLog) {
                                synchronized (Z3Helper.getInstance()) {
                                    Logger.DEBUG("[UnsafeHook] freeMemory0 " + e);
                                }
                            }
                        }
                    } else {
                        if (Logger.compileLog) {
                            Logger.WARNING("[UnsafeHook] Not found size for freeMemory0" + heapOffset);
                        }
                    }
                }
                break;
            case "compareAndSetInt":
            case "compareAndSetLong":
            // case "compareAndSetObject":
            case "compareAndSetReference":
                return wrapCompareAndSet(className, methodName, args, signature, returnedObject);
            // case "putAddress":
            case "putBoolean":
            case "putBooleanVolatile":
            case "putByte":
            case "putByteVolatile":
            case "putChar":
            case "putCharVolatile":
            case "putDouble":
            case "putDoubleVolatile":
            case "putFloat":
            case "putFloatVolatile":
            case "putInt":
            case "putIntVolatile":
            case "putLong":
            case "putLongVolatile":
            case "putObject":
            case "putObjectVolatile":
            // case "putOrderedInt":
            // case "putOrderedLong":
            // case "putOrderedObject":
            case "putReference":
            case "putReferenceVolatile":
            case "putShort":
            case "putShortVolatile":
                return wrapPut(className, methodName, args, signature, returnedObject);
            // case "getAddress":
            case "getBoolean":
            case "getBooleanVolatile":
            case "getByte":
            case "getByteVolatile":
            case "getChar":
            case "getCharVolatile":
            case "getDouble":
            case "getDoubleVolatile":
            case "getFloat":
            case "getFloatVolatile":
            case "getInt":
            case "getIntVolatile":
            // case "getLoadAverage0":
            case "getLong":
            case "getLongVolatile":
            case "getObject":
            case "getObjectVolatile":
            case "getReference":
            case "getReferenceVolatile":
            case "getShort":
            case "getShortVolatile":
                return wrapGet(className, methodName, args, signature, returnedObject);
            default:
                break;
        }

// addressSize0:()I
// allocateInstance:(Ljava/lang/Class;)Ljava/lang/Object;
// arrayBaseOffset0:(Ljava/lang/Class;)I
// arrayIndexScale0:(Ljava/lang/Class;)I
// compareAndExchangeByte:(Ljava/lang/Object;JBB)B
// compareAndExchangeInt:(Ljava/lang/Object;JII)I
// compareAndExchangeLong:(Ljava/lang/Object;JJJ)J
// compareAndExchangeObject:(Ljava/lang/Object;JLjava/lang/Object;Ljava/lang/Object;)Ljava/lang/Object;
// compareAndExchangeReference:(Ljava/lang/Object;JLjava/lang/Object;Ljava/lang/Object;)Ljava/lang/Object;
// compareAndExchangeShort:(Ljava/lang/Object;JSS)S
// copySwapMemory0:(Ljava/lang/Object;JLjava/lang/Object;JJJ)V
// defineAnonymousClass0:(Ljava/lang/Class;[B[Ljava/lang/Object;)Ljava/lang/Class;
// defineClass0:(Ljava/lang/String;[BIILjava/lang/ClassLoader;Ljava/security/ProtectionDomain;)Ljava/lang/Class;
// ensureClassInitialized0:(Ljava/lang/Class;)V
// fullFence:()V
// isBigEndian0:()Z
// loadFence:()V
// objectFieldOffset0:(Ljava/lang/reflect/Field;)J
// objectFieldOffset1:(Ljava/lang/Class;Ljava/lang/String;)J
// pageSize:()I
// park:(ZJ)V
// reallocateMemory0:(JJ)J
// registerNatives:()V
// setMemory0:(Ljava/lang/Object;JJB)V
// shouldBeInitialized0:(Ljava/lang/Class;)Z
// staticFieldBase0:(Ljava/lang/reflect/Field;)Ljava/lang/Object;
// staticFieldOffset0:(Ljava/lang/reflect/Field;)J
// storeFence:()V
// throwException:(Ljava/lang/Throwable;)V
// tryMonitorEnter:(Ljava/lang/Object;)Z
// unalignedAccess0:()Z
// unpark

        return returnedObject;
    }

    public static Object wrapCompareAndSet(String className,
                                    String methodName,
                                    Object[] args,
                                    String signature,
                                    Object returnedObject) {
        if (Logger.compileLog) {
            synchronized (Z3Helper.getInstance()) {
                Logger.DEBUG("[UnsafeHook.wrapCompareAndSet] " + methodName + ": " + (Boolean) returnedObject);
            }
        }
        if ((Boolean) returnedObject == false) {
            return returnedObject;
        }

        ConcolicValueWrapper<?> newValue = null;
        switch (signature) {
            case "(Ljava/lang/Object;JII)Z":
                newValue = (ConcolicInt) args[4];
                break;
            case "(Ljava/lang/Object;JJJ)Z":
                newValue = (ConcolicLong) args[4];
                break;
            case "(Ljava/lang/Object;JLjava/lang/Object;Ljava/lang/Object;)Z":
                newValue = (ConcolicObject) args[4];
                break;
            default:
                if (Logger.compileLog) {
                    Logger.DEBUG("Unsupported: " + signature);
                }
                return returnedObject;
        }

        ConcolicObjectImpl obj = (ConcolicObjectImpl) args[1];
        ConcolicLong offset = (ConcolicLong) args[2];
        int index = getSlot(obj, offset.getConcreteValue());
        obj.putField(index, newValue);
        return returnedObject;
    }

    public static Object wrapPut(String className,
                                 String methodName,
                                 Object[] args,
                                 String signature,
                                 Object returnedObject) {
        if (Logger.compileLog) {
            Logger.DEBUG("[UnsafeHook.wrapPut] " + methodName);
        }

        ConcolicValueWrapper<?> x = null;
        JavaKind kind = null;
        switch (signature) {
            // case "(JJ)V":
            // case "(JB)V":
            // case "(JC)V":
            // case "(JD)V":
            // case "(JF)V":
            // case "(JI)V":
            // case "(JS)V":
            case "(Ljava/lang/Object;JZ)V":
                x = (ConcolicBoolean) args[3];
                kind = JavaKind.Boolean;
                break;
            case "(Ljava/lang/Object;JB)V":
                x = (ConcolicByte) args[3];
                kind = JavaKind.Byte;
                break;
            case "(Ljava/lang/Object;JC)V":
                x = (ConcolicChar) args[3];
                kind = JavaKind.Char;
                break;
            case "(Ljava/lang/Object;JD)V":
                x = (ConcolicDouble) args[3];
                kind = JavaKind.Double;
                break;
            case "(Ljava/lang/Object;JF)V":
                x = (ConcolicFloat) args[3];
                kind = JavaKind.Float;
                break;
            case "(Ljava/lang/Object;JI)V":
                x = (ConcolicInt) args[3];
                kind = JavaKind.Int;
                break;
            case "(Ljava/lang/Object;JJ)V":
                x = (ConcolicLong) args[3];
                kind = JavaKind.Long;
                break;
            case "(Ljava/lang/Object;JLjava/lang/Object;)V":
                x = (ConcolicObject) args[3];
                kind = JavaKind.Object;
                break;
            case "(Ljava/lang/Object;JS)V":
                x = (ConcolicShort) args[3];
                kind = JavaKind.Short;
                break;
            default:
                if (Logger.compileLog) {
                    Logger.DEBUG("Unsupported: " + signature);
                }
                return returnedObject;
        }

        ConcolicObjectImpl obj = (ConcolicObjectImpl) args[1];
        ConcolicLong offset = (ConcolicLong) args[2];
        int index = getSlot(obj, offset.getConcreteValue());

        if (x == null) {
            if (Logger.compileLog) {
                Logger.WARNING("Invalid!");
            }
            return returnedObject;
        }
        obj.putAs(kind, index, x);
        return returnedObject;
    }

    public static Object wrapGet(String className,
                                 String methodName,
                                 Object[] args,
                                 String signature,
                                 Object returnedObject) {
        if (Logger.compileLog) {
            Logger.DEBUG("[UnsafeHook.wrapGet] " + methodName);
        }

        switch (signature) {
            // case "(J)B":
            // case "(J)C":
            // case "(J)D":
            // case "(J)F":
            // case "(J)I":
            // case "(J)J":
            // case "(J)S":
            // case "([DI)I":
            case "(Ljava/lang/Object;J)Z":
            case "(Ljava/lang/Object;J)B":
            case "(Ljava/lang/Object;J)C":
            case "(Ljava/lang/Object;J)D":
            case "(Ljava/lang/Object;J)F":
            case "(Ljava/lang/Object;J)I":
            case "(Ljava/lang/Object;J)J":
            case "(Ljava/lang/Object;J)Ljava/lang/Object;":
            case "(Ljava/lang/Object;J)S":
                break;
            default:
                if (Logger.compileLog) {
                    Logger.WARNING("Unsupported: " + signature);
                }
                return returnedObject;
        }

        if (!(args[1] instanceof ConcolicObjectImpl)) {
            if (Logger.compileLog) {
                synchronized (Z3Helper.getInstance()) {
                    Logger.WARNING("Unimplemented ConcolicObject:" + args[1]);
                }
            }
            return returnedObject;
        }
        ConcolicObjectImpl obj = (ConcolicObjectImpl) args[1];
        ConcolicLong offset = (ConcolicLong) args[2];
        int index = getSlot(obj, offset.getConcreteValue());

        switch (signature.charAt(signature.length()-1)) {
            case 'Z': {
                ConcolicValueWrapper<?> concolic = obj.getAs(JavaKind.Boolean, index);
                boolean concrete = (Boolean) returnedObject;
                if (concolic == null || !concolic.getConcreteValue().equals(concrete)) {
                    if (Logger.compileLog && concolic != null && concolic.isSymbolic()) {
                        synchronized (Z3Helper.getInstance()) {
                            Logger.WARNING("[Mismatch wrapGet] concolic: " + concolic + ", concrete: " + concrete);
                        }
                    }
                    concolic = ConcolicBoolean.createWithoutConstraints(concrete);
                    // ConcolicObjectImpl.putField(obj, index, concolic);
                }
                return concolic;
            }
            case 'B': {
                ConcolicValueWrapper<?> concolic = obj.getAs(JavaKind.Byte, index);
                byte concrete = (Byte) returnedObject;
                if (concolic == null || !concolic.getConcreteValue().equals(concrete)) {
                    if (Logger.compileLog && concolic != null && concolic.isSymbolic()) {
                        synchronized (Z3Helper.getInstance()) {
                            Logger.WARNING("[Mismatch wrapGet] concolic: " + concolic + ", concrete: " + returnedObject);
                        }
                    }
                    concolic = ConcolicByte.createWithoutConstraints(concrete);
                    // ConcolicObjectImpl.putField(obj, index, concolic);
                }
                return concolic;
            }
            case 'C': {
                ConcolicValueWrapper<?> concolic = obj.getAs(JavaKind.Char, index);
                char concrete = (Character) returnedObject;
                if (concolic == null || !concolic.getConcreteValue().equals(concrete)) {
                    if (Logger.compileLog && concolic != null && concolic.isSymbolic()) {
                        synchronized (Z3Helper.getInstance()) {
                            Logger.WARNING("[Mismatch wrapGet] concolic: " + concolic + ", concrete: " + concrete);
                        }
                    }
                    concolic = ConcolicChar.createWithoutConstraints(concrete);
                    // ConcolicObjectImpl.putField(obj, index, concolic);
                }
                return concolic;
            }
            case 'D': {
                ConcolicValueWrapper<?> concolic = obj.getAs(JavaKind.Double, index);
                double concrete = (Double) returnedObject;
                if (concolic == null || !concolic.getConcreteValue().equals(concrete)) {
                    if (Logger.compileLog && concolic != null && concolic.isSymbolic()) {
                        synchronized (Z3Helper.getInstance()) {
                            Logger.WARNING("[Mismatch wrapGet] concolic: " + concolic + ", concrete: " + concrete);
                        }
                    }
                    concolic = ConcolicDouble.createWithoutConstraints(concrete);
                    // ConcolicObjectImpl.putField(obj, index, concolic);
                }
                return concolic;
            }
            case 'F': {
                ConcolicValueWrapper<?> concolic = obj.getAs(JavaKind.Float, index);
                float concrete = (Float) returnedObject;
                if (concolic == null || !concolic.getConcreteValue().equals(concrete)) {
                    if (Logger.compileLog && concolic != null && concolic.isSymbolic()) {
                        synchronized (Z3Helper.getInstance()) {
                            Logger.WARNING("[Mismatch wrapGet] concolic: " + concolic + ", concrete: " + concrete);
                        }
                    }
                    concolic = ConcolicFloat.createWithoutConstraints(concrete);
                    // ConcolicObjectImpl.putField(obj, index, concolic);
                }
                return concolic;
            }
            case 'I': {
                ConcolicValueWrapper<?> concolic = obj.getAs(JavaKind.Int, index);
                int concrete = (Integer) returnedObject;
                if (concolic == null || !concolic.getConcreteValue().equals(concrete)) {
                    if (Logger.compileLog && concolic != null && concolic.isSymbolic()) {
                        synchronized (Z3Helper.getInstance()) {
                            Logger.WARNING("[Mismatch wrapGet] concolic: " + concolic + ", concrete: " + concrete);
                        }
                    }
                    concolic = ConcolicInt.createWithoutConstraints(concrete);
                    // ConcolicObjectImpl.putField(obj, index, concolic);
                }
                return concolic;
            }
            case 'J': {
                ConcolicValueWrapper<?> concolic = obj.getAs(JavaKind.Long, index);
                long concrete = (Long) returnedObject;
                if (concolic == null || !concolic.getConcreteValue().equals(concrete)) {
                    if (Logger.compileLog && concolic != null && concolic.isSymbolic()) {
                        synchronized (Z3Helper.getInstance()) {
                            Logger.WARNING("[Mismatch wrapGet] concolic: " + concolic + ", concrete: " + concrete);
                        }
                    }
                    concolic = ConcolicLong.createWithoutConstraints(concrete);
                    // ConcolicObjectImpl.putField(obj, index, concolic);
                }
                return concolic;
            }
            case 'S': {
                ConcolicValueWrapper<?> concolic = obj.getAs(JavaKind.Short, index);
                short concrete = (Short) returnedObject;
                if (concolic == null || !concolic.getConcreteValue().equals(concrete)) {
                    if (Logger.compileLog && concolic != null && concolic.isSymbolic()) {
                        synchronized (Z3Helper.getInstance()) {
                            Logger.WARNING("[Mismatch wrapGet] concolic: " + concolic + ", concrete: " + concrete);
                        }
                    }
                    concolic = ConcolicShort.createWithoutConstraints(concrete);
                    // ConcolicObjectImpl.putField(obj, index, concolic);
                }
                return concolic;
            }
            case ';': {
                ConcolicValueWrapper<?> concolic = obj.getField(index);
                StaticObject concrete = (StaticObject) returnedObject;
                Klass klass = concrete.getKlass();
                if (concolic == null || klass == null) {
                    concolic = ConcolicObjectFactory.createWithoutConstraints(returnedObject);
                } else {
                    boolean isEqual = InterpreterToVM.referenceIdentityEqual(
                            concrete, (StaticObject) concolic.getConcreteValue(), klass.getContext().getLanguage());
                    if (!isEqual) {
                        if (Logger.compileLog && concolic != null && concolic.isSymbolic()) {
                            synchronized (Z3Helper.getInstance()) {
                                Logger.WARNING("[Mismatch wrapGet] concolic: " + concolic + ", concrete: " + returnedObject);
                            }
                        }
                        concolic = ConcolicObjectFactory.createWithoutConstraints(returnedObject);
                        // ConcolicObjectImpl.putField(obj, index, concolic);
                    }
                }
                return concolic;
            }
            default:
                if (Logger.compileLog) {
                    Logger.WARNING("Unsupported: " + signature);
                }
                return returnedObject;
        }
    }
}
