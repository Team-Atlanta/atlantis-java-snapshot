package com.oracle.truffle.espresso.concolic;

import com.oracle.truffle.api.concolic.*;
import com.oracle.truffle.espresso.EspressoLanguage;
import com.oracle.truffle.espresso.impl.Klass;
import com.oracle.truffle.espresso.impl.ArrayKlass;
import com.oracle.truffle.espresso.classfile.descriptors.Symbol;
import com.oracle.truffle.espresso.classfile.descriptors.Type;
import com.oracle.truffle.espresso.classfile.descriptors.Name;
import com.oracle.truffle.espresso.classfile.descriptors.Signature;
import com.oracle.truffle.espresso.classfile.JavaKind;
import com.oracle.truffle.espresso.impl.Field;
import com.oracle.truffle.espresso.impl.ObjectKlass;
import com.oracle.truffle.espresso.runtime.EspressoContext;
import com.oracle.truffle.espresso.runtime.staticobject.StaticObject;
import com.oracle.truffle.espresso.vm.InterpreterToVM;
import com.oracle.truffle.espresso.meta.Meta;
import com.microsoft.z3.*;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

public class ConcolicObjectImpl extends ConcolicObject {
    protected Field[] objFields;
    protected JavaKind[] kinds;
    protected boolean[] symbolicFlags;
    protected boolean hasSymbolic = false;
    protected Map<String, Object> extraDataMap;

    public static final String COLLECTION_ABSTRACT_KEY = "collection_abstract";
    public static final String COLLECTION_MAP_KEY = "collection_map";
    public static final String COLLECTION_EXIST_EXPR = "collection_exist_expr";

    // private static HashMap<Integer, ConcolicValueWrapper<?>[]> fieldsMap = new HashMap<Integer, ConcolicValueWrapper<?>[]>();

    // public static ConcolicValueWrapper<?>[] getFieldsFromMap(ConcolicObject obj) {

    //     if (obj == null) {
    //         Logger.DEBUG("OBJ NULL");
    //         return null;
    //     }
    //     if (obj.getConcreteValue() == null) {
    //         Logger.DEBUG("OBJ CONCRETE NULL");
    //         return null;
    //     }

    //     Integer key = Integer.valueOf(obj.getIdentityHashCode());

    //     Logger.DEBUG("Key: " + key + " Contains: " + fieldsMap.containsKey(key));

    //     ConcolicValueWrapper<?>[] returnFields = null;
    //     if (fieldsMap.containsKey(key)) {
    //         returnFields = fieldsMap.get(key);
    //         Logger.DEBUG("Existing field: " + System.identityHashCode(returnFields));
    //     } else {
    //         StaticObject staticObj = (StaticObject) obj.getConcreteValue();
    //         Klass klass = staticObj.getKlass();
    //         int size;
    //         if (klass == null) {
    //             size = 0;
    //         } else if (staticObj.isArray()) {
    //             size = staticObj.length(staticObj.getKlass().getMeta().getLanguage());
    //         } else if (klass instanceof ObjectKlass objKlass) {
    //             size = Math.max(objKlass.getFieldTable().length, objKlass.getStaticFieldTable().length);
    //         } else {
    //             System.err.println("Unsupported type: " + klass);
    //             throw new RuntimeException();
    //         }
    //         returnFields = new ConcolicValueWrapper<?>[size];
    //         setFieldsOnMap(obj, returnFields);
    //         Logger.DEBUG("New: " + System.identityHashCode(returnFields));
    //     }
    //     return returnFields;
    // }

    // public static void setFieldsOnMap(ConcolicObject obj, ConcolicValueWrapper<?>[] fields) {
    //     Integer key = Integer.valueOf(obj.getIdentityHashCode());
    //     Logger.DEBUG("Store new field: " + key + " : " + System.identityHashCode(fields));
    //     fieldsMap.put(key, fields);
    // }

    @Override
    public String toString() {
        synchronized (Z3Helper.getInstance()) {
            int len = this._fields != null ? this._fields.length : 0;
            String hash = Integer.toHexString(System.identityHashCode(this));
            StringBuilder fieldStr = new StringBuilder();
            if (isSymbolic() && this._fields != null) {
                int i = 0;
                int end = 10;
                fieldStr.append("{");
                for (; i < this._fields.length && i < end; i++) {
                    ConcolicValueWrapper<?> v = this._fields[i];
                    if (v != null && v.isSymbolic()) {
                        fieldStr.append("\n  [");
                        fieldStr.append(i);
                        fieldStr.append("] ");
                        // fieldStr.append(v);
                        fieldStr.append(v.getConcreteValue());
                        fieldStr.append("@");
                        fieldStr.append(Integer.toHexString(System.identityHashCode(v)));
                        if (v.getExpr() != null)  {
                            fieldStr.append(" ");
                            fieldStr.append(v.getExpr());
                        }
                        fieldStr.append(", ");
                    }
                }
                if (i == end) {
                    fieldStr.append("... ");
                }
                fieldStr.append("}");
            }
            if (!isInitialized())
                return "ConcolicObject(" + len + ", " + concrete_value + "@" + hash + ", " + fieldStr + ")";
            else if (isArray())
                return "ConcolicArray(" + len + ", " + concrete_value + "@" + hash + ", " + fieldStr + ") ";    // + this.getExpr();
            else if (isString())
                return "ConcolicString(" + len + ", " + concrete_value + "@" + hash + ", " + fieldStr + ") ";   // + this.getExpr();
            else if (isBoxed())
                return "ConcolicNumber(" + len + ", " + concrete_value + "@" + hash + ", " + fieldStr + ")";
            else if (isCollection())
                return "ConcolicCollection(" + len + ", " + concrete_value + "@" + hash + ", " + fieldStr + ")";
            else
                return "ConcolicObjectImpl(" + len + ", " + concrete_value + "@" + hash + ", " + fieldStr + ")";
        }
    }

    public ConcolicObjectImpl() {
        extraDataMap = new ConcurrentHashMap<String, Object>();
        targetClassName = "";
    }

    // @Override
    // public boolean isConcreteEqual(ConcolicValueWrapper<?> v) {
    //     if (v.getConcreteValue() instanceof StaticObject sv) {
    //         if (StaticObject.isNull(getConcreteObject())) {
    //             return StaticObject.isNull(sv);
    //         }
    //         return InterpreterToVM.referenceIdentityEqual(
    //                 getConcreteObject(), sv, getConcreteObject().getKlass().getContext().getLanguage());
    //     }
    //     return false;
    // }

    public StaticObject getConcreteObject() {
        return (StaticObject) getConcreteValue();
    }

    public AbstractCollection<ConcolicValueWrapper<?>> getAbstractCollection() {
        Object ret = getExtraData(COLLECTION_ABSTRACT_KEY);
        return ret != null ? (AbstractCollection<ConcolicValueWrapper<?>>) ret : null;
    }

    public AbstractMap<ConcolicValueWrapper<?>, ConcolicValueWrapper<?>> getMap() {
        Object ret = getExtraData(COLLECTION_MAP_KEY);
        return ret != null ? (AbstractMap<ConcolicValueWrapper<?>, ConcolicValueWrapper<?>>) ret : null;
    }

    public ArrayExpr<?, BoolSort> getExistExprWithInit(ConcolicValueWrapper<?> key) {
        Object ret = getExtraData(COLLECTION_EXIST_EXPR);
        if (ret == null) {
            ArrayExpr<?, BoolSort> existExpr = createNewSymbolicExistExpr(key);
            for (ConcolicValueWrapper<?> existingKey : getMap().keySet()) {
                if (existingKey.isBoxed()) {
                    existExpr = Z3Helper.mkStore((ArrayExpr<BitVecSort, BoolSort>) existExpr,
                            (BitVecExpr) existingKey.getExprWithInit(), Z3Helper.mkBool(true));
                } else if (existingKey.isString()) {
                    existExpr = Z3Helper.mkStore((ArrayExpr<SeqSort<BitVecSort>, BoolSort>) existExpr,
                            (SeqExpr<BitVecSort>) existingKey.getSeqExprWithInit(), Z3Helper.mkBool(true));
                } else {
                    if (Logger.compileLog) {
                        synchronized (Z3Helper.getInstance()) {
                            Logger.WARNING("Invalid: " + existingKey);
                        }
                        break;
                    }
                }
            }
            setExistExpr(existExpr);
            return existExpr;
        }
        return (ArrayExpr<?, BoolSort>) ret;
    }

    public void setExistExpr(ArrayExpr<?, BoolSort> expr) {
        putExtraData(COLLECTION_EXIST_EXPR, expr);
    }

    public Object getExtraData(String key) {
        int hashcode = this.getIdentityHashCode();
        if (Logger.compileLog) {
            Logger.DEBUG(String.format("getExtraData to %s from 0x%08x", key, hashcode));
        }
        return this.extraDataMap.get(key);
    }

    // returns true if the data is overwritten
    public boolean putExtraData(String key, Object obj) {
        boolean overwritten = this.extraDataMap.containsKey(key);
        this.extraDataMap.put(key, obj);
        int hashcode = this.getIdentityHashCode();
        if (Logger.compileLog) {
            Logger.DEBUG(String.format("putExtraData to %s from 0x%08x", key, hashcode));
        }

        return overwritten;
    }

    public ConcolicValueWrapper<?> getAs(JavaKind kind, int index) {
        if (Logger.compileLog) {
            Logger.DEBUG("getAs(" + kind + ", " + index + ")");
        }
        switch(kind) {
            case Boolean: return (ConcolicBoolean) getField(index);
            case Byte:    return (ConcolicByte) getField(index);
            case Char:    return (ConcolicChar) getField(index);
            case Int:     return (ConcolicInt) getField(index);
            case Long:    return (ConcolicLong) getField(index);
            case Float:   return (ConcolicFloat) getField(index);
            case Double:  return (ConcolicDouble) getField(index);
            case Short:   return (ConcolicShort) getField(index);
            default:
                if (Logger.compileLog) {
                    Logger.WARNING("Unknown getAs(" + kind + ", " + index + ")");
                }
                return getField(index);
        }
    }

    public void putAs(JavaKind kind, int index, ConcolicValueWrapper<?> v) {
        if (Logger.compileLog) {
            synchronized (Z3Helper.getInstance()) {
                Logger.DEBUG("putAs(" + kind + ", " + index + ", " + v + ")");
            }
        }
        JavaKind fieldKind = getFieldKind(index);
        if (fieldKind.equals(kind)) {
            putField(index, v);
            return;
        }
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
                if (Logger.compileLog) {
                    synchronized (Z3Helper.getInstance()) {
                        Logger.WARNING("Unknown putAs(" + kind + ", " + index + ", " + v + ")");
                    }
                }
        }
    }

    public static ConcolicObject createWithoutConstraints(Object value) {
        if (value instanceof ConcolicValue) {
            throw new RuntimeException("ConcolicValue couldn't be concrete value of ConcolicObject");
        }
        ConcolicObjectImpl ret = new ConcolicObjectImpl();
        ret.setValueWithoutConstraints(value);
        return ret;
    }

    public static String getConcreteClassName(Object o) {
        if (o == null) {
            return "ConcolicObjectImpl.NULL";
        }

        StaticObject staticObject = null;
        if (o instanceof ConcolicObject co) {
            staticObject = (StaticObject) co.getConcreteValue();
        } else if (o instanceof StaticObject so) {
            staticObject = so;
        } else {
            // not Concolic nor Static
            return o.getClass().getName().toString();
        }
        if (staticObject != null) {
            Klass klass = staticObject.getKlass();
            if (klass == null) {
                return "StaticObject.Klass.NULL";
            }
            Symbol<Name> name = klass.getName();
            if (name == null) {
                return "StaticObject.Klass.Name.NULL";
            } else {
                return name.toString();
            }
        } else {
            return "StaticObject.NULL";
        }
    }

    public String getConcreteStringValue() {
        if (this.concrete_value == null) {
            return "";  // null, but for Z3 seq building
        }
        if (!this.targetClassName.equals("java/lang/String")) {
            this.targetClassName = getConcreteClassName(this);
        }
        if (!this.targetClassName.equals("java/lang/String")) {
            return "";  // null, but for Z3 seq building
            //throw new RuntimeException("getConcreteStringValue() invoked for : " + this.targetClassName);
        }
        return Meta.toHostStringStatic((StaticObject) concrete_value);
    }

    public ConcolicValueWrapper<?> getConcreteFieldValue(int index) {
        if (index < 0 || _fields == null || this._fields.length <= index) {
            if (Logger.compileLog) {
                Logger.DEBUG("Wrong Index (" + index + ")");
            }
            return null;
        }
        StaticObject obj = getConcreteObject();
        Klass klass = obj.getKlass();
        if (obj.isArray()) {
            InterpreterToVM interpreterToVM = klass.getContext().getInterpreterToVM();
            EspressoLanguage language = klass.getMeta().getLanguage();
            switch (this.kinds[index]) {
                case Boolean:
                    return ConcolicBoolean.createWithoutConstraints(interpreterToVM.getArrayByte(language, index, obj) != 0);
                case Byte:
                    return ConcolicByte.createWithoutConstraints(interpreterToVM.getArrayByte(language, index, obj));
                case Char:
                    return ConcolicChar.createWithoutConstraints(interpreterToVM.getArrayChar(language, index, obj));
                case Short:
                    return ConcolicShort.createWithoutConstraints(interpreterToVM.getArrayShort(language, index, obj));
                case Int:
                    return ConcolicInt.createWithoutConstraints(interpreterToVM.getArrayInt(language, index, obj));
                case Long:
                    return ConcolicLong.createWithoutConstraints(interpreterToVM.getArrayLong(language, index, obj));
                case Float:
                    return ConcolicFloat.createWithoutConstraints(interpreterToVM.getArrayFloat(language, index, obj));
                case Double:
                    return ConcolicDouble.createWithoutConstraints(interpreterToVM.getArrayDouble(language, index, obj));
                case Object:
                    return ConcolicObjectFactory.createWithoutConstraints(interpreterToVM.getArrayObject(language, index, obj));
                default:
                    if (Logger.compileLog) {
                        Logger.WARNING("Unsupported type: " + this.kinds[index]);
                    }
                    return null;
            }
        } else if (klass instanceof ObjectKlass) {
            switch (this.kinds[index]) {
                case Boolean:
                    return ConcolicBoolean.createWithoutConstraints(InterpreterToVM.getFieldBoolean(obj, this.objFields[index]));
                case Byte:
                    return ConcolicByte.createWithoutConstraints(InterpreterToVM.getFieldByte(obj, this.objFields[index]));
                case Char:
                    return ConcolicChar.createWithoutConstraints(InterpreterToVM.getFieldChar(obj, this.objFields[index]));
                case Short:
                    return ConcolicShort.createWithoutConstraints(InterpreterToVM.getFieldShort(obj, this.objFields[index]));
                case Int:
                    return ConcolicInt.createWithoutConstraints(InterpreterToVM.getFieldInt(obj, this.objFields[index]));
                case Long:
                    return ConcolicLong.createWithoutConstraints(InterpreterToVM.getFieldLong(obj, this.objFields[index]));
                case Float:
                    return ConcolicFloat.createWithoutConstraints(InterpreterToVM.getFieldFloat(obj, this.objFields[index]));
                case Double:
                    return ConcolicDouble.createWithoutConstraints(InterpreterToVM.getFieldDouble(obj, this.objFields[index]));
                case Object:
                    return ConcolicObjectFactory.createWithoutConstraints(InterpreterToVM.getFieldObject(obj, this.objFields[index]));
                default:
                    if (Logger.compileLog) {
                        Logger.WARNING("Unsupported type: " + this.kinds[index]);
                    }
                    return null;
            }
        }
        if (Logger.compileLog) {
            Logger.WARNING("Unexpected state");
        }
        return null;
    }

    @Override
    public ConcolicValueWrapper<?> getOrCreateField(int index) {
        if (index < 0 || _fields == null || this._fields.length <= index) {
            if (Logger.compileLog) {
                Logger.DEBUG("Wrong ConcolicObject.getOrCreateField(" + index + ")");
            }
            return null;
        }
        if (this._fields[index] == null) {
            ConcolicValueWrapper<?> v = getConcreteFieldValue(index);
            if (v != null) {
                putField(index, v);
            }
        }
        return this._fields[index];
    }

    @Override
    public void setValueWithoutConstraints(Object value) {
        if (value instanceof ConcolicValue) {
            throw new RuntimeException("ConcolicValue couldn't be concrete value of ConcolicObject");
        }
        super.setValueWithoutConstraints(value);
        // if (getFieldsFromMap(this) == null) {
        assert concrete_value != null;
        assert concrete_value instanceof StaticObject;
        if (value == null || !(concrete_value instanceof StaticObject)) {
            return;
        }
        initialize();
    }

    public ConcolicObjectImpl clone() {
        try {
            EspressoContext ctx = getConcreteObject().getKlass().getMeta().getContext();
            ConcolicObjectImpl ret = (ConcolicObjectImpl) ConcolicObjectFactory.createWithoutConstraints(getConcreteObject().copy(ctx));
            //ConcolicObjectImpl ret = (ConcolicObjectImpl) ConcolicObjectFactory.createWithoutConstraints(getConcreteObject().clone());
            ret.setExpr(getExpr());
            return ret;
        } catch (Exception e) {
            if (Logger.compileLog) {
                synchronized (Z3Helper.getInstance()) {
                    Logger.WARNING("[ConcolicObjectImpl] Failed to clone() " + this);
                }
            }
            return null;
        }
    }

    public static Sort getSort(ConcolicValueWrapper<?> key) {
        if (key.isString()) {
            return Z3Helper.mkSeqSort(Z3Helper.mkBitVecSort(32));
        }
        if (getConcreteClassName(key).equals("Ljava/lang/Long;")) {
            return Z3Helper.mkBitVecSort(64);
        }
        return Z3Helper.mkBitVecSort(32);
    }

    public ArrayExpr<?, ?> createNewSymbolicMap(Sort keySort, Sort valSort) {
        String variableName = ConcolicValueHelper.getSymbolicMapName();
        return Z3Helper.mkArrayConst(variableName, keySort, valSort);
    }

    public ArrayExpr<?, BoolSort> createNewSymbolicExistExpr(ConcolicValueWrapper<?> key) {
        return Z3Helper.mkConstArray(getSort(key), Z3Helper.mkBool(false));
    }

    @Override
    public void setExpr(Expr<?> expr) {
        if (isBoxed() && expr != null) {
            getOrCreateField(0).setExpr(expr);
        } else {
            super.setExpr(expr);
        }
    }

    @Override
    public Expr<?> getExpr() {
        return !isSymbolic()
            ? null
            : isBoxed() ? getOrCreateField(0).getExpr() : super.getExpr();
    }

    @Override
    public Expr<?> getExprWithInit() {
        return isBoxed() ? getOrCreateField(0).getExprWithInit() : super.getExprWithInit();
    }

    public ArrayExpr<?, ?> getMapExprWithInit(Sort keySort, Sort valSort) {
        if (this.expr == null) {
            this.expr = createNewSymbolicMap(keySort, valSort);
        }
        return (ArrayExpr<?, ?>) this.expr;
    }

    public SeqExpr<?> getSeqExprWithInit() {
        if (this.expr == null) {
            if (isString()) {
                this.expr = SeqSupport.createStrSeqExpr(this, -1);
            } else if (isAbstractCollection()) {
                this.expr = SeqSupport.createSeqExpr(this, -1);
            }
        }
        return (SeqExpr<?>) this.expr;
    }

    public SeqExpr<?> getSeqExprWithInitInWidth(int width) {
        if (this.expr == null) {
            if (isString()) {
                this.expr = SeqSupport.createStrSeqExpr(this, width);
            } else if (isAbstractCollection()) {
                this.expr = SeqSupport.createSeqExpr(this, width);
            }
        }
        return (SeqExpr<?>) this.expr;
    }

    public boolean isArray() {
        return getConcreteObject().isArray();
    }

    @Override
    public boolean isString() {
        return isString(getConcreteObject().getKlass());
    }

    public static boolean isString(Klass klass) {
        return klass != null && klass == klass.getMeta().java_lang_String;
    }

    @Override
    public boolean isBoxed() {
        return isBoxed(getConcreteObject().getKlass());
    }

    public static boolean isBoxed(Klass klass) {
        return klass != null && klass.getMeta().isBoxed(klass);
    }

    public boolean isCollection() {
        return isList() || isSet() || isMap();
    }

    public boolean isAbstractCollection() {
        return isList() || isSet();
    }

    public boolean isList() {
        Klass klass = getConcreteObject().getKlass();
        return klass != null && klass.getMeta().java_util_AbstractList.checkOrdinaryClassSubclassing(klass);
    }

    public boolean isMap() {
        Klass klass = getConcreteObject().getKlass();
        return klass != null && klass.getMeta().java_util_AbstractMap.checkOrdinaryClassSubclassing(klass);
    }

    public boolean isSet() {
        Klass klass = getConcreteObject().getKlass();
        return klass != null && klass.getMeta().java_util_AbstractSet.checkOrdinaryClassSubclassing(klass);
    }

    private void initialize() {
        if (this.isInitialized) {
            return;
        }
        if (!(concrete_value instanceof StaticObject)) {
            return;
        }
        StaticObject obj = (StaticObject) concrete_value;
        Klass klass = obj.getKlass();
        targetClassName = getConcreteClassName(obj);
        if (Logger.compileLog) {
            Logger.DEBUG(String.format(
                    "[ConcolicObjectImpl] klass name: [%s]", targetClassName));
        }

        if (StaticObject.isNull(obj)) {
            this._fields = new ConcolicValueWrapper<?>[0];
        } else if (isArray()) {
            int size = obj.length(klass.getMeta().getLanguage());
            this._fields = new ConcolicValueWrapper<?>[size];
            this.symbolicFlags = new boolean[size];
            this.kinds = new JavaKind[size];
            for (int i=0; i < size; i++) {
                this.kinds[i] = klass.getElementalType().getJavaKind();
            }
        } else if (klass instanceof ObjectKlass objKlass) {
            this.objFields = obj.isStaticStorage() ? objKlass.getStaticFieldTable() : objKlass.getFieldTable();
            this._fields = new ConcolicValueWrapper<?>[this.objFields.length];
            this.symbolicFlags = new boolean[this.objFields.length];
            this.kinds = new JavaKind[this.objFields.length];
            for (int i=0; i < this.objFields.length; i++) {
                this.kinds[i] = this.objFields[i].getKind();
            }
            if (isList()) {
                putExtraData(COLLECTION_ABSTRACT_KEY, new ArrayList<ConcolicValueWrapper<?>>());
            } else if (isMap()) {
                putExtraData(COLLECTION_MAP_KEY, new HashMap<ConcolicValueWrapper<?>, ConcolicValueWrapper<?>>());
            } else if (isSet()) {
                putExtraData(COLLECTION_ABSTRACT_KEY, new HashSet<ConcolicValueWrapper<?>>());
            }
        } else {
            System.err.println("Unsupported type: " + klass);
            throw new RuntimeException();
        }
        this.isInitialized = true;
    }

    public static final ConcolicValueWrapper<?> getField(ConcolicObject obj, int offset) {
        if (obj == null) {
            if (Logger.compileLog) {
                synchronized (Z3Helper.getInstance()) {
                    Logger.DEBUG("getField [" + offset + "] from null: " + obj);
                }
            }
            return null;
        } else if (obj.getFields() == null) {
            if (Logger.compileLog) {
                synchronized (Z3Helper.getInstance()) {
                    Logger.DEBUG("getField [" + offset + "] from null: " + obj);
                }
            }
            ConcolicObject newObj = ConcolicObjectFactory.createWithoutConstraints((StaticObject) obj.getConcreteValue());
            newObj.setValueWithConstraints(obj.getConcreteValue(), obj.getExpr());
            obj = newObj;
        }
        return ((ConcolicObjectImpl) obj).getOrCreateField(offset);
    }

    public static final void putField(ConcolicObject obj, int offset, ConcolicValueWrapper<?> value) {
        if (obj == null) {
            if (Logger.compileLog) {
                synchronized (Z3Helper.getInstance()) {
                    Logger.DEBUG("putField [" + offset + "] from null: " + obj);
                }
            }
            return;
        } else if (obj.getFields() == null) {
            if (Logger.compileLog) {
                synchronized (Z3Helper.getInstance()) {
                    Logger.DEBUG("putField [" + offset + "] from null: " + obj);
                }
            }
            ConcolicObject newObj = ConcolicObjectFactory.createWithoutConstraints((StaticObject) obj.getConcreteValue());
            newObj.setValueWithConstraints(obj.getConcreteValue(), obj.getExpr());
            obj = newObj;
        }
        obj.putField(offset, value);
    }

    public final JavaKind getFieldKind(int index) {
        if (index < 0 || this.kinds == null || this.kinds.length <= index) {
            if (Logger.compileLog) {
                Logger.DEBUG("Wrong ConcolicObject.getFieldKind(" + index + ")");
            }
            return null;
        }
        return this.kinds[index];
    }

    @Override
    public final ConcolicValueWrapper<?> getField(int offset) {
        // ConcolicValueWrapper<?>[] fields = getFieldsFromMap(this);
        // return fields[offset];
        if (offset < 0 || _fields == null || this._fields.length <= offset) {
            if (Logger.compileLog) {
                Logger.DEBUG("Wrong ConcolicObject.getField(" + offset + ")");
            }
            return null;
        }
        if (Logger.compileLog) {
            if (this.isSymbolic()) {
                synchronized (Z3Helper.getInstance()) {
                    Logger.DEBUG("ConcolicObjectImpl@" + Integer.toHexString(System.identityHashCode(this)) + ".getField(" + offset + "): " + this._fields[offset]);
                }
            }
        }
        return this._fields[offset];
    }

    @Override
    public final void putField(int offset, ConcolicValueWrapper<?> value) {
        // ConcolicValueWrapper<?>[] fields = getFieldsFromMap(this);
        // fields[offset] = value;
        if (offset < 0 || _fields == null || this._fields.length <= offset) {
            if (Logger.compileLog) {
                Logger.DEBUG("Wrong ConcolicObject.getField(" + offset + ")");
            }
            return;
        }
        if (Logger.compileLog) {
            if (ConcolicValueHelper.eitherSymbolic(this, value)) {
                synchronized (Z3Helper.getInstance()) {
                    Logger.DEBUG("ConcolicObjectImpl@" + Integer.toHexString(System.identityHashCode(this)) +".putField(" + offset +", " + value + ")");
                }
            }
        }
        this._fields[offset] = value;
        value.setParent(this, offset);
        updateSymbolic(value.isSymbolic(), offset);
    }

    @Override
    public void updateSymbolic(boolean newSymbolic, int offset) {
        if (this.symbolicFlags[offset] != newSymbolic) {
            this.symbolicFlags[offset] = newSymbolic;
            boolean hasSymbolic = false;
            for (boolean b : this.symbolicFlags) {
                if (b) {
                    hasSymbolic = true;
                    break;
                }
            }
            if (this.hasSymbolic != hasSymbolic) {
                this.hasSymbolic = hasSymbolic;
                if (this.parent != null) {
                    this.parent.updateSymbolic(hasSymbolic, this.parentElementIdx);
                }
            }
        }
    }

    @Override
    public boolean isSymbolic() {
        return hasSymbolic;
    }

    @Override
    public void setNonSymbolic() {
        this.symbolicFlags = new boolean[this.symbolicFlags.length];
        this.expr = null;
        this.extraDataMap.clear();
        if (this.hasSymbolic != false) {
            this.hasSymbolic = false;
            if (this.parent != null) {
                this.parent.updateSymbolic(false, this.parentElementIdx);
            }
        }
    }

    public final int getFieldSize(int index) {
        return this.kinds[index] == null ? 0 : this.kinds[index].getByteCount();
    }

    public final int getConcreteSize() {
        return (this._fields == null) ? 0 : this._fields.length;
    }
}
