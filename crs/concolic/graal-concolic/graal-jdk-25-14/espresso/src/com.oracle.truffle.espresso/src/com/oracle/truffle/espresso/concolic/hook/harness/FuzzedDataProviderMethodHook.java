package com.oracle.truffle.espresso.concolic.hook.harness;

import com.oracle.truffle.api.concolic.*;
import com.oracle.truffle.espresso.concolic.*;
import com.oracle.truffle.espresso.meta.Meta;
import com.oracle.truffle.espresso.runtime.staticobject.StaticObject;
import com.oracle.truffle.espresso.vm.InterpreterToVM;
import com.oracle.truffle.espresso.impl.*;
import com.oracle.truffle.espresso.concolic.hook.*;
import com.microsoft.z3.*;
import java.util.HashMap;
import java.util.Map;

public class FuzzedDataProviderMethodHook extends CompleteHook {
    private static Map<StaticObject, Long> latestDataPtrMap = new HashMap<>();
    private static Map<StaticObject, Integer> latestRemainingBytesMap = new HashMap<>();

    public static void reset() {
        latestDataPtrMap = new HashMap<>();
        latestRemainingBytesMap = new HashMap<>();
    }

    public static Object wrapMethod(String className, String methodName, Object target_obj, Object[] args, String signature, Object returnedObject) {
        if (Logger.compileLog) {
            Logger.DEBUG("[FuzzedDataProviderHook]: " + className + "." + methodName + signature);
        }
        if (!className.equals("org/team_atlanta/provider/FuzzedDataProvider")
                && !className.equals("com/code_intelligence/jazzer/api/FuzzedDataProvider")
                && !className.equals("com/code_intelligence/jazzer/driver/FuzzedDataProviderImpl")) {
            throw new RuntimeException("[FuzzedDataProviderHook] bad className: " + className);
        }

        if (Logger.compileLog) {
            Logger.DEBUG("FDP." + methodName + "(): " + returnedObject);
        }

        ConcolicValueWrapper<?> ret;
        switch (methodName) {
            case "consumeBoolean":
                ret = consumeIntegral((ConcolicObjectImpl) args[0], Boolean.class);
                break;
            case "consumeByte":
                if (signature.equals("(BB)B")) {
                    return ConcolicHelper.toConcolic(returnedObject);
                }
                ret = consumeIntegral((ConcolicObjectImpl) args[0], Byte.class);
                break;
            case "consumeByteUnchecked":
                ret = consumeIntegralInRange((ConcolicObjectImpl) args[0], ((ConcolicByte) args[1]).ToLong(), ((ConcolicByte) args[2]).ToLong(), Byte.class).ToByte();
                break;
            case "consumeShort":
                if (signature.equals("(SS)S")) {
                    return ConcolicHelper.toConcolic(returnedObject);
                }
                ret = consumeIntegral((ConcolicObjectImpl) args[0], Short.class);
                break;
            case "consumeShortUnchecked":
                ret = consumeIntegralInRange((ConcolicObjectImpl) args[0], ((ConcolicShort) args[1]).ToLong(), ((ConcolicShort) args[2]).ToLong(), Short.class).ToShort();
                break;
            case "consumeInt":
                if (signature.equals("(II)I")) {
                    return ConcolicHelper.toConcolic(returnedObject);
                }
                ret = consumeIntegral((ConcolicObjectImpl) args[0], Integer.class);
                break;
            case "consumeIntUnchecked":
                ret = consumeIntegralInRange((ConcolicObjectImpl) args[0], ((ConcolicInt) args[1]).ToLong(), ((ConcolicInt) args[2]).ToLong(), Integer.class).ToInt();
                break;
            case "consumeLong":
                if (signature.equals("(JJ)J")) {
                    return ConcolicHelper.toConcolic(returnedObject);
                }
                ret = consumeIntegral((ConcolicObjectImpl) args[0], Long.class);
                break;
            case "consumeLongUnchecked":
                ret = consumeIntegralInRange((ConcolicObjectImpl) args[0], (ConcolicLong) args[1], (ConcolicLong) args[2], Long.class);
                break;
            case "consumeFloat":                    // (char *)"()F", (void *)&ConsumeFloat<jfloat>},
            case "consumeRegularFloat":             // (char *)"()F", (void *)&ConsumeRegularFloat<jfloat>},
            case "consumeRegularFloatUnchecked":    // (char *)"(FF)F", (void *)&ConsumeFloatInRange<jfloat>},
            case "consumeProbabilityFloat":         // (char *)"()F", (void *)&ConsumeProbability<jfloat>},
            case "consumeDouble":                   // (char *)"()D", (void *)&ConsumeFloat<jdouble>},
            case "consumeRegularDouble":            // (char *)"()D", (void *)&ConsumeRegularFloat<jdouble>},
            case "consumeRegularDoubleUnchecked":   // (char *)"(DD)D", (void *)&ConsumeFloatInRange<jdouble>},
            case "consumeProbabilityDouble":        // (char *)"()D", (void *)&ConsumeProbability<jdouble>},
                // Note: Need to update members
                dataPtr((ConcolicObjectImpl) args[0]);
                remainingBytes((ConcolicObjectImpl) args[0]);
                return ConcolicHelper.toConcolic(returnedObject);
            case "consumeChar":
            case "consumeCharUnchecked":
                ret = consumeIntegral((ConcolicObjectImpl) args[0], Character.class);
                break;
            case "consumeCharNoSurrogates":
                ret = consumeIntegral((ConcolicObjectImpl) args[0], Character.class);
                if ((char) ret.getConcreteValue() >= 0xd800 && (char) ret.getConcreteValue() < 0xe000) {
                    ret = ((ConcolicChar) ret).Subtract(ConcolicChar.createWithoutConstraints((char) 0xd800));
                }
                break;
            case "consumeAsciiString":
                ret = consumeString((ConcolicObjectImpl) args[0], returnedObject, args[1], true, true);
                break;
            case "consumeRemainingAsAsciiString":
                ret = consumeString((ConcolicObjectImpl) args[0], returnedObject, Integer.MAX_VALUE, true, false);
                break;
            case "consumeString":
                ret = consumeString((ConcolicObjectImpl) args[0], returnedObject, args[1], false, true);
                break;
            case "consumeRemainingAsString":
                ret = consumeString((ConcolicObjectImpl) args[0], returnedObject, Integer.MAX_VALUE, false, false);
                break;
            case "consumeBooleans":
                ret = consumeIntegralArray((ConcolicObjectImpl) args[0], returnedObject, Boolean.class);
                break;
            case "consumeBytes":
            case "consumeRemainingAsBytes":
                ret = consumeIntegralArray((ConcolicObjectImpl) args[0], returnedObject, Byte.class);
                break;
            case "consumeShorts":
                ret = consumeIntegralArray((ConcolicObjectImpl) args[0], returnedObject, Short.class);
                break;
            case "consumeInts":
                ret = consumeIntegralArray((ConcolicObjectImpl) args[0], returnedObject, Integer.class);
                break;
            case "consumeLongs":
                ret = consumeIntegralArray((ConcolicObjectImpl) args[0], returnedObject, Long.class);
                break;
            // "remainingBytes", (char *)"()I", (void *)&RemainingBytes},
            case "<init>":
                reset();
            default:
                return ConcolicHelper.toConcolic(returnedObject);
        }
        if (ret == null || !returnedObject.equals(ret.getConcreteValue())) {
            if (Logger.compileLog) {
                Logger.WARNING("[Mismatch FDPHook] concolic:" + ret + ", concrete: " + returnedObject);
            }
            return ConcolicHelper.toConcolic(returnedObject);
        }
        if (Logger.compileLog) {
            if (!ret.isSymbolic()) {
                Logger.WARNING("[FDPHook] FDP return is not symbolic: " + ret);
            }
        }
        return ret;
    }

    public static int remainingBytes(ConcolicObjectImpl fdp) {
        StaticObject obj = fdp.getConcreteObject();
        ObjectKlass objKlass = (ObjectKlass) obj.getKlass();
        int ret = objKlass.getFieldTable()[4].getInt(obj);
        latestRemainingBytesMap.put(obj, ret);
        return ret;
    }

    public static int originalRemainingBytes(ConcolicObjectImpl fdp) {
        StaticObject obj = fdp.getConcreteObject();
        ObjectKlass objKlass = (ObjectKlass) obj.getKlass();
        return objKlass.getFieldTable()[2].getInt(obj);
    }

    public static int latestRemainingBytes(ConcolicObjectImpl fdp) {
        StaticObject obj = fdp.getConcreteObject();
        return latestRemainingBytesMap.containsKey(obj) ? latestRemainingBytesMap.get(obj) : originalRemainingBytes(fdp);
    }

    public static long dataPtr(ConcolicObjectImpl fdp) {
        StaticObject obj = fdp.getConcreteObject();
        ObjectKlass objKlass = (ObjectKlass) obj.getKlass();
        long ret = objKlass.getFieldTable()[3].getLong(obj);
        latestDataPtrMap.put(obj, ret);
        return ret;
    }

    public static long originalDataPtr(ConcolicObjectImpl fdp) {
        StaticObject obj = fdp.getConcreteObject();
        ObjectKlass objKlass = (ObjectKlass) obj.getKlass();
        return objKlass.getFieldTable()[1].getLong(obj);
    }

    public static long latestDataPtr(ConcolicObjectImpl fdp) {
        StaticObject obj = fdp.getConcreteObject();
        return latestDataPtrMap.containsKey(obj) ? latestDataPtrMap.get(obj) : originalDataPtr(fdp);
    }

    public static ConcolicLong consumeIntegralInRange(ConcolicObjectImpl fdp, ConcolicLong min, ConcolicLong max, Class<?> clazz) {
        ConcolicLong ret = consumeIntegral(fdp, clazz).ToLong();
        ConcolicLong range = max.Subtract(min).Add(ConcolicLong.createWithoutConstraints(1));
        return (min.getConcreteValue() != 0) ? ret.Modulo(range).Add(min) : ret;
    }

    public static ConcolicValueWrapper<?> consumeIntegral(ConcolicObjectImpl fdp, Class<?> clazz) {
        int byteSize;
        if (clazz == Boolean.class) {
            byteSize = 1;
        } else if (clazz == Byte.class) {
            byteSize = Byte.BYTES;
        } else if (clazz == Short.class) {
            byteSize = Short.BYTES;
        } else if (clazz == Integer.class) {
            byteSize = Integer.BYTES;
        } else if (clazz == Long.class) {
            byteSize = Long.BYTES;
        } else if (clazz == Float.class) {
            byteSize = Float.BYTES;
        } else if (clazz == Double.class) {
            byteSize = Double.BYTES;
        } else if (clazz == Character.class) {
            byteSize = Character.BYTES;
        } else {
            if (Logger.compileLog) {
                Logger.WARNING("[consumeIntegral] Invalid input");
            }
            return null;
        }

        long result = 0;
        BitVecExpr expr = null;
        ConcolicArrayObject arr = (ConcolicArrayObject) fdp.getOrCreateField(0);
        int cur = (int) (dataPtr(fdp) - originalDataPtr(fdp)) + latestRemainingBytes(fdp);
        int end = (int) (dataPtr(fdp) - originalDataPtr(fdp)) + remainingBytes(fdp);
        int index = cur;
        while (index > end) {
            index--;
            ConcolicValueWrapper<?> concolic = arr.getElement(index);
            BitVecExpr bitExpr = Z3Helper.mkExtract(7, 0, (BitVecExpr) concolic.getExprWithInit());
            result = (result << 8) | ((Number) concolic.getConcreteValue()).byteValue() & 0xFF; // compare unsigned
            expr = (expr == null) ? bitExpr : Z3Helper.mkConcat(expr, bitExpr);
        }
        if (clazz == Boolean.class) {
            ConcolicBoolean ret = new ConcolicBoolean();
            ret.setValueWithConstraints((result & 1) != 0, expr);
            return ret;
        } else if (clazz == Byte.class) {
            ConcolicByte ret = new ConcolicByte();
            ret.setValueWithConstraints((byte) result, expr);
            return ret;
        } else if (clazz == Short.class) {
            ConcolicShort ret = new ConcolicShort();
            ret.setValueWithConstraints((short) result, expr);
            return ret;
        } else if (clazz == Integer.class) {
            ConcolicInt ret = new ConcolicInt();
            ret.setValueWithConstraints((int) result, expr);
            return ret;
        } else if (clazz == Long.class) {
            ConcolicLong ret = new ConcolicLong();
            ret.setValueWithConstraints(result, expr);
            return ret;
        } else if (clazz == Float.class) {
            ConcolicFloat ret = new ConcolicFloat();
            ret.setValueWithConstraints(Float.intBitsToFloat((int) result), expr);
            return ret;
        } else if (clazz == Double.class) {
            ConcolicDouble ret = new ConcolicDouble();
            ret.setValueWithConstraints(Double.longBitsToDouble(result), expr);
            return ret;
        } else if (clazz == Character.class) {
            ConcolicChar ret = new ConcolicChar();
            ret.setValueWithConstraints((char) result, expr);
            return ret;
        } else {
            if (Logger.compileLog) {
                Logger.WARNING("[consumeIntegral] Invalid input");
            }
            return null;
        }
    }

    public static ConcolicValueWrapper<?> consumeIntegralArray(ConcolicObjectImpl fdp, Object returnedObject, Class<?> clazz) {
        int byteSize;
        if (clazz == Boolean.class) {
            byteSize = 1;
        } else if (clazz == Byte.class) {
            byteSize = Byte.BYTES;
        } else if (clazz == Short.class) {
            byteSize = Short.BYTES;
        } else if (clazz == Integer.class) {
            byteSize = Integer.BYTES;
        } else if (clazz == Long.class) {
            byteSize = Long.BYTES;
        } else if (clazz == Float.class) {
            byteSize = Float.BYTES;
        } else if (clazz == Double.class) {
            byteSize = Double.BYTES;
        } else if (clazz == Character.class) {
            byteSize = Character.BYTES;
        } else {
            if (Logger.compileLog) {
                Logger.WARNING("[consumeIntegralArray] Invalid input");
            }
            return null;
        }

        ConcolicArrayObject ret = (ConcolicArrayObject) ConcolicHelper.toConcolic(returnedObject);
        ConcolicArrayObject arr = (ConcolicArrayObject) fdp.getOrCreateField(0);
        int cur = (int) (dataPtr(fdp) - originalDataPtr(fdp));
        int length = ret.getSize().getConcreteValue();
        remainingBytes(fdp);
        for (int i = 0; i < length; i++) {
            long result = 0;
            BitVecExpr expr = null;
            int index = cur - (length - i) * byteSize;
            int elementIndex = index + byteSize;
            while (elementIndex > index) {
                elementIndex--;
                ConcolicValueWrapper<?> concolic = arr.getElement(elementIndex);
                BitVecExpr bitExpr = Z3Helper.mkExtract(7, 0, (BitVecExpr) concolic.getExprWithInit());
                result = (result << 8) | ((Number) concolic.getConcreteValue()).byteValue();    // compare signed
                expr = (expr == null) ? bitExpr : Z3Helper.mkConcat(expr, bitExpr);
            }
            ConcolicValueWrapper<?> retElement = ret.getElement(i);
            if (((Number) retElement.getConcreteValue()).longValue() != result) {
                if (Logger.compileLog) {
                    Logger.WARNING("[Mismatch consumeIntegralArray] concolic: " + retElement.getConcreteValue() + ", concrete: " + result);
                }
                continue;
            }
            retElement.setExpr(expr);
            ret.setElement(i, retElement);
        }
        return ret;
    }

    private static int countlOne(int ub) {
        if ((byte) ub == 0xFF) {
            return 8;
        }
        int inverted = (~ub) & 0xFF;
        return Integer.numberOfLeadingZeros(inverted) - 24;
    }

    private static int forceContinuationByte(int ub) {
        return (ub | (1 << 7)) & ~(1 << 6) & 0xFF;
    }

    private static final int K_TWO_BYTE_ZERO_LEADING_BYTE      = 0b1100_0000;
    private static final int K_TWO_BYTE_ZERO_CONTINUATION_BYTE = 0b1000_0000;
    private static final int K_THREE_BYTE_LOW_LEADING_BYTE     = 0b1110_0000;
    private static final int K_SURROGATE_LEADING_BYTE          = 0b1110_1101;

    public enum Utf8GenerationState {
        LeadingByte_Generic,
        LeadingByte_AfterBackslash,
        ContinuationByte_Generic,
        ContinuationByte_LowLeadingByte,
        FirstContinuationByte_LowLeadingByte,
        FirstContinuationByte_SurrogateLeadingByte,
        FirstContinuationByte_Generic,
        SecondContinuationByte_Generic,
        LeadingByte_LowSurrogate,
        FirstContinuationByte_LowSurrogate,
        SecondContinuationByte_HighSurrogate,
        SecondContinuationByte_LowSurrogate,
    }

    public static ConcolicValueWrapper<?> consumeString(ConcolicObjectImpl fdp, Object returnedObject, Object maxLengthObject, boolean asciiOnly, boolean stopOnBackslash) {
        ConcolicObjectImpl ret = (ConcolicObjectImpl) ConcolicHelper.toConcolic(returnedObject);
        ConcolicArrayObject retArr = (ConcolicArrayObject) ret.getOrCreateField(0);
        ConcolicArrayObject fdpArr = (ConcolicArrayObject) fdp.getOrCreateField(0);
        boolean isLatin1 = StringMethodHook.getCoder(ret) == 0x00;
        int retLength = retArr.getSize().getConcreteValue();
        long maxLength = (long) ((ConcolicInt) ConcolicHelper.toConcolic(maxLengthObject)).getConcreteValue();
        if (asciiOnly) {
            maxLength = Math.min(2 * maxLength, 2 * latestRemainingBytes(fdp));
        } else {
            maxLength = Math.min(6 * maxLength, 2 * latestRemainingBytes(fdp));
        }
        remainingBytes(fdp);

        int cur = (int) (latestDataPtr(fdp) - originalDataPtr(fdp));
        int dataEnd = (int) (dataPtr(fdp) - originalDataPtr(fdp));
        if (Logger.compileLog) {
            Logger.DEBUG("[consumeString] isLatin1: " + isLatin1 + ", cur: " + cur + ", dataEnd: " + dataEnd + ", maxLength: " + maxLength);
        }

        byte[] value = new byte[dataEnd - cur + 10];
        int valueLen = 0;
        BitVecExpr[] exprs = new BitVecExpr[dataEnd - cur + 10];
        Utf8GenerationState state = Utf8GenerationState.LeadingByte_Generic;
        boolean hasMultiByte = !isLatin1;
        int length = 0;

        outer:
        for (; length < maxLength && cur < dataEnd; ++cur) {
            ConcolicByte fdpCur = (ConcolicByte) fdpArr.getElement(cur);
            if (fdpArr == null) {
                if (Logger.compileLog) {
                    Logger.WARNING("[consumeString] fdpArr is null at " + cur);
                }
                break;
            }

            int uc = ((byte) fdpCur.getConcreteValue()) & 0xFF;
            BitVecExpr expr = (BitVecExpr) fdpCur.getExprWithInitInWidthUnsigned(8);
            if ((uc & (1 << 7)) == 0x80) {
                hasMultiByte = true;
            }
            if (asciiOnly) {
                uc &= 0x7F;
                expr = Z3Helper.mkBVAND(expr, Z3Helper.mkBV(0x7F, 8));
            }
            if (Logger.compileLog) {
                Logger.DEBUG("[consumeString] uc: " + uc + "(" + countlOne(uc) + "), length: " + length + ", cur: " + cur + ", state: " + state);
            }
            switch (state) {
                case LeadingByte_Generic: {
                    switch (asciiOnly ? 0 : countlOne(uc)) {
                        case 0: {
                            if (uc == 0) {
                                value[valueLen]   = (byte) K_TWO_BYTE_ZERO_LEADING_BYTE;
                                exprs[valueLen++] = expr;
                                ConcolicByte fdpNext = (ConcolicByte) fdpArr.getElement(cur + 1);
                                if (fdpNext == null) {
                                    if (Logger.compileLog) {
                                        Logger.WARNING("[consumeString] fdpArr is null at " + cur + 1);
                                    }
                                    continue;
                                }
                                uc   = K_TWO_BYTE_ZERO_CONTINUATION_BYTE;
                                expr = (BitVecExpr) fdpNext.getExprWithInitInWidthUnsigned(8);
                                hasMultiByte = true;
                            } else if (stopOnBackslash && uc == '\\') {
                                state = Utf8GenerationState.LeadingByte_AfterBackslash;
                                continue;
                            }
                            ++length;
                            break;
                        }
                        case 1: {
                            uc |= 1 << 6;
                            uc &= ~(1 << 5);
                            expr = Z3Helper.mkBVOR(expr, Z3Helper.mkBV(1 << 6, 8));
                            expr = Z3Helper.mkBVAND(expr, Z3Helper.mkBV(~(1 << 5), 8));
                        }
                        case 2: {
                            state = ((uc & 0b0001_1110) == 0)
                                    ? Utf8GenerationState.ContinuationByte_LowLeadingByte
                                    : Utf8GenerationState.ContinuationByte_Generic;
                            break;
                        }
                        default: {
                            uc &= ~(1 << 4);
                            expr = Z3Helper.mkBVAND(expr, Z3Helper.mkBV(~(1 << 4), 8));
                        }
                        case 3: {
                            if (uc == K_THREE_BYTE_LOW_LEADING_BYTE) {
                                state = Utf8GenerationState.FirstContinuationByte_LowLeadingByte;
                            } else if (uc == K_SURROGATE_LEADING_BYTE) {
                                state = Utf8GenerationState.FirstContinuationByte_SurrogateLeadingByte;
                            } else {
                                state = Utf8GenerationState.FirstContinuationByte_Generic;
                            }
                            break;
                        }
                    }
                    break;
                }
                case LeadingByte_AfterBackslash: {
                    if (uc != '\\') {
                        ++cur;
                        break outer;
                    }
                    state = Utf8GenerationState.LeadingByte_Generic;
                    ++length;
                    break;
                }
                case ContinuationByte_LowLeadingByte: {
                    uc = forceContinuationByte(uc);
                    expr = Z3Helper.mkBVOR(expr, Z3Helper.mkBV(1 << 7, 8));
                    expr = Z3Helper.mkBVAND(expr, Z3Helper.mkBV(~(1 << 6), 8));
                    byte prev = value[valueLen - 1];
                    if ((prev & 0xFF) != K_TWO_BYTE_ZERO_LEADING_BYTE
                            || uc != K_TWO_BYTE_ZERO_CONTINUATION_BYTE) {
                        prev |= 1 << 1;
                        value[valueLen - 1] = prev;
                        exprs[valueLen - 1] = Z3Helper.mkBVOR(
                                exprs[valueLen - 1], Z3Helper.mkBV(1 << 1, 8));
                    }
                    state = Utf8GenerationState.LeadingByte_Generic;
                    ++length;
                    break;
                }
                case ContinuationByte_Generic: {
                    uc = forceContinuationByte(uc);
                    expr = Z3Helper.mkBVOR(expr, Z3Helper.mkBV(1 << 7, 8));
                    expr = Z3Helper.mkBVAND(expr, Z3Helper.mkBV(~(1 << 6), 8));
                    state = Utf8GenerationState.LeadingByte_Generic;
                    ++length;
                    break;
                }
                case FirstContinuationByte_LowLeadingByte: {
                    uc = forceContinuationByte(uc);
                    expr = Z3Helper.mkBVOR(expr, Z3Helper.mkBV(1 << 7, 8));
                    expr = Z3Helper.mkBVAND(expr, Z3Helper.mkBV(~(1 << 6), 8));
                    uc |= 1 << 5;
                    expr = Z3Helper.mkBVOR(expr, Z3Helper.mkBV(1 << 5, 8));
                    state = Utf8GenerationState.SecondContinuationByte_Generic;
                    break;
                }
                case FirstContinuationByte_SurrogateLeadingByte: {
                    uc = forceContinuationByte(uc);
                    expr = Z3Helper.mkBVOR(expr, Z3Helper.mkBV(1 << 7, 8));
                    expr = Z3Helper.mkBVAND(expr, Z3Helper.mkBV(~(1 << 6), 8));
                    if ((uc & (1 << 5)) != 0) {
                        uc |= 1 << 5;
                        uc &= ~(1 << 4);
                        expr = Z3Helper.mkBVOR(expr, Z3Helper.mkBV(1 << 5, 8));
                        expr = Z3Helper.mkBVAND(expr, Z3Helper.mkBV(~(1 << 4), 8));
                        state = Utf8GenerationState.SecondContinuationByte_HighSurrogate;
                    } else {
                        state = Utf8GenerationState.SecondContinuationByte_Generic;
                    }
                    break;
                }
                case FirstContinuationByte_Generic: {
                    uc = forceContinuationByte(uc);
                    expr = Z3Helper.mkBVOR(expr, Z3Helper.mkBV(1 << 7, 8));
                    expr = Z3Helper.mkBVAND(expr, Z3Helper.mkBV(~(1 << 6), 8));
                    state = Utf8GenerationState.SecondContinuationByte_Generic;
                    break;
                }
                case SecondContinuationByte_HighSurrogate: {
                    uc = forceContinuationByte(uc);
                    expr = Z3Helper.mkBVOR(expr, Z3Helper.mkBV(1 << 7, 8));
                    expr = Z3Helper.mkBVAND(expr, Z3Helper.mkBV(~(1 << 6), 8));
                    state = Utf8GenerationState.LeadingByte_LowSurrogate;
                    ++length;
                    break;
                }
                case SecondContinuationByte_LowSurrogate:
                case SecondContinuationByte_Generic: {
                    uc = forceContinuationByte(uc);
                    expr = Z3Helper.mkBVOR(expr, Z3Helper.mkBV(1 << 7, 8));
                    expr = Z3Helper.mkBVAND(expr, Z3Helper.mkBV(~(1 << 6), 8));
                    state = Utf8GenerationState.LeadingByte_Generic;
                    ++length;
                    break;
                }
                case LeadingByte_LowSurrogate: {
                    uc = K_SURROGATE_LEADING_BYTE;
                    state = Utf8GenerationState.FirstContinuationByte_LowSurrogate;
                    break;
                }
                case FirstContinuationByte_LowSurrogate: {
                    uc = forceContinuationByte(uc);
                    uc |= (1 << 5) | (1 << 4);
                    expr = Z3Helper.mkBVOR(expr, Z3Helper.mkBV((1 << 5) | (1 << 4), 8));
                    state = Utf8GenerationState.SecondContinuationByte_LowSurrogate;
                    break;
                }
            }
            if (Logger.compileLog) {
                Logger.DEBUG("[consumeString] SET value[" + valueLen + "] = " + uc + ": " + expr);
            }
            if (valueLen >= value.length) {
                if (Logger.compileLog) {
                    Logger.WARNING("[consumeString] value.length is " + value.length);
                }
                continue;
            }
            value[valueLen]   = (byte) uc;
            exprs[valueLen++] = expr;
        }

        switch (state) {
            case SecondContinuationByte_LowSurrogate:
                value[--valueLen] = 0;
                // exprs[valueLen] = null;
            case FirstContinuationByte_LowSurrogate:
                value[--valueLen] = 0;
                // exprs[valueLen] = null;
            case LeadingByte_LowSurrogate:
                value[--valueLen] = 0;
                // exprs[valueLen] = null;
            case SecondContinuationByte_Generic:
            case SecondContinuationByte_HighSurrogate:
                value[--valueLen] = 0;
                // exprs[valueLen] = null;
            case ContinuationByte_Generic:
            case ContinuationByte_LowLeadingByte:
            case FirstContinuationByte_Generic:
            case FirstContinuationByte_LowLeadingByte:
            case FirstContinuationByte_SurrogateLeadingByte:
                value[--valueLen] = 0;
                // exprs[valueLen] = null;
            case LeadingByte_Generic:
            case LeadingByte_AfterBackslash:
                break;
        }

        String result;
        if (!hasMultiByte) {
            if (Logger.compileLog) {
                Logger.DEBUG("[UTF8 ascii]");
            }
            result = new String(value);
        } else if (isLatin1) {
            if (Logger.compileLog) {
                Logger.DEBUG("[UTF8 unicode]");
            }
            char[] unicode = convertToUnicode(value, exprs);
            result = new String(unicode);
        } else {
            if (Logger.compileLog) {
                Logger.DEBUG("[UTF16 unicode]");
            }
            char[] unicode = convertToUnicode(value, exprs);
            for (int i = 0; i < retLength; i += 2) {
                ConcolicByte fieldR = (ConcolicByte) retArr.getElement(i);
                ConcolicByte fieldL = (ConcolicByte) retArr.getElement(i + 1);
                int resultChar = (int) unicode[i / 2] & 0xffff;
                int concrete = (fieldL.getConcreteValue() & 0xff) << 8 | fieldR.getConcreteValue() & 0xff;
                if (resultChar != concrete) {
                    if (Logger.compileLog) {
                        Logger.WARNING("[Mismatch consumeString] concolic: " + resultChar + ", concrete: " + fieldR + fieldL);
                    }
                    return ret;
                }
                fieldR.setExpr(Z3Helper.mkBVAND(exprs[i / 2], Z3Helper.mkBV(0xFF, 8)));
                fieldL.setExpr(Z3Helper.mkBVLSHR(exprs[i / 2], Z3Helper.mkBV(8, 8)));
                retArr.setElement(i, fieldR);
                retArr.setElement(i + 1, fieldL);
            }
            if (Logger.compileLog) {
                Logger.DEBUG("[consumeString] RET: " + retArr);
            }
            return ret;
        }
        for (int i = 0; i < retLength; i++) {
            ConcolicByte field = (ConcolicByte) retArr.getElement(i);
            int resultChar = result.charAt(i) & 0xff;
            int concrete = (int) field.getConcreteValue() & 0xff;
            if (resultChar != concrete) {
                if (Logger.compileLog) {
                    Logger.WARNING("[Mismatch consumeString] concolic: " + resultChar + ", concrete: " + field);
                }
                return ret;
            }
            field.setExpr(exprs[i]);
            retArr.setElement(i, field);
        }
        if (Logger.compileLog) {
            Logger.DEBUG("[consumeString] RET: " + retArr);
        }
        return ret;
    }

    public static char[] convertToUnicode(byte[] bytes, BitVecExpr[] exprs) {
        char[] ret = new char[bytes.length];
        int ptr = 0;
        int i = 0;

        for (; i < bytes.length; i++) {
            int ch = bytes[ptr] & 0xFF;
            if(ch > 0x7F) { break; }
            ret[i] = (char) ch;
            ptr += 1;
        }

        for (; ptr < bytes.length; i++) {
            int ch = bytes[ptr] & 0xFF;
            int ch2, ch3;
            int length = -1;
            int result = 0;
            BitVecExpr expr = exprs[ptr];
            BitVecExpr expr2, expr3;
            switch ((ch >> 4) & 0xF) {
                default:
                    result = ch;
                    length = 1;
                    break;

                case 0x8: case 0x9: case 0xA: case 0xB: case 0xF:
                    /* Shouldn't happen. */
                    break;

                case 0xC: case 0xD:
                    /* 110xxxxx  10xxxxxx */
                    ch2 = bytes[ptr + 1] & 0xFF;
                    expr2 = exprs[ptr + 1];
                    if ((ch2 & 0xC0) == 0x80) {
                        int high_five = ch & 0x1F;
                        int low_six = ch2 & 0x3F;
                        result = (high_five << 6) + low_six;
                        length = 2;
                        expr = Z3Helper.mkBVAND(expr, Z3Helper.mkBV(0x1F, 8));
                        expr = Z3Helper.mkBVSHL(expr, Z3Helper.mkBV(6, 8));
                        expr = Z3Helper.mkBVOR(expr, expr2);
                        break;
                    }
                    break;

                case 0xE:
                    /* 1110xxxx 10xxxxxx 10xxxxxx */
                    ch2 = bytes[ptr + 1] & 0xFF;
                    ch3 = bytes[ptr + 2] & 0xFF;
                    expr2 = exprs[ptr + 1];
                    expr3 = exprs[ptr + 2];
                    if ((ch2 & 0xC0) == 0x80) {
                        if ((ch3 & 0xC0) == 0x80) {
                            int high_four = ch & 0x0f;
                            int mid_six = ch2 & 0x3f;
                            int low_six = ch3 & 0x3f;
                            result = (((high_four << 6) + mid_six) << 6) + low_six;
                            length = 3;
                            expr  = Z3Helper.mkBVAND(expr, Z3Helper.mkBV(0x0F, 8));
                            expr  = Z3Helper.mkBVSHL(expr, Z3Helper.mkBV(12, 8));
                            expr2 = Z3Helper.mkBVAND(expr, Z3Helper.mkBV(0x3F, 8));
                            expr2 = Z3Helper.mkBVSHL(expr, Z3Helper.mkBV(6, 8));
                            expr3 = Z3Helper.mkBVAND(expr, Z3Helper.mkBV(0x3F, 8));
                            expr  = Z3Helper.mkBVOR(expr, expr2);
                            expr  = Z3Helper.mkBVOR(expr, expr3);
                        }
                    }
                    break;

            } /* end of switch */
            // if (Logger.compileLog) {
            //     Logger.DEBUG("[convertToUnicode] i=" + i + ", ptr=" + ptr + ", ch=" + ch + ", result=" + result + ", length=" + length);
            // }
            if (length <= 0) {
                ret[i] = (char) ch;
                ptr += 1;
            } else {
                ret[i] = (char) result;
                ptr += length;
            }
            exprs[i] = expr;
        }
        return ret;
    }
}
