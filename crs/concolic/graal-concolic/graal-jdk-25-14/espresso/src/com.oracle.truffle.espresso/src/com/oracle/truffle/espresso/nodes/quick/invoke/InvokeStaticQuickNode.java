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
import com.oracle.truffle.espresso.descriptors.EspressoSymbols.Names;
import com.oracle.truffle.espresso.impl.Method;
import com.oracle.truffle.espresso.nodes.EspressoRootNode;
import com.oracle.truffle.espresso.nodes.bytecodes.InvokeStatic;
import com.oracle.truffle.espresso.nodes.bytecodes.InvokeStaticNodeGen;
import com.oracle.truffle.espresso.vm.VM;
import com.oracle.truffle.api.concolic.ExposedMethods;
import com.oracle.truffle.api.concolic.*;
import java.util.Objects;
import com.microsoft.z3.*;
public final class InvokeStaticQuickNode extends InvokeQuickNode {

    @Child InvokeStatic invokeStatic;
    final boolean isDoPrivilegedCall;

    public InvokeStaticQuickNode(Method method, int top, int curBCI) {
        super(method, top, curBCI);
        assert method.isStatic();
        this.isDoPrivilegedCall = method.getMeta().java_security_AccessController.equals(method.getDeclaringKlass()) &&
                        Names.doPrivileged.equals(method.getName());
        this.invokeStatic = insert(InvokeStaticNodeGen.create(method));
    }

    @Override
    public int execute(VirtualFrame frame, boolean isContinuationResume) {
        // Support for AccessController.doPrivileged.
        if (isDoPrivilegedCall) {
            EspressoRootNode rootNode = (EspressoRootNode) getRootNode();
            if (rootNode != null) {
                // Put cookie in the caller frame.
                rootNode.setFrameId(frame, VM.GlobalFrameIDs.getID());
            }
        }

        Object[] args = getArguments(frame);

        // YJ: Hook at the start
        String methodName = method.getName().toString();
        String className = method.getDeclaringKlass().getName().toString();
        String classMethodName = className + "." + methodName;
        String method_signature = method.getRawSignature().toString();

        // invoke hook
        ConcolicFunctionHook.invokeHook(className, methodName, ConcolicFunctionHook.Type.STATIC, null, args, method_signature);
        Boolean shouldNotTrack = ConcolicFunctionHook.shouldNotTrackExpression(className, methodName);
        Expr<?>[] backupExpressions = null;
        if (shouldNotTrack) {
            backupExpressions = ConcolicFunctionHook.backupExpressions(args);
        }

        if (methodName.equals("graalSymbolizeInt")) {
            // graalSymbolizeInt call
            if (Logger.compileLog) {
                Logger.DEBUG("[InvokeStaticQuickNode] Call " + classMethodName);
                for (Object arg : args) {
                    Logger.DEBUG("[InvokeStaticQuickNode] Arg: " + arg.toString() + " class: " + arg.getClass().getName());
                }
            }
            ExposedMethods.graalSymbolizeInt((ConcolicInt) args[0], ((ConcolicObject) args[1]).getConcreteValue().toString());
        }
        else if (methodName.equals("printExprFromObject")) {
            // printExprFromObject call
            if (Logger.compileLog) {
                Logger.DEBUG("[InvokeStaticQuickNode] Call " + classMethodName);
                for (Object arg : args) {
                    Logger.DEBUG("[InvokeStaticQuickNode] Arg: " + arg.toString());
                }
            }
            ExposedMethods.printExprFromObject((ConcolicObject) args[0]);
        }

        if (Logger.compileLog) {
            Logger.DEBUG("[" + invokeStatic + "] START");
        }
        Object returnedObject = invokeStatic.execute(args);
        Object latestReturnValue = ConcolicUtils.latestReturnValue.get();

        if (shouldNotTrack) {
            ConcolicFunctionHook.restoreExpressions(args, backupExpressions);
        }

        if (Logger.compileLog) {
            Logger.DEBUG("[" + invokeStatic + "] END");
        }

        if (latestReturnValue instanceof ConcolicValueWrapper<?> concolicValueWrapper) {
            // Latest return value is a ConcolicValueWrapper
            if (returnedObject != concolicValueWrapper.getConcreteValue()) {
                throw new RuntimeException("[" + invokeStatic + "] Returned object is different from the latest return value " + returnedObject + " vs " + concolicValueWrapper.getConcreteValue());
            }

            // YJ: Hook before setting the result (after RETURN)
            latestReturnValue = ConcolicFunctionHook.returnHook(className, methodName, ConcolicFunctionHook.Type.STATIC, latestReturnValue, null, args, method_signature);

            return pushConcolicResult(frame, (ConcolicValueWrapper<?>) latestReturnValue);
        }
        else {
            // Latest return value is not a ConcolicValueWrapper: It is concrete value
            if (returnedObject != latestReturnValue) {
                throw new RuntimeException("[" + invokeStatic + "] Returned object is different from the latest return value " + returnedObject + " vs " + ConcolicUtils.latestReturnValue.get());
            }

            // YJ: Hook before setting the result (after RETURN)
            latestReturnValue = ConcolicFunctionHook.returnHook(className, methodName, ConcolicFunctionHook.Type.STATIC, latestReturnValue, null, args, method_signature);
            if (latestReturnValue instanceof ConcolicValueWrapper<?>) {
                return pushConcolicResult(frame, (ConcolicValueWrapper<?>) latestReturnValue);
            } else {
                return pushResult(frame, latestReturnValue);
            }
        }
    }

    public void initializeResolvedKlass() {
        invokeStatic.getStaticMethod().getDeclaringKlass().safeInitialize();
    }
}
