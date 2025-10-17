/*
 * Copyright (c) 2018, 2021, Oracle and/or its affiliates. All rights reserved.
 * DO NOT ALTER OR REMOVE COPYRIGHT NOTICES OR THIS FILE HEADER.
 *
 * This code is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License version 2 only, as
 * published by the Free Software Foundation.
 *
 * This code is distributed in the hope that it will be useful, but WITHOUT
 * ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 * FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
 * version 2 for more details (a copy is included in the LICENSE file that
 * accompanied this code).
 *
 * You should have received a copy of the GNU General Public License version
 * 2 along with this work; if not, write to the Free Software Foundation,
 * Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA.
 *
 * Please contact Oracle, 500 Oracle Parkway, Redwood Shores, CA 94065 USA
 * or visit www.oracle.com if you need additional information or have any
 * questions.
 */
package com.oracle.truffle.espresso.nodes.quick.invoke;

import com.oracle.truffle.api.frame.VirtualFrame;
import com.oracle.truffle.espresso.impl.Method;
import com.oracle.truffle.espresso.nodes.bytecodes.InvokeVirtual;
import com.oracle.truffle.espresso.nodes.bytecodes.InvokeVirtualNodeGen;
import com.oracle.truffle.espresso.runtime.staticobject.StaticObject;
import com.oracle.truffle.api.concolic.*;
import com.oracle.truffle.espresso.concolic.*;

import com.oracle.truffle.espresso.impl.Field;
import com.oracle.truffle.espresso.impl.Klass;
import com.oracle.truffle.espresso.impl.ObjectKlass;
import com.oracle.truffle.espresso.meta.Meta;
import com.oracle.truffle.espresso.runtime.EspressoContext;
import com.oracle.truffle.espresso.runtime.GuestAllocator;
import com.oracle.truffle.espresso.runtime.StringTable;
import com.oracle.truffle.espresso.substitutions.Substitutions;
import com.oracle.truffle.espresso.vm.InterpreterToVM;
import com.oracle.truffle.espresso.vm.VM;
import com.microsoft.z3.*;

public final class InvokeVirtualQuickNode extends InvokeQuickNode {

    @Child InvokeVirtual.WithoutNullCheck invokeVirtual;

    public InvokeVirtualQuickNode(Method method, int top, int curBCI) {
        super(method, top, curBCI);
        assert !method.isStatic();
        this.invokeVirtual = insert(InvokeVirtualNodeGen.WithoutNullCheckNodeGen.create(method));
    }

    @Override
    public int execute(VirtualFrame frame, boolean isContinuationResume) {
        Object[] args = getArguments(frame);
        StaticObject receiver = (StaticObject) ConcolicHelper.toConcrete(args[0]);
        nullCheck(receiver);

        Meta m = receiver.getKlass().getMeta();
        String methodName = method.getName().toString();
        String className = method.getDeclaringKlass().getName().toString();
        String funcName = className + "." + methodName;
        String method_signature = method.getRawSignature().toString();
        int hashCode = System.identityHashCode(receiver);
        if (Logger.compileLog) {
            Logger.DEBUG("[" + invokeVirtual + "] START");
        }
        // invoke hook
        ConcolicFunctionHook.invokeHook(className, methodName, ConcolicFunctionHook.Type.VIRTUAL, args[0], args, method_signature);
        Boolean shouldNotTrack = ConcolicFunctionHook.shouldNotTrackExpression(className, methodName);
        Expr<?>[] backupExpressions = null;
        if (shouldNotTrack) {
            backupExpressions = ConcolicFunctionHook.backupExpressions(args);
        }

        Object returnedObject = invokeVirtual.execute(args);
        if (Logger.compileLog) {
            Logger.DEBUG("[" + invokeVirtual + "] END");
        }
        Object latestReturnValue = ConcolicUtils.latestReturnValue.get();

        if (shouldNotTrack) {
            ConcolicFunctionHook.restoreExpressions(args, backupExpressions);
        }

        if (latestReturnValue instanceof ConcolicValueWrapper<?> concolicValueWrapper) {
            if (returnedObject != concolicValueWrapper.getConcreteValue()) {
                throw new RuntimeException("[InvokeVirtualQuickNode] Returned object is different from the latest return value " + returnedObject + " vs " + concolicValueWrapper.getConcreteValue());
            }
            latestReturnValue = ConcolicFunctionHook.returnHook(className, methodName, ConcolicFunctionHook.Type.VIRTUAL, latestReturnValue, args[0], args, method_signature);
            return pushConcolicResult(frame, (ConcolicValueWrapper<?>) latestReturnValue);
        }
        else {
            if (returnedObject != latestReturnValue) {
                throw new RuntimeException("[InvokeVirtualQuickNode] Returned object is different from the latest return value " + returnedObject + " vs " + ConcolicUtils.latestReturnValue.get());
            }
            latestReturnValue = ConcolicFunctionHook.returnHook(className, methodName, ConcolicFunctionHook.Type.VIRTUAL, latestReturnValue, args[0], args, method_signature);
            if (latestReturnValue instanceof ConcolicValueWrapper<?>) {
                return pushConcolicResult(frame, (ConcolicValueWrapper<?>) latestReturnValue);
            } else {
                return pushResult(frame, latestReturnValue);
            }
        }
    }
}
