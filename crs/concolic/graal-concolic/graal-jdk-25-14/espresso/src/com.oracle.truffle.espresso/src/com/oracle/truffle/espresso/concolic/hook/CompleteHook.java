package com.oracle.truffle.espresso.concolic.hook;

import com.oracle.truffle.api.concolic.*;
import com.oracle.truffle.espresso.concolic.*;
import com.oracle.truffle.espresso.meta.Meta;
import com.oracle.truffle.espresso.runtime.staticobject.StaticObject;
import com.oracle.truffle.espresso.descriptors.*;
import com.oracle.truffle.espresso.vm.InterpreterToVM;
import com.oracle.truffle.espresso.impl.*;
import com.oracle.truffle.espresso.classfile.descriptors.*;

import java.util.HashSet;

public class CompleteHook {
    protected ConcolicValueWrapper<?>[] storedArguments;
    protected ConcolicValueWrapper<?>[] concreteArguments;

    static Symbols names = Symbols.fromExisting(new HashSet<>(), 1 << 12);
    static Symbols types = Symbols.fromExisting(new HashSet<>(), 1 << 12);

    public CompleteHook() {
        storedArguments = null;
        concreteArguments = null;
    }

    public static ConcolicValueWrapper<?> makeNonSymbolic(ConcolicValueWrapper<?> originalArgument) {
        // do nothing for now
        if (originalArgument instanceof ConcolicValue valueArgument) {
        } else if (originalArgument instanceof ConcolicArrayObject) {
        } else if (originalArgument instanceof ConcolicObjectImpl objectArgument) {
        } else if (originalArgument instanceof ConcolicObject objectArgument) {
        }
        return originalArgument;
    }

    public Object[] processArguments(Object[] args) {
        if (!(args instanceof ConcolicValueWrapper<?>[])) {
            throw new RuntimeException("Non-concolic object array passed to CompleteHook.processArguments");
        }

        storedArguments = (ConcolicValueWrapper<?>[]) args;
        concreteArguments = new ConcolicValueWrapper<?>[storedArguments.length];

        for (int i=0; i < concreteArguments.length; ++i) {
            // do nothing for now
            concreteArguments[i] = storedArguments[i];
        }

        return concreteArguments;
    }

    static Field calculateField(ConcolicObjectImpl impl, String name, String type) {
        return calculateField((StaticObject) impl.getConcreteValue(), name, type);
    }

    static Field calculateField(StaticObject impl, String name, String type) {
        return impl.getKlass().lookupField(
            names.getOrCreate(name),
            types.getOrCreate(type)
        );
    }

    static Object getField(ConcolicObjectImpl impl, Field field) {
        Object ret = (Object) ConcolicObjectImpl.getField(impl, field.getSlot());
        return ret;
    }

    // static Object getField(ConcolicObjectImpl impl, String name, String type) {
    //     Field field = calculateField(impl, name, type);
    //     return getField(impl, field);
    // }
}

