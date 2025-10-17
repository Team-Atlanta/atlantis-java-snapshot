/*
 * Copyright (c) 2017, 2020, Oracle and/or its affiliates. All rights reserved.
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
import com.oracle.truffle.espresso.classfile.JavaKind;
import com.oracle.truffle.espresso.impl.Method;
import com.oracle.truffle.espresso.nodes.EspressoFrame;
import com.oracle.truffle.espresso.nodes.methodhandle.MHInvokeGenericNode.MethodHandleInvoker;
import com.oracle.truffle.espresso.nodes.methodhandle.MethodHandleIntrinsicNode;
import com.oracle.truffle.espresso.runtime.staticobject.StaticObject;
import com.oracle.truffle.api.concolic.*;

public final class InvokeHandleNode extends InvokeQuickNode {
    @Child private MethodHandleIntrinsicNode intrinsic;
    private final boolean hasReceiver;
    private final int argCount;

    public InvokeHandleNode(Method method, MethodHandleInvoker invoker, int top, int curBCI) {
        super(method, top, curBCI);
        this.hasReceiver = !method.isStatic();
        this.intrinsic = insert(method.spawnIntrinsicNode(invoker));
        this.argCount = method.getParameterCount() + (method.isStatic() ? 0 : 1) + (method.isInvokeIntrinsic() ? 1 : 0);
    }

    @Override
    protected Object[] getArguments(VirtualFrame frame) {
        Object[] args = new Object[argCount];
        EspressoFrame.popBasicArgumentsWithArray(frame, top, method.getMethod().getParsedSignature(), hasReceiver, args);
        return args;
    }

    public ConcolicValueWrapper<?> processConcolicReturnValue(ConcolicValueWrapper<?> concolic, JavaKind kind) {
        switch (kind) {
            case Boolean:
                return concolic.ToLong().ToBoolean();
            case Byte:
                return concolic.ToLong().ToByte();
            case Char:
                return concolic.ToLong().ToChar();
            case Short:
                return concolic.ToLong().ToShort();
            case Float:
                return concolic.ToLong().ToFloat();
            case Int:
                return concolic.ToLong().ToInt();
            case Double:
                return concolic.ToLong().ToDouble();
            case Long:
                return concolic.ToLong();
            default:
                return concolic;
        }
    }

    @Override
    public int execute(VirtualFrame frame, boolean isContinuationResume) {
        Object[] args = getArguments(frame);
        if (hasReceiver) {
            nullCheck((StaticObject) ConcolicHelper.toConcrete(args[0]));
        }
        JavaKind kind = method.getMethod().getReturnKind();

        if (Logger.compileLog) {
            Logger.DEBUG("[" + intrinsic + "] START");
        }
        Object result = intrinsic.processReturnValue(intrinsic.call(args), kind);
        if (Logger.compileLog) {
            Logger.DEBUG("[" + intrinsic + "] END");
        }

        Object latestReturnValue = ConcolicUtils.latestReturnValue.get();
        if (latestReturnValue instanceof ConcolicValueWrapper<?> concolicValueWrapper) {
            concolicValueWrapper = processConcolicReturnValue(concolicValueWrapper, kind);
            if (!result.equals(concolicValueWrapper.getConcreteValue())) {
                throw new RuntimeException("[InvokeHandleNode] Returned object is different from the latest return value " + result + " vs " + concolicValueWrapper.getConcreteValue());
            }
            return pushConcolicResult(frame, concolicValueWrapper);
        }
        else {
            latestReturnValue = intrinsic.processReturnValue(latestReturnValue, kind);
            if (result != latestReturnValue) {
                throw new RuntimeException("[InvokeHandleNode] Returned object is different from the latest return value " + result + " vs " + latestReturnValue);
            }
            return pushResult(frame, result);
        }
    }
}
