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
import com.oracle.truffle.espresso.concolic.ConcolicFunctionHook;
import com.oracle.truffle.espresso.impl.Method;
import com.oracle.truffle.espresso.nodes.bytecodes.InvokeInterface;
import com.oracle.truffle.espresso.nodes.bytecodes.InvokeInterfaceNodeGen;
import com.oracle.truffle.espresso.runtime.staticobject.StaticObject;
import com.oracle.truffle.api.concolic.*;
import com.microsoft.z3.*;

public final class InvokeInterfaceQuickNode extends InvokeQuickNode {

    @Child InvokeInterface.WithoutNullCheck invokeInterface;

    public InvokeInterfaceQuickNode(Method method, int top, int curBCI) {
        super(method, top, curBCI);
        assert !method.isStatic();
        this.invokeInterface = insert(InvokeInterfaceNodeGen.WithoutNullCheckNodeGen.create(method));
    }

    @Override
    public int execute(VirtualFrame frame, boolean isContinuationResume) {
        Object[] args = getArguments(frame);
        StaticObject receiver = (StaticObject) ConcolicHelper.toConcrete(args[0]);
        nullCheck(receiver);

        String methodName = method.getName().toString();
        String className = method.getDeclaringKlass().getName().toString();
        String method_signature = method.getRawSignature().toString();

        ConcolicFunctionHook.invokeHook(className, methodName, ConcolicFunctionHook.Type.INTERFACE, args[0], args, method_signature);
        Boolean shouldNotTrack = ConcolicFunctionHook.shouldNotTrackExpression(className, methodName);
        Expr<?>[] backupExpressions = null;
        if (shouldNotTrack) {
            backupExpressions = ConcolicFunctionHook.backupExpressions(args);
        }

        if (Logger.compileLog) {
            Logger.DEBUG("[" + invokeInterface + "] START");
        }
        Object result = invokeInterface.execute(args);
        if (Logger.compileLog) {
            Logger.DEBUG("[" + invokeInterface + "] END");
        }
        Object latestReturnValue = ConcolicUtils.latestReturnValue.get();

        if (shouldNotTrack) {
            ConcolicFunctionHook.restoreExpressions(args, backupExpressions);
        }
        if (latestReturnValue instanceof ConcolicValueWrapper<?> concolicValueWrapper) {
            if (result != concolicValueWrapper.getConcreteValue()) {
                throw new RuntimeException("[InvokeInterfaceQuickNode] Returned object is different from the latest return value " + result + " vs " + concolicValueWrapper.getConcreteValue());
            }
            latestReturnValue = ConcolicFunctionHook.returnHook(className, methodName, ConcolicFunctionHook.Type.INTERFACE, latestReturnValue, args[0], args, method_signature);
            return pushConcolicResult(frame, (ConcolicValueWrapper<?>) latestReturnValue);
        }
        else {
            if (result != latestReturnValue) {
                throw new RuntimeException("[InvokeInterfaceQuickNode] Returned object is different from the latest return value " + result + " vs " + ConcolicUtils.latestReturnValue.get());
            }
            latestReturnValue = ConcolicFunctionHook.returnHook(className, methodName, ConcolicFunctionHook.Type.INTERFACE, latestReturnValue, args[0], args, method_signature);
            if (latestReturnValue instanceof ConcolicValueWrapper<?>) {
                return pushConcolicResult(frame, (ConcolicValueWrapper<?>) latestReturnValue);
            } else {
                return pushResult(frame, latestReturnValue);
            }
        }
    }
}
