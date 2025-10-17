package com.oracle.truffle.espresso.concolic;

import com.oracle.truffle.api.concolic.*;
import com.oracle.truffle.espresso.impl.Field;
import com.oracle.truffle.espresso.meta.Meta;
import com.oracle.truffle.espresso.runtime.staticobject.StaticObject;
import com.oracle.truffle.espresso.vm.InterpreterToVM;

public class ConcolicObjectFactory {
    static {
        ConcolicObject.createWithoutConstraintsImpl = ConcolicObjectFactory::createWithoutConstraints;
    }
    public static ConcolicObject createWithoutConstraints(Object object) {
        if (object == null) {
            return ConcolicObjectImpl.createWithoutConstraints(object);
        }
        if (object instanceof ConcolicValueWrapper<?> cv) {
            synchronized (Z3Helper.getInstance()) {
                throw new RuntimeException("Unexpected returnObject: " + cv);
            }
        }
        if (!(object instanceof StaticObject)) {
            return ConcolicObjectImpl.createWithoutConstraints(object);
        }
        if (object instanceof StaticObject staticObject) {
            if (staticObject.isArray()) {
                int size = staticObject.length(staticObject.getKlass().getMeta().getLanguage());
                return ConcolicObjectFactory.createWithoutConstraints(staticObject, ConcolicInt.createWithoutConstraints(size));
            } else {
                return ConcolicObjectImpl.createWithoutConstraints(staticObject);
            }
        }
        else {
            return ConcolicObjectImpl.createWithoutConstraints(object);
        }
    }

    public static ConcolicObject createWithoutConstraints(StaticObject staticObject, ConcolicInt size) {
        if (staticObject == null || !staticObject.isArray()) {
            return ConcolicObjectImpl.createWithoutConstraints(staticObject);
        }
        ConcolicArrayObject ret = new ConcolicArrayObject(staticObject, size);
        Object array = staticObject.unwrap(staticObject.getKlass().getMeta().getLanguage());
        for (int i=0; i<size.getConcreteValue(); i++) {
            ConcolicValueWrapper<?> concolic;
            if (array instanceof byte[] || array instanceof Byte[]) {
                concolic = ConcolicByte.createWithoutConstraints(((byte[]) array)[i]);
            } else if (array instanceof short[] || array instanceof Short[]) {
                concolic = ConcolicShort.createWithoutConstraints(((short[]) array)[i]);
            } else if (array instanceof int[] || array instanceof Integer[]) {
                concolic = ConcolicInt.createWithoutConstraints(((int[]) array)[i]);
            } else if (array instanceof long[] || array instanceof Long[]) {
                concolic = ConcolicLong.createWithoutConstraints(((long[]) array)[i]);
            } else if (array instanceof char[] || array instanceof Character[]) {
                concolic = ConcolicChar.createWithoutConstraints(((char[]) array)[i]);
            } else if (array instanceof float[] || array instanceof Float[]) {
                concolic = ConcolicFloat.createWithoutConstraints(((float[]) array)[i]);
            } else if (array instanceof double[] || array instanceof Double[]) {
                concolic = ConcolicDouble.createWithoutConstraints(((double[]) array)[i]);
            } else if (array instanceof boolean[] || array instanceof Boolean[]) {
                concolic = ConcolicBoolean.createWithoutConstraints(((boolean[]) array)[i]);
            } else if (array instanceof StaticObject[]) {
                concolic = ConcolicObjectFactory.createWithoutConstraints(((StaticObject[]) array)[i]);
            } else {
                System.out.println("Not supported type: ");
                throw new RuntimeException();
            }
            ret.setElement(i, concolic);
        }
        return ret;
    }

    public static ConcolicObject createNewSymbolic(StaticObject so) {
        if (StaticObject.isNull(so)) {
            return ConcolicObjectFactory.createWithoutConstraints(so);
        } else if (so.isArray()) {
            Meta meta = so.getKlass().getMeta();
            int size = so.length(meta.getLanguage());
            Object array = so.unwrap(meta.getLanguage());
            ConcolicArrayObject ret = new ConcolicArrayObject(so, ConcolicInt.createWithoutConstraints(size));
            for (int i=0; i<size; i++) {
                ConcolicValueWrapper<?> concolic;
                if (array instanceof byte[] || array instanceof Byte[]) {
                    concolic = ConcolicByte.createNewSymbolicByte(((byte[]) array)[i], i);
                } else if (array instanceof short[] || array instanceof Short[]) {
                    concolic = ConcolicShort.createNewSymbolicShort(((short[]) array)[i]);
                } else if (array instanceof int[] || array instanceof Integer[]) {
                    concolic = ConcolicInt.createNewSymbolicInt(((int[]) array)[i]);
                } else if (array instanceof long[] || array instanceof Long[]) {
                    concolic = ConcolicLong.createNewSymbolicLong(((long[]) array)[i]);
                } else if (array instanceof char[] || array instanceof Character[]) {
                    concolic = ConcolicChar.createWithoutConstraints(((char[]) array)[i]);
                } else if (array instanceof float[] || array instanceof Float[]) {
                    concolic = ConcolicFloat.createWithoutConstraints(((float[]) array)[i]);
                } else if (array instanceof double[] || array instanceof Double[]) {
                    concolic = ConcolicDouble.createWithoutConstraints(((double[]) array)[i]);
                } else if (array instanceof boolean[] || array instanceof Boolean[]) {
                    concolic = ConcolicBoolean.createWithoutConstraints(((boolean[]) array)[i]);
                } else if (array instanceof StaticObject[]) {
                    concolic = createNewSymbolic(((StaticObject[]) array)[i]);
                } else {
                    System.out.println("Not supported type");
                    throw new RuntimeException();
                }
                ret.setElement(i, concolic);
            }
            return ret;
        } else if (so.getKlass().getName().toString().endsWith("FuzzedDataProvider")
                || so.getKlass().getName().toString().endsWith("FuzzedDataProviderImpl")) {
            ConcolicObjectImpl ret = new ConcolicObjectImpl();
            ret.setValueWithoutConstraints(so);
            for (int i = 0; i < ret.getConcreteSize(); i++) {
                ConcolicValueWrapper<?> newField = null;
                Field concreteField = so.getKlass().lookupFieldTable(i);
                switch (concreteField.getKind()) {
                    // case Byte:
                    //     newField = ConcolicByte.createNewSymbolicByte(InterpreterToVM.getFieldByte(so, concreteField));
                    //     break;
                    // case Short:
                    //     newField = ConcolicShort.createNewSymbolicShort(InterpreterToVM.getFieldShort(so, concreteField));
                    //     break;
                    // case Int:
                    //     newField = ConcolicInt.createNewSymbolicInt(InterpreterToVM.getFieldInt(so, concreteField));
                    //     break;
                    // case Long:
                    //     newField = ConcolicLong.createNewSymbolicLong(InterpreterToVM.getFieldLong(so, concreteField));
                    //     break;
                    case Object: {
                        StaticObject fieldObject = InterpreterToVM.getFieldObject(so, concreteField);
                        if (fieldObject.isArray()) {
                            newField = createNewSymbolic(fieldObject);
                        }
                        break;
                    }
                    default:
                        break;
                }
                if (newField != null) {
                    ret.putField(i, newField);
                }
            }
            return ret;
        } else {
            return ConcolicObjectFactory.createWithoutConstraints(so);
        }
    }
}
