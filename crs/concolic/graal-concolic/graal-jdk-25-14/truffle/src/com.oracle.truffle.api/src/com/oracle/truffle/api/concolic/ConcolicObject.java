package com.oracle.truffle.api.concolic;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.Function;

public class ConcolicObject extends ConcolicValueWrapper<Object> implements ConcolicValue {

    public static Map<Integer, ConcolicObject> staticReceiverMap = new ConcurrentHashMap<>();

    public static void reset() {
        staticReceiverMap = new ConcurrentHashMap<>();
    }

    protected ConcolicValueWrapper<?>[] _fields = null;
    protected boolean isInitialized = false;

    protected String className = null;
    protected String targetClassName;

    public static Function<Object, ConcolicObject> createWithoutConstraintsImpl;

    public String getClassName() {
        if (concrete_value == null) {
            return "NULL_OBJECT";
        } else {
            return className;
        }
    }

    public boolean isInitialized() {
        return this.isInitialized;
    }

    public String getTargetClassName() {
        return this.targetClassName;
    }

    public ConcolicObject() {
        super();
    }


    public ConcolicValueWrapper<?>[] getFields() {
        //throw new RuntimeException("ConcolicObject.getFields is not implemented");
        return _fields;
    }

    public static ConcolicObject createWithoutConstraints(Object value) {
        // if (value instanceof ConcolicValue) {
        //     Logger.WARNING("ConcolicValue couldn't be concrete value of ConcolicObject");
        //     throw new RuntimeException();
        // }
        // ConcolicObject concolicObject = new ConcolicObject();
        // concolicObject.setValueWithoutConstraints(value);
        // return concolicObject;
        if (createWithoutConstraintsImpl == null) {
            if (value instanceof ConcolicValue) {
                throw new RuntimeException("ConcolicValue couldn't be concrete value of ConcolicObject");
            }
            ConcolicObject concolicObject = new ConcolicObject();
            concolicObject.setValueWithoutConstraints(value);
            return concolicObject;
        }
        try {
            return createWithoutConstraintsImpl.apply(value);
            // if (value instanceof ConcolicValue) {
            //     Logger.WARNING("ConcolicValue couldn't be concrete value of ConcolicObject");
            //     throw new RuntimeException();
            // }
            // ConcolicObject concolicObject = new ConcolicObject();
            // concolicObject.setValueWithoutConstraints(value);
            // return concolicObject;
        } catch (Exception e) {
            throw new RuntimeException("Failed to call ConcolicObjectImpl.createWithoutConstraints", e);
        }
    }

    @Override
    protected void calculateExpr() {
        // NOTE: I believe calculateExpr is not used in ConcolicObject
        throw new RuntimeException("ConcolicObject doesn't have expr");
    }

    public void setValueWithoutConstraints(Object value) {
        if (value instanceof ConcolicValue) {
            throw new RuntimeException("ConcolicValue couldn't be concrete value of ConcolicObject");
        }
        super.setValueWithoutConstraints(value);
        if (concrete_value != null) {
            // it is StaticObject...
            className = concrete_value.getClass().getName();
        }
    }

    public void updateSymbolic(boolean newSymbolic, int offset) {
        throw new RuntimeException("Invalid operation");
    }

    public ConcolicValueWrapper<?> getOrCreateField(int offset) {
        throw new RuntimeException("Invalid operation");
    }

    public ConcolicValueWrapper<?> getField(int offset) {
        throw new RuntimeException("Invalid operation");
    }

    public void putField(int offset, ConcolicValueWrapper<?> value) {
        throw new RuntimeException("Invalid operation");
    }

    public static boolean notNull(ConcolicObject cObj) {
        return !ConcolicObject.isNull(cObj);
    }

    public static boolean isNull(ConcolicObject cObj) {
        if (cObj == null) {
            return true;
        }
        if (cObj.getConcreteValue() == null) {
            return true;
        }
        return false;
    }

    public int getIdentityHashCode() {
        return System.identityHashCode(this.getConcreteValue());
    }
}
