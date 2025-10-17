package com.oracle.truffle.espresso.concolic.box;

import com.oracle.truffle.api.concolic.*;
import com.oracle.truffle.espresso.meta.Meta;
import com.oracle.truffle.espresso.runtime.staticobject.StaticObject;
import com.oracle.truffle.espresso.vm.InterpreterToVM;
import com.oracle.truffle.espresso.impl.*;
import com.oracle.truffle.espresso.classfile.descriptors.*;
import java.util.HashSet;

public class TopBox {
    static Symbols names = Symbols.fromExisting(new HashSet<>(), 1 << 12);
    static Symbols types = Symbols.fromExisting(new HashSet<>(), 1 << 12);
}
