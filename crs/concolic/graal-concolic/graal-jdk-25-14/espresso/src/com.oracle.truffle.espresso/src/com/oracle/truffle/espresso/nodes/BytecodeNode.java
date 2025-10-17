/*
 * Copyright (c) 2018, 2025, Oracle and/or its affiliates. All rights reserved.
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
package com.oracle.truffle.espresso.nodes;

import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.AALOAD;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.AASTORE;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.ACONST_NULL;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.ALOAD;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.ALOAD_0;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.ALOAD_1;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.ALOAD_2;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.ALOAD_3;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.ANEWARRAY;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.ARETURN;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.ARRAYLENGTH;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.ASTORE;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.ASTORE_0;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.ASTORE_1;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.ASTORE_2;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.ASTORE_3;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.ATHROW;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.BALOAD;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.BASTORE;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.BIPUSH;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.BREAKPOINT;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.CALOAD;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.CASTORE;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.CHECKCAST;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.D2F;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.D2I;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.D2L;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.DADD;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.DALOAD;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.DASTORE;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.DCMPG;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.DCMPL;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.DCONST_0;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.DCONST_1;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.DDIV;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.DLOAD;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.DLOAD_0;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.DLOAD_1;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.DLOAD_2;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.DLOAD_3;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.DMUL;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.DNEG;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.DREM;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.DRETURN;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.DSTORE;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.DSTORE_0;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.DSTORE_1;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.DSTORE_2;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.DSTORE_3;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.DSUB;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.DUP;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.DUP2;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.DUP2_X1;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.DUP2_X2;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.DUP_X1;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.DUP_X2;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.F2D;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.F2I;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.F2L;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.FADD;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.FALOAD;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.FASTORE;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.FCMPG;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.FCMPL;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.FCONST_0;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.FCONST_1;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.FCONST_2;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.FDIV;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.FLOAD;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.FLOAD_0;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.FLOAD_1;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.FLOAD_2;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.FLOAD_3;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.FMUL;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.FNEG;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.FREM;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.FRETURN;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.FSTORE;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.FSTORE_0;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.FSTORE_1;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.FSTORE_2;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.FSTORE_3;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.FSUB;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.GETFIELD;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.GETSTATIC;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.GOTO;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.GOTO_W;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.I2B;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.I2C;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.I2D;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.I2F;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.I2L;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.I2S;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.IADD;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.IALOAD;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.IAND;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.IASTORE;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.ICONST_0;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.ICONST_1;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.ICONST_2;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.ICONST_3;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.ICONST_4;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.ICONST_5;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.ICONST_M1;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.IDIV;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.IFEQ;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.IFGE;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.IFGT;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.IFLE;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.IFLT;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.IFNE;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.IFNONNULL;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.IFNULL;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.IF_ACMPEQ;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.IF_ACMPNE;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.IF_ICMPEQ;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.IF_ICMPGE;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.IF_ICMPGT;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.IF_ICMPLE;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.IF_ICMPLT;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.IF_ICMPNE;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.IINC;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.ILOAD;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.ILOAD_0;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.ILOAD_1;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.ILOAD_2;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.ILOAD_3;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.IMUL;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.INEG;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.INSTANCEOF;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.INVOKEDYNAMIC;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.INVOKEINTERFACE;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.INVOKESPECIAL;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.INVOKESTATIC;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.INVOKEVIRTUAL;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.IOR;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.IREM;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.IRETURN;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.ISHL;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.ISHR;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.ISTORE;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.ISTORE_0;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.ISTORE_1;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.ISTORE_2;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.ISTORE_3;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.ISUB;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.IUSHR;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.IXOR;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.JSR;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.JSR_W;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.L2D;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.L2F;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.L2I;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.LADD;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.LALOAD;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.LAND;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.LASTORE;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.LCMP;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.LCONST_0;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.LCONST_1;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.LDC;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.LDC2_W;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.LDC_W;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.LDIV;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.LLOAD;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.LLOAD_0;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.LLOAD_1;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.LLOAD_2;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.LLOAD_3;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.LMUL;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.LNEG;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.LOOKUPSWITCH;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.LOR;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.LREM;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.LRETURN;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.LSHL;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.LSHR;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.LSTORE;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.LSTORE_0;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.LSTORE_1;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.LSTORE_2;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.LSTORE_3;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.LSUB;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.LUSHR;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.LXOR;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.MONITORENTER;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.MONITOREXIT;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.MULTIANEWARRAY;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.NEW;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.NEWARRAY;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.NOP;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.POP;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.POP2;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.PUTFIELD;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.PUTSTATIC;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.QUICK;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.RET;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.RETURN;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.RETURN_VALUE;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.SALOAD;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.SASTORE;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.SIPUSH;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.SLIM_QUICK;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.SWAP;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.TABLESWITCH;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.THROW_VALUE;
import static com.oracle.truffle.espresso.classfile.bytecode.Bytecodes.WIDE;
import static com.oracle.truffle.espresso.nodes.EspressoFrame.clear;
import static com.oracle.truffle.espresso.nodes.EspressoFrame.createFrameDescriptor;
import static com.oracle.truffle.espresso.nodes.EspressoFrame.dup1;
import static com.oracle.truffle.espresso.nodes.EspressoFrame.dup2;
import static com.oracle.truffle.espresso.nodes.EspressoFrame.dup2x1;
import static com.oracle.truffle.espresso.nodes.EspressoFrame.dup2x2;
import static com.oracle.truffle.espresso.nodes.EspressoFrame.dupx1;
import static com.oracle.truffle.espresso.nodes.EspressoFrame.dupx2;
import static com.oracle.truffle.espresso.nodes.EspressoFrame.getBCI;
import static com.oracle.truffle.espresso.nodes.EspressoFrame.getLocalDouble;
import static com.oracle.truffle.espresso.nodes.EspressoFrame.getLocalFloat;
import static com.oracle.truffle.espresso.nodes.EspressoFrame.getLocalInt;
import static com.oracle.truffle.espresso.nodes.EspressoFrame.getLocalLong;
import static com.oracle.truffle.espresso.nodes.EspressoFrame.getLocalObject;
import static com.oracle.truffle.espresso.nodes.EspressoFrame.getLocalReturnAddress;
import static com.oracle.truffle.espresso.nodes.EspressoFrame.peekObject;
import static com.oracle.truffle.espresso.nodes.EspressoFrame.popDouble;
import static com.oracle.truffle.espresso.nodes.EspressoFrame.popFloat;
import static com.oracle.truffle.espresso.nodes.EspressoFrame.popInt;
import static com.oracle.truffle.espresso.nodes.EspressoFrame.popLong;
import static com.oracle.truffle.espresso.nodes.EspressoFrame.popObject;
import static com.oracle.truffle.espresso.nodes.EspressoFrame.popReturnAddressOrObject;
import static com.oracle.truffle.espresso.nodes.EspressoFrame.putDouble;
import static com.oracle.truffle.espresso.nodes.EspressoFrame.putFloat;
import static com.oracle.truffle.espresso.nodes.EspressoFrame.putInt;
import static com.oracle.truffle.espresso.nodes.EspressoFrame.putLong;
import static com.oracle.truffle.espresso.nodes.EspressoFrame.putObject;
import static com.oracle.truffle.espresso.nodes.EspressoFrame.putReturnAddress;
import static com.oracle.truffle.espresso.nodes.EspressoFrame.setBCI;
import static com.oracle.truffle.espresso.nodes.EspressoFrame.setLocalDouble;
import static com.oracle.truffle.espresso.nodes.EspressoFrame.setLocalFloat;
import static com.oracle.truffle.espresso.nodes.EspressoFrame.setLocalInt;
import static com.oracle.truffle.espresso.nodes.EspressoFrame.setLocalLong;
import static com.oracle.truffle.espresso.nodes.EspressoFrame.setLocalObject;
import static com.oracle.truffle.espresso.nodes.EspressoFrame.setLocalObjectOrReturnAddress;
import static com.oracle.truffle.espresso.nodes.EspressoFrame.startingStackOffset;
import static com.oracle.truffle.espresso.nodes.EspressoFrame.swapSingle;
import static com.oracle.truffle.espresso.nodes.EspressoFrame.*;

import java.io.Serial;
import java.util.Arrays;
import java.util.List;
import java.util.Locale;
import java.util.Objects;
import java.util.Set;
import java.util.concurrent.locks.Lock;
import java.util.concurrent.locks.ReentrantLock;
import java.util.HashMap;
import java.util.Map;

import com.oracle.truffle.api.Assumption;
import com.oracle.truffle.api.CompilerAsserts;
import com.oracle.truffle.api.CompilerDirectives;
import com.oracle.truffle.api.CompilerDirectives.CompilationFinal;
import com.oracle.truffle.api.CompilerDirectives.TruffleBoundary;
import com.oracle.truffle.api.HostCompilerDirectives.BytecodeInterpreterSwitch;
import com.oracle.truffle.api.Truffle;
import com.oracle.truffle.api.TruffleSafepoint;
import com.oracle.truffle.api.TruffleStackTrace;
import com.oracle.truffle.api.exception.AbstractTruffleException;
import com.oracle.truffle.api.frame.Frame;
import com.oracle.truffle.api.frame.FrameDescriptor;
import com.oracle.truffle.api.frame.VirtualFrame;
import com.oracle.truffle.api.instrumentation.GenerateWrapper.YieldException;
import com.oracle.truffle.api.instrumentation.InstrumentableNode;
import com.oracle.truffle.api.instrumentation.ProbeNode;
import com.oracle.truffle.api.instrumentation.StandardTags.StatementTag;
import com.oracle.truffle.api.instrumentation.Tag;
import com.oracle.truffle.api.interop.InteropLibrary;
import com.oracle.truffle.api.nodes.BytecodeOSRNode;
import com.oracle.truffle.api.nodes.ControlFlowException;
import com.oracle.truffle.api.nodes.ExplodeLoop;
import com.oracle.truffle.api.nodes.LoopNode;
import com.oracle.truffle.api.source.Source;
import com.oracle.truffle.api.source.SourceSection;
import com.oracle.truffle.espresso.EspressoLanguage;
import com.oracle.truffle.espresso.analysis.liveness.LivenessAnalysis;
import com.oracle.truffle.espresso.bytecode.MapperBCI;
import com.oracle.truffle.espresso.classfile.ExceptionHandler;
import com.oracle.truffle.espresso.classfile.JavaKind;
import com.oracle.truffle.espresso.classfile.attributes.BootstrapMethodsAttribute;
import com.oracle.truffle.espresso.classfile.attributes.LineNumberTableAttribute;
import com.oracle.truffle.espresso.classfile.bytecode.BytecodeLookupSwitch;
import com.oracle.truffle.espresso.classfile.bytecode.BytecodeStream;
import com.oracle.truffle.espresso.classfile.bytecode.BytecodeTableSwitch;
import com.oracle.truffle.espresso.classfile.bytecode.Bytecodes;
import com.oracle.truffle.espresso.classfile.bytecode.VolatileArrayAccess;
import com.oracle.truffle.espresso.classfile.constantpool.ClassConstant;
import com.oracle.truffle.espresso.classfile.constantpool.DoubleConstant;
import com.oracle.truffle.espresso.classfile.constantpool.DynamicConstant;
import com.oracle.truffle.espresso.classfile.constantpool.FloatConstant;
import com.oracle.truffle.espresso.classfile.constantpool.IntegerConstant;
import com.oracle.truffle.espresso.classfile.constantpool.LongConstant;
import com.oracle.truffle.espresso.classfile.constantpool.MethodHandleConstant;
import com.oracle.truffle.espresso.classfile.constantpool.MethodRefConstant;
import com.oracle.truffle.espresso.classfile.constantpool.MethodTypeConstant;
import com.oracle.truffle.espresso.classfile.constantpool.PoolConstant;
import com.oracle.truffle.espresso.classfile.constantpool.Resolvable;
import com.oracle.truffle.espresso.classfile.constantpool.StringConstant;
import com.oracle.truffle.espresso.classfile.descriptors.SignatureSymbols;
import com.oracle.truffle.espresso.classfile.descriptors.Symbol;
import com.oracle.truffle.espresso.classfile.descriptors.Type;
import com.oracle.truffle.espresso.classfile.perf.DebugCounter;
import com.oracle.truffle.espresso.constantpool.Resolution;
import com.oracle.truffle.espresso.constantpool.ResolvedDynamicConstant;
import com.oracle.truffle.espresso.constantpool.ResolvedWithInvokerClassMethodRefConstant;
import com.oracle.truffle.espresso.constantpool.RuntimeConstantPool;
import com.oracle.truffle.espresso.impl.ArrayKlass;
import com.oracle.truffle.espresso.impl.Field;
import com.oracle.truffle.espresso.impl.Klass;
import com.oracle.truffle.espresso.impl.Method;
import com.oracle.truffle.espresso.impl.Method.MethodVersion;
import com.oracle.truffle.espresso.impl.ObjectKlass;
import com.oracle.truffle.espresso.meta.EspressoError;
import com.oracle.truffle.espresso.meta.Meta;
import com.oracle.truffle.espresso.nodes.helper.EspressoReferenceArrayStoreNode;
import com.oracle.truffle.espresso.nodes.methodhandle.MHInvokeGenericNode.MethodHandleInvoker;
import com.oracle.truffle.espresso.nodes.quick.BaseQuickNode;
import com.oracle.truffle.espresso.nodes.quick.CheckCastQuickNode;
import com.oracle.truffle.espresso.nodes.quick.InstanceOfQuickNode;
import com.oracle.truffle.espresso.nodes.quick.QuickNode;
import com.oracle.truffle.espresso.nodes.quick.interop.ArrayLengthQuickNode;
import com.oracle.truffle.espresso.nodes.quick.interop.ByteArrayLoadQuickNode;
import com.oracle.truffle.espresso.nodes.quick.interop.ByteArrayStoreQuickNode;
import com.oracle.truffle.espresso.nodes.quick.interop.CharArrayLoadQuickNode;
import com.oracle.truffle.espresso.nodes.quick.interop.CharArrayStoreQuickNode;
import com.oracle.truffle.espresso.nodes.quick.interop.DoubleArrayLoadQuickNode;
import com.oracle.truffle.espresso.nodes.quick.interop.DoubleArrayStoreQuickNode;
import com.oracle.truffle.espresso.nodes.quick.interop.FloatArrayLoadQuickNode;
import com.oracle.truffle.espresso.nodes.quick.interop.FloatArrayStoreQuickNode;
import com.oracle.truffle.espresso.nodes.quick.interop.IntArrayLoadQuickNode;
import com.oracle.truffle.espresso.nodes.quick.interop.IntArrayStoreQuickNode;
import com.oracle.truffle.espresso.nodes.quick.interop.LongArrayLoadQuickNode;
import com.oracle.truffle.espresso.nodes.quick.interop.LongArrayStoreQuickNode;
import com.oracle.truffle.espresso.nodes.quick.interop.QuickenedGetFieldNode;
import com.oracle.truffle.espresso.nodes.quick.interop.QuickenedPutFieldNode;
import com.oracle.truffle.espresso.nodes.quick.interop.ReferenceArrayLoadQuickNode;
import com.oracle.truffle.espresso.nodes.quick.interop.ReferenceArrayStoreQuickNode;
import com.oracle.truffle.espresso.nodes.quick.interop.ShortArrayLoadQuickNode;
import com.oracle.truffle.espresso.nodes.quick.interop.ShortArrayStoreQuickNode;
import com.oracle.truffle.espresso.nodes.quick.invoke.InvokeContinuableNode;
import com.oracle.truffle.espresso.nodes.quick.invoke.InvokeDynamicCallSiteNode;
import com.oracle.truffle.espresso.nodes.quick.invoke.InvokeHandleNode;
import com.oracle.truffle.espresso.nodes.quick.invoke.InvokeInterfaceQuickNode;
import com.oracle.truffle.espresso.nodes.quick.invoke.InvokeQuickNode;
import com.oracle.truffle.espresso.nodes.quick.invoke.InvokeSpecialQuickNode;
import com.oracle.truffle.espresso.nodes.quick.invoke.InvokeStaticQuickNode;
import com.oracle.truffle.espresso.nodes.quick.invoke.InvokeVirtualQuickNode;
import com.oracle.truffle.espresso.nodes.quick.invoke.inline.InlinedMethodNode;
import com.oracle.truffle.espresso.runtime.EspressoContext;
import com.oracle.truffle.espresso.runtime.EspressoException;
import com.oracle.truffle.espresso.runtime.EspressoExitException;
import com.oracle.truffle.espresso.runtime.EspressoLinkResolver;
import com.oracle.truffle.espresso.runtime.GuestAllocator;
import com.oracle.truffle.espresso.runtime.staticobject.StaticObject;
import com.oracle.truffle.espresso.shared.resolver.CallKind;
import com.oracle.truffle.espresso.shared.resolver.CallSiteType;
import com.oracle.truffle.espresso.shared.resolver.FieldAccessType;
import com.oracle.truffle.espresso.shared.resolver.ResolvedCall;
import com.oracle.truffle.espresso.substitutions.standard.Target_java_lang_invoke_MethodHandleNatives.SiteTypes;
import com.oracle.truffle.espresso.vm.InterpreterToVM;
import com.oracle.truffle.espresso.vm.continuation.HostFrameRecord;
import com.oracle.truffle.espresso.vm.continuation.UnwindContinuationException;

import com.oracle.truffle.api.concolic.*;
import com.oracle.truffle.espresso.concolic.*;
import com.oracle.truffle.espresso.concolic.hook.SentinelHook;
import com.oracle.truffle.espresso.concolic.hook.StringMethodHook;

import com.oracle.truffle.espresso.bytecode.Opcodes;
import com.microsoft.z3.*;

import java.io.StringWriter;
import java.io.PrintWriter;

import com.oracle.truffle.api.nodes.Node;
import com.oracle.truffle.api.TruffleStackTraceElement;

import com.oracle.truffle.api.frame.FrameInstance;
import com.oracle.truffle.api.frame.FrameInstanceVisitor;

import java.util.ArrayList;

/**
 * Bytecode interpreter loop.
 *
 * Calling convention uses strict Java primitive types although internally the VM basic types are
 * used with conversions at the boundaries.
 *
 * <h3>Operand stack</h3>
 * <p>
 * The operand stack is implemented in a PE-friendly way, with the {@code top} of the stack index
 * being a local variable. With ad-hoc implementation there's no explicit pop operation. Each
 * bytecode is first processed/executed without growing or shrinking the stack and only then the
 * {@code top} of the stack index is adjusted depending on the bytecode stack offset.
 */
public final class BytecodeNode extends AbstractInstrumentableBytecodeNode implements BytecodeOSRNode, GuestAllocator.AllocationProfiler {

    private static final DebugCounter EXECUTED_BYTECODES_COUNT = DebugCounter.create("Executed bytecodes");
    private static final DebugCounter QUICKENED_BYTECODES = DebugCounter.create("Quickened bytecodes");
    private static final DebugCounter QUICKENED_INVOKES = DebugCounter.create("Quickened invokes (excluding INDY)");

    private static final byte TRIVIAL_UNINITIALIZED = -1;
    private static final byte TRIVIAL_NO = 0;
    private static final byte TRIVIAL_YES = 1;

    private static final int REPORT_LOOP_STRIDE = 1 << 8;

    static {
        assert Integer.bitCount(REPORT_LOOP_STRIDE) == 1 : "must be a power of 2";
    }

    // Nodes for bytecodes that were replaced with QUICK, indexed by the constant pool index
    // referenced by the bytecode.
    // Must not be of type QuickNode as it might be wrapped by instrumentation
    @Children private BaseQuickNode[] nodes = BaseQuickNode.EMPTY_ARRAY;
    @Children private BaseQuickNode[] sparseNodes = BaseQuickNode.EMPTY_ARRAY;

    /**
     * Ideally, we would want one such node per AASTORE bytecode. Unfortunately, the AASTORE
     * bytecode is a single byte long, so we cannot quicken it, and it is far too common to pay for
     * spawning the sparse nodes array.
     */
    @Child private volatile EspressoReferenceArrayStoreNode refArrayStoreNode;

    @CompilationFinal(dimensions = 1) //
    private final int[] stackOverflowErrorInfo;

    /**
     * Outer array should be seen and used as a {@code @CompilationFinal volatile} array, while
     * inner arrays can be seen as {@code final} arrays.
     */
    @CompilationFinal(dimensions = 2) //
    private volatile int[][] jsrBci = null;

    private final BytecodeStream bs;

    @CompilationFinal private EspressoRootNode rootNode;

    @Child private volatile InstrumentationSupport instrumentation;

    private final Assumption noForeignObjects;

    // Cheap profile for implicit exceptions e.g. null checks, division by 0, index out of bounds.
    // All implicit exception paths in the method will be compiled if at least one implicit
    // exception is thrown.
    @CompilationFinal private boolean implicitExceptionProfile;
    @CompilationFinal private boolean linkageExceptionProfile;

    private final LivenessAnalysis livenessAnalysis;

    private byte trivialBytecodesCache = -1;

    @CompilationFinal private Object osrMetadata;

    private final FrameDescriptor frameDescriptor;

    private final MethodVersion methodVersion;

    @CompilationFinal(dimensions = 1) private final byte[] code;
    private final int returnValueBci;
    private final int throwValueBci;

    public BytecodeNode(MethodVersion methodVersion) {
        CompilerAsserts.neverPartOfCompilation();
        Method method = methodVersion.getMethod();
        assert method.hasBytecodes();
        this.methodVersion = methodVersion;
        byte[] originalCode = method.getOriginalCode();
        byte[] customCode = Arrays.copyOf(originalCode, originalCode.length + 2);
        customCode[returnValueBci = originalCode.length] = (byte) Bytecodes.RETURN_VALUE;
        customCode[throwValueBci = originalCode.length + 1] = (byte) THROW_VALUE;
        this.code = customCode;
        this.bs = new BytecodeStream(code);
        this.stackOverflowErrorInfo = method.getSOEHandlerInfo();
        this.frameDescriptor = createFrameDescriptor(methodVersion.getMaxLocals(), methodVersion.getMaxStackSize());
        this.noForeignObjects = Truffle.getRuntime().createAssumption("noForeignObjects");
        this.implicitExceptionProfile = false;
        this.livenessAnalysis = methodVersion.getLivenessAnalysis();
        /*
         * The "triviality" is partially computed here since isTrivial is called from a compiler
         * thread where the context is not accessible.
         */
        this.trivialBytecodesCache = originalCode.length <= method.getContext().getEspressoEnv().TrivialMethodSize
                        ? TRIVIAL_UNINITIALIZED
                        : TRIVIAL_NO;
    }

    public FrameDescriptor getFrameDescriptor() {
        return frameDescriptor;
    }

    Source getSource() {
        return getMethodVersion().getMethod().getSource();
    }

    public SourceSection getSourceSectionAtBCI(int bci) {
        return getMethodVersion().getSourceSectionAtBCI(bci);
    }

    @ExplodeLoop
    private void initArguments(VirtualFrame frame) {
        Object[] arguments = frame.getConcolicArguments();
        for (int i=0; i < arguments.length; i++) {
            if (arguments[i] instanceof ConcolicObject co) {
                if (!co.isInitialized()) {
                    arguments[i] = ConcolicObjectFactory.createWithoutConstraints(co.getConcreteValue());
                }
            }
        }
        if (getMethodVersion().getMethod().isStatic()) {
            switch (getMethodVersion().getMethod().getName().toString()) {
                case "fuzzerTestOneInput", "startSymbolicExecutionBytes", "startSymbolicExecutionProvider": {
                    ConcolicExecutionManager.atStartSymbolicExecution(arguments);
                    break;
                }
            }
        }

        if (Logger.compileLog) {
            Logger.DEBUG("[initArgument]");
            for (int i=0; i<arguments.length; ++i) {
                Logger.DEBUG("arguments[" + i + "] class: " + arguments[i]);
            }
        }

        boolean hasReceiver = !getMethod().isStatic();
        int receiverSlot = hasReceiver ? 1 : 0;
        int curSlot = 0;
        if (hasReceiver) {
            if (arguments[0] instanceof ConcolicObject receiver) {
                assert ConcolicObject.notNull(receiver) : "null receiver in init arguments !";
                setLocalConcolicObject(frame, curSlot, receiver);
                checkNoForeignObjectAssumption((StaticObject)receiver.getConcreteValue());
                curSlot += JavaKind.Object.getSlotCount();
            } else {
                assert StaticObject.notNull((StaticObject) arguments[0]) : "null receiver in init arguments !";
                StaticObject receiver = (StaticObject) arguments[0];
                setLocalObject(frame, curSlot, receiver);
                checkNoForeignObjectAssumption(receiver);
                curSlot += JavaKind.Object.getSlotCount();
            }
        }

        Symbol<Type>[] methodSignature = getMethod().getParsedSignature();
        int argCount = SignatureSymbols.parameterCount(methodSignature);
        CompilerAsserts.partialEvaluationConstant(argCount);
        for (int i = 0; i < argCount; ++i) {
            Symbol<Type> argType = SignatureSymbols.parameterType(methodSignature, i);
            // @formatter:off
            if (arguments[i + receiverSlot] instanceof ConcolicValueWrapper<?> arg) {
                switch (argType.byteAt(0)) {
                    case 'Z' : setLocalConcolicBoolean(frame, curSlot, arg.ToLong().ToBoolean());        break;
                    case 'B' : setLocalConcolicByte(frame, curSlot, arg.ToLong().ToByte());        break;
                    case 'S' : setLocalConcolicShort(frame, curSlot, arg.ToLong().ToShort());        break;
                    case 'C' : setLocalConcolicChar(frame, curSlot, arg.ToLong().ToChar());        break;
                    case 'I' : setLocalConcolicInt(frame, curSlot, arg.ToLong().ToInt());        break;
                    case 'F' : setLocalConcolicFloat(frame, curSlot, arg.ToLong().ToFloat());      break;
                    case 'J' : setLocalConcolicLong(frame, curSlot, arg.ToLong()); ++curSlot; break;
                    case 'D' : setLocalConcolicDouble(frame, curSlot, arg.ToLong().ToDouble()); ++curSlot; break;
                    case '[' : // fall through
                    case 'L' : {
                               // Reference type.
                               setLocalConcolicObject(frame, curSlot, (ConcolicObject) arg);
                               checkNoForeignObjectAssumption(
                                       (StaticObject) arg.getConcreteValue());
                               break;
                    }
                    default :
                               CompilerDirectives.transferToInterpreterAndInvalidate();
                               throw EspressoError.shouldNotReachHere();
                }
            } else {
                switch (argType.byteAt(0)) {
                    case 'Z' : setLocalInt(frame, curSlot, ((boolean) arguments[i + receiverSlot]) ? 1 : 0); break;
                    case 'B' : setLocalInt(frame, curSlot, ((byte) arguments[i + receiverSlot]));            break;
                    case 'S' : setLocalInt(frame, curSlot, ((short) arguments[i + receiverSlot]));           break;
                    case 'C' : setLocalInt(frame, curSlot, ((char) arguments[i + receiverSlot]));            break;
                    case 'I' : setLocalInt(frame, curSlot, (int) arguments[i + receiverSlot]);               break;
                    case 'F' : setLocalFloat(frame, curSlot, (float) arguments[i + receiverSlot]);           break;
                    case 'J' : setLocalLong(frame, curSlot, (long) arguments[i + receiverSlot]);     ++curSlot; break;
                    case 'D' : setLocalDouble(frame, curSlot, (double) arguments[i + receiverSlot]); ++curSlot; break;
                    case '[' : // fall through
                    case 'L' : {
                       StaticObject argument = (StaticObject) arguments[i + receiverSlot];
                       setLocalObject(frame, curSlot, argument);
                       checkNoForeignObjectAssumption(argument);
                       break;
                    }
                    default :
                               CompilerDirectives.transferToInterpreterAndInvalidate();
                               throw EspressoError.shouldNotReachHere();
                }
            }
            // @formatter:on
            ++curSlot;
        }
    }

    // region continuation

    public void createContinuableNode(int bci, int top) {
        int opcode = bs.opcode(bci);
        if (opcode == QUICK && nodes[bs.readCPI2(bci)] instanceof InvokeContinuableNode) {
            return;
        }
        CompilerDirectives.transferToInterpreterAndInvalidate();
        for (;;) { // At most 2 iterations
            opcode = bs.volatileOpcode(bci);
            if (opcode == QUICK) {
                assert nodes[bs.readCPI2(bci)] instanceof InvokeQuickNode;
                InvokeQuickNode quick = (InvokeQuickNode) nodes[bs.readCPI2(bci)];
                // Atomically place a continuable node.
                while (!(quick instanceof InvokeContinuableNode)) {
                    InvokeContinuableNode icn = new InvokeContinuableNode(top, bci, quick);
                    quick = (InvokeQuickNode) replaceQuickAt(opcode, bci, quick, icn);
                }
                return;
            } else {
                InstrumentationSupport instrument = instrumentation;
                int statementIndex = instrument == null ? InstrumentationSupport.NO_STATEMENT : instrument.getStartStatementIndex(bci);
                quickenInvoke(top, bci, opcode, statementIndex);
                // continue loop, will execute at most once more.
            }
        }
    }

    /**
     * Entry point for rewinding continuations.
     * <p>
     * The first executed {@code bci} goes to a special {@link InvokeContinuableNode}, which handles
     * frame restoration and re-winding of further frames. Further executions of this node delegates
     * to a regular invoke node.
     */
    @Override
    public Object resumeContinuation(VirtualFrame frame, int bci, int top) {
        CompilerAsserts.partialEvaluationConstant(bci);
        CompilerAsserts.partialEvaluationConstant(top);

        // Ensure the InvokeContinuableNode for this BCI is spawned.
        createContinuableNode(bci, top);

        // set up local state.
        InstrumentationSupport instrument = instrumentation;
        int statementIndex = instrument == null ? InstrumentationSupport.NO_STATEMENT : instrument.getStartStatementIndex(bci);
        assert bs.opcode(bci) == QUICK && nodes[bs.readCPI2(bci)] instanceof InvokeContinuableNode;

        return executeBodyFromBCI(frame, bci, top, statementIndex, true, true);
    }

    // endregion continuation

    public void checkNoForeignObjectAssumption(StaticObject object) {
        if (noForeignObjects.isValid() && object.isForeignObject()) {
            CompilerDirectives.transferToInterpreterAndInvalidate();
            noForeignObjects.invalidate();
        }
    }

    @Override
    void initializeFrame(VirtualFrame frame) {
        // Before arguments are set up, the frame is in a weird spot in which inspecting the frame
        // is pretty meaningless. Return the 'Unknown bci' value to signify that.
        setBCI(frame, -1);
        // Push frame arguments into locals.
        initArguments(frame);
        // Initialize the BCI slot.
        setBCI(frame, 0);

        // Dump concrete values of arguments
        Validator.dumpConcreateArguments(frame, getMethod());
    }

    // region OSR support

    private static final class EspressoOSRInterpreterState {
        // The index of the top of the stack. At a back-edge, it is typically 0, but the JVM spec
        // does not guarantee this.
        final int top;
        // The statement index of the next instruction (if instrumentation is enabled).
        final int statementIndex;

        EspressoOSRInterpreterState(int top, int statementIndex) {
            this.top = top;
            this.statementIndex = statementIndex;
        }
    }

    @SuppressWarnings("serial")
    public static final class EspressoOSRReturnException extends ControlFlowException implements YieldException {
        private final Object result;
        private final Throwable throwable;

        EspressoOSRReturnException(Object result) {
            this.result = result;
            this.throwable = null;
        }

        public EspressoOSRReturnException(Throwable throwable) {
            this.result = null;
            this.throwable = throwable;
        }

        Object getResultOrRethrow() {
            if (throwable != null) {
                throw sneakyThrow(throwable);
            }
            return result;
        }

        @SuppressWarnings("unchecked")
        private static <T extends Throwable> RuntimeException sneakyThrow(Throwable ex) throws T {
            throw (T) ex;
        }

        @Override
        public Object getYieldValue() {
            return null;
        }
    }

    @Override
    public Object executeOSR(VirtualFrame osrFrame, int target, Object interpreterState) {
        EspressoOSRInterpreterState state = (EspressoOSRInterpreterState) interpreterState;
        return executeBodyFromBCI(osrFrame, target, state.top, state.statementIndex, true, false);
    }

    @Override
    public Object getOSRMetadata() {
        return osrMetadata;
    }

    @Override
    public void setOSRMetadata(Object osrMetadata) {
        this.osrMetadata = osrMetadata;
    }

    @Override
    public void prepareOSR(int target) {
        getRoot(); // force initialization of root node since we need it in OSR
    }

    @Override
    public void copyIntoOSRFrame(VirtualFrame frame, VirtualFrame parentFrame, int target, Object entryMetadata) {
        BytecodeOSRNode.super.copyIntoOSRFrame(frame, parentFrame, target, entryMetadata);
        setBCI(frame, target);
    }

    @Override
    public void restoreParentFrame(VirtualFrame osrFrame, VirtualFrame parentFrame) {
        BytecodeOSRNode.super.restoreParentFrame(osrFrame, parentFrame);
        setBCI(parentFrame, getBci(osrFrame));
    }

    // endregion OSR support

    /**
     * Smaller than int[1], does not kill int[] on write and doesn't need bounds checks.
     */
    private static final class Counter {
        int value;
    }

    private Object[] retrieveSwitchTarget(  VirtualFrame frame,
                                            BytecodeLookupSwitch switchHelper,
                                            int jumpOffset) {
        try {
            int aloadInstruction = -1;
            int aloadOffset = -1;
            Object[] ret = new Object[2];

            // skipping nops
            while (aloadInstruction <= 0) {
                ++aloadOffset;
                aloadInstruction = bs.opcode(jumpOffset + aloadOffset);
            }
            aloadOffset = jumpOffset + aloadOffset;
            aloadInstruction = bs.opcode(aloadOffset);
            if (Logger.compileLog) {
                Logger.DEBUG("Aload: " + aloadInstruction + " offset: " + aloadOffset);
            }
            int ldcOffset = -1;
            if (aloadInstruction == ALOAD) {        // 1 byte index
                ret[0] = getLocalConcolicObject(frame, bs.readLocalIndex2(aloadOffset));
                ldcOffset = aloadOffset + 2;
            } else if (aloadInstruction >= ALOAD_0 && aloadInstruction <= ALOAD_3) {
                int objectIndex = aloadInstruction - ALOAD_0;
                ret[0] = getLocalConcolicObject(frame, objectIndex);
                ldcOffset = aloadOffset + 1;
            } else if (aloadInstruction == ACONST_NULL) {
                // no index
                ret[0] = null;
                ldcOffset = aloadOffset + 1;
            } else {
                if (Logger.compileLog) {
                    Logger.DEBUG("Not ALOAD/ACONST! " + aloadInstruction);
                }
                return null;
            }
            int ldcInstruction = bs.opcode(ldcOffset);
            char cpi = (char)-1;

            if (ldcInstruction == LDC) {            // 1 byte index
                cpi = bs.readCPI1(ldcOffset);
            } else if (ldcInstruction == LDC_W || ldcInstruction == LDC2_W) {   // 2 byte index
                cpi = bs.readCPI2(ldcOffset);
            } else {
                if (Logger.compileLog) {
                    Logger.DEBUG("Not LDC/LDC_W! " + ldcInstruction);
                    return null;
                }
            }
            if (Logger.compileLog) {
                Logger.DEBUG("LDC: " + ldcInstruction + " offset: " + ldcOffset + " cpi " + (int)cpi);
            }
            RuntimeConstantPool pool = getConstantPool();
            PoolConstant constant = pool.at(cpi);
            if (constant instanceof StringConstant) {
                StaticObject internedString = pool.resolvedStringAt(cpi);
                if (Logger.compileLog) {
                    Logger.DEBUG("Constant: " + internedString);
                }
                ConcolicObject constantString = ConcolicObjectFactory.createWithoutConstraints(internedString);
                ret[1] = constantString;
                return ret;
            } else {
                if (constant != null) {
                    if (Logger.compileLog) {
                        Logger.DEBUG("Not a string constant: " + constant.getClass().getName().toString());
                    }
                } else {
                    if (Logger.compileLog) {
                        Logger.DEBUG("Constant is null!");
                    }
                }
                return null;
            }
        } catch (java.lang.ArrayIndexOutOfBoundsException e) {
            return null;
        }
    }

    @Override
    public Object execute(VirtualFrame frame) {
        int startTop = startingStackOffset(getMethodVersion().getMaxLocals());
        if (methodVersion.hasJsr()) {
            getLanguage().getThreadLocalState().blockContinuationSuspension();
        }
        try {
            int statementIndex = instrumentation == null ? InstrumentationSupport.NO_STATEMENT : instrumentation.getStartStatementIndex(0);
            // return executeBodyFromBCI(frame, 0, startTop, statementIndex, false, false);

            // YJ: Timeout exception routine that waits until <clinit> finishes

            // 1. Store the return value
            Object ret = executeBodyFromBCI(frame, 0, startTop, statementIndex, false, false);

            // 2. Check if timeout is triggered
            if (com.oracle.truffle.api.concolic.Config.getInstance().getTimeoutInterrupted()) {
                // 3. get guest stack trace
                ArrayList<String> callTargets = new ArrayList<>();
                Truffle.getRuntime().iterateFrames(new FrameInstanceVisitor<Void>() {
                    @Override
                    public Void visitFrame(FrameInstance frameInstance) {
                        callTargets.add(frameInstance.getCallTarget().toString());
                        return null; // or break after first, etc.
                    }
                });

                // flags
                boolean classLoaderExists = false;
                boolean startSymbolicExecutionExists = false;
                boolean clinitExists = false;

                for (int i=callTargets.size()-1; i>=0; --i) {
                    String callTarget = callTargets.get(i);
                    // has clinit? then do not raise an exception
                    if (callTarget.contains("clinit")) {
                        clinitExists = true;
                        break;
                    }
                    // has startSymbolicExecution?
                    if (callTarget.contains("startSymbolicExecution") || callTarget.contains("fuzzerTestOneInput")) {
                        // must be executed
                        startSymbolicExecutionExists = true;
                    }
                }

                // 4. if no <clinit> on the stack trace and startSymbolicExecution has been invoked, STOP!
                if (!clinitExists && startSymbolicExecutionExists) {
                    System.out.println("Status: clinitExists=" + clinitExists + ", startSymbolicExecutionExists=" + startSymbolicExecutionExists);
                    for (String callTarget : callTargets) {
                        System.out.println("Method: " + callTarget);
                    }
                    throw new RuntimeException("STOP!");
                }
            }
            return ret;
        } finally {
            if (methodVersion.hasJsr()) {
                getLanguage().getThreadLocalState().unblockContinuationSuspension();
            }
        }
    }

    String[] getOpcodeLocation(int curBCI) {
        String className = methodVersion.getKlassVersion().getKlass().getName().toString();
        String methodName = methodVersion.getName().toString();
        Method method = methodVersion.getMethod();
        String methodSignature = method.getRawSignature().toString();
        // signature?
        //String combined = className + "." + methodName + ":" + curBCI;
        String[] triplet = new String[3];
        triplet[0] = className;
        triplet[1] = methodName + methodSignature;
        triplet[2] = "" + curBCI;
        return triplet;

    }

    @SuppressWarnings("DataFlowIssue")   // Too complex for IntelliJ to analyze.
    @ExplodeLoop(kind = ExplodeLoop.LoopExplosionKind.MERGE_EXPLODE)
    @BytecodeInterpreterSwitch
    private Object executeBodyFromBCI(VirtualFrame frame, int startBCI, int startTop, int startStatementIndex,
                    boolean isOSR, boolean resumeContinuation) {
        CompilerAsserts.partialEvaluationConstant(startBCI);
        final InstrumentationSupport instrument = this.instrumentation;
        int statementIndex = startStatementIndex;
        boolean skipLivenessActions = instrument != null;
        boolean shouldResumeContinuation = resumeContinuation;
        ConcolicValueWrapper<?> concolicReturnValue = null;

        final Counter loopCount = new Counter();

        // The canonical program counter (bci) is in the first slot of the stack frame, but we
        // prefer to work with a shadow copy in a local variable and only update the frame when
        // needed, because that's faster.
        setBCI(frame, startBCI);
        int curBCI = startBCI;
        int top = startTop;

        if (instrument != null) {
            if (resumeContinuation) {
                instrument.notifyResume(frame, this);
                instrument.notifyStatementResume(frame, statementIndex);
            } else if (!isOSR) {
                instrument.notifyEntry(frame, this);
                instrument.notifyStatementEnter(frame, statementIndex);
            }
        }

        // During OSR or continuation resume, the method is not executed from the beginning hence
        // onStart is not applicable.
        if (!isOSR) {
            livenessAnalysis.onStart(frame, skipLivenessActions);
        }

        loop: while (true) {
            final int curOpcode = bs.opcode(curBCI);
            if (Logger.compileLog) {
                Logger.DEBUG("--------------------");
                Logger.DEBUG("Opcode: " + Opcodes.getOpcodeName(curOpcode) + ":" + curOpcode + " @" + String.join(".", getOpcodeLocation(curBCI)));
                Logger.DEBUG("--------------------");
            }
            EXECUTED_BYTECODES_COUNT.inc();
            try {
                CompilerAsserts.partialEvaluationConstant(top);
                CompilerAsserts.partialEvaluationConstant(curBCI);
                CompilerAsserts.partialEvaluationConstant(curOpcode);

                CompilerAsserts.partialEvaluationConstant(statementIndex);
                assert statementIndex == InstrumentationSupport.NO_STATEMENT || curBCI == returnValueBci || curBCI == throwValueBci ||
                                statementIndex == instrumentation.hookBCIToNodeIndex.lookupBucket(curBCI);

                if (instrument != null || Bytecodes.canTrap(curOpcode)) {
                    /*
                     * curOpcode can be == WIDE, but none of the WIDE-prefixed bytecodes throw
                     * exceptions.
                     */
                    setBCI(frame, curBCI);
                }

                // @formatter:off
                switch (curOpcode) {
                    case NOP: break;        // YJ: not required to handle
                    case ACONST_NULL: putObject(frame, top, StaticObject.NULL); break;  // YJ: not required to handle; will be stored as ConcolicObject with StaticObject.NULL at the conversion site


                    case ICONST_M1: // fall through
                    case ICONST_0: // fall through
                    case ICONST_1: // fall through
                    case ICONST_2: // fall through
                    case ICONST_3: // fall through
                    case ICONST_4: // fall through
                    case ICONST_5: {
                        int value = curOpcode - ICONST_0;
                        ConcolicInt concolicValue = ConcolicInt.createWithoutConstraints(value);    // YJ: const so it is OK to have no constraints
                        putConcolicInt(frame, top, concolicValue);
                        break;
                        //putInt(frame, top, curOpcode - ICONST_0); break;
                    }

                    case LCONST_0: // fall through
                    case LCONST_1: {
                        int value = curOpcode - LCONST_0;
                        ConcolicLong concolicValue = ConcolicLong.createWithoutConstraints(value);  // YJ: const so it OK to have no constraints
                        putConcolicLong(frame, top, concolicValue);
                        break;
                        //putLong(frame, top, curOpcode - LCONST_0); break;
                    }

                    case FCONST_0: // fall through
                    case FCONST_1: // fall through
                    case FCONST_2: {
                        int value = curOpcode - FCONST_0;
                        float floatValue = (float) value;
                        ConcolicFloat concolicValue = ConcolicFloat.createWithoutConstraints(floatValue);
                        putConcolicFloat(frame, top, concolicValue);
                        break;
                        //putFloat(frame, top, curOpcode - FCONST_0); break;
                    }

                    case DCONST_0: // fall through
                    case DCONST_1: {
                        int value = curOpcode - DCONST_0;
                        double doubleValue = (double) value;
                        ConcolicDouble concolicValue = ConcolicDouble.createWithoutConstraints(doubleValue);
                        putConcolicDouble(frame, top, concolicValue);
                        break;
                        //putDouble(frame, top, curOpcode - DCONST_0); break;              // YJ: pass on double rn
                    }

                    case BIPUSH: {
                        byte constant = bs.readByte(curBCI);
                        ConcolicByte cb = ConcolicByte.createWithoutConstraints(constant);
                        putConcolicByte(frame, top, cb);
                        break;
                        //putInt(frame, top, bs.readByte(curBCI)); break;
                    }
                    case SIPUSH: {
                        short constant = bs.readShort(curBCI);
                        ConcolicShort cs = ConcolicShort.createWithoutConstraints(constant);
                        putConcolicShort(frame, top, cs);
                        break;
                        //putInt(frame, top, bs.readShort(curBCI)); break;
                    }

                    // YJ: constants, so ignore them; it internally uses putInt, etc..
                    case LDC   : {
                        putPoolConcolicConstant(frame, top, bs.readCPI1(curBCI), curOpcode); break;
                    }
                    case LDC_W : // fall through
                    case LDC2_W: {
                        putPoolConcolicConstant(frame, top, bs.readCPI2(curBCI), curOpcode); break;
                    }

                    case ILOAD: {
                        int idx = bs.readLocalIndex1(curBCI);
                        ConcolicInt ci = getLocalConcolicInt(frame, idx);
                        if (Logger.compileLog) {
                            Logger.DEBUG("[ILOAD] CONCOLIC: " + ci);
                            Logger.DEBUG("[ILOAD] EXPR    : " + ci.getExpr() + " Value: " + ci.getConcreteValue());
                        }
                        putConcolicInt(frame, top, ci);
                        //putInt(frame, top, getLocalInt(frame, bs.readLocalIndex1(curBCI)));
                        livenessAnalysis.performPostBCI(frame, curBCI, skipLivenessActions);
                        break;
                    }
                    case LLOAD: {
                        int idx = bs.readLocalIndex1(curBCI);
                        ConcolicLong cl = getLocalConcolicLong(frame, idx);
                        if (Logger.compileLog) {
                            Logger.DEBUG("[LLOAD] CONCOLIC: " + cl);
                            Logger.DEBUG("[LLOAD] EXPR    : " + cl.getExpr() + " Value: " + cl.getConcreteValue());
                        }
                        putConcolicLong(frame, top, cl);
                        //putLong(frame, top, getLocalLong(frame, bs.readLocalIndex1(curBCI)));
                        livenessAnalysis.performPostBCI(frame, curBCI, skipLivenessActions);
                        break;
                    }
                    case FLOAD: {
                        int idx = bs.readLocalIndex1(curBCI);
                        ConcolicFloat cf = getLocalConcolicFloat(frame, idx);
                        if (Logger.compileLog) {
                            Logger.DEBUG("[FLOAD] CONCOLIC: " + cf);
                            Logger.DEBUG("[FLOAD] EXPR    : " + cf.getExpr() + " Value: " + cf.getConcreteValue());
                        }
                        putConcolicFloat(frame, top, cf);
                        //putFloat(frame, top, getLocalFloat(frame, bs.readLocalIndex1(curBCI)));
                        livenessAnalysis.performPostBCI(frame, curBCI, skipLivenessActions);
                        break;
                    }
                    case DLOAD: {
                        int idx = bs.readLocalIndex1(curBCI);
                        ConcolicDouble cd = getLocalConcolicDouble(frame, idx);
                        if (Logger.compileLog) {
                            Logger.DEBUG("[DLOAD] CONCOLIC: " + cd);
                            Logger.DEBUG("[DLOAD] EXPR    : " + cd.getExpr() + " Value: " + cd.getConcreteValue());
                        }
                        putConcolicDouble(frame, top, cd);
                        //putDouble(frame, top, getLocalDouble(frame, bs.readLocalIndex1(curBCI)));
                        livenessAnalysis.performPostBCI(frame, curBCI, skipLivenessActions);
                        break;
                    }
                    case ALOAD: {
                        ConcolicObject concolicObj = getLocalConcolicObject(frame, bs.readLocalIndex1(curBCI));
                        if (Logger.compileLog) {
                            int guestObjectId = concolicObj.getIdentityHashCode();
                            Logger.DEBUG("[ALOAD CONCOLIC] " + concolicObj);
                            Logger.DEBUG("[ALOAD HASHCODE] " + Integer.toHexString(guestObjectId));
                        }

                        putConcolicObject(frame, top, concolicObj);
                        livenessAnalysis.performPostBCI(frame, curBCI, skipLivenessActions);
                        break;
                    }

                    case ILOAD_0: // fall through
                    case ILOAD_1: // fall through
                    case ILOAD_2: // fall through
                    case ILOAD_3: {
                        int idx = curOpcode - ILOAD_0;
                        ConcolicInt ci = getLocalConcolicInt(frame, idx);
                        if (Logger.compileLog) {
                            Logger.DEBUG("[ILOAD " + idx + "] CONCOLIC: " + ci);
                            Logger.DEBUG("[ILOAD " + idx + "] EXPR    : " + ci.getExpr() + " Value: " + ci.getConcreteValue());
                        }
                        putConcolicInt(frame, top, ci);
                        //putInt(frame, top, getLocalInt(frame, curOpcode - ILOAD_0));
                        livenessAnalysis.performPostBCI(frame, curBCI, skipLivenessActions);
                        break;
                    }
                    case LLOAD_0: // fall through
                    case LLOAD_1: // fall through
                    case LLOAD_2: // fall through
                    case LLOAD_3: {
                        int idx = curOpcode - LLOAD_0;
                        ConcolicLong cl = getLocalConcolicLong(frame, idx);
                        if (Logger.compileLog) {
                            Logger.DEBUG("[LLOAD " + idx + "] CONCOLIC: " + cl);
                            Logger.DEBUG("[LLOAD " + idx + "] EXPR    : " + cl.getExpr() + " Value: " + cl.getConcreteValue());
                        }
                        putConcolicLong(frame, top, cl);
                        //putLong(frame, top, getLocalLong(frame, curOpcode - LLOAD_0));
                        livenessAnalysis.performPostBCI(frame, curBCI, skipLivenessActions);
                        break;
                    }
                    case FLOAD_0: // fall through
                    case FLOAD_1: // fall through
                    case FLOAD_2: // fall through
                    case FLOAD_3: {
                        int idx = curOpcode - FLOAD_0;
                        ConcolicFloat cf = getLocalConcolicFloat(frame, idx);
                        if (Logger.compileLog) {
                            Logger.DEBUG("[FLOAD " + idx + "] CONCOLIC: " + cf);
                            Logger.DEBUG("[FLOAD " + idx + "] EXPR    : " + cf.getExpr() + " Value: " + cf.getConcreteValue());
                        }
                        putConcolicFloat(frame, top, cf);
                        //putFloat(frame, top, getLocalFloat(frame, curOpcode - FLOAD_0));
                        livenessAnalysis.performPostBCI(frame, curBCI, skipLivenessActions);
                        break;
                    }
                    case DLOAD_0: // fall through
                    case DLOAD_1: // fall through
                    case DLOAD_2: // fall through
                    case DLOAD_3: {
                        int idx = curOpcode - DLOAD_0;
                        ConcolicDouble cd = getLocalConcolicDouble(frame, idx);
                        if (Logger.compileLog) {
                            Logger.DEBUG("[DLOAD " + idx + "] CONCOLIC: " + cd);
                            Logger.DEBUG("[DLOAD " + idx + "] EXPR    : " + cd.getExpr() + " Value: " + cd.getConcreteValue());
                        }
                        putConcolicDouble(frame, top, cd);
                        //putDouble(frame, top, getLocalDouble(frame, curOpcode - DLOAD_0));
                        livenessAnalysis.performPostBCI(frame, curBCI, skipLivenessActions);
                        break;
                    }
                    case ALOAD_0: {
                        ConcolicObject concolicObj = getLocalConcolicObject(frame, 0);

                        if (Logger.compileLog) {
                            int guestObjectId = concolicObj.getIdentityHashCode();
                            Logger.DEBUG("[ALOAD_0 CONCOLIC] " + concolicObj);
                            Logger.DEBUG("[ALOAD_0 HASHCODE] " + Integer.toHexString(guestObjectId));
                        }

                        putConcolicObject(frame, top, concolicObj);
                        livenessAnalysis.performPostBCI(frame, curBCI, skipLivenessActions);
                        break;
                    }
                    case ALOAD_1: // fall through
                    case ALOAD_2: // fall through
                    case ALOAD_3: {
                        ConcolicObject concolicObj = getLocalConcolicObject(frame, curOpcode - ALOAD_0);

                        if (Logger.compileLog) {
                            int guestObjectId = concolicObj.getIdentityHashCode();
                            Logger.DEBUG("[ALOAD_" + (curOpcode - ALOAD_0) +" CONCOLIC] " + concolicObj);
                            Logger.DEBUG("[ALOAD_" + (curOpcode - ALOAD_0) +" HASHCODE] " + Integer.toHexString(guestObjectId));
                        }

                        putConcolicObject(frame, top, concolicObj);
                        livenessAnalysis.performPostBCI(frame, curBCI, skipLivenessActions);
                        break;
                    }

                    case IALOAD: // fall through
                    case LALOAD: // fall through
                    case FALOAD: // fall through
                    case DALOAD: // fall through
                    case BALOAD: // fall through
                    case CALOAD: // fall through
                    case SALOAD: arrayLoad(frame, top, curBCI, curOpcode); break;
                    case AALOAD:
                        arrayLoad(frame, top, curBCI, AALOAD);
                        checkNoForeignObjectAssumption(peekObject(frame, top - 2));
                        break;

                    case ISTORE: {
                        ConcolicInt ci = popConcolicInt(frame, top - 1);
                        int idx = bs.readLocalIndex1(curBCI);
                        if (Logger.compileLog) {
                            Logger.DEBUG("[ISTORE " + idx + "] CONCOLIC: " + ci);
                            Logger.DEBUG("[ISTORE " + idx + "] EXPR    : " + ci.getExpr() + " Value: " + ci.getConcreteValue());
                        }
                        setLocalConcolicInt(frame, idx, ci);
                        //setLocalConcolicInt(frame, bs.readLocalIndex1(curBCI), popConcolicInt(frame, top - 1));
                        livenessAnalysis.performPostBCI(frame, curBCI, skipLivenessActions);
                        break;
                    }
                    case LSTORE: {
                        ConcolicLong cl = popConcolicLong(frame, top - 1);
                        int idx = bs.readLocalIndex1(curBCI);
                        if (Logger.compileLog) {
                            Logger.DEBUG("[LSTORE " + idx + "] CONCOLIC: " + cl);
                            Logger.DEBUG("[LSTORE " + idx + "] EXPR    : " + cl.getExpr() + " Value: " + cl.getConcreteValue());
                        }
                        setLocalConcolicLong(frame, idx, cl);

                        //setLocalConcolicLong(frame, bs.readLocalIndex1(curBCI), popConcolicLong(frame, top - 1));
                        livenessAnalysis.performPostBCI(frame, curBCI, skipLivenessActions);
                        break;
                    }
                    case FSTORE: {
                        ConcolicFloat cf = popConcolicFloat(frame, top - 1);
                        int idx = bs.readLocalIndex1(curBCI);
                        if (Logger.compileLog) {
                            Logger.DEBUG("[FSTORE " + idx + "] CONCOLIC: " + cf);
                            Logger.DEBUG("[FSTORE " + idx + "] EXPR    : " + cf.getExpr() + " Value: " + cf.getConcreteValue());
                        }
                        setLocalConcolicFloat(frame, idx, cf);

                        //setLocalConcolicFloat(frame, bs.readLocalIndex1(curBCI), popConcolicFloat(frame, top - 1));
                        livenessAnalysis.performPostBCI(frame, curBCI, skipLivenessActions);
                        break;
                    }
                    case DSTORE: {
                        ConcolicDouble cd = popConcolicDouble(frame, top - 1);
                        int idx = bs.readLocalIndex1(curBCI);
                        if (Logger.compileLog) {
                            Logger.DEBUG("[DSTORE " + idx + "] CONCOLIC: " + cd);
                            Logger.DEBUG("[DSTORE " + idx + "] EXPR    : " + cd.getExpr() + " Value: " + cd.getConcreteValue());
                        }
                        setLocalConcolicDouble(frame, idx, cd);

                        //setLocalConcolicDouble(frame, bs.readLocalIndex1(curBCI), popConcolicDouble(frame, top - 1));
                        livenessAnalysis.performPostBCI(frame, curBCI, skipLivenessActions);
                        break;
                    }
                    case ASTORE: {
                        ConcolicObject concolic = popConcolicReturnAddressOrObject(frame, top - 1);
                        int guestObjectId = concolic.getIdentityHashCode();
                        if (Logger.compileLog) {
                            Logger.DEBUG("[ASTORE CONCOLIC] " + concolic);
                            Logger.DEBUG("[ASTORE HASHCODE] " + Integer.toHexString(guestObjectId));
                        }
                        setLocalConcolicObjectOrReturnAddress(frame, bs.readLocalIndex1(curBCI), concolic);
                        livenessAnalysis.performPostBCI(frame, curBCI, skipLivenessActions);
                        break;
                    }

                    case ISTORE_0: // fall through
                    case ISTORE_1: // fall through
                    case ISTORE_2: // fall through
                    case ISTORE_3: {
                        int idx = curOpcode - ISTORE_0;
                        ConcolicInt ci = popConcolicInt(frame, top - 1);
                        if (Logger.compileLog) {
                            Logger.DEBUG("[ISTORE " + idx + "] CONCOLIC: " + ci);
                            Logger.DEBUG("[ISTORE " + idx + "] EXPR    : " + ci.getExpr() + " Value: " + ci.getConcreteValue());
                        }
                        setLocalConcolicInt(frame, idx, ci);
                        //setLocalConcolicInt(frame, curOpcode - ISTORE_0, popConcolicInt(frame, top - 1));
                        livenessAnalysis.performPostBCI(frame, curBCI, skipLivenessActions);
                        break;
                    }
                    case LSTORE_0: // fall through
                    case LSTORE_1: // fall through
                    case LSTORE_2: // fall through
                    case LSTORE_3: {
                        int idx = curOpcode - LSTORE_0;
                        ConcolicLong cl = popConcolicLong(frame, top - 1);
                        if (Logger.compileLog) {
                            Logger.DEBUG("[LSTORE " + idx + "] CONCOLIC: " + cl);
                            Logger.DEBUG("[LSTORE " + idx + "] EXPR    : " + cl.getExpr() + " Value: " + cl.getConcreteValue());
                        }
                        setLocalConcolicLong(frame, idx, cl);

                        //setLocalConcolicLong(frame, curOpcode - LSTORE_0, popConcolicLong(frame, top - 1));
                        livenessAnalysis.performPostBCI(frame, curBCI, skipLivenessActions);
                        break;
                    }
                    case FSTORE_0: // fall through
                    case FSTORE_1: // fall through
                    case FSTORE_2: // fall through
                    case FSTORE_3: {
                        int idx = curOpcode - FSTORE_0;
                        ConcolicFloat cf = popConcolicFloat(frame, top - 1);
                        if (Logger.compileLog) {
                            Logger.DEBUG("[FSTORE " + idx + "] CONCOLIC: " + cf);
                            Logger.DEBUG("[FSTORE " + idx + "] EXPR    : " + cf.getExpr() + " Value: " + cf.getConcreteValue());
                        }
                        setLocalConcolicFloat(frame, idx, cf);

                        //setLocalConcolicFloat(frame, curOpcode - FSTORE_0, popConcolicFloat(frame, top - 1));
                        livenessAnalysis.performPostBCI(frame, curBCI, skipLivenessActions);
                        break;
                    }
                    case DSTORE_0: // fall through
                    case DSTORE_1: // fall through
                    case DSTORE_2: // fall through
                    case DSTORE_3: {
                        int idx = curOpcode - DSTORE_0;
                        ConcolicDouble cd = popConcolicDouble(frame, top - 1);
                        if (Logger.compileLog) {
                            Logger.DEBUG("[DSTORE " + idx + "] CONCOLIC: " + cd);
                            Logger.DEBUG("[DSTORE " + idx + "] EXPR    : " + cd.getExpr() + " Value: " + cd.getConcreteValue());
                        }
                        setLocalConcolicDouble(frame, idx, cd);

                        //setLocalConcolicDouble(frame, curOpcode - DSTORE_0, popConcolicDouble(frame, top - 1));
                        livenessAnalysis.performPostBCI(frame, curBCI, skipLivenessActions);
                        break;
                    }
                    case ASTORE_0: // fall through
                    case ASTORE_1: // fall through
                    case ASTORE_2: // fall through
                    case ASTORE_3: {
                        ConcolicObject concolic = popConcolicReturnAddressOrObject(frame, top - 1);
                        int guestObjectId = concolic.getIdentityHashCode();
                        if (Logger.compileLog) {
                            Logger.DEBUG("[ASTORE_" + (curOpcode - ASTORE_0) +" CONCOLIC] " + concolic);
                            Logger.DEBUG("[ASTORE_" + (curOpcode - ASTORE_0) +" HASHCODE] " + Integer.toHexString(guestObjectId));
                        }

                        setLocalConcolicObjectOrReturnAddress(frame, curOpcode - ASTORE_0, concolic);
                        livenessAnalysis.performPostBCI(frame, curBCI, skipLivenessActions);
                        break;
                    }

                    case IASTORE: // fall through
                    case LASTORE: // fall through
                    case FASTORE: // fall through
                    case DASTORE: // fall through
                    case AASTORE: // fall through
                    case BASTORE: // fall through
                    case CASTORE: // fall through
                    case SASTORE: arrayStore(frame, top, curBCI, curOpcode); break;

                    case POP2:
                        clear(frame, top - 1);
                        clear(frame, top - 2);
                        break;
                    case POP:
                        clear(frame, top - 1);
                        break;

                    // TODO(peterssen): Stack shuffling is expensive.
                    case DUP     : dup1(frame, top);       break;
                    case DUP_X1  : dupx1(frame, top);      break;
                    case DUP_X2  : dupx2(frame, top);      break;
                    case DUP2    : dup2(frame, top);       break;
                    case DUP2_X1 : dup2x1(frame, top);     break;
                    case DUP2_X2 : dup2x2(frame, top);     break;
                    case SWAP    : swapSingle(frame, top); break;

                    case IADD: {
                        ConcolicInt value1 = popConcolicInt(frame, top - 2);
                        ConcolicInt value2 = popConcolicInt(frame, top - 1);
                        ConcolicInt result = value1.Add(value2);
                        putConcolicInt(frame, top - 2, result);
                        break;
                    }
                    case LADD: {
                        ConcolicLong value1 = popConcolicLong(frame, top - 3);
                        ConcolicLong value2 = popConcolicLong(frame, top - 1);
                        ConcolicLong result = value1.Add(value2);
                        putConcolicLong(frame, top - 4, result);
                        break;
                    }
                    case FADD: {
                        ConcolicFloat value1 = popConcolicFloat(frame, top - 2);
                        ConcolicFloat value2 = popConcolicFloat(frame, top - 1);
                        ConcolicFloat result = value1.Add(value2);
                        putConcolicFloat(frame, top - 2, result);
                        break;
                    }
                    case DADD: {
                        ConcolicDouble value1 = popConcolicDouble(frame, top - 3);
                        ConcolicDouble value2 = popConcolicDouble(frame, top - 1);
                        ConcolicDouble result = value1.Add(value2);
                        putConcolicDouble(frame, top - 4, result);
                        break;
                    }

                    case ISUB: {
                        ConcolicInt value1 = popConcolicInt(frame, top - 2);
                        ConcolicInt value2 = popConcolicInt(frame, top - 1);
                        ConcolicInt result = value1.Subtract(value2);
                        putConcolicInt(frame, top - 2, result);
                        break;
                        //putInt(frame, top - 2, popInt(frame, top - 2) - popInt(frame, top - 1)); break;
                    }
                    case LSUB: {
                        ConcolicLong value1 = popConcolicLong(frame, top - 3);
                        ConcolicLong value2 = popConcolicLong(frame, top - 1);
                        ConcolicLong result = value1.Subtract(value2);
                        putConcolicLong(frame, top - 4, result);
                        break;
                        //putLong(frame, top - 4, popLong(frame, top - 3) - popLong(frame, top - 1)); break;
                    }
                    case FSUB: { // XXX: YJ: not handle this and double yet
                        ConcolicFloat value1 = popConcolicFloat(frame, top - 2);
                        ConcolicFloat value2 = popConcolicFloat(frame, top - 1);
                        ConcolicFloat result = value1.Subtract(value2);
                        putConcolicFloat(frame, top - 2, result);
                        break;
                        //putFloat(frame, top - 2, popFloat(frame, top - 2) - popFloat(frame, top - 1)); break;
                    }
                    case DSUB: {
                        ConcolicDouble value1 = popConcolicDouble(frame, top - 3);
                        ConcolicDouble value2 = popConcolicDouble(frame, top - 1);
                        ConcolicDouble result = value1.Subtract(value2);
                        putConcolicDouble(frame, top - 4, result);
                        break;
                        //putDouble(frame, top - 4, popDouble(frame, top - 3) - popDouble(frame, top - 1)); break;
                    }

                    case IMUL: {
                        ConcolicInt value1 = popConcolicInt(frame, top - 2);
                        ConcolicInt value2 = popConcolicInt(frame, top - 1);
                        ConcolicInt result = value1.Multiply(value2);
                        putConcolicInt(frame, top - 2, result);
                        break;
                        //putInt(frame, top - 2, popInt(frame, top - 1) * popInt(frame, top - 2)); break;
                    }

                    case LMUL: {
                        ConcolicLong value1 = popConcolicLong(frame, top - 3);
                        ConcolicLong value2 = popConcolicLong(frame, top - 1);
                        ConcolicLong result = value1.Multiply(value2);
                        putConcolicLong(frame, top - 4, result);
                        break;
                        //putLong(frame, top - 4, popLong(frame, top - 1) * popLong(frame, top - 3)); break;
                    }
                    case FMUL: {
                        ConcolicFloat value1 = popConcolicFloat(frame, top - 2);
                        ConcolicFloat value2 = popConcolicFloat(frame, top - 1);
                        ConcolicFloat result = value1.Multiply(value2);
                        putConcolicFloat(frame, top - 2, result);
                        break;
                        //putFloat(frame, top - 2, popFloat(frame, top - 1) * popFloat(frame, top - 2)); break;
                    }
                    case DMUL: {
                        ConcolicDouble value1 = popConcolicDouble(frame, top - 3);
                        ConcolicDouble value2 = popConcolicDouble(frame, top - 1);
                        ConcolicDouble result = value1.Multiply(value2);
                        putConcolicDouble(frame, top - 4, result);
                        break;
                        //putDouble(frame, top - 4, popDouble(frame, top - 1) * popDouble(frame, top - 3)); break;
                    }
                    case IDIV: {
                        ConcolicInt value1 = popConcolicInt(frame, top - 2);
                        ConcolicInt value2 = popConcolicInt(frame, top - 1);
                        ConcolicInt result = value1.Divide(value2);
                        putConcolicInt(frame, top - 2, result);
                        break;
                        //putInt(frame, top - 2, divInt(checkNonZero(popInt(frame, top - 1)), popInt(frame, top - 2))); break;
                    }
                    case LDIV: {
                        ConcolicLong value1 = popConcolicLong(frame, top - 3);
                        ConcolicLong value2 = popConcolicLong(frame, top - 1);
                        ConcolicLong result = value1.Divide(value2);
                        putConcolicLong(frame, top - 4, result);
                        break;
                        //putLong(frame, top - 4, divLong(checkNonZero(popLong(frame, top - 1)), popLong(frame, top - 3))); break;
                    }
                    case FDIV: {
                        ConcolicFloat value1 = popConcolicFloat(frame, top - 2);
                        ConcolicFloat value2 = popConcolicFloat(frame, top - 1);
                        ConcolicFloat result = value1.Divide(value2);
                        putConcolicFloat(frame, top - 2, result);
                        break;

                        //putFloat(frame, top - 2, divFloat(popFloat(frame, top - 1), popFloat(frame, top - 2))); break;
                    }
                    case DDIV: {
                        ConcolicDouble value1 = popConcolicDouble(frame, top - 3);
                        ConcolicDouble value2 = popConcolicDouble(frame, top - 1);
                        ConcolicDouble result = value1.Divide(value2);
                        putConcolicDouble(frame, top - 4, result);
                        break;
                        //putDouble(frame, top - 4, divDouble(popDouble(frame, top - 1), popDouble(frame, top - 3))); break;
                    }

                    case IREM: {
                        ConcolicInt value1 = popConcolicInt(frame, top - 2);
                        ConcolicInt value2 = popConcolicInt(frame, top - 1);
                        ConcolicInt result = value1.Modulo(value2);
                        putConcolicInt(frame, top - 2, result);
                        break;
                        //putInt(frame, top - 2, remInt(checkNonZero(popInt(frame, top - 1)), popInt(frame, top - 2))); break;
                    }
                    case LREM: {
                        ConcolicLong value1 = popConcolicLong(frame, top - 3);
                        ConcolicLong value2 = popConcolicLong(frame, top - 1);
                        ConcolicLong result = value1.Modulo(value2);
                        putConcolicLong(frame, top - 4, result);
                        break;
                        //putLong(frame, top - 4, remLong(checkNonZero(popLong(frame, top - 1)), popLong(frame, top - 3))); break;
                    }
                    case FREM: {
                        ConcolicFloat value1 = popConcolicFloat(frame, top - 2);
                        ConcolicFloat value2 = popConcolicFloat(frame, top - 1);
                        ConcolicFloat result = value1.Modulo(value2);
                        putConcolicFloat(frame, top - 2, result);
                        break;
                        //putFloat(frame, top - 2, remFloat(popFloat(frame, top - 1), popFloat(frame, top - 2))); break;
                    }
                    case DREM: {
                        ConcolicDouble value1 = popConcolicDouble(frame, top - 3);
                        ConcolicDouble value2 = popConcolicDouble(frame, top - 1);
                        ConcolicDouble result = value1.Modulo(value2);
                        putConcolicDouble(frame, top - 4, result);
                        break;

                        //putDouble(frame, top - 4, remDouble(popDouble(frame, top - 1), popDouble(frame, top - 3))); break;
                    }

                    case INEG: {
                        ConcolicInt value1 = popConcolicInt(frame, top - 1);
                        ConcolicInt result = value1.Negate();
                        putConcolicInt(frame, top - 1, result);
                        break;
                        //putInt(frame, top - 1, -popInt(frame, top - 1)); break;
                    }
                    case LNEG: {
                        ConcolicLong value1 = popConcolicLong(frame, top - 1);
                        ConcolicLong result = value1.Negate();
                        putConcolicLong(frame, top - 2, result);
                        break;
                        //putLong(frame, top - 2, -popLong(frame, top - 1)); break;
                    }
                    case FNEG: {
                        ConcolicFloat value1 = popConcolicFloat(frame, top - 1);
                        ConcolicFloat result = value1.Negate();
                        putConcolicFloat(frame, top - 1, result);
                        break;

                        //putFloat(frame, top - 1, -popFloat(frame, top - 1)); break;
                    }
                    case DNEG: {
                        ConcolicDouble value1 = popConcolicDouble(frame, top - 1);
                        ConcolicDouble result = value1.Negate();
                        putConcolicDouble(frame, top - 2, result);
                        break;

                        //putDouble(frame, top - 2, -popDouble(frame, top - 1)); break;
                    }

                    case ISHL: {
                        ConcolicInt value1 = popConcolicInt(frame, top - 2);
                        ConcolicInt value2 = popConcolicInt(frame, top - 1);
                        ConcolicInt result = value1.ShiftLeft(value2);
                        putConcolicInt(frame, top - 2, result);
                        break;
                        //putInt(frame, top - 2, shiftLeftInt(popInt(frame, top - 1), popInt(frame, top - 2))); break;
                    }
                    case LSHL: {
                        if (Logger.compileLog) {
                            Logger.DEBUG("LSHL START");
                        }
                        ConcolicLong value1 = popConcolicLong(frame, top - 2);
                        if (Logger.compileLog) {
                            Logger.DEBUG("LSHL value 1: " + value1);
                        }
                        ConcolicInt value2 = popConcolicInt(frame, top - 1);
                        if (Logger.compileLog) {
                            Logger.DEBUG("LSHL value 2: " + value2);
                        }
                        ConcolicLong result = value1.ShiftLeft(value2.ToLong());
                        if (Logger.compileLog) {
                            Logger.DEBUG("LSHL result: " + result);
                        }
                        putConcolicLong(frame, top - 3, result);
                        break;
                        //putLong(frame, top - 3, shiftLeftLong(popInt(frame, top - 1), popLong(frame, top - 2))); break;
                    }
                    case ISHR: {
                        ConcolicInt value1 = popConcolicInt(frame, top - 2);
                        ConcolicInt value2 = popConcolicInt(frame, top - 1);
                        ConcolicInt result = value1.ShiftRight(value2);
                        putConcolicInt(frame, top - 2, result);
                        break;
                        //putInt(frame, top - 2, shiftRightSignedInt(popInt(frame, top - 1), popInt(frame, top - 2))); break;
                    }
                    case LSHR: {
                        ConcolicLong value1 = popConcolicLong(frame, top - 2);
                        ConcolicInt value2 = popConcolicInt(frame, top - 1);
                        ConcolicLong result = value1.ShiftRight(value2.ToLong());
                        putConcolicLong(frame, top - 3, result);
                        break;
                        //putLong(frame, top - 3, shiftRightSignedLong(popInt(frame, top - 1), popLong(frame, top - 2))); break;
                    }
                    case IUSHR: {
                        ConcolicInt value1 = popConcolicInt(frame, top - 2);
                        ConcolicInt value2 = popConcolicInt(frame, top - 1);
                        ConcolicInt result = value1.ShiftRightUnsigned(value2);
                        putConcolicInt(frame, top - 2, result);
                        break;
                        //putInt(frame, top - 2, shiftRightUnsignedInt(popInt(frame, top - 1), popInt(frame, top - 2))); break;
                    }
                    case LUSHR: {
                        ConcolicLong value1 = popConcolicLong(frame, top - 2);
                        ConcolicInt value2 = popConcolicInt(frame, top - 1);
                        ConcolicLong result = value1.ShiftRightUnsigned(value2.ToLong());
                        putConcolicLong(frame, top - 3, result);
                        break;
                        //putLong(frame, top - 3, shiftRightUnsignedLong(popInt(frame, top - 1), popLong(frame, top - 2))); break;
                    }

                    case IAND: {
                        ConcolicInt value1 = popConcolicInt(frame, top - 2);
                        ConcolicInt value2 = popConcolicInt(frame, top - 1);
                        ConcolicInt result = value1.BitwiseAnd(value2);
                        putConcolicInt(frame, top - 2, result);
                        break;
                        //putInt(frame, top - 2, popInt(frame, top - 1) & popInt(frame, top - 2)); break;
                    }
                    case LAND: {
                        ConcolicLong value1 = popConcolicLong(frame, top - 3);
                        ConcolicLong value2 = popConcolicLong(frame, top - 1);
                        ConcolicLong result = value1.BitwiseAnd(value2);
                        putConcolicLong(frame, top - 4, result);
                        break;
                        //putLong(frame, top - 4, popLong(frame, top - 1) & popLong(frame, top - 3)); break;
                    }
                    case IOR: {
                        ConcolicInt value1 = popConcolicInt(frame, top - 2);
                        ConcolicInt value2 = popConcolicInt(frame, top - 1);
                        ConcolicInt result = value1.BitwiseOr(value2);
                        putConcolicInt(frame, top - 2, result);
                        break;
                        //putInt(frame, top - 2, popInt(frame, top - 1) | popInt(frame, top - 2)); break;
                    }
                    case LOR: {
                        ConcolicLong value1 = popConcolicLong(frame, top - 3);
                        ConcolicLong value2 = popConcolicLong(frame, top - 1);
                        ConcolicLong result = value1.BitwiseOr(value2);
                        putConcolicLong(frame, top - 4, result);
                        break;
                        //putLong(frame, top - 4, popLong(frame, top - 1) | popLong(frame, top - 3)); break;
                    }

                    case IXOR: {
                        ConcolicInt value1 = popConcolicInt(frame, top - 2);
                        ConcolicInt value2 = popConcolicInt(frame, top - 1);
                        ConcolicInt result = value1.BitwiseXor(value2);
                        putConcolicInt(frame, top - 2, result);
                        break;
                        //putInt(frame, top - 2, popInt(frame, top - 1) ^ popInt(frame, top - 2)); break;
                    }
                    case LXOR: {
                        ConcolicLong value1 = popConcolicLong(frame, top - 3);
                        ConcolicLong value2 = popConcolicLong(frame, top - 1);
                        ConcolicLong result = value1.BitwiseXor(value2);
                        putConcolicLong(frame, top - 4, result);
                        break;
                        //putLong(frame, top - 4, popLong(frame, top - 1) ^ popLong(frame, top - 3)); break;
                    }

                    case IINC: {
                        int idx = bs.readLocalIndex1(curBCI);
                        int increment = bs.readIncrement1(curBCI);
                        ConcolicInt originalConcolicInt = getLocalConcolicInt(frame, idx);
                        ConcolicInt incrementConcolicInt = ConcolicInt.createWithoutConstraints(increment);
                        ConcolicInt resultConcolicInt = originalConcolicInt.Add(incrementConcolicInt);
                        setLocalConcolicInt(frame, idx, resultConcolicInt);
                        //setLocalInt(frame, bs.readLocalIndex1(curBCI), getLocalInt(frame, bs.readLocalIndex1(curBCI)) + bs.readIncrement1(curBCI));
                        livenessAnalysis.performPostBCI(frame, curBCI, skipLivenessActions);
                        break;
                    }

                    case I2L: {
                        ConcolicInt c1 = popConcolicInt(frame, top - 1);
                        putConcolicLong(frame, top - 1, c1.ToLongExpr());
                        break;
                        //putLong(frame, top - 1, popInt(frame, top - 1)); break;
                    }
                    case I2F: {
                        ConcolicInt ci = popConcolicInt(frame, top - 1);
                        ConcolicFloat cf = ci.ToFloatConversion();
                        putConcolicFloat(frame, top - 1, cf);
                        break;
                        //putFloat(frame, top - 1, popInt(frame, top - 1)); break;
                    }
                    case I2D: {
                        ConcolicInt ci = popConcolicInt(frame, top - 1);
                        ConcolicDouble cd = ci.ToDoubleConversion();
                        putConcolicDouble(frame, top - 1, cd);
                        break;
                        //putDouble(frame, top - 1, popInt(frame, top - 1)); break;
                    }

                    case L2I: {
                        ConcolicLong c1 = popConcolicLong(frame, top - 1);
                        putConcolicInt(frame, top - 2, c1.ToIntExpr());
                        break;
                        //putInt(frame, top - 2, (int) popLong(frame, top - 1)); break;
                    }

                    case L2F: {
                        ConcolicLong c1 = popConcolicLong(frame, top - 1);
                        ConcolicFloat cf = c1.ToFloatConversion();
                        putConcolicFloat(frame, top - 2, cf);
                        break;
                        //putFloat(frame, top - 2, popLong(frame, top - 1)); break;
                    }
                    case L2D: {
                        ConcolicLong c1 = popConcolicLong(frame, top - 1);
                        ConcolicDouble cd = c1.ToDoubleConversion();
                        putConcolicDouble(frame, top - 2, cd);
                        break;
                        //putDouble(frame, top - 2, popLong(frame, top - 1)); break;
                    }

                    case F2I: {
                        ConcolicFloat c1 = popConcolicFloat(frame, top - 1);
                        ConcolicInt ci = c1.ToIntConversion();
                        putConcolicInt(frame, top - 1, ci);
                        break;
                        //putInt(frame, top - 1, (int) popFloat(frame, top - 1)); break;
                    }
                    case F2L: {
                        ConcolicFloat c1 = popConcolicFloat(frame, top - 1);
                        ConcolicLong cl = c1.ToLongConversion();
                        putConcolicLong(frame, top - 1, cl);
                        break;
                        //putLong(frame, top - 1, (long) popFloat(frame, top - 1)); break;
                    }
                    case F2D: {
                        ConcolicFloat c1 = popConcolicFloat(frame, top - 1);
                        ConcolicDouble cd = c1.ToDoubleConversion();
                        putConcolicDouble(frame, top - 1, cd);
                        break;
                        //putDouble(frame, top - 1, popFloat(frame, top - 1)); break;
                    }

                    case D2I: {
                        ConcolicDouble c1 = popConcolicDouble(frame, top - 1);
                        ConcolicInt ci = c1.ToIntConversion();
                        putConcolicInt(frame, top - 2, ci);
                        break;
                        //putInt(frame, top - 2, (int) popDouble(frame, top - 1)); break;
                    }
                    case D2L: {
                        ConcolicDouble c1 = popConcolicDouble(frame, top - 1);
                        ConcolicLong cl = c1.ToLongConversion();
                        putConcolicLong(frame, top - 2, cl);
                        break;
                        //putLong(frame, top - 2, (long) popDouble(frame, top - 1)); break;
                    }
                    case D2F: {
                        ConcolicDouble c1 = popConcolicDouble(frame, top - 1);
                        ConcolicFloat cf = c1.ToFloatConversion();
                        putConcolicFloat(frame, top - 2, cf);
                        break;
                        //putFloat(frame, top - 2, (float) popDouble(frame, top - 1)); break;
                    }

                    case I2B: {
                        ConcolicInt ci = popConcolicInt(frame, top - 1);
                        putConcolicByte(frame, top - 1, ci.ToByteExpr());
                        break;
                    }
                    case I2C: {
                        // TODO: Handle concolic
                        // TODO: handle char later (YJ)
                        // putInt(frame, top - 1, (char) popInt(frame, top - 1)); break;
                        ConcolicLong ci = popConcolicLong(frame, top - 1);
                        putConcolicChar(frame, top - 1, ci.ToCharExpr());
                        break;
                    }
                    case I2S: {
                        ConcolicInt ci = popConcolicInt(frame, top - 1);
                        putConcolicShort(frame, top - 1, ci.ToShortExpr());
                        break;
                    }

                    case LCMP : {
                        ConcolicLong value1 = popConcolicLong(frame, top - 3);
                        ConcolicLong value2 = popConcolicLong(frame, top - 1);
                        ConcolicInt result = value1.Compare(value2);
                        putConcolicInt(frame, top - 4, result);
                        break;
                        //putInt(frame, top - 4, compareLong(popLong(frame, top - 1), popLong(frame, top - 3))); break;
                    }

                    // XXX: YJ: handle float/double later
                    case FCMPL: {

                        ConcolicFloat c1 = popConcolicFloat(frame, top - 2);
                        ConcolicFloat c2 = popConcolicFloat(frame, top - 1);
                        if (Logger.compileLog) {
                            Logger.DEBUG("[FCMPL] " + c1.getConcreteValue() + " < " + c2.getConcreteValue());
                        }
                        ConcolicInt ci = c1.Compare(c2);
                        putConcolicInt(frame, top - 2, ci);
                        break;

                        //putInt(frame, top - 2, compareFloatLess(popFloat(frame, top - 1), popFloat(frame, top - 2))); break;
                    }
                    case FCMPG: {

                        ConcolicFloat c1 = popConcolicFloat(frame, top - 2);
                        ConcolicFloat c2 = popConcolicFloat(frame, top - 1);
                        if (Logger.compileLog) {
                            Logger.DEBUG("[FCMPG] " + c1.getConcreteValue() + " > " + c2.getConcreteValue());
                        }
                        ConcolicInt ci = c1.Compare(c2);
                        putConcolicInt(frame, top - 2, ci);
                        break;
                        //putInt(frame, top - 2, compareFloatGreater(popFloat(frame, top - 1), popFloat(frame, top - 2))); break;
                    }
                    case DCMPL: {
                        ConcolicDouble c1 = popConcolicDouble(frame, top - 3);
                        ConcolicDouble c2 = popConcolicDouble(frame, top - 1);
                        ConcolicInt ci = c1.Compare(c2);
                        putConcolicInt(frame, top - 4, ci);
                        break;
                        //putInt(frame, top - 4, compareDoubleLess(popDouble(frame, top - 1), popDouble(frame, top - 3))); break;
                    }
                    case DCMPG: {
                        ConcolicDouble c1 = popConcolicDouble(frame, top - 3);
                        ConcolicDouble c2 = popConcolicDouble(frame, top - 1);
                        ConcolicInt ci = c1.Compare(c2);
                        putConcolicInt(frame, top - 4, ci);
                        break;

                        //putInt(frame, top - 4, compareDoubleGreater(popDouble(frame, top - 1), popDouble(frame, top - 3))); break;
                    }

                    // @formatter:on
                    case IFEQ: // fall through
                    case IFNE: // fall through
                    case IFLT: // fall through
                    case IFGE: // fall through
                    case IFGT: // fall through
                    case IFLE: // fall through
                        //if (takeBranchPrimitive1(popInt(frame, top - 1), curOpcode)) {
                        if (takeBranchPrimitiveConcolic1(popConcolicInt(frame, top - 1), curOpcode, getOpcodeLocation(curBCI))) {
                            if (Logger.compileLog) {
                                Logger.DEBUG("[IF] True");
                            }
                            int targetBCI = bs.readBranchDest2(curBCI);
                            top += Bytecodes.stackEffectOf(IFLE);
                            statementIndex = beforeJumpChecks(frame, curBCI, targetBCI, top, statementIndex, instrument, loopCount, skipLivenessActions);
                            curBCI = targetBCI;
                            continue loop;
                        } else {
                            if (Logger.compileLog) {
                                Logger.DEBUG("[IF] False");
                            }
                        }
                        break;

                    case IF_ICMPEQ: // fall through
                    case IF_ICMPNE: // fall through
                    case IF_ICMPLT: // fall through
                    case IF_ICMPGE: // fall through
                    case IF_ICMPGT: // fall through
                    case IF_ICMPLE:
                        ConcolicInt c1 = popConcolicInt(frame, top - 1);
                        ConcolicInt c2 = popConcolicInt(frame, top - 2);
                        //if (takeBranchPrimitive2(popInt(frame, top - 1), popInt(frame, top - 2), curOpcode)) {
                        if (takeBranchPrimitiveConcolic2(c1, c2, curOpcode, getOpcodeLocation(curBCI))) {
                            // branch taken
                            if (Logger.compileLog) {
                                Logger.DEBUG("[ICMP] True " + c1.getConcreteValue() + " vs " + c2.getConcreteValue());
                            }
                            top += Bytecodes.stackEffectOf(IF_ICMPLE);
                            statementIndex = beforeJumpChecks(frame, curBCI, bs.readBranchDest2(curBCI), top, statementIndex, instrument, loopCount, skipLivenessActions);
                            curBCI = bs.readBranchDest2(curBCI);
                            continue loop;
                        }
                        else {
                            // branch untaken
                            if (Logger.compileLog) {
                                Logger.DEBUG("[ICMP] False " + c1.getConcreteValue() + " vs " + c2.getConcreteValue());
                            }
                        }
                        break;

                    case IF_ACMPEQ: // fall through
                    case IF_ACMPNE: {
                        if (takeConcolicBranchRef2(popConcolicObject(frame, top - 1), popConcolicObject(frame, top - 2), curOpcode)) {
                        //if (takeBranchRef2(popObject(frame, top - 1), popObject(frame, top - 2), curOpcode)) {
                            int targetBCI = bs.readBranchDest2(curBCI);
                            top += Bytecodes.stackEffectOf(IF_ACMPNE);
                            statementIndex = beforeJumpChecks(frame, curBCI, targetBCI, top, statementIndex, instrument, loopCount, skipLivenessActions);
                            curBCI = targetBCI;
                            continue loop;
                        }
                        break;
                    }

                    case IFNULL: // fall through
                    case IFNONNULL: {
                        if (takeConcolicBranchRef1(popConcolicObject(frame, top - 1), curOpcode)) {
                        //if (takeBranchRef1(popObject(frame, top - 1), curOpcode)) {
                            int targetBCI = bs.readBranchDest2(curBCI);
                            top += Bytecodes.stackEffectOf(IFNONNULL);
                            statementIndex = beforeJumpChecks(frame, curBCI, targetBCI, top, statementIndex, instrument, loopCount, skipLivenessActions);
                            curBCI = targetBCI;
                            continue loop;
                        }
                        break;
                    }

                    case GOTO: {
                        int targetBCI = bs.readBranchDest2(curBCI);
                        statementIndex = beforeJumpChecks(frame, curBCI, targetBCI, top, statementIndex, instrument, loopCount, skipLivenessActions);
                        curBCI = targetBCI;
                        continue loop;
                    }
                    case GOTO_W: {
                        int targetBCI = bs.readBranchDest4(curBCI);
                        statementIndex = beforeJumpChecks(frame, curBCI, targetBCI, top, statementIndex, instrument, loopCount, skipLivenessActions);
                        curBCI = targetBCI;
                        continue loop;
                    }
                    case JSR: {
                        putReturnAddress(frame, top, bs.nextBCI(curBCI));
                        int targetBCI = bs.readBranchDest2(curBCI);
                        top += Bytecodes.stackEffectOf(JSR);
                        statementIndex = beforeJumpChecks(frame, curBCI, targetBCI, top, statementIndex, instrument, loopCount, skipLivenessActions);
                        curBCI = targetBCI;
                        continue loop;
                    }
                    case JSR_W: {
                        putReturnAddress(frame, top, bs.nextBCI(curBCI));
                        int targetBCI = bs.readBranchDest4(curBCI);
                        top += Bytecodes.stackEffectOf(JSR_W);
                        statementIndex = beforeJumpChecks(frame, curBCI, targetBCI, top, statementIndex, instrument, loopCount, skipLivenessActions);
                        curBCI = targetBCI;
                        continue loop;
                    }
                    case RET: {
                        // Use final local variables to pass in lambdas.
                        final int retOpBci = curBCI;
                        final int targetBCI = getLocalReturnAddress(frame, bs.readLocalIndex1(curBCI));
                        livenessAnalysis.performPostBCI(frame, curBCI, skipLivenessActions);

                        // Safely obtain the known targets mappings.
                        int[][] knownTargets = jsrBci;
                        if (knownTargets == null) {
                            CompilerDirectives.transferToInterpreterAndInvalidate();
                            atomic(() -> {
                                // Double-checked locking.
                                if (jsrBci == null) {
                                    jsrBci = new int[bs.endBCI()][];
                                }
                            });
                            knownTargets = jsrBci;
                        }

                        // Safely obtain the known targets for the current ret operation.
                        int[] knownRets = VolatileArrayAccess.volatileRead(knownTargets, retOpBci);
                        if (knownRets == null) {
                            CompilerDirectives.transferToInterpreterAndInvalidate();
                            atomic(() -> {
                                if (VolatileArrayAccess.volatileRead(jsrBci, retOpBci) != null) {
                                    return;
                                }
                                /*
                                 * Be very careful on updating the known target bcis, as if another
                                 * thread reads the not fully initialized array, it may consider 0
                                 * to be a valid RET target, completely breaking PE.
                                 */
                                int[] targets = new int[]{targetBCI};
                                // Also serves as a "final publication" barrier for the assignment
                                // above.
                                VolatileArrayAccess.volatileWrite(jsrBci, retOpBci, targets);
                            });
                            knownRets = VolatileArrayAccess.volatileRead(knownTargets, retOpBci);
                        }
                        assert knownRets != null;

                        // Lookup in the known targets to transform the return address to a
                        // constant.
                        for (int jsr : knownRets) {
                            if (jsr == targetBCI) {
                                CompilerAsserts.partialEvaluationConstant(jsr);
                                top += Bytecodes.stackEffectOf(RET);
                                statementIndex = beforeJumpChecks(frame, curBCI, jsr, top, statementIndex, instrument, loopCount, skipLivenessActions);
                                curBCI = jsr;
                                continue loop;
                            }
                        }

                        // Lookup failed: Add the current target to the known targets.
                        CompilerDirectives.transferToInterpreterAndInvalidate();
                        atomic(() -> {
                            int[] currentRets = VolatileArrayAccess.volatileRead(jsrBci, retOpBci);
                            for (int jsr : currentRets) {
                                if (jsr == targetBCI) {
                                    // target has been added by another thread.
                                    return;
                                }
                            }
                            int[] updatedTargets = Arrays.copyOf(currentRets, currentRets.length + 1);
                            /*
                             * Be very careful on updating the known target bcis, as if another
                             * thread reads the not fully initialized array, it may consider 0 to be
                             * a valid RET target, completely breaking PE.
                             */
                            updatedTargets[updatedTargets.length - 1] = targetBCI;
                            // Also serves as a "final publication" barrier for the assignment
                            // above.
                            VolatileArrayAccess.volatileWrite(jsrBci, retOpBci, updatedTargets);
                        });
                        top += Bytecodes.stackEffectOf(RET);
                        statementIndex = beforeJumpChecks(frame, retOpBci, targetBCI, top, statementIndex, instrument, loopCount, skipLivenessActions);
                        curBCI = targetBCI;
                        continue loop;
                    }
                    // TODO: YJ: required to handle table switch concolically!!!
                    case TABLESWITCH: {
                        ConcolicInt concolicIndex = popConcolicInt(frame, top - 1);
                        int index = concolicIndex.getConcreteValue();
                        //int index = popInt(frame, top - 1);
                        BytecodeTableSwitch switchHelper = BytecodeTableSwitch.INSTANCE;
                        int low = switchHelper.lowKey(bs, curBCI);
                        int high = switchHelper.highKey(bs, curBCI);
                        assert low <= high;

                        if (ConcolicValueHelper.eitherSymbolicExpr(concolicIndex.getExpr())) {
                            ConcolicBranch br = new ConcolicBranch();
                            String[] branchIdentifier = getOpcodeLocation(curBCI);
                            br.setIdentifier(branchIdentifier);
                            if (Logger.compileLog) {
                                Logger.DEBUG("[TABLESWITCH] low: " + low + " high: " + high);
                            }
                            for (int sk = low; sk != (high + 1); ++sk) {
                                boolean branchTaken = (sk == index);
                                if (Logger.compileLog) {
                                    Logger.DEBUG("[TABLESWITCH] sk: " + sk + " val: " + index);
                                }
                                br.addSwitch(concolicIndex, sk, branchTaken);
                            }
                            ConcolicBranch.addBranch(br);
                        }

                        // Interpreter uses direct lookup.
                        if (CompilerDirectives.inInterpreter()) {
                            int targetBCI;
                            if (low <= index && index <= high) {
                                targetBCI = switchHelper.targetAt(bs, curBCI, index - low);
                            } else {
                                targetBCI = switchHelper.defaultTarget(bs, curBCI);
                            }
                            top += Bytecodes.stackEffectOf(TABLESWITCH);
                            statementIndex = beforeJumpChecks(frame, curBCI, targetBCI, top, statementIndex, instrument, loopCount, skipLivenessActions);
                            curBCI = targetBCI;
                            continue loop;
                        }

                        // i could overflow if high == Integer.MAX_VALUE.
                        // This loops take that into account.
                        for (int i = low; i != high + 1; ++i) {
                            if (i == index) {
                                // Key found.
                                int targetBCI = switchHelper.targetAt(bs, curBCI, i - low);
                                top += Bytecodes.stackEffectOf(TABLESWITCH);
                                statementIndex = beforeJumpChecks(frame, curBCI, targetBCI, top, statementIndex, instrument, loopCount, skipLivenessActions);
                                curBCI = targetBCI;
                                continue loop;
                            }
                        }

                        // Key not found.
                        int targetBCI = switchHelper.defaultTarget(bs, curBCI);
                        top += Bytecodes.stackEffectOf(TABLESWITCH);
                        statementIndex = beforeJumpChecks(frame, curBCI, targetBCI, top, statementIndex, instrument, loopCount, skipLivenessActions);
                        curBCI = targetBCI;
                        continue loop;
                    }

                    // TODO: YJ: required to handle lookupswitch concolically!!!
                    case LOOKUPSWITCH: {
                        // get and set concolic/concrete key
                        ConcolicInt concolicKey = popConcolicInt(frame, top - 1);
                        boolean passedHashCode = concolicKey.getPassedHashCode();
                        int key = concolicKey.getConcreteValue();
                        //int key = popInt(frame, top - 1);
                        BytecodeLookupSwitch switchHelper = BytecodeLookupSwitch.INSTANCE;
                        int low = 0;
                        int high = switchHelper.numberOfCases(bs, curBCI) - 1;

                        String[] branchIdentifier = getOpcodeLocation(curBCI);
                        String locationSignature = branchIdentifier[0] + "." + branchIdentifier[1] + ":" + branchIdentifier[2];

                        // if hashCode switch for string
                        if (passedHashCode && !locationSignature.startsWith("java/")) {
                            if (Logger.compileLog) {
                                Logger.DEBUG(   "[LOOKUPSWITCH] hashcode: " +
                                                concolicKey.toString() +
                                                " passedHashCode: " +
                                                passedHashCode +
                                                " Location: " +
                                                locationSignature);
                            }
                            ConcolicBranch br = new ConcolicBranch();
                            br.setIdentifier(branchIdentifier);
                            boolean branchAdded = false;
                            for (int sk = low; sk <= high; ++sk) {
                                int keyVal = switchHelper.keyAt(bs, curBCI, sk);
                                int jumpOffset = switchHelper.offsetAt(bs, curBCI, sk);
                                if (Logger.compileLog) {
                                    Logger.DEBUG("[LOOKUPSWITCH] switchOffset: " + curBCI +
                                            " jump target offset: " + jumpOffset +
                                            " target location: " + (jumpOffset + curBCI) +
                                            " label: " + keyVal);
                                }

                                Object[] _s = retrieveSwitchTarget(frame, switchHelper, curBCI + jumpOffset);
                                if (_s != null) {
                                    ConcolicObjectImpl originalString = (ConcolicObjectImpl) _s[0];
                                    ConcolicObjectImpl targetString = (ConcolicObjectImpl) _s[1];
                                    boolean branchTaken = (keyVal == key);
                                    ConcolicBoolean dummyBooleanObject = ConcolicBoolean.createWithoutConstraints(branchTaken);
                                    ConcolicBoolean exprBooleanObject = (ConcolicBoolean)
                                                                StringMethodHook.wrapEquals(_s[0], _s, "", dummyBooleanObject);
                                    if (Logger.compileLog) {
                                        Logger.DEBUG("EXPR: " + exprBooleanObject);
                                    }
                                    if (exprBooleanObject.isSymbolic()) {
                                        BitVecExpr resultExpr = (BitVecExpr) exprBooleanObject.getExpr();
                                        BitVecExpr oneExpr = Z3Helper.getInstance().oneExpr;
                                        BoolExpr eqExpr = Z3Helper.mkEq(resultExpr, oneExpr);
                                        br.addStringSwitch(eqExpr, branchTaken);
                                        branchAdded = true;
                                    }
                                    //br.addStringSwitch(originalString, targetString, branchTaken);
                                }
                            }
                            if (branchAdded) {
                                ConcolicBranch.addBranch(br);
                            }
                        }
                        // setup branch conditions for all switch variables if symbolic
                        if (!passedHashCode && ConcolicValueHelper.eitherSymbolicExpr(concolicKey.getExpr())) {
                            ConcolicBranch br = new ConcolicBranch();
                            br.setIdentifier(branchIdentifier);
                            if (Logger.compileLog) {
                                Logger.DEBUG("[LOOKUPSWITCH] low: " + low + " high: " + high);
                            }
                            for (int sk = low; sk <= high; ++sk) {
                                int keyVal = switchHelper.keyAt(bs, curBCI, sk);
                                if (Logger.compileLog) {
                                    Logger.DEBUG("[LOOKUP SWITCH] sk: " + sk + " val: " + keyVal);
                                }
                                boolean branchTaken = (keyVal == key);
                                // add branch here
                                br.addSwitch(concolicKey, keyVal, branchTaken);
                            }
                            ConcolicBranch.addBranch(br);
                        } else {
                            if (Logger.compileLog) {
                                Logger.DEBUG("[LOOKUPSWITCH] nonsymbolic switch, val: " + key + " expr: " + concolicKey.getExpr());
                            }
                        }
                        // binary search for fast concrete operation
                        while (low <= high) {
                            int mid = (low + high) >>> 1;
                            int midVal = switchHelper.keyAt(bs, curBCI, mid);
                            if (midVal < key) {
                                low = mid + 1;
                            } else if (midVal > key) {
                                high = mid - 1;
                            } else {
                                // Key found.
                                int targetBCI = curBCI + switchHelper.offsetAt(bs, curBCI, mid);
                                top += Bytecodes.stackEffectOf(LOOKUPSWITCH);
                                statementIndex = beforeJumpChecks(frame, curBCI, targetBCI, top, statementIndex, instrument, loopCount, skipLivenessActions);
                                curBCI = targetBCI;
                                continue loop;
                            }
                        }

                        // Key not found.
                        int targetBCI = switchHelper.defaultTarget(bs, curBCI);
                        top += Bytecodes.stackEffectOf(LOOKUPSWITCH);
                        statementIndex = beforeJumpChecks(frame, curBCI, targetBCI, top, statementIndex, instrument, loopCount, skipLivenessActions);
                        curBCI = targetBCI;
                        continue loop;
                    }

                    case IRETURN: // fall through
                    case LRETURN: // fall through
                    case FRETURN: // fall through
                    case DRETURN: // fall through
                    case ARETURN: // fall through
                    case RETURN: {
                        if (Logger.compileLog) {
                            Logger.DEBUG("[RETURN STARTED]");
                        }
                        if (CompilerDirectives.hasNextTier() && loopCount.value > 0) {
                            LoopNode.reportLoopCount(this, loopCount.value);
                        }
                        Object returnValue = getReturnValueAsObject(frame, top);
                        if (instrument != null) {
                            instrument.exitAt(frame, statementIndex, ConcolicHelper.toConcrete(returnValue));
                        }

                        // This branch must not be a loop exit.
                        // Let the next loop iteration return this
                        top = startingStackOffset(getMethodVersion().getMaxLocals());
                        // frame.setObjectStatic(top, returnValue);
                        concolicReturnValue = (ConcolicValueWrapper<?>)returnValue;
                        top++;
                        curBCI = returnValueBci;
                        if (Logger.compileLog) {
                            Logger.DEBUG("[RETURN FINISHED] " + returnValue);
                        }
                        continue loop;
                    }
                    // TODO(peterssen): Order shuffled.
                    case GETSTATIC:
                        top += getField(frame, top,
                                        resolveField(curOpcode, /*- Quickenable -> read from original code for thread safety */ readOriginalCPI(curBCI)),
                                        curBCI, curOpcode, statementIndex, FieldAccessType.GetStatic);
                        break;
                    case GETFIELD:
                        top += getField(frame, top,
                                        resolveField(curOpcode, /*- Quickenable -> read from original code for thread safety */ readOriginalCPI(curBCI)),
                                        curBCI, curOpcode, statementIndex, FieldAccessType.GetInstance);
                        break;
                    case PUTSTATIC:
                        top += putField(frame, top,
                                        resolveField(curOpcode, /*- Quickenable -> read from original code for thread safety */ readOriginalCPI(curBCI)),
                                        curBCI, curOpcode, statementIndex, FieldAccessType.PutStatic);
                        break;
                    case PUTFIELD:
                        top += putField(frame, top,
                                        resolveField(curOpcode, /*- Quickenable -> read from original code for thread safety */ readOriginalCPI(curBCI)),
                                        curBCI, curOpcode, statementIndex, FieldAccessType.PutInstance);
                        break;
                    // @formatter:off
                    case INVOKEVIRTUAL: // fall through
                    case INVOKESPECIAL: // fall through
                    case INVOKESTATIC:  // fall through
                    case INVOKEINTERFACE:
                        top += quickenInvoke(frame, top, curBCI, curOpcode, statementIndex); break;

                    case NEW         :
                        Klass klass = resolveType(NEW, bs.readCPI2(curBCI));
                        putObject(frame, top, newReferenceObject(klass)); break;
                    case NEWARRAY    : {
                        byte jvmPrimitiveType = bs.readByte(curBCI);
                        ConcolicInt concolicLength = popConcolicInt(frame, top - 1);
                        if (concolicLength.isSymbolic()) {
                            SentinelHook.injectOOM(concolicLength, String.join(".", getOpcodeLocation(curBCI)));
                        }
                        ConcolicObject concolicArray = newPrimitiveArray(jvmPrimitiveType, concolicLength);
                        putConcolicObject(frame, top - 1, concolicArray);
                        break;
                    }
                    case ANEWARRAY   : {
                        ConcolicInt concolicLength = popConcolicInt(frame, top - 1);
                        if (concolicLength.isSymbolic()) {
                            SentinelHook.injectOOM(concolicLength, String.join(".", getOpcodeLocation(curBCI)));
                        }
                        ConcolicObject concolicArray = newReferenceArray(resolveType(ANEWARRAY, bs.readCPI2(curBCI)), concolicLength);
                        putConcolicObject(frame, top - 1, concolicArray);
                        break;
                    }
                    case ARRAYLENGTH : arrayLength(frame, top, curBCI); break;

                    case ATHROW      :
                        throw getMethod().getMeta().throwException(nullCheck(popObject(frame, top - 1)));

                    case CHECKCAST   : {
                        StaticObject receiver = peekObject(frame, top - 1);
                        if (StaticObject.isNull(receiver) || receiver.getKlass() == resolveType(CHECKCAST, readOriginalCPI(curBCI))) {
                            // Most common case, avoid spawning a node.
                        } else {
                            CompilerDirectives.transferToInterpreterAndInvalidate();
                            quickenCheckCast(frame, top, curBCI, CHECKCAST);
                        }
                        break;
                    }
                    // XXX: YJ: ConcolicInt will be returned, but let's see for these
                    case INSTANCEOF  : {
                        ConcolicObject concolicReceiver = popConcolicObject(frame, top - 1);
                        StaticObject receiver = (StaticObject) concolicReceiver.getConcreteValue();
                        if (StaticObject.isNull(receiver)) {
                            // Skip resolution.
                            putInt(frame, top - 1, /* false */ 0);
                        } else if (receiver.getKlass() == resolveType(INSTANCEOF, readOriginalCPI(curBCI))) {
                            // Quick-check, avoid spawning a node.
                            putInt(frame, top - 1, /* true */ 1);
                        } else {
                            CompilerDirectives.transferToInterpreterAndInvalidate();
                            putConcolicObject(frame, top - 1, concolicReceiver);
                            quickenInstanceOf(frame, top, curBCI, INSTANCEOF);
                        }
                        break;
                    }
                    case MONITORENTER: getRoot().monitorEnter(frame, nullCheck(popObject(frame, top - 1))); break;
                    case MONITOREXIT : getRoot().monitorExit(frame, nullCheck(popObject(frame, top - 1))); break;

                    case WIDE: {
                        // TODO: Handle concolic (Low priority). It seems rare.
                        int wideOpcode = bs.opcode(curBCI + 1);
                        switch (wideOpcode) {
                            case ILOAD: {
                                int idx = bs.readLocalIndex2(curBCI);
                                ConcolicInt ci = getLocalConcolicInt(frame, idx);
                                if (Logger.compileLog) {
                                    Logger.DEBUG("[WIDE ILOAD " + idx + "] EXPR: " + ci.getExpr() + " Value: " + ci.getConcreteValue());
                                }
                                putConcolicInt(frame, top, ci);
                                break;
                                //putInt(frame, top, getLocalInt(frame, bs.readLocalIndex2(curBCI))); break;
                            }
                            case LLOAD: {
                                int idx = bs.readLocalIndex2(curBCI);
                                ConcolicLong cl = getLocalConcolicLong(frame, idx);
                                if (Logger.compileLog) {
                                    Logger.DEBUG("[WIDE LLOAD] EXPR: " + cl.getExpr() + " Value: " + cl.getConcreteValue());
                                }
                                putConcolicLong(frame, top, cl);
                                break;
                                //putLong(frame, top, getLocalLong(frame, bs.readLocalIndex2(curBCI))); break;
                            }
                            case FLOAD: {
                                int idx = bs.readLocalIndex2(curBCI);
                                ConcolicFloat cf = getLocalConcolicFloat(frame, idx);
                                if (Logger.compileLog) {
                                    Logger.DEBUG("[WIDE FLOAD] EXPR: " + cf.getExpr() + " Value: " + cf.getConcreteValue());
                                }
                                putConcolicFloat(frame, top, cf);
                                break;
                                //putFloat(frame, top, getLocalFloat(frame, bs.readLocalIndex2(curBCI))); break;
                            }
                            case DLOAD: {
                                int idx = bs.readLocalIndex2(curBCI);
                                ConcolicDouble cd = getLocalConcolicDouble(frame, idx);
                                if (Logger.compileLog) {
                                    Logger.DEBUG("[WIDE DLOAD] EXPR: " + cd.getExpr() + " Value: " + cd.getConcreteValue());
                                }
                                putConcolicDouble(frame, top, cd);
                                break;
                                //putDouble(frame, top, getLocalDouble(frame, bs.readLocalIndex2(curBCI))); break;
                            }
                            case ALOAD: {
                                ConcolicObject concolicObj = getLocalConcolicObject(frame, bs.readLocalIndex2(curBCI));
                                int guestObjectId = concolicObj.getIdentityHashCode();
                                if (Logger.compileLog) {
                                    Logger.DEBUG("[WIDE ALOAD CONCOLIC] " + concolicObj);
                                    Logger.DEBUG("[WIDE ALOAD HASHCODE] " + Integer.toHexString(guestObjectId));
                                }
                                break;
                                //putObject(frame, top, getLocalObject(frame, bs.readLocalIndex2(curBCI))); break;
                            }

                            case ISTORE: {
                                ConcolicInt ci = popConcolicInt(frame, top - 1);
                                int idx = bs.readLocalIndex2(curBCI);
                                if (Logger.compileLog) {
                                    Logger.DEBUG("[WIDE ISTORE " + idx + "] EXPR: " + ci.getExpr() + " Value: " + ci.getConcreteValue());
                                }
                                setLocalConcolicInt(frame, idx, ci);
                                break;
                                //setLocalInt(frame, bs.readLocalIndex2(curBCI), popInt(frame, top - 1)); break;
                            }
                            case LSTORE: {
                                ConcolicLong cl = popConcolicLong(frame, top - 1);
                                int idx = bs.readLocalIndex2(curBCI);
                                if (Logger.compileLog) {
                                    Logger.DEBUG("[WIDE LSTORE " + idx + "] EXPR: " + cl.getExpr() + " Value: " + cl.getConcreteValue());
                                }
                                setLocalConcolicLong(frame, idx, cl);
                                break;
                                //setLocalLong(frame, bs.readLocalIndex2(curBCI), popLong(frame, top - 1)); break;
                            }
                            case FSTORE: {
                                ConcolicFloat cf = popConcolicFloat(frame, top - 1);
                                int idx = bs.readLocalIndex2(curBCI);
                                if (Logger.compileLog) {
                                    Logger.DEBUG("[WIDE FSTORE " + idx + "] EXPR: " + cf.getExpr() + " Value: " + cf.getConcreteValue());
                                }
                                setLocalConcolicFloat(frame, idx, cf);
                                break;
                                //setLocalFloat(frame, bs.readLocalIndex2(curBCI), popFloat(frame, top - 1)); break;
                            }
                            case DSTORE: {
                                ConcolicDouble cd = popConcolicDouble(frame, top - 1);
                                int idx = bs.readLocalIndex2(curBCI);
                                if (Logger.compileLog) {
                                    Logger.DEBUG("[WIDE DSTORE " + idx + "] EXPR: " + cd.getExpr() + " Value: " + cd.getConcreteValue());
                                }
                                setLocalConcolicDouble(frame, idx, cd);
                                break;
                                //setLocalDouble(frame, bs.readLocalIndex2(curBCI), popDouble(frame, top - 1)); break;
                            }
                            case ASTORE: {
                                ConcolicObject concolic = popConcolicReturnAddressOrObject(frame, top - 1);
                                int guestObjectId = concolic.getIdentityHashCode();
                                if (Logger.compileLog) {
                                    Logger.DEBUG("[WIDE ASTORE CONCOLIC] " + concolic);
                                    Logger.DEBUG("[WIDE ASTORE HASHCODE] " + Integer.toHexString(guestObjectId));
                                }
                                setLocalConcolicObjectOrReturnAddress(frame, bs.readLocalIndex2(curBCI), concolic);
                                break;
                                //setLocalObjectOrReturnAddress(frame, bs.readLocalIndex2(curBCI), popReturnAddressOrObject(frame, top - 1)); break;
                            }
                            case IINC: {
                                int idx = bs.readLocalIndex2(curBCI);
                                int increment = bs.readIncrement2(curBCI);
                                ConcolicInt originalConcolicInt = getLocalConcolicInt(frame, idx);
                                ConcolicInt incrementConcolicInt = ConcolicInt.createWithoutConstraints(increment);
                                ConcolicInt resultConcolicInt = originalConcolicInt.Add(incrementConcolicInt);
                                setLocalConcolicInt(frame, idx, resultConcolicInt);
                                break;
                                //setLocalInt(frame, bs.readLocalIndex2(curBCI), getLocalInt(frame, bs.readLocalIndex2(curBCI)) + bs.readIncrement2(curBCI)); break;
                            }
                            // @formatter:on
                            case RET: {
                                // Use final local variables to pass in lambdas.
                                final int retOpBci = curBCI;
                                final int targetBCI = getLocalReturnAddress(frame, bs.readLocalIndex2(curBCI));
                                livenessAnalysis.performPostBCI(frame, curBCI, skipLivenessActions);

                                // Safely obtain the known targets mappings.
                                int[][] knownTargets = jsrBci;
                                if (knownTargets == null) {
                                    CompilerDirectives.transferToInterpreterAndInvalidate();
                                    atomic(() -> {
                                        // Double-checked locking.
                                        if (jsrBci == null) {
                                            jsrBci = new int[bs.endBCI()][];
                                        }
                                    });
                                    knownTargets = jsrBci;
                                }

                                // Safely obtain the known targets for the current ret operation.
                                int[] knownRets = VolatileArrayAccess.volatileRead(knownTargets, retOpBci);
                                if (knownRets == null) {
                                    CompilerDirectives.transferToInterpreterAndInvalidate();
                                    atomic(() -> {
                                        if (VolatileArrayAccess.volatileRead(jsrBci, retOpBci) != null) {
                                            return;
                                        }
                                        /*
                                         * Be very careful on updating the known target bcis, as if
                                         * another thread reads the not fully initialized array, it
                                         * may consider 0 to be a valid RET target, completely
                                         * breaking PE.
                                         */
                                        int[] targets = new int[]{targetBCI};
                                        // Also serves as a "final publication" barrier for the
                                        // assignment above.
                                        VolatileArrayAccess.volatileWrite(jsrBci, retOpBci, targets);
                                    });
                                    knownRets = VolatileArrayAccess.volatileRead(knownTargets, retOpBci);
                                }
                                assert knownRets != null;

                                // Lookup in the known targets to transform the return address to a
                                // constant.
                                for (int jsr : knownRets) {
                                    if (jsr == targetBCI) {
                                        CompilerAsserts.partialEvaluationConstant(jsr);
                                        top += Bytecodes.stackEffectOf(RET);
                                        statementIndex = beforeJumpChecks(frame, curBCI, jsr, top, statementIndex, instrument, loopCount, skipLivenessActions);
                                        curBCI = jsr;
                                        continue loop;
                                    }
                                }

                                // Lookup failed: Add the current target to the known targets.
                                CompilerDirectives.transferToInterpreterAndInvalidate();
                                atomic(() -> {
                                    int[] currentRets = VolatileArrayAccess.volatileRead(jsrBci, retOpBci);
                                    for (int jsr : currentRets) {
                                        if (jsr == targetBCI) {
                                            // target has been added by another thread.
                                            return;
                                        }
                                    }
                                    int[] updatedTargets = Arrays.copyOf(currentRets, currentRets.length + 1);
                                    /*
                                     * Be very careful on updating the known target bcis, as if
                                     * another thread reads the not fully initialized array, it may
                                     * consider 0 to be a valid RET target, completely breaking PE.
                                     */
                                    updatedTargets[updatedTargets.length - 1] = targetBCI;
                                    // Also serves as a "final publication" barrier for the
                                    // assignment above.
                                    VolatileArrayAccess.volatileWrite(jsrBci, retOpBci, updatedTargets);
                                });
                                top += Bytecodes.stackEffectOf(RET);
                                statementIndex = beforeJumpChecks(frame, retOpBci, targetBCI, top, statementIndex, instrument, loopCount, skipLivenessActions);
                                curBCI = targetBCI;
                                continue loop;
                            }
                            default:
                                CompilerDirectives.transferToInterpreterAndInvalidate();
                                throw EspressoError.shouldNotReachHere(Bytecodes.nameOf(curOpcode));
                        }
                        livenessAnalysis.performPostBCI(frame, curBCI, skipLivenessActions);
                        int targetBCI = bs.nextBCI(curBCI);
                        livenessAnalysis.performOnEdge(frame, curBCI, targetBCI, skipLivenessActions);
                        top += Bytecodes.stackEffectOf(wideOpcode);
                        curBCI = targetBCI;
                        continue loop;
                    }

                    case MULTIANEWARRAY:
                        top += allocateMultiArray(frame, top, resolveType(MULTIANEWARRAY, bs.readCPI2(curBCI)), bs.readUByte(curBCI + 3));
                        break;

                    case BREAKPOINT:
                        CompilerDirectives.transferToInterpreterAndInvalidate();
                        throw EspressoError.unimplemented(Bytecodes.nameOf(curOpcode) + " not supported.");

                    case INVOKEDYNAMIC:
                        top += quickenInvokeDynamic(frame, top, curBCI, INVOKEDYNAMIC);
                        break;

                    case QUICK: {
                        // TODO: Dig this in detail. What is this bytecode?
                        // Force a volatile read of the opcode.
                        if (bs.currentVolatileBC(curBCI) != QUICK) {
                            // Possible case of read reordering. Retry handling the bytecode to make
                            // sure we get a correct CPI.
                            CompilerDirectives.transferToInterpreterAndInvalidate();
                            continue loop;
                        }
                        BaseQuickNode quickNode = nodes[bs.readCPI2(curBCI)];
                        if (quickNode.removedByRedefinition()) {
                            CompilerDirectives.transferToInterpreterAndInvalidate();
                            quickNode = getBaseQuickNode(curBCI, top, statementIndex, quickNode);
                        }
                        if (Logger.compileLog) {
                            Logger.DEBUG("[QUICK] " + quickNode);
                        }
                        top += quickNode.execute(frame, shouldResumeContinuation);
                        shouldResumeContinuation = false;
                        break;
                    }
                    case SLIM_QUICK:
                        top += sparseNodes[curBCI].execute(frame, false);
                        break;
                    case RETURN_VALUE:
                        /*
                         * Synthetic bytecode used to avoid merging interpreter loop exits too early
                         * (and thus lose partial-evaluation constants too early). When reached, the
                         * object at stack slot 0 should be returned.
                         */
                        assert top == startingStackOffset(getMethodVersion().getMaxLocals()) + 1;
                        assert curBCI == returnValueBci;
                        // return frame.getObjectStatic(top - 1);

                        if (getMethod().getName().toString().equals("main")) {
                            if (getMethod().getDeclaringKlass().getName().toString().equals("Runner")) {
                                Validator.doneRunnerMain = true;
                            }
                        }

                        if (Logger.compileLog) {
                            Logger.DEBUG("[RETURN_VALUE] : " + concolicReturnValue);
                        }

                        return concolicReturnValue;
                    case THROW_VALUE:
                        /*
                         * Synthetic bytecode used to avoid merging interpreter loop exits too early
                         * (and thus lose partial-evaluation constants too early). When reached, the
                         * object at stack slot 0 should be thrown.
                         */
                        assert top == startingStackOffset(getMethodVersion().getMaxLocals()) + 1;
                        assert curBCI == throwValueBci;

                        if (getMethod().getName().toString().equals("main")) {
                            if (getMethod().getDeclaringKlass().getName().toString().equals("Runner")) {
                                Validator.doneRunnerMain = true;
                            }
                        }

                        throw new ThrowOutOfInterpreterLoop((RuntimeException) frame.getObjectStatic(top - 1).getConcreteValue());

                    default:
                        CompilerDirectives.transferToInterpreterAndInvalidate();
                        throw EspressoError.shouldNotReachHere(Bytecodes.nameOf(curOpcode));
                }
            } catch (UnwindContinuationException unwindContinuationExceptionRequest) {
                /*
                 * Note: The absence of a continuum record for the bci in the method acts as a
                 * per-bci profile.
                 */
                // Get the frame from the stack into the VM heap.
                copyFrameToUnwindRequest(frame, unwindContinuationExceptionRequest, curBCI, top);
                if (instrument != null) {
                    instrument.notifyYieldAt(frame, unwindContinuationExceptionRequest.getContinuation(), statementIndex);
                }
                // This branch must not be a loop exit. Let the next loop iteration throw this
                top = startingStackOffset(getMethodVersion().getMaxLocals());
                frame.setObjectStatic(top, ConcolicObject.createWithoutConstraints(unwindContinuationExceptionRequest));
                top++;
                curBCI = throwValueBci;
                continue loop;
            } catch (AbstractTruffleException | StackOverflowError | OutOfMemoryError e) {
                //System.out.println("Exception: " + e.getMessage());
                //e.printStackTrace();
                CompilerAsserts.partialEvaluationConstant(curBCI);
                // Handle both guest and host StackOverflowError.
                if (e == getContext().getStackOverflow() || e instanceof StackOverflowError) {
                    // Always deopt on SOE.
                    CompilerDirectives.transferToInterpreter();
                    EspressoException wrappedStackOverflowError = null;
                    if (e == getContext().getStackOverflow()) {
                        wrappedStackOverflowError = (EspressoException) e;
                    } else {
                        wrappedStackOverflowError = getContext().getStackOverflow();
                    }
                    /*
                     * Stack Overflow management. All calls to stack manipulation are manually
                     * inlined to prevent another SOE.
                     *
                     * Note: no need to check for the stacktrace being null, as we reset the frames
                     * at each apparition of a host SOE.
                     */
                    if (stackOverflowErrorInfo != null) {
                        for (int i = 0; i < stackOverflowErrorInfo.length; i += 3) {
                            if (curBCI >= stackOverflowErrorInfo[i] && curBCI < stackOverflowErrorInfo[i + 1]) {
                                clearOperandStack(frame, top);
                                top = startingStackOffset(getMethodVersion().getMaxLocals());
                                putObject(frame, top, wrappedStackOverflowError.getGuestException());
                                top++;
                                int targetBCI = stackOverflowErrorInfo[i + 2];
                                statementIndex = beforeJumpChecks(frame, curBCI, targetBCI, top, statementIndex, instrument, loopCount, skipLivenessActions);
                                curBCI = targetBCI;
                                continue loop; // skip bs.next()
                            }
                        }
                    }
                    if (instrument != null) {
                        instrument.notifyExceptionAt(frame, wrappedStackOverflowError, statementIndex);
                    }
                    if (CompilerDirectives.hasNextTier() && loopCount.value > 0) {
                        LoopNode.reportLoopCount(this, loopCount.value);
                    }
                    // this branch is not compiled, it can be a loop exit
                    if (wrappedStackOverflowError == null) {
                        throw e;
                    } else {
                        throw wrappedStackOverflowError;
                    }

                } else /* EspressoException or AbstractTruffleException or OutOfMemoryError */ {
                    EspressoException wrappedException;
                    if (e instanceof EspressoException) {
                        wrappedException = (EspressoException) e;
                    } else if (e instanceof AbstractTruffleException) {
                        if (e instanceof EspressoExitException) {
                            CompilerDirectives.transferToInterpreter();
                            getRoot().abortMonitor(frame);
                            // Tearing down the VM, no need to report loop count.
                            // this branch is not compiled, it can be a loop exit
                            throw e;
                        }
                        assert getContext().getEspressoEnv().Polyglot;
                        Meta meta = getMethod().getMeta();
                        meta.polyglot.ForeignException.safeInitialize(); // should fold
                        wrappedException = EspressoException.wrap(
                                        getAllocator().createForeignException(getContext(), e, InteropLibrary.getUncached(e)), meta);
                    } else {
                        assert e instanceof OutOfMemoryError;
                        CompilerDirectives.transferToInterpreter();
                        wrappedException = getContext().getOutOfMemory();
                    }

                    ExceptionHandler[] handlers = getMethodVersion().getExceptionHandlers();
                    ExceptionHandler handler = null;
                    for (ExceptionHandler toCheck : handlers) {
                        CompilerAsserts.partialEvaluationConstant(toCheck);
                        if (toCheck.covers(curBCI)) {
                            Klass catchType = null;
                            if (!toCheck.isCatchAll()) {
                                // exception handlers are similar to instanceof bytecodes, so we
                                // pass instanceof
                                catchType = resolveType(Bytecodes.INSTANCEOF, (char) toCheck.catchTypeCPI());
                            }
                            CompilerAsserts.partialEvaluationConstant(catchType);
                            if (catchType == null || InterpreterToVM.instanceOf(wrappedException.getGuestException(), catchType)) {
                                // the first found exception handler is our exception handler
                                handler = toCheck;
                                break;
                            }
                        }
                    }
                    if (handler != null) {
                        // If there is a lazy stack trace being collected
                        // we need to materialize here since the handler is likely
                        // on a different line than the exception point
                        TruffleStackTrace.fillIn(wrappedException);
                        clearOperandStack(frame, top);
                        top = startingStackOffset(getMethodVersion().getMaxLocals());
                        checkNoForeignObjectAssumption(wrappedException.getGuestException());
                        putObject(frame, top, wrappedException.getGuestException());
                        top++;
                        int targetBCI = handler.getHandlerBCI();
                        statementIndex = beforeJumpChecks(frame, curBCI, targetBCI, top, statementIndex, instrument, loopCount, skipLivenessActions);
                        curBCI = targetBCI;
                        continue loop; // skip bs.next()
                    } else {
                        if (instrument != null) {
                            instrument.notifyExceptionAt(frame, wrappedException, statementIndex);
                        }
                        if (CompilerDirectives.hasNextTier() && loopCount.value > 0) {
                            LoopNode.reportLoopCount(this, loopCount.value);
                        }

                        // This branch must not be a loop exit.
                        // Let the next loop iteration throw this
                        top = startingStackOffset(getMethodVersion().getMaxLocals());
                        frame.setObjectStatic(top, ConcolicObject.createWithoutConstraints(wrappedException));
                        top++;
                        curBCI = throwValueBci;
                        continue loop;
                    }
                }
            } catch (EspressoOSRReturnException e) {
                if (CompilerDirectives.hasNextTier() && loopCount.value > 0) {
                    LoopNode.reportLoopCount(this, loopCount.value);
                }
                Object returnValue = e.getResultOrRethrow();
                if (instrument != null) {
                    instrument.notifyReturn(frame, statementIndex, returnValue);
                }

                // This branch must not be a loop exit. Let the next loop iteration return this
                top = startingStackOffset(getMethodVersion().getMaxLocals());
                if (returnValue instanceof ConcolicObject) {
                    frame.setObjectStatic(top, (ConcolicObject) returnValue);
                } else {
                    if (returnValue instanceof ConcolicValueWrapper<?>) {
                        throw new RuntimeException("returnValue should be concrete or ConcolicObject");
                    }
                    frame.setObjectStatic(top, ConcolicObject.createWithoutConstraints(returnValue));
                }
                top++;
                curBCI = returnValueBci;
                continue loop;
            } catch (ThrowOutOfInterpreterLoop e) {
                throw e.reThrow();
            }
            assert curOpcode != WIDE && curOpcode != LOOKUPSWITCH && curOpcode != TABLESWITCH;

            int targetBCI = curBCI + Bytecodes.lengthOf(curOpcode);
            livenessAnalysis.performOnEdge(frame, curBCI, targetBCI, skipLivenessActions);
            if (instrument != null) {
                int nextStatementIndex = instrument.getNextStatementIndex(statementIndex, targetBCI);
                if (nextStatementIndex != statementIndex) {
                    instrument.notifyStatementChange(frame, statementIndex, nextStatementIndex, targetBCI);
                    statementIndex = nextStatementIndex;
                }
            }
            top += Bytecodes.stackEffectOf(curOpcode);
            curBCI = targetBCI;
        }
    }

    private static final class ThrowOutOfInterpreterLoop extends ControlFlowException {
        @Serial private static final long serialVersionUID = 774753014650104744L;
        private final RuntimeException exception;

        private ThrowOutOfInterpreterLoop(RuntimeException exception) {
            this.exception = exception;
        }

        RuntimeException reThrow() {
            throw exception;
        }
    }

    private void copyFrameToUnwindRequest(VirtualFrame frame, UnwindContinuationException unwindContinuationExceptionRequest, int bci, int top) {
        // Extend the linked list of frame records as we unwind.
        unwindContinuationExceptionRequest.head = HostFrameRecord.recordFrame(frame, getMethodVersion(), bci, top, unwindContinuationExceptionRequest.head);
    }

    @Override
    public void enterNewReference() {
        enterImplicitExceptionProfile();
    }

    @Override
    public void enterNewArray() {
        enterImplicitExceptionProfile();
    }

    @Override
    public void enterNewMultiArray() {
        enterImplicitExceptionProfile();
    }

    private StaticObject newReferenceObject(Klass klass) {
        assert !klass.isPrimitive() : "Verifier guarantee";
        GuestAllocator.AllocationChecks.checkCanAllocateNewReference(getMethod().getMeta(), klass, true, this);
        return getAllocator().createNew((ObjectKlass) klass);
    }

    // private StaticObject newPrimitiveArray(byte jvmPrimitiveType, int length) {
    //     Meta meta = getMethod().getMeta();
    //     GuestAllocator.AllocationChecks.checkCanAllocateArray(meta, length, this);
    //     return getAllocator().createNewPrimitiveArray(meta, jvmPrimitiveType, length);
    // }
    private ConcolicObject newPrimitiveArray(byte jvmPrimitiveType, ConcolicInt concolicLength) {
        GuestAllocator.AllocationChecks.checkCanAllocateArray(getMethod().getMeta(), concolicLength.getConcreteValue(), this);
        return getAllocator().createNewPrimitiveArray(getMethod().getMeta(), jvmPrimitiveType, concolicLength);
    }

    // private StaticObject newReferenceArray(Klass componentType, int length) {
    //     GuestAllocator.AllocationChecks.checkCanAllocateArray(getMethod().getMeta(), length, this);
    //     return getAllocator().createNewReferenceArray(componentType, length);
    // }
    private ConcolicObject newReferenceArray(Klass componentType, ConcolicInt concolicLength) {
        GuestAllocator.AllocationChecks.checkCanAllocateArray(getMethod().getMeta(), concolicLength.getConcreteValue(), this);
        return getAllocator().createNewReferenceArray(componentType, concolicLength);
    }

    private BaseQuickNode getBaseQuickNode(int curBCI, int top, int statementIndex, BaseQuickNode quickNode) {
        // block while class redefinition is ongoing
        getMethod().getContext().getClassRedefinition().check();
        // re-check if node was already replaced by another thread
        if (quickNode != nodes[readCPI(curBCI)]) {
            // another thread beat us
            return nodes[readCPI(curBCI)];
        }
        BytecodeStream original = new BytecodeStream(getMethodVersion().getCodeAttribute().getOriginalCode());
        char originalCpi = original.readCPI(curBCI);
        int originalOpcode = original.currentBC(curBCI);
        ResolvedInvoke resolvedInvoke = reResolvedInvoke(originalOpcode, originalCpi);
        return atomic(() -> {
            char cpi = readCPI(curBCI);
            if (quickNode != nodes[cpi]) {
                // another thread beat us
                return nodes[cpi];
            } else {
                BaseQuickNode newNode = insert(dispatchQuickened(top, curBCI, originalOpcode, statementIndex, resolvedInvoke, getMethod().getContext().getEspressoEnv().bytecodeLevelInlining));
                nodes[cpi] = newNode;
                return newNode;
            }
        });
    }

    private Object getReturnValueAsObject(VirtualFrame frame, int top) {
        Symbol<Type> returnType = SignatureSymbols.returnType(getMethod().getParsedSignature());
        // @formatter:off
        switch (returnType.byteAt(0)) {
            case 'Z' : {
                return popConcolicBoolean(frame, top - 1);
            }
            case 'B' : {
                return popConcolicByte(frame, top - 1);
            }
            case 'S' : {
                return popConcolicShort(frame, top - 1);
            }
            case 'C' : {
                return popConcolicChar(frame, top - 1);
            }
            case 'I' : {
                return popConcolicInt(frame, top - 1);
            }
            case 'J' : {
                return popConcolicLong(frame, top - 1);
            }
            case 'F' : {
                return popConcolicFloat(frame, top - 1);
            }
            case 'D' : {
                return popConcolicDouble(frame, top - 1);
            }
            case 'V' : {
                return ConcolicObjectFactory.createWithoutConstraints(StaticObject.NULL); // void
            }
            case '[' : // fall through
            case 'L' : {
                return popConcolicObject(frame, top - 1);
            }
            default:
                CompilerDirectives.transferToInterpreterAndInvalidate();
                throw EspressoError.shouldNotReachHere();
        }
        // @formatter:on
    }

    @ExplodeLoop
    private void clearOperandStack(VirtualFrame frame, int top) {
        int stackStart = startingStackOffset(getMethodVersion().getMaxLocals());
        for (int slot = top - 1; slot >= stackStart; --slot) {
            clear(frame, slot);
        }
    }

    @Override
    MethodVersion getMethodVersion() {
        return methodVersion;
    }

    private ObjectKlass getDeclaringKlass() {
        return methodVersion.getDeclaringKlass();
    }

    private EspressoRootNode getRoot() {
        if (rootNode == null) {
            CompilerDirectives.transferToInterpreterAndInvalidate();
            rootNode = (EspressoRootNode) getRootNode();
        }
        return rootNode;
    }

    @Override
    public int getBci(Frame frame) {
        return getBCI(frame);
    }

    @Override
    public InstrumentableNode materializeInstrumentableNodes(Set<Class<? extends Tag>> materializedTags) {
        InstrumentationSupport info = this.instrumentation;
        if (info == null && materializedTags.contains(StatementTag.class)) {
            Lock lock = getLock();
            lock.lock();
            try {
                info = this.instrumentation;
                // double checked locking
                if (info == null) {
                    generifyBytecodeLevelInlining();
                    this.instrumentation = info = insert(new InstrumentationSupport(getMethodVersion()));
                    // the debug info contains instrumentable nodes so we need to notify for
                    // instrumentation updates.
                    notifyInserted(info);
                }
            } finally {
                lock.unlock();
            }
        }
        return this;
    }

    private static boolean takeBranchRef1(StaticObject operand, int opcode) {
        assert IFNULL <= opcode && opcode <= IFNONNULL;
        // @formatter:off
        switch (opcode) {
            case IFNULL    : return StaticObject.isNull(operand);
            case IFNONNULL : return StaticObject.notNull(operand);
            default        :
                CompilerDirectives.transferToInterpreterAndInvalidate();
                throw EspressoError.shouldNotReachHere("expected IFNULL or IFNONNULL bytecode");
        }
        // @formatter:on
    }

    private static boolean takeConcolicBranchRef1(ConcolicObject operand, int opcode) {
        // XXX: YJ: required to handle object null check concolically?
        assert IFNULL <= opcode && opcode <= IFNONNULL;
        // @formatter:off
        switch (opcode) {
            case IFNULL    : return StaticObject.isNull((StaticObject)operand.getConcreteValue());
            case IFNONNULL : return StaticObject.notNull((StaticObject)operand.getConcreteValue());
            default        :
                CompilerDirectives.transferToInterpreterAndInvalidate();
                throw EspressoError.shouldNotReachHere("expected IFNULL or IFNONNULL bytecode");
        }
        // @formatter:on
    }


    private static boolean takeBranchPrimitive1(int operand, int opcode) {
        assert IFEQ <= opcode && opcode <= IFLE;
        // @formatter:off
        switch (opcode) {
            case IFEQ      : return operand == 0;
            case IFNE      : return operand != 0;
            case IFLT      : return operand  < 0;
            case IFGE      : return operand >= 0;
            case IFGT      : return operand  > 0;
            case IFLE      : return operand <= 0;
            default        :
                CompilerDirectives.transferToInterpreterAndInvalidate();
                throw EspressoError.shouldNotReachHere("expecting IFEQ,IFNE,IFLT,IFGE,IFGT,IFLE");
        }
        // @formatter:on
    }

    private static boolean takeBranchPrimitiveConcolic1(ConcolicInt operand, int opcode, String[] branchIdentifier) {
        assert IFEQ <= opcode && opcode <= IFLE;

        int rawOperand = operand.getConcreteValue();
        boolean concreteReturnValue = false;
        String identifier = "";
        // @formatter:off
        switch (opcode) {
            case IFEQ      : concreteReturnValue = rawOperand == 0; identifier = "EQ"; break;
            case IFNE      : concreteReturnValue = rawOperand != 0; identifier = "NE"; break;
            case IFLT      : concreteReturnValue = rawOperand  < 0; identifier = "LT"; break;
            case IFGE      : concreteReturnValue = rawOperand >= 0; identifier = "GE"; break;
            case IFGT      : concreteReturnValue = rawOperand  > 0; identifier = "GT"; break;
            case IFLE      : concreteReturnValue = rawOperand <= 0; identifier = "LE"; break;
            default        :
                CompilerDirectives.transferToInterpreterAndInvalidate();
                throw EspressoError.shouldNotReachHere("expecting IFEQ,IFNE,IFLT,IFGE,IFGT,IFLE");
        }
        // @formatter:on

        /* symbolic execution */
        if (operand.isSymbolic()) {
            ConcolicBranch br = new ConcolicBranch();
            boolean isSymbolicBranch = br.setIF(opcode, operand, concreteReturnValue);
            if (isSymbolicBranch) {
                br.setIdentifier(branchIdentifier);
                if (Logger.compileLog) {
                    Logger.DEBUG("[IF" + identifier + ", " + br.isTaken() + "] " + br.getExpr());
                }
                ConcolicBranch.addBranch(br);
            }
        }
        return concreteReturnValue;
    }


    private static boolean takeBranchPrimitive2(int operand1, int operand2, int opcode) {
        assert IF_ICMPEQ <= opcode && opcode <= IF_ICMPLE;
        // @formatter:off
        switch (opcode) {
            case IF_ICMPEQ : return operand1 == operand2;
            case IF_ICMPNE : return operand1 != operand2;
            case IF_ICMPLT : return operand1  > operand2;
            case IF_ICMPGE : return operand1 <= operand2;
            case IF_ICMPGT : return operand1  < operand2;
            case IF_ICMPLE : return operand1 >= operand2;
            default        :
                CompilerDirectives.transferToInterpreterAndInvalidate();
                throw EspressoError.shouldNotReachHere("expecting IF_ICMPEQ,IF_ICMPNE,IF_ICMPLT,IF_ICMPGE,IF_ICMPGT,IF_ICMPLE");
        }
        // @formatter:on
    }

    private static boolean takeBranchPrimitiveConcolic2(ConcolicInt operand1, ConcolicInt operand2, int opcode, String[] branchIdentifier) {

        assert IF_ICMPEQ <= opcode && opcode <= IF_ICMPLE;

        /* concrete execution */
        int ioperand1 = operand1.getConcreteValue();
        int ioperand2 = operand2.getConcreteValue();
        boolean concreteReturnValue = false;
        String identifier = "";
        // @formatter:off
        switch (opcode) {
            case IF_ICMPEQ : concreteReturnValue = ioperand1 == ioperand2; identifier = "EQ"; break;
            case IF_ICMPNE : concreteReturnValue = ioperand1 != ioperand2; identifier = "NE"; break;
            case IF_ICMPLT : concreteReturnValue = ioperand1  > ioperand2; identifier = "LT"; break;
            case IF_ICMPGE : concreteReturnValue = ioperand1 <= ioperand2; identifier = "GE"; break;
            case IF_ICMPGT : concreteReturnValue = ioperand1  < ioperand2; identifier = "GT"; break;
            case IF_ICMPLE : concreteReturnValue = ioperand1 >= ioperand2; identifier = "LE"; break;
            default        :
                CompilerDirectives.transferToInterpreterAndInvalidate();
                throw EspressoError.shouldNotReachHere("expecting IF_ICMPEQ,IF_ICMPNE,IF_ICMPLT,IF_ICMPGE,IF_ICMPGT,IF_ICMPLE");
        }

        /* symbolic execution */
        if (ConcolicValueHelper.eitherSymbolic(operand1, operand2)) {
            /*
             1. get expressions
             2. generate icmp expressions
             3. set that as path condition
             4. mark taken/untaken
             */
            ConcolicBranch br = new ConcolicBranch();
            boolean isSymbolicBranch = br.setICMP(opcode, operand1, operand2, concreteReturnValue);
            if (isSymbolicBranch) {
                br.setIdentifier(branchIdentifier);
                if (Logger.compileLog) {
                    Logger.DEBUG("[ICMP" + identifier + ", " + br.isTaken() + "] " + operand1.getExpr() +" vs " + operand2.getExpr() + " : " + br.getExpr());
                }
                ConcolicBranch.addBranch(br);
            }
        }

        return concreteReturnValue;

        /*
        switch (opcode) {
            case IF_ICMPEQ : return operand1.getConcreteValue() == operand2.getConcreteValue();
            case IF_ICMPNE : return operand1.getConcreteValue() != operand2.getConcreteValue();
            case IF_ICMPLT : return operand1.getConcreteValue()  > operand2.getConcreteValue();
            case IF_ICMPGE : return operand1.getConcreteValue() <= operand2.getConcreteValue();
            case IF_ICMPGT : return operand1.getConcreteValue()  < operand2.getConcreteValue();
            case IF_ICMPLE : return operand1.getConcreteValue() >= operand2.getConcreteValue();
            default        :
                CompilerDirectives.transferToInterpreterAndInvalidate();
                throw EspressoError.shouldNotReachHere("expecting IF_ICMPEQ,IF_ICMPNE,IF_ICMPLT,IF_ICMPGE,IF_ICMPGT,IF_ICMPLE");
        }
        */
        // @formatter:on
    }

    private boolean takeBranchRef2(StaticObject operand1, StaticObject operand2, int opcode) {
        assert IF_ACMPEQ <= opcode && opcode <= IF_ACMPNE;
        // @formatter:off
        if (noForeignObjects.isValid()) {
            switch (opcode) {
                case IF_ACMPEQ:
                    return operand1 == operand2;
                case IF_ACMPNE:
                    return operand1 != operand2;
                default:
                    CompilerDirectives.transferToInterpreterAndInvalidate();
                    throw EspressoError.shouldNotReachHere("expecting IF_ACMPEQ,IF_ACMPNE");
            }
        } else {
            boolean equal = InterpreterToVM.referenceIdentityEqual(operand1, operand2, getLanguage());
            switch (opcode) {
                case IF_ACMPEQ: {
                    return equal;
                }
                case IF_ACMPNE: {
                    return !equal;
                }
                default:
                    CompilerDirectives.transferToInterpreterAndInvalidate();
                    throw EspressoError.shouldNotReachHere("expecting IF_ACMPEQ,IF_ACMPNE");
            }
        }
        // @formatter:on
    }

    private boolean takeConcolicBranchRef2(ConcolicObject operand1, ConcolicObject operand2, int opcode) {
        // XXX: YJ: required to handle concolic object equality?
        assert IF_ACMPEQ <= opcode && opcode <= IF_ACMPNE;
        // @formatter:off
        if (noForeignObjects.isValid()) {
            switch (opcode) {
                case IF_ACMPEQ:
                    return ((StaticObject) operand1.getConcreteValue()) ==
                                        ((StaticObject) operand2.getConcreteValue());
                case IF_ACMPNE:
                    return ((StaticObject) operand1.getConcreteValue()) !=
                                        ((StaticObject) operand2.getConcreteValue());
                default:
                    CompilerDirectives.transferToInterpreterAndInvalidate();
                    throw EspressoError.shouldNotReachHere("expecting IF_ACMPEQ,IF_ACMPNE");
            }
        } else {
            boolean equal = InterpreterToVM.referenceIdentityEqual((StaticObject) operand1.getConcreteValue(),
                                    (StaticObject) operand2.getConcreteValue(), getLanguage());
            switch (opcode) {
                case IF_ACMPEQ: {
                    return equal;
                }
                case IF_ACMPNE: {
                    return !equal;
                }
                default:
                    CompilerDirectives.transferToInterpreterAndInvalidate();
                    throw EspressoError.shouldNotReachHere("expecting IF_ACMPEQ,IF_ACMPNE");
            }
        }
        // @formatter:on
    }


    private void arrayLength(VirtualFrame frame, int top, int curBCI) {
        ConcolicObject concolicObject = nullCheck(popConcolicObject(frame, top - 1));
        if (Logger.compileLog) {
            Logger.DEBUG("ARRAY: " + concolicObject);
        }
        StaticObject array = (StaticObject) concolicObject.getConcreteValue();
        if (noForeignObjects.isValid() || array.isEspressoObject()) {
            int concrete = InterpreterToVM.arrayLength(array, getLanguage());
            ConcolicInt concolic = null;
            if (concolicObject instanceof ConcolicArrayObject concolicArray) {
                concolic = concolicArray.getSize();
            }
            if (concolic == null || concrete != concolic.getConcreteValue()) {
                concolic = ConcolicInt.createWithoutConstraints(concrete);
            }
            if (Logger.compileLog) {
                Logger.DEBUG("concrete: " + concrete + ", concolic: " + concolic);
            }
            putConcolicInt(frame, top - 1, concolic);
        } else {
            CompilerDirectives.transferToInterpreterAndInvalidate();
            // The array was released, it must be restored for the quickening.
            putConcolicObject(frame, top - 1, concolicObject);
            // The stack effect difference vs. original bytecode is always 0.
            quickenArrayLength(frame, top, curBCI);
        }
    }

    private void arrayLoad(VirtualFrame frame, int top, int curBCI, int loadOpcode) {
        assert IALOAD <= loadOpcode && loadOpcode <= SALOAD;
        CompilerAsserts.partialEvaluationConstant(loadOpcode);
        ConcolicInt concolicIndex = popConcolicInt(frame, top - 1);
        ConcolicObject concolicObject = nullCheck(popConcolicObject(frame, top - 2));
        int index = concolicIndex.getConcreteValue();
        StaticObject array = nullCheck((StaticObject) concolicObject.getConcreteValue());
        if (Logger.compileLog) {
            Logger.DEBUG("ARRAY LOAD VAL: " + concolicObject);
            Logger.DEBUG("ARRAY LOAD IDX: " + concolicIndex);
            if (!(concolicObject instanceof ConcolicArrayObject)) {
                Logger.WARNING("Not array: " + concolicObject + ":" + ((ConcolicObjectImpl) concolicObject).getConcreteObject().isArray());
            }
        }
        if (noForeignObjects.isValid() || array.isEspressoObject()) {
            EspressoLanguage language = getLanguage();
            // @formatter:off
            switch (loadOpcode) {
                case BALOAD: {
                    byte concrete = getInterpreterToVM().getArrayByte(language, index, array, this);
                    ConcolicByte concolic = null;
                    if (concolicObject instanceof ConcolicArrayObject concolicArray) {
                        concolic = (ConcolicByte) concolicArray.getElement(index);
                    }
                    if (concolic == null || concolic.getConcreteValue() != concrete) {
                        if (Logger.compileLog && concolic != null && concolic.isSymbolic()) {
                            Logger.WARNING("ARRAY LOAD Mismatch concolic: " + concolic + ", concrete: " + concrete);
                        }
                        concolic = ConcolicByte.createWithoutConstraints(concrete);
                        if (concolicObject instanceof ConcolicArrayObject concolicArray) {
                            concolicArray.setElement(index, concolic);
                        }
                    }
                    if (Logger.compileLog) {
                        Logger.DEBUG("concrete: " + concrete + ", concolic: " + concolic);
                    }
                    putConcolicByte(frame, top - 2, concolic);
                    break;
                }
                case SALOAD: {
                    short concrete = getInterpreterToVM().getArrayShort(language, index, array, this);
                    ConcolicShort concolic = null;
                    if (concolicObject instanceof ConcolicArrayObject concolicArray) {
                        concolic = (ConcolicShort) concolicArray.getElement(index);
                    }
                    if (concolic == null || concolic.getConcreteValue() != concrete) {
                        if (Logger.compileLog && concolic != null && concolic.isSymbolic()) {
                            Logger.WARNING("ARRAY LOAD Mismatch concolic: " + concolic + ", concrete: " + concrete);
                        }
                        concolic = ConcolicShort.createWithoutConstraints(concrete);
                        if (concolicObject instanceof ConcolicArrayObject concolicArray) {
                            concolicArray.setElement(index, concolic);
                        }
                    }
                    if (Logger.compileLog) {
                        Logger.DEBUG("concrete: " + concrete + ", concolic: " + concolic);
                    }
                    putConcolicShort(frame, top - 2, concolic);
                    break;
                }
                case CALOAD: {
                    char concrete = getInterpreterToVM().getArrayChar(language, index, array, this);
                    ConcolicChar concolic = null;
                    if (concolicObject instanceof ConcolicArrayObject concolicArray) {
                        concolic = (ConcolicChar) concolicArray.getElement(index);
                    }
                    if (concolic == null || concolic.getConcreteValue() != concrete) {
                        if (Logger.compileLog && concolic != null && concolic.isSymbolic()) {
                            Logger.WARNING("ARRAY LOAD Mismatch concolic: " + concolic + ", concrete: " + concrete);
                        }
                        concolic = ConcolicChar.createWithoutConstraints(concrete);
                        if (concolicObject instanceof ConcolicArrayObject concolicArray) {
                            concolicArray.setElement(index, concolic);
                        }
                    }
                    if (Logger.compileLog) {
                        Logger.DEBUG("concrete: " + concrete + ", concolic: " + concolic);
                    }
                    putConcolicChar(frame, top - 2, concolic);
                    break;
                }
                case IALOAD: {
                    int concrete = getInterpreterToVM().getArrayInt(language, index, array, this);
                    ConcolicInt concolic = null;
                    if (concolicObject instanceof ConcolicArrayObject concolicArray) {
                        concolic = (ConcolicInt) concolicArray.getElement(index);
                    }
                    if (concolic == null || concolic.getConcreteValue() != concrete) {
                        if (Logger.compileLog && concolic != null && concolic.isSymbolic()) {
                            Logger.WARNING("ARRAY LOAD Mismatch concolic: " + concolic + ", concrete: " + concrete);
                        }
                        concolic = ConcolicInt.createWithoutConstraints(concrete);
                        if (concolicObject instanceof ConcolicArrayObject concolicArray) {
                            concolicArray.setElement(index, concolic);
                        }
                    }
                    if (Logger.compileLog) {
                        Logger.DEBUG("concrete: " + concrete + ", concolic: " + concolic);
                    }
                    putConcolicInt(frame, top - 2, concolic);
                    break;
                }
                case FALOAD: {
                    float concrete = getInterpreterToVM().getArrayFloat(language, index, array, this);
                    ConcolicFloat concolic = null;
                    if (concolicObject instanceof ConcolicArrayObject concolicArray) {
                        concolic = (ConcolicFloat) concolicArray.getElement(index);
                    }
                    if (concolic == null || concolic.getConcreteValue() != concrete) {
                        concolic = ConcolicFloat.createWithoutConstraints(concrete);
                        if (concolicObject instanceof ConcolicArrayObject concolicArray) {
                            concolicArray.setElement(index, concolic);
                        }
                    }
                    if (Logger.compileLog) {
                        Logger.DEBUG("concrete: " + concrete + ", concolic: " + concolic);
                    }
                    putConcolicFloat(frame, top - 2, concolic);
                    break;
                }
                case LALOAD: {
                    long concrete = getInterpreterToVM().getArrayLong(language, index, array, this);
                    ConcolicLong concolic = null;
                    if (concolicObject instanceof ConcolicArrayObject concolicArray) {
                        concolic = (ConcolicLong) concolicArray.getElement(index);
                    }
                    if (concolic == null || concolic.getConcreteValue() != concrete) {
                        if (Logger.compileLog && concolic != null && concolic.isSymbolic()) {
                            Logger.WARNING("ARRAY LOAD Mismatch concolic: " + concolic + ", concrete: " + concrete);
                        }
                        concolic = ConcolicLong.createWithoutConstraints(concrete);
                        if (concolicObject instanceof ConcolicArrayObject concolicArray) {
                            concolicArray.setElement(index, concolic);
                        }
                    }
                    if (Logger.compileLog) {
                        Logger.DEBUG("concrete: " + concrete + ", concolic: " + concolic);
                    }
                    putConcolicLong(frame, top - 2, concolic);
                    break;
                }
                case DALOAD: {
                    double concrete = getInterpreterToVM().getArrayDouble(language, index, array, this);
                    ConcolicDouble concolic = null;
                    if (concolicObject instanceof ConcolicArrayObject concolicArray) {
                        concolic = (ConcolicDouble) concolicArray.getElement(index);
                    }
                    if (concolic == null || concolic.getConcreteValue() != concrete) {
                        if (Logger.compileLog && concolic != null && concolic.isSymbolic()) {
                            Logger.WARNING("ARRAY LOAD Mismatch concolic: " + concolic + ", concrete: " + concrete);
                        }
                        concolic = ConcolicDouble.createWithoutConstraints(concrete);
                        if (concolicObject instanceof ConcolicArrayObject concolicArray) {
                            concolicArray.setElement(index, concolic);
                        }
                    }
                    if (Logger.compileLog) {
                        Logger.DEBUG("concrete: " + concrete + ", concolic: " + concolic);
                    }
                    putConcolicDouble(frame, top - 2, concolic);
                    break;
                }
                case AALOAD: {
                    StaticObject concrete = getInterpreterToVM().getArrayObject(language, index, array, this);
                    ConcolicObjectImpl concolic = null;
                    if (concolicObject instanceof ConcolicArrayObject concolicArray) {
                        concolic = (ConcolicObjectImpl) concolicArray.getElement(index);
                    }
                    boolean isEqual = (concolic == null) ? false
                            : InterpreterToVM.referenceIdentityEqual(concrete, concolic.getConcreteObject(), getLanguage());
                    if (!isEqual) {
                        if (concolic != null && StaticObject.notNull(concolic.getConcreteObject())) {
                            String concolicHash = Integer.toHexString(concolic.getIdentityHashCode());
                            String concreteHash = Integer.toHexString(System.identityHashCode(concrete));
                            if (Logger.compileLog && concolic.isSymbolic()) {
                                Logger.WARNING("ARRAY LOAD Mismatch hashcode - concrete: " + concrete + "@" + concreteHash + ", concolic: " + concolic);
                            }
                        }
                        concolic = (ConcolicObjectImpl) ConcolicObjectFactory.createWithoutConstraints(concrete);
                        if (concolicObject instanceof ConcolicArrayObject concolicArray) {
                            concolicArray.setElement(index, concolic);
                        }
                    }
                    if (Logger.compileLog) {
                        Logger.DEBUG("concrete: " + concrete + ", concolic: " + concolic);
                    }
                    putConcolicObject(frame, top - 2, concolic);
                    break;
                }
                default:
                    CompilerDirectives.transferToInterpreterAndInvalidate();
                    throw EspressoError.shouldNotReachHere();
            }
            // @formatter:on
        } else {
            if (Logger.compileLog) {
                Logger.DEBUG("arrayLoad: else");
            }
            CompilerDirectives.transferToInterpreterAndInvalidate();
            // The array was released, it must be restored for the quickening.
            putConcolicInt(frame, top - 1, concolicIndex);
            putConcolicObject(frame, top - 2, concolicObject);
            // The stack effect difference vs. original bytecode is always 0.
            quickenArrayLoad(frame, top, curBCI, loadOpcode);
        }
    }

    private void arrayStore(VirtualFrame frame, int top, int curBCI, int storeOpcode) {
        assert IASTORE <= storeOpcode && storeOpcode <= SASTORE;
        CompilerAsserts.partialEvaluationConstant(storeOpcode);
        int offset = (storeOpcode == LASTORE || storeOpcode == DASTORE) ? 2 : 1;
        ConcolicInt concolicIndex = popConcolicInt(frame, top - 1 - offset);
        int index = concolicIndex.getConcreteValue();
        ConcolicObject concolicObject = nullCheck(popConcolicObject(frame, top - 2 - offset));
        StaticObject array = (StaticObject) concolicObject.getConcreteValue();
        if (Logger.compileLog) {
            Logger.DEBUG("ARRAY STORE VAL: " + concolicObject);
            Logger.DEBUG("ARRAY STORE IDX: " + concolicIndex);
            if (!(concolicObject instanceof ConcolicArrayObject)) {
                Logger.WARNING("Not array: " + concolicObject + ":" + ((ConcolicObjectImpl) concolicObject).getConcreteObject().isArray());
            }
        }
        if (noForeignObjects.isValid() || array.isEspressoObject()) {
            EspressoLanguage language = getLanguage();
            // @formatter:off
            switch (storeOpcode) {
                case BASTORE: {
                    ConcolicByte concolic = popConcolicByte(frame, top - 1);
                    byte concrete = concolic.getConcreteValue();
                    if (concolicObject instanceof ConcolicArrayObject concolicArray) {
                        concolicArray.setElement(index, concolic);
                    }
                    if (Logger.compileLog) {
                        Logger.DEBUG("concrete: " + concrete + ", concolic: " + concolic);
                    }
                    getInterpreterToVM().setArrayByte(language, concrete, index, array, this);
                    break;
                }
                case SASTORE: {
                    ConcolicShort concolic = popConcolicShort(frame, top - 1);
                    short concrete = concolic.getConcreteValue();
                    if (concolicObject instanceof ConcolicArrayObject concolicArray) {
                        concolicArray.setElement(index, concolic);
                    }
                    if (Logger.compileLog) {
                        Logger.DEBUG("concrete: " + concrete + ", concolic: " + concolic);
                    }
                    getInterpreterToVM().setArrayShort(language, concrete, index, array, this);
                    break;
                }
                case CASTORE: {
                    ConcolicChar concolic = popConcolicChar(frame, top - 1);
                    char concrete = concolic.getConcreteValue();
                    if (concolicObject instanceof ConcolicArrayObject concolicArray) {
                        concolicArray.setElement(index, concolic);
                    }
                    if (Logger.compileLog) {
                        Logger.DEBUG("concrete: " + concrete + ", concolic: " + concolic);
                    }
                    getInterpreterToVM().setArrayChar(language, concrete, index, array, this);
                    break;
                }
                case IASTORE: {
                    ConcolicInt concolic = popConcolicInt(frame, top - 1);
                    int concrete = concolic.getConcreteValue();
                    if (concolicObject instanceof ConcolicArrayObject concolicArray) {
                        concolicArray.setElement(index, concolic);
                    }
                    if (Logger.compileLog) {
                        Logger.DEBUG("concrete: " + concrete + ", concolic: " + concolic);
                    }
                    getInterpreterToVM().setArrayInt(language, concrete, index, array, this);
                    break;
                }
                case FASTORE: {
                    ConcolicFloat concolic = popConcolicFloat(frame, top - 1);
                    float concrete = concolic.getConcreteValue();
                    if (concolicObject instanceof ConcolicArrayObject concolicArray) {
                        concolicArray.setElement(index, concolic);
                    }
                    if (Logger.compileLog) {
                        Logger.DEBUG("concrete: " + concrete + ", concolic: " + concolic);
                    }
                    getInterpreterToVM().setArrayFloat(language, concrete, index, array, this);
                    break;
                }
                case LASTORE: {
                    ConcolicLong concolic = popConcolicLong(frame, top - 1);
                    long concrete = concolic.getConcreteValue();
                    if (concolicObject instanceof ConcolicArrayObject concolicArray) {
                        concolicArray.setElement(index, concolic);
                    }
                    if (Logger.compileLog) {
                        Logger.DEBUG("concrete: " + concrete + ", concolic: " + concolic);
                    }
                    getInterpreterToVM().setArrayLong(language, concrete, index, array, this);
                    break;
                }
                case DASTORE: {
                    ConcolicDouble concolic = popConcolicDouble(frame, top - 1);
                    double concrete = concolic.getConcreteValue();
                    if (concolicObject instanceof ConcolicArrayObject concolicArray) {
                        concolicArray.setElement(index, concolic);
                    }
                    if (Logger.compileLog) {
                        Logger.DEBUG("concrete: " + concrete + ", concolic: " + concolic);
                    }
                    getInterpreterToVM().setArrayDouble(language, concrete, index, array, this);
                    break;
                }
                case AASTORE: {
                    ConcolicObject concolic = popConcolicObject(frame, top - 1);
                    StaticObject concrete = (StaticObject) concolic.getConcreteValue();
                    if (concolicObject instanceof ConcolicArrayObject concolicArray) {
                        concolicArray.setElement(index, concolic);
                    }
                    if (Logger.compileLog) {
                        Logger.DEBUG("concrete: " + concrete + ", concolic: " + concolic);
                    }
                    referenceArrayStore(frame, top, concrete, index, array);
                    break;
                }
                default:
                    CompilerDirectives.transferToInterpreterAndInvalidate();
                    throw EspressoError.shouldNotReachHere();
            }
            // @formatter:on
        } else {
            if (Logger.compileLog) {
                Logger.DEBUG("arrayStore: else");
            }
            CompilerDirectives.transferToInterpreterAndInvalidate();
            // The array was released, it must be restored for the quickening.
            putConcolicInt(frame, top - 1 - offset, concolicIndex);
            putConcolicObject(frame, top - 2 - offset, concolicObject);
            // The stack effect difference vs. original bytecode is always 0.
            quickenArrayStore(frame, top, curBCI, storeOpcode);
        }
    }

    private void referenceArrayStore(VirtualFrame frame, int top, StaticObject element, int index, StaticObject array) {
        if (refArrayStoreNode == null) {
            CompilerDirectives.transferToInterpreterAndInvalidate();
            atomic(() -> {
                if (refArrayStoreNode == null) {
                    refArrayStoreNode = insert(new EspressoReferenceArrayStoreNode());
                }
            });
        }
        refArrayStoreNode.arrayStore(getLanguage(), getContext().getMeta(), element, index, array);
    }

    private int beforeJumpChecks(VirtualFrame frame, int curBCI, int targetBCI, int top, int statementIndex, InstrumentationSupport instrument, Counter loopCount, boolean skipLivenessActions) {
        CompilerAsserts.partialEvaluationConstant(targetBCI);
        int nextStatementIndex = (instrument == null) ? InstrumentationSupport.NO_STATEMENT : instrument.getStatementIndexAfterJump(statementIndex, curBCI, targetBCI);
        if (nextStatementIndex != statementIndex) {
            instrument.notifyStatementChange(frame, statementIndex, nextStatementIndex, targetBCI);
        }
        if (targetBCI <= curBCI) {
            TruffleSafepoint.poll(this);
            if (CompilerDirectives.hasNextTier() && ++loopCount.value >= REPORT_LOOP_STRIDE) {
                LoopNode.reportLoopCount(this, REPORT_LOOP_STRIDE);
                loopCount.value = 0;
            }
            if (CompilerDirectives.inInterpreter() && BytecodeOSRNode.pollOSRBackEdge(this)) {
                livenessAnalysis.catchUpOSR(frame, targetBCI, skipLivenessActions);
                Object osrResult;
                try {
                    osrResult = BytecodeOSRNode.tryOSR(this, targetBCI, new EspressoOSRInterpreterState(top, nextStatementIndex), null, frame);
                } catch (Throwable any) {
                    // Has already been guest-handled in OSR. Shortcut out of the method.
                    throw new EspressoOSRReturnException(any);
                }
                if (osrResult != null) {
                    throw new EspressoOSRReturnException(osrResult);
                }
            }
        }
        livenessAnalysis.performOnEdge(frame, curBCI, targetBCI, skipLivenessActions);
        return nextStatementIndex;
    }

    @ExplodeLoop
    @SuppressWarnings("unused")
    private ExceptionHandler resolveExceptionHandlers(int bci, StaticObject ex) {
        CompilerAsserts.partialEvaluationConstant(bci);
        ExceptionHandler[] handlers = getMethodVersion().getExceptionHandlers();
        ExceptionHandler resolved = null;
        for (ExceptionHandler toCheck : handlers) {
            if (toCheck.covers(bci)) {
                Klass catchType = null;
                if (!toCheck.isCatchAll()) {
                    // exception handlers are similar to instanceof bytecodes, so we pass instanceof
                    catchType = resolveType(Bytecodes.INSTANCEOF, (char) toCheck.catchTypeCPI());
                }
                if (catchType == null || InterpreterToVM.instanceOf(ex, catchType)) {
                    // the first found exception handler is our exception handler
                    resolved = toCheck;
                    break;
                }
            }
        }
        return resolved;
    }

    private void putPoolConstant(VirtualFrame frame, int top, char cpi, int opcode) {
        assert opcode == LDC || opcode == LDC_W || opcode == LDC2_W;
        RuntimeConstantPool pool = getConstantPool();
        PoolConstant constant = pool.at(cpi);
        if (constant instanceof IntegerConstant) {
            assert opcode == LDC || opcode == LDC_W;
            putInt(frame, top, ((IntegerConstant) constant).value());
        } else if (constant instanceof LongConstant) {
            assert opcode == LDC2_W;
            putLong(frame, top, ((LongConstant) constant).value());
        } else if (constant instanceof DoubleConstant) {
            assert opcode == LDC2_W;
            putDouble(frame, top, ((DoubleConstant) constant).value());
        } else if (constant instanceof FloatConstant) {
            assert opcode == LDC || opcode == LDC_W;
            putFloat(frame, top, ((FloatConstant) constant).value());
        } else if (constant instanceof StringConstant) {
            assert opcode == LDC || opcode == LDC_W;
            StaticObject internedString = pool.resolvedStringAt(cpi);
            putObject(frame, top, internedString);
        } else if (constant instanceof ClassConstant) {
            assert opcode == LDC || opcode == LDC_W;
            Klass klass = pool.resolvedKlassAt(getDeclaringKlass(), cpi);
            putObject(frame, top, klass.mirror());
        } else if (constant instanceof MethodHandleConstant) {
            assert opcode == LDC || opcode == LDC_W;
            StaticObject methodHandle = pool.resolvedMethodHandleAt(getDeclaringKlass(), cpi);
            putObject(frame, top, methodHandle);
        } else if (constant instanceof MethodTypeConstant) {
            assert opcode == LDC || opcode == LDC_W;
            StaticObject methodType = pool.resolvedMethodTypeAt(getDeclaringKlass(), cpi);
            putObject(frame, top, methodType);
        } else if (constant instanceof DynamicConstant) {
            ResolvedDynamicConstant dynamicConstant = pool.resolvedDynamicConstantAt(getDeclaringKlass(), cpi);
            dynamicConstant.putResolved(frame, top, this);
        } else {
            CompilerDirectives.transferToInterpreterAndInvalidate();
            throw EspressoError.unimplemented(constant.toString());
        }
    }

    private void putPoolConcolicConstant(VirtualFrame frame, int top, char cpi, int opcode) {
        assert opcode == LDC || opcode == LDC_W || opcode == LDC2_W;
        RuntimeConstantPool pool = getConstantPool();
        PoolConstant constant = pool.at(cpi);
        if (constant instanceof IntegerConstant) {
            assert opcode == LDC || opcode == LDC_W;
            ConcolicInt concolicValue = ConcolicInt.createWithoutConstraints(((IntegerConstant) constant).value());
            putConcolicInt(frame, top, concolicValue);
            //putInt(frame, top, ((IntegerConstant) constant).value());
        } else if (constant instanceof LongConstant) {
            assert opcode == LDC2_W;
            ConcolicLong concolicValue = ConcolicLong.createWithoutConstraints(((LongConstant) constant).value());
            putConcolicLong(frame, top, concolicValue);
            //putLong(frame, top, ((LongConstant) constant).value());
        } else if (constant instanceof DoubleConstant) {
            assert opcode == LDC2_W;
            ConcolicDouble concolicValue = ConcolicDouble.createWithoutConstraints(((DoubleConstant) constant).value());
            putConcolicDouble(frame, top, concolicValue);
            //putDouble(frame, top, ((DoubleConstant) constant).value());
        } else if (constant instanceof FloatConstant) {
            assert opcode == LDC || opcode == LDC_W;
            ConcolicFloat concolicValue = ConcolicFloat.createWithoutConstraints(((FloatConstant) constant).value());
            putConcolicFloat(frame, top, concolicValue);
            //putFloat(frame, top, ((FloatConstant) constant).value());
        } else if (constant instanceof StringConstant) {
            assert opcode == LDC || opcode == LDC_W;
            // TODO YJ: handle string here correctly.
            StaticObject internedString = pool.resolvedStringAt(cpi);
            putObject(frame, top, internedString);
        } else if (constant instanceof ClassConstant) {
            assert opcode == LDC || opcode == LDC_W;
            // TODO YJ: check object here correctly.
            Klass klass = pool.resolvedKlassAt(getDeclaringKlass(), cpi);
            putObject(frame, top, klass.mirror());
        } else if (constant instanceof MethodHandleConstant) {
            assert opcode == LDC || opcode == LDC_W;
            // TODO YJ: check object here correctly.
            StaticObject methodHandle = pool.resolvedMethodHandleAt(getDeclaringKlass(), cpi);
            putObject(frame, top, methodHandle);
        } else if (constant instanceof MethodTypeConstant) {
            assert opcode == LDC || opcode == LDC_W;
            // TODO YJ: check object here correctly.
            StaticObject methodType = pool.resolvedMethodTypeAt(getDeclaringKlass(), cpi);
            putObject(frame, top, methodType);
        } else if (constant instanceof DynamicConstant) {
            // TODO YJ: check object here correctly.
            ResolvedDynamicConstant dynamicConstant = pool.resolvedDynamicConstantAt(getDeclaringKlass(), cpi);
            dynamicConstant.putResolved(frame, top, this);
        } else {
            CompilerDirectives.transferToInterpreterAndInvalidate();
            throw EspressoError.unimplemented(constant.toString());
        }
    }

    private RuntimeConstantPool getConstantPool() {
        return getMethodVersion().getPool();
    }

    @TruffleBoundary
    private BootstrapMethodsAttribute getBootstrapMethods() {
        return (BootstrapMethodsAttribute) (getDeclaringKlass()).getAttribute(BootstrapMethodsAttribute.NAME);
    }

    // region Bytecode quickening

    private char readCPI(int curBCI) {
        assert (!Bytecodes.isQuickenable(bs.currentBC(curBCI)) ||
                        lockIsHeld()) : "Reading the CPI for a quickenable bytecode must be done under the BytecodeNode lock. Please obtain the lock, or use readOriginalCPI.";
        return bs.readCPI(curBCI);
    }

    private char readOriginalCPI(int curBCI) {
        return BytecodeStream.readCPI(getMethodVersion().getOriginalCode(), curBCI);
    }

    private char addQuickNode(BaseQuickNode node) {
        CompilerAsserts.neverPartOfCompilation();
        Objects.requireNonNull(node);
        nodes = Arrays.copyOf(nodes, nodes.length + 1);
        int nodeIndex = nodes.length - 1; // latest empty slot
        nodes[nodeIndex] = insert(node);
        return (char) nodeIndex;
    }

    private void addSlimQuickNode(BaseQuickNode node, int curBCI) {
        CompilerAsserts.neverPartOfCompilation();
        Objects.requireNonNull(node);
        if (sparseNodes == QuickNode.EMPTY_ARRAY) {
            sparseNodes = new QuickNode[code.length];
        }
        sparseNodes[curBCI] = insert(node);
    }

    private void patchBci(int bci, byte opcode, char nodeIndex) {
        CompilerAsserts.neverPartOfCompilation();
        assert Bytecodes.isQuickened(opcode);

        int oldBC = code[bci];
        if (opcode == (byte) QUICK) {
            code[bci + 1] = (byte) ((nodeIndex >> 8) & 0xFF);
            code[bci + 2] = (byte) ((nodeIndex) & 0xFF);
        }
        // NOP-padding.
        for (int i = Bytecodes.lengthOf(opcode); i < Bytecodes.lengthOf(oldBC); ++i) {
            code[bci + i] = (byte) NOP;
        }
        // Make sure the Quickened bytecode is written after the rest, as it is used for
        // synchronization.
        VolatileArrayAccess.volatileWrite(code, bci, opcode);
    }

    private BaseQuickNode injectQuick(int curBCI, BaseQuickNode quick, int opcode) {
        QUICKENED_BYTECODES.inc();
        CompilerAsserts.neverPartOfCompilation();
        if (opcode == SLIM_QUICK) {
            addSlimQuickNode(quick, curBCI);
            patchBci(curBCI, (byte) SLIM_QUICK, (char) 0);
        } else {
            char nodeIndex = addQuickNode(quick);
            patchBci(curBCI, (byte) QUICK, nodeIndex);
        }
        return quick;
    }

    @FunctionalInterface
    private interface QuickNodeFactory<T> {
        BaseQuickNode get(T t);
    }

    @FunctionalInterface
    private interface QuickNodeResolver<T> {
        T get(char cpi);
    }

    private <T> BaseQuickNode tryPatchQuick(int curBCI, QuickNodeResolver<T> resolver, QuickNodeFactory<T> newQuickNode) {
        Object found = atomic(() -> {
            if (bs.currentVolatileBC(curBCI) == QUICK) {
                return nodes[readCPI(curBCI)];
            } else {
                return readCPI(curBCI);
            }
        });
        if (found instanceof BaseQuickNode) {
            return (BaseQuickNode) found;
        }
        char cpi = (char) found;
        // Perform resolution outside the lock: it can call arbitrary guest code.
        T resolved = resolver.get(cpi);
        return atomic(() -> {
            if (bs.currentVolatileBC(curBCI) == QUICK) {
                return nodes[readCPI(curBCI)];
            } else {
                return injectQuick(curBCI, newQuickNode.get(resolved), QUICK);
            }
        });
    }

    @FunctionalInterface
    private interface QuickNodeSupplier {
        BaseQuickNode get();
    }

    private BaseQuickNode tryPatchQuick(int curBCI, QuickNodeSupplier newQuickNode) {
        return tryPatchQuick(curBCI, cpi -> null, unused -> newQuickNode.get());
    }

    private int quickenCheckCast(VirtualFrame frame, int top, int curBCI, int opcode) {
        CompilerAsserts.neverPartOfCompilation();
        assert opcode == CHECKCAST;
        BaseQuickNode quick = tryPatchQuick(curBCI, cpi -> resolveType(CHECKCAST, cpi), k -> new CheckCastQuickNode(k, top, curBCI));
        quick.execute(frame, false);
        assert Bytecodes.stackEffectOf(opcode) == 0;
        return 0; // Bytecodes.stackEffectOf(opcode);
    }

    private int quickenInstanceOf(VirtualFrame frame, int top, int curBCI, int opcode) {
        CompilerAsserts.neverPartOfCompilation();
        assert opcode == INSTANCEOF;
        BaseQuickNode quick = tryPatchQuick(curBCI, cpi -> resolveType(INSTANCEOF, cpi), k -> new InstanceOfQuickNode(k, top, curBCI));
        quick.execute(frame, false);
        assert Bytecodes.stackEffectOf(opcode) == 0;
        return 0; // Bytecodes.stackEffectOf(opcode);
    }

    @SuppressWarnings("try")
    private int quickenInvoke(VirtualFrame frame, int top, int curBCI, int opcode, int statementIndex) {
        InvokeQuickNode quick = quickenInvoke(top, curBCI, opcode, statementIndex);
        if (opcode == INVOKESTATIC && quick instanceof InvokeStaticQuickNode invokeStaticQuickNode) {
            try (EspressoLanguage.DisableSingleStepping ignored = getLanguage().disableStepping()) {
                invokeStaticQuickNode.initializeResolvedKlass();
            }
        }
        // Perform the call outside of the lock.
        // We _subtract_ the stack effect here to undo its effect, as the stack effect of the
        // replaced opcode will be computed by quick.execute(frame), and then re-applied at
        // the bottom of the interpreter loop. So we have to subtract the stack effect to
        // prevent double counting.
        return quick.execute(frame, false) - Bytecodes.stackEffectOf(opcode);
    }

    private InvokeQuickNode quickenInvoke(int top, int curBCI, int opcode, int statementIndex) {
        QUICKENED_INVOKES.inc();
        CompilerDirectives.transferToInterpreterAndInvalidate();
        assert Bytecodes.isInvoke(opcode);
        InvokeQuickNode quick = (InvokeQuickNode) tryPatchQuick(curBCI, cpi -> getResolvedInvoke(opcode, cpi),
                        resolvedInvoke -> dispatchQuickened(top, curBCI, opcode, statementIndex, resolvedInvoke, getMethod().getContext().getEspressoEnv().bytecodeLevelInlining));
        return quick;
    }

    /**
     * Revert speculative quickening e.g. revert inlined fields accessors to a normal invoke.
     * INVOKEVIRTUAL -> QUICK (InlinedGetter/SetterNode) -> QUICK (InvokeVirtualNode)
     */
    public int reQuickenInvoke(VirtualFrame frame, int top, int opcode, int curBCI, int statementIndex) {
        CompilerAsserts.neverPartOfCompilation();
        assert Bytecodes.isInvoke(opcode);
        BaseQuickNode invoke = generifyInlinedMethodNode(top, opcode, curBCI, statementIndex);
        // Perform the call outside of the lock.
        return invoke.execute(frame, false);
    }

    /**
     * Atomically replaces a quick node with another one.
     */
    public int replaceQuickAt(VirtualFrame frame, int opcode, int curBCI, BaseQuickNode old, BaseQuickNode replacement) {
        BaseQuickNode invoke = replaceQuickAt(opcode, curBCI, old, replacement);
        // Perform the call outside of the lock.
        return invoke.execute(frame, false);
    }

    private BaseQuickNode replaceQuickAt(int opcode, int curBCI, BaseQuickNode old, BaseQuickNode replacement) {
        CompilerAsserts.neverPartOfCompilation();
        assert Bytecodes.isInvoke(opcode) || opcode == QUICK;
        BaseQuickNode invoke = atomic(() -> {
            assert bs.currentBC(curBCI) == QUICK;
            char nodeIndex = readCPI(curBCI);
            BaseQuickNode currentQuick = nodes[nodeIndex];
            if (currentQuick != old) {
                // Another thread might have already replaced our node at this point.
                return currentQuick;
            }
            nodes[nodeIndex] = currentQuick.replace(replacement);
            return replacement;
        });
        return invoke;
    }

    /**
     * Reverts Bytecode-level method inlining at the current bci, in case instrumentation starts
     * happening on this node.
     */
    public BaseQuickNode generifyInlinedMethodNode(int top, int opcode, int curBCI, int statementIndex) {
        CompilerAsserts.neverPartOfCompilation();
        ResolvedInvoke resolvedInvoke = getResolvedInvoke(opcode, readOriginalCPI(curBCI));
        return atomic(() -> {
            assert bs.currentBC(curBCI) == QUICK;
            char nodeIndex = readCPI(curBCI);
            BaseQuickNode currentQuick = nodes[nodeIndex];
            if (!(currentQuick instanceof InlinedMethodNode)) {
                // Another thread might have already generify-ed our node at this point.
                // Might be racy, as read is not volatile, but redoing the work should be OK.
                return currentQuick;
            }
            BaseQuickNode invoke = dispatchQuickened(top, curBCI, opcode, statementIndex, resolvedInvoke, false);
            nodes[nodeIndex] = currentQuick.replace(invoke);
            return invoke;
        });
    }

    /**
     * Reverts all bytecode-level inlining to a generic invoke quick node.
     */
    private void generifyBytecodeLevelInlining() {
        atomic(() -> {
            for (BaseQuickNode quick : nodes) {
                if (quick instanceof InlinedMethodNode) {
                    notifyInserted(((InlinedMethodNode) quick).revertToGeneric(this));
                }
            }
        });
    }

    // region quickenForeign
    public int quickenGetField(final VirtualFrame frame, int top, int curBCI, int opcode, int statementIndex, Field field) {
        CompilerDirectives.transferToInterpreterAndInvalidate();
        assert opcode == GETFIELD;
        BaseQuickNode getField = tryPatchQuick(curBCI, () -> new QuickenedGetFieldNode(top, curBCI, statementIndex, field));
        return getField.execute(frame, false) - Bytecodes.stackEffectOf(opcode);
    }

    public int quickenPutField(VirtualFrame frame, int top, int curBCI, int opcode, int statementIndex, Field field) {
        CompilerDirectives.transferToInterpreterAndInvalidate();
        assert opcode == PUTFIELD;
        BaseQuickNode putField = tryPatchQuick(curBCI, () -> new QuickenedPutFieldNode(top, curBCI, field, statementIndex));
        return putField.execute(frame, false) - Bytecodes.stackEffectOf(opcode);
    }

    private int quickenArrayLength(VirtualFrame frame, int top, int curBCI) {
        CompilerDirectives.transferToInterpreterAndInvalidate();
        BaseQuickNode arrayLengthNode = atomic(() -> {
            if (bs.currentVolatileBC(curBCI) == SLIM_QUICK) {
                return sparseNodes[curBCI];
            } else {
                return injectQuick(curBCI, new ArrayLengthQuickNode(top, curBCI), SLIM_QUICK);
            }
        });
        return arrayLengthNode.execute(frame, false) - Bytecodes.stackEffectOf(ARRAYLENGTH);
    }

    private int quickenArrayLoad(VirtualFrame frame, int top, int curBCI, int loadOpcode) {
        CompilerDirectives.transferToInterpreterAndInvalidate();
        assert IALOAD <= loadOpcode && loadOpcode <= SALOAD;
        BaseQuickNode arrayLoadNode = atomic(() -> {
            if (bs.currentVolatileBC(curBCI) == SLIM_QUICK) {
                return sparseNodes[curBCI];
            } else {
                // @formatter:off
                BaseQuickNode quickNode;
                switch (loadOpcode)  {
                    case BALOAD: quickNode = new ByteArrayLoadQuickNode(top, curBCI);   break;
                    case SALOAD: quickNode = new ShortArrayLoadQuickNode(top, curBCI);  break;
                    case CALOAD: quickNode = new CharArrayLoadQuickNode(top, curBCI);   break;
                    case IALOAD: quickNode = new IntArrayLoadQuickNode(top, curBCI);    break;
                    case FALOAD: quickNode = new FloatArrayLoadQuickNode(top, curBCI);  break;
                    case LALOAD: quickNode = new LongArrayLoadQuickNode(top, curBCI);   break;
                    case DALOAD: quickNode = new DoubleArrayLoadQuickNode(top, curBCI); break;
                    case AALOAD: quickNode = new ReferenceArrayLoadQuickNode(top, curBCI); break;
                    default:
                        CompilerDirectives.transferToInterpreterAndInvalidate();
                        throw EspressoError.shouldNotReachHere("unexpected kind");
                }
                // @formatter:on
                return injectQuick(curBCI, quickNode, SLIM_QUICK);
            }
        });
        return arrayLoadNode.execute(frame, false) - Bytecodes.stackEffectOf(loadOpcode);
    }

    private int quickenArrayStore(final VirtualFrame frame, int top, int curBCI, int storeOpcode) {
        CompilerDirectives.transferToInterpreterAndInvalidate();
        assert IASTORE <= storeOpcode && storeOpcode <= SASTORE;
        BaseQuickNode arrayStoreNode = atomic(() -> {
            if (bs.currentVolatileBC(curBCI) == SLIM_QUICK) {
                return sparseNodes[curBCI];
            } else {
                BaseQuickNode quickNode;
                // @formatter:off
                switch (storeOpcode)  {
                    case BASTORE: quickNode = new ByteArrayStoreQuickNode(top, curBCI);   break;
                    case SASTORE: quickNode = new ShortArrayStoreQuickNode(top, curBCI);  break;
                    case CASTORE: quickNode = new CharArrayStoreQuickNode(top, curBCI);   break;
                    case IASTORE: quickNode = new IntArrayStoreQuickNode(top, curBCI);    break;
                    case FASTORE: quickNode = new FloatArrayStoreQuickNode(top, curBCI);  break;
                    case LASTORE: quickNode = new LongArrayStoreQuickNode(top, curBCI);   break;
                    case DASTORE: quickNode = new DoubleArrayStoreQuickNode(top, curBCI); break;
                    case AASTORE: quickNode = new ReferenceArrayStoreQuickNode(top, curBCI); break;
                    default:
                        CompilerDirectives.transferToInterpreterAndInvalidate();
                        throw EspressoError.shouldNotReachHere("unexpected kind");
                }
                // @formatter:on
                return injectQuick(curBCI, quickNode, SLIM_QUICK);
            }
        });
        return arrayStoreNode.execute(frame, false) - Bytecodes.stackEffectOf(storeOpcode);
    }

    // endregion quickenForeign

    private InvokeQuickNode dispatchQuickened(int top, int curBCI, int opcode, int statementIndex, ResolvedInvoke resolvedInvoke, boolean allowBytecodeInlining) {
        ResolvedCall<Klass, Method, Field> resolvedCall = resolvedInvoke.resolvedCall();
        Method resolved = resolvedCall.getResolvedMethod();
        CallKind callKind = resolvedCall.getCallKind();

        // Skip inlined nodes if instrumentation is live.
        // Lock must be owned for correctness.
        assert lockIsHeld();
        boolean tryBytecodeLevelInlining = this.instrumentation == null && allowBytecodeInlining;
        if (tryBytecodeLevelInlining) {
            InlinedMethodNode node = InlinedMethodNode.createFor(resolvedCall, top, opcode, curBCI, statementIndex);
            if (node != null) {
                return node;
            }
        }

        if (resolved.isPolySignatureIntrinsic()) {
            return new InvokeHandleNode(resolved, resolvedInvoke.invoker(), top, curBCI);
        } else {
            // @formatter:off
            return switch (callKind) {
                case STATIC          -> new InvokeStaticQuickNode(resolved, top, curBCI);
                case ITABLE_LOOKUP   -> new InvokeInterfaceQuickNode(resolved, top, curBCI);
                case VTABLE_LOOKUP   -> new InvokeVirtualQuickNode(resolved, top, curBCI);
                case DIRECT          -> new InvokeSpecialQuickNode(resolved, top, curBCI);
            };
            // @formatter:on
        }
    }

    @TruffleBoundary
    private RuntimeException throwBoundary(ObjectKlass exceptionKlass) {
        throw getMeta().throwException(exceptionKlass);
    }

    @TruffleBoundary
    private RuntimeException throwBoundary(ObjectKlass exceptionKlass, String message) {
        throw getMeta().throwExceptionWithMessage(exceptionKlass, message);
    }

    @TruffleBoundary
    private RuntimeException throwBoundary(ObjectKlass exceptionKlass, String messageFormat, Object... args) {
        throw getMeta().throwExceptionWithMessage(exceptionKlass, String.format(Locale.ENGLISH, messageFormat, args));
    }

    private int quickenInvokeDynamic(final VirtualFrame frame, int top, int curBCI, int opcode) {
        CompilerDirectives.transferToInterpreterAndInvalidate();
        assert opcode == Bytecodes.INVOKEDYNAMIC;
        BaseQuickNode quick = tryPatchQuick(curBCI,
                        cpi -> getConstantPool().linkInvokeDynamic(getMethod().getDeclaringKlass(), cpi, getMethod(), curBCI),
                        link -> new InvokeDynamicCallSiteNode(link.getMemberName(), link.getUnboxedAppendix(), link.getParsedSignature(), getMethod().getMeta(), top, curBCI));
        return quick.execute(frame, false) - Bytecodes.stackEffectOf(opcode);
    }

    // endregion Bytecode quickening

    // region Class/Method/Field resolution

    // Exposed to CheckCastNode and InstanceOfNode
    public Klass resolveType(int opcode, char cpi) {
        assert opcode == INSTANCEOF || opcode == CHECKCAST || opcode == NEW || opcode == ANEWARRAY || opcode == MULTIANEWARRAY;
        return getConstantPool().resolvedKlassAt(getDeclaringKlass(), cpi);
    }

    private Field resolveField(int opcode, char cpi) {
        assert opcode == GETFIELD || opcode == GETSTATIC || opcode == PUTFIELD || opcode == PUTSTATIC;
        Field field = getConstantPool().resolvedFieldAt(getMethod().getDeclaringKlass(), cpi);
        if (field.needsReResolution()) {
            CompilerDirectives.transferToInterpreterAndInvalidate();
            getMethod().getContext().getClassRedefinition().check();
            field = getConstantPool().resolveFieldAndUpdate(getMethod().getDeclaringKlass(), cpi, field);
        }
        return field;
    }

    private record ResolvedInvoke(ResolvedCall<Klass, Method, Field> resolvedCall, MethodHandleInvoker invoker) {
    }

    private ResolvedInvoke reResolvedInvoke(int opcode, char cpi) {
        getConstantPool().resolveMethodAndUpdate(getDeclaringKlass(), cpi);
        return getResolvedInvoke(opcode, cpi);
    }

    private ResolvedInvoke getResolvedInvoke(int opcode, char cpi) {
        assert !lockIsHeld();
        // During resolution of the symbolic reference to the method, any of the exceptions
        // pertaining to method resolution (&sect;5.4.3.3) can be thrown.
        MethodRefConstant methodRefConstant = getConstantPool().resolvedMethodRefAt(getDeclaringKlass(), cpi);
        Method resolutionSeed = (Method) ((Resolvable.ResolvedConstant) methodRefConstant).value();

        Klass symbolicRef = Resolution.getResolvedHolderKlass(getConstantPool().methodAt(cpi), getConstantPool(), getDeclaringKlass());
        CallSiteType callSiteType = SiteTypes.callSiteFromOpCode(opcode);
        ResolvedCall<Klass, Method, Field> resolvedCall = EspressoLinkResolver.resolveCallSiteOrThrow(getContext(), getDeclaringKlass(), resolutionSeed, callSiteType, symbolicRef);
        MethodHandleInvoker invoker = null;
        // There might be an invoker if it's an InvokeGeneric
        if (methodRefConstant instanceof ResolvedWithInvokerClassMethodRefConstant withInvoker) {
            invoker = withInvoker.invoker();
            assert invoker == null || ((opcode == INVOKEVIRTUAL || opcode == INVOKESPECIAL) && resolvedCall.getResolvedMethod().isInvokeIntrinsic());
        }

        return new ResolvedInvoke(resolvedCall, invoker);
    }

    // endregion Class/Method/Field resolution

    // region Instance/array allocation

    @ExplodeLoop
    private int allocateMultiArray(VirtualFrame frame, int top, Klass klass, int allocatedDimensions) {
        assert klass.isArray();
        CompilerAsserts.partialEvaluationConstant(allocatedDimensions);
        CompilerAsserts.partialEvaluationConstant(klass);
        ConcolicInt[] concolicDims = new ConcolicInt[allocatedDimensions];
        int[] dimensions = new int[allocatedDimensions];
        for (int i = 0; i < allocatedDimensions; ++i) {
            // dimensions[i] = popInt(frame, top - allocatedDimensions + i);
            concolicDims[i] = popConcolicInt(frame, top - allocatedDimensions + i);
            dimensions[i] = concolicDims[i].getConcreteValue();
            if (Logger.compileLog) {
                Logger.DEBUG("DIM [" + i + "] " + concolicDims[i]);
            }
        }
        Klass component = ((ArrayKlass) klass).getComponentType();
        GuestAllocator.AllocationChecks.checkCanAllocateMultiArray(getMethod().getMeta(), component, dimensions, this);
        // StaticObject value = getAllocator().createNewMultiArray(component, dimensions);
        // putObject(frame, top - allocatedDimensions, value);
        ConcolicObject value = getAllocator().createNewMultiArray(component, concolicDims);
        if (Logger.compileLog) {
            Logger.DEBUG("NEW " + value);
        }
        putConcolicObject(frame, top - allocatedDimensions, value);
        return -allocatedDimensions; // Does not include the created (pushed) array.
    }

    // endregion Instance/array allocation

    // region Method return

    private boolean stackIntToBoolean(int result) {
        return getJavaVersion().java9OrLater() ? (result & 1) != 0 : result != 0;
    }

    // endregion Method return

    // region Arithmetic/binary operations

    private static int divInt(int divisor, int dividend) {
        return dividend / divisor;
    }

    private static long divLong(long divisor, long dividend) {
        return dividend / divisor;
    }

    private static float divFloat(float divisor, float dividend) {
        return dividend / divisor;
    }

    private static double divDouble(double divisor, double dividend) {
        return dividend / divisor;
    }

    private static int remInt(int divisor, int dividend) {
        return dividend % divisor;
    }

    private static long remLong(long divisor, long dividend) {
        return dividend % divisor;
    }

    private static float remFloat(float divisor, float dividend) {
        return dividend % divisor;
    }

    private static double remDouble(double divisor, double dividend) {
        return dividend % divisor;
    }

    private static int shiftLeftInt(int bits, int value) {
        return value << bits;
    }

    private static long shiftLeftLong(int bits, long value) {
        return value << bits;
    }

    private static int shiftRightSignedInt(int bits, int value) {
        return value >> bits;
    }

    private static long shiftRightSignedLong(int bits, long value) {
        return value >> bits;
    }

    private static int shiftRightUnsignedInt(int bits, int value) {
        return value >>> bits;
    }

    private static long shiftRightUnsignedLong(int bits, long value) {
        return value >>> bits;
    }

    // endregion Arithmetic/binary operations

    // region Comparisons

    private static int compareLong(long y, long x) {
        return Long.compare(x, y);
    }

    private static int compareFloatGreater(float y, float x) {
        return (x < y ? -1 : ((x == y) ? 0 : 1));
    }

    private static int compareFloatLess(float y, float x) {
        return (x > y ? 1 : ((x == y) ? 0 : -1));
    }

    private static int compareDoubleGreater(double y, double x) {
        return (x < y ? -1 : ((x == y) ? 0 : 1));
    }

    private static int compareDoubleLess(double y, double x) {
        return (x > y ? 1 : ((x == y) ? 0 : -1));
    }
    // endregion Comparisons

    // region Misc. checks

    public void enterImplicitExceptionProfile() {
        if (!implicitExceptionProfile) {
            CompilerDirectives.transferToInterpreterAndInvalidate();
            implicitExceptionProfile = true;
        }
    }

    public void enterLinkageExceptionProfile() {
        if (!linkageExceptionProfile) {
            CompilerDirectives.transferToInterpreterAndInvalidate();
            linkageExceptionProfile = true;
        }
    }

    private StaticObject nullCheck(StaticObject value) {
        if (!StaticObject.isNull(value)) {
            return value;
        }
        enterImplicitExceptionProfile();
        throw getMethod().getMeta().throwNullPointerException();
    }

    private ConcolicObject nullCheck(ConcolicObject value) {
        if (!ConcolicObject.isNull(value)) {
            return value;
        }
        enterImplicitExceptionProfile();
        throw getMeta().throwNullPointerException();
    }

    private int checkNonZero(int value) {
        if (value != 0) {
            return value;
        }
        enterImplicitExceptionProfile();
        throw throwBoundary(getMethod().getMeta().java_lang_ArithmeticException, "/ by zero");
    }

    private long checkNonZero(long value) {
        if (value != 0L) {
            return value;
        }
        enterImplicitExceptionProfile();
        throw throwBoundary(getMethod().getMeta().java_lang_ArithmeticException, "/ by zero");
    }

    // endregion Misc. checks

    // region Field read/write

    /**
     * Returns the stack effect (slot delta) that cannot be inferred solely from the bytecode. e.g.
     * GETFIELD always pops the receiver, but the (read) result size (1 or 2) is unknown.
     *
     * <pre>
     *   top += putField(frame, top, resolveField(...)); break; // stack effect that depends on the field
     *   top += Bytecodes.stackEffectOf(curOpcode); // stack effect that depends solely on PUTFIELD.
     *   // at this point `top` must have the correct value.
     *   curBCI = bs.next(curBCI);
     * </pre>
     */
    private int putField(VirtualFrame frame, int top, Field field, int curBCI, int opcode, int statementIndex, FieldAccessType mode) {
        assert opcode == PUTFIELD || opcode == PUTSTATIC;
        CompilerAsserts.partialEvaluationConstant(field);
        CompilerAsserts.partialEvaluationConstant(mode);

        EspressoLinkResolver.checkFieldAccessOrThrow(getContext(), field, mode, getDeclaringKlass(), getMethod());

        byte typeHeader = field.getType().byteAt(0);
        int slotCount = (typeHeader == 'J' || typeHeader == 'D') ? 2 : 1;
        assert slotCount == field.getKind().getSlotCount();
        int slot = top - slotCount - 1; // -receiver

        StaticObject receiver;
        ConcolicObject concolicReceiver;

        if (mode.isStatic()) {
            receiver = initializeAndGetStatics(field);
            int key = System.identityHashCode(receiver);
            if (!ConcolicObject.staticReceiverMap.containsKey(key)) {
                ConcolicObject.staticReceiverMap.put(key, ConcolicObjectFactory.createWithoutConstraints(receiver));
            }
            concolicReceiver = ConcolicObject.staticReceiverMap.get(key);
        } else {
            if (!noForeignObjects.isValid()) {
                // Do not release the object, it might be read again in PutFieldNode
                concolicReceiver = nullCheck(peekConcolicObject(frame, slot));
                receiver = nullCheck((StaticObject) concolicReceiver.getConcreteValue());
                if (receiver.isForeignObject()) {
                    CompilerDirectives.transferToInterpreterAndInvalidate();
                    // Restore the receiver for quickening.
                    putConcolicObject(frame, slot, concolicReceiver);
                    return quickenPutField(frame, top, curBCI, opcode, statementIndex, field);
                }
                popConcolicObject(frame, slot); // clear the slot
            } else {
                concolicReceiver = nullCheck(popConcolicObject(frame, slot));
                receiver = nullCheck((StaticObject) concolicReceiver.getConcreteValue());
            }
        }

        if (Logger.compileLog) {
            if (concolicReceiver == null) {
                Logger.WARNING("concolicReceiver is null " + receiver);
            } else {
                Logger.DEBUG("Put field '" + (char) typeHeader + "' " + receiver.getKlass().getName() + "@" + Integer.toHexString(concolicReceiver.getIdentityHashCode()) + " [" + field.getSlot() + "]");
            }
        }

        switch (typeHeader) {
            case 'Z': {
                ConcolicBoolean concolic = popConcolicBoolean(frame, top - 1);
                boolean concrete = concolic.getConcreteValue();
                if (instrumentation != null) {
                    instrumentation.notifyFieldModification(frame, statementIndex, field, receiver, concrete);
                }
                if (Logger.compileLog) {
                    Logger.DEBUG("Put value: " + concolic);
                }
                ConcolicObjectImpl.putField(concolicReceiver, field.getSlot(), concolic);
                InterpreterToVM.setFieldBoolean(concrete, receiver, field);
                break;
            }
            case 'B': {
                ConcolicByte concolic = popConcolicByte(frame, top - 1);
                byte concrete = concolic.getConcreteValue();
                if (instrumentation != null) {
                    instrumentation.notifyFieldModification(frame, statementIndex, field, receiver, concrete);
                }
                if (Logger.compileLog) {
                    Logger.DEBUG("Put value: " + concolic);
                }
                ConcolicObjectImpl.putField(concolicReceiver, field.getSlot(), concolic);
                InterpreterToVM.setFieldByte(concrete, receiver, field);
                break;
            }
            case 'C': {
                ConcolicChar concolic = popConcolicChar(frame, top - 1);
                char concrete = concolic.getConcreteValue();
                if (instrumentation != null) {
                    instrumentation.notifyFieldModification(frame, statementIndex, field, receiver, concrete);
                }
                if (Logger.compileLog) {
                    Logger.DEBUG("Put value: " + concolic);
                }
                ConcolicObjectImpl.putField(concolicReceiver, field.getSlot(), concolic);
                InterpreterToVM.setFieldChar(concrete, receiver, field);
                break;
            }
            case 'S': {
                ConcolicShort concolic = popConcolicShort(frame, top - 1);
                short concrete = concolic.getConcreteValue();
                if (instrumentation != null) {
                    instrumentation.notifyFieldModification(frame, statementIndex, field, receiver, concrete);
                }
                if (Logger.compileLog) {
                    Logger.DEBUG("Put value: " + concolic);
                }
                ConcolicObjectImpl.putField(concolicReceiver, field.getSlot(), concolic);
                InterpreterToVM.setFieldShort(concrete, receiver, field);
                break;
            }
            case 'I': {
                ConcolicInt concolic = popConcolicInt(frame, top - 1);
                int concrete = concolic.getConcreteValue();
                if (instrumentation != null) {
                    instrumentation.notifyFieldModification(frame, statementIndex, field, receiver, concrete);
                }
                if (Logger.compileLog) {
                    Logger.DEBUG("Put value: " + concolic);
                }
                ConcolicObjectImpl.putField(concolicReceiver, field.getSlot(), concolic);
                InterpreterToVM.setFieldInt(concrete, receiver, field);
                break;
            }
            case 'D': {
                ConcolicDouble concolic = popConcolicDouble(frame, top - 1);
                double concrete = concolic.getConcreteValue();
                if (instrumentation != null) {
                    instrumentation.notifyFieldModification(frame, statementIndex, field, receiver, concrete);
                }
                if (Logger.compileLog) {
                    Logger.DEBUG("Put value: " + concolic);
                }
                ConcolicObjectImpl.putField(concolicReceiver, field.getSlot(), concolic);
                InterpreterToVM.setFieldDouble(concrete, receiver, field);
                break;
            }
            case 'F': {
                ConcolicFloat concolic = popConcolicFloat(frame, top - 1);
                float concrete = concolic.getConcreteValue();
                if (instrumentation != null) {
                    instrumentation.notifyFieldModification(frame, statementIndex, field, receiver, concrete);
                }
                if (Logger.compileLog) {
                    Logger.DEBUG("Put value: " + concolic);
                }
                ConcolicObjectImpl.putField(concolicReceiver, field.getSlot(), concolic);
                InterpreterToVM.setFieldFloat(concrete, receiver, field);
                break;
            }
            case 'J': {
                ConcolicLong concolic = popConcolicLong(frame, top - 1);
                long concrete = concolic.getConcreteValue();
                if (instrumentation != null) {
                    instrumentation.notifyFieldModification(frame, statementIndex, field, receiver, concrete);
                }
                if (Logger.compileLog) {
                    Logger.DEBUG("Put value: " + concolic);
                }
                ConcolicObjectImpl.putField(concolicReceiver, field.getSlot(), concolic);
                InterpreterToVM.setFieldLong(concrete, receiver, field);
                break;
            }
            case '[': // fall through
            case 'L': {
                ConcolicObject concolic = popConcolicObject(frame, top - 1);
                StaticObject concrete = (StaticObject) concolic.getConcreteValue();
                if (instrumentation != null) {
                    instrumentation.notifyFieldModification(frame, statementIndex, field, receiver, concrete);
                }
                if (Logger.compileLog) {
                    Logger.DEBUG("Put value: " + concolic);
                }
                ConcolicObjectImpl.putField(concolicReceiver, field.getSlot(), concolic);
                InterpreterToVM.setFieldObject(concrete, receiver, field);
                break;
            }
            default:
                CompilerDirectives.transferToInterpreterAndInvalidate();
                throw EspressoError.shouldNotReachHere("unexpected kind");
        }
        return -slotCount;
    }

    /**
     * Returns the stack effect (slot delta) that cannot be inferred solely from the bytecode. e.g.
     * PUTFIELD always pops the receiver, but the result size (1 or 2) is unknown.
     *
     * <pre>
     *   top += getField(frame, top, resolveField(...)); break; // stack effect that depends on the field
     *   top += Bytecodes.stackEffectOf(curOpcode); // stack effect that depends solely on GETFIELD.
     *   // at this point `top` must have the correct value.
     *   curBCI = bs.next(curBCI);
     * </pre>
     */
    private int getField(VirtualFrame frame, int top, Field field, int curBCI, int opcode, int statementIndex, FieldAccessType mode) {
        assert opcode == GETFIELD || opcode == GETSTATIC;

        CompilerAsserts.partialEvaluationConstant(field);

        EspressoLinkResolver.checkFieldAccessOrThrow(getContext(), field, mode, getDeclaringKlass(), getMethod());

        byte typeHeader = field.getType().byteAt(0);
        if (Logger.compileLog) {
            }

        int slot = top - 1;
        StaticObject receiver;
        ConcolicObject concolicReceiver;
        if (mode.isStatic()) {
            receiver = initializeAndGetStatics(field);
            int key = System.identityHashCode(receiver);
            if (!ConcolicObject.staticReceiverMap.containsKey(key)) {
                ConcolicObject.staticReceiverMap.put(key, ConcolicObjectFactory.createWithoutConstraints(receiver));
            }
            concolicReceiver = ConcolicObject.staticReceiverMap.get(key);
        } else {
            if (!noForeignObjects.isValid()) {
                // Do not release the object yet, it might be read again in GetFieldNode
                concolicReceiver = nullCheck(peekConcolicObject(frame, slot));
                receiver = nullCheck((StaticObject) concolicReceiver.getConcreteValue());
                if (receiver.isForeignObject()) {
                    CompilerDirectives.transferToInterpreterAndInvalidate();
                    // Restore the receiver for quickening.
                    putConcolicObject(frame, slot, concolicReceiver);
                    return quickenGetField(frame, top, curBCI, opcode, statementIndex, field);
                }
                popConcolicObject(frame, slot); // clear the slot
            } else {
                concolicReceiver = nullCheck(popConcolicObject(frame, slot));
                receiver = nullCheck((StaticObject) concolicReceiver.getConcreteValue());
            }
        }

        if (instrumentation != null) {
            instrumentation.notifyFieldAccess(frame, statementIndex, field, receiver);
        }

        int resultAt = mode.isStatic() ? top : (top - 1);
        if (Logger.compileLog) {
            if (concolicReceiver == null) {
                Logger.WARNING("concolicReceiver is null " + receiver);
            } else {
                Logger.DEBUG("Get field '" + (char) typeHeader + "' " + receiver.getKlass().getName() + "@" + Integer.toHexString(concolicReceiver.getIdentityHashCode()) + " [" + field.getSlot() + "]");
            }
        }
        // @formatter:off
        switch (typeHeader) {
            case 'Z' : {
                // putInt(frame, resultAt, InterpreterToVM.getFieldBoolean(receiver, field) ? 1 : 0);
                boolean concrete = InterpreterToVM.getFieldBoolean(receiver, field);
                ConcolicBoolean concolic = (ConcolicBoolean) ConcolicObjectImpl.getField(concolicReceiver, field.getSlot());
                if (Logger.compileLog) {
                    Logger.DEBUG("Get value: " + concolic);
                }
                if (concolic == null || !concolic.getConcreteValue().equals(concrete)) {
                    if (concolic != null) {
                        if (Logger.compileLog) {
                            Logger.DEBUG("concolic: " + concolic.getConcreteValue() + ", concrete: " + String.valueOf(concrete));
                        }
                    }
                    concolic = ConcolicBoolean.createWithoutConstraints(concrete);
                    ConcolicObjectImpl.putField(concolicReceiver, field.getSlot(), concolic);
                }
                putConcolicBoolean(frame, resultAt, concolic);
                break;
            }
            case 'B' : {
                // putInt(frame, resultAt, InterpreterToVM.getFieldByte(receiver, field));
                byte concrete = InterpreterToVM.getFieldByte(receiver, field);
                ConcolicByte concolic = (ConcolicByte) ConcolicObjectImpl.getField(concolicReceiver, field.getSlot());
                if (Logger.compileLog) {
                    Logger.DEBUG("Get value: " + concolic);
                }
                if (concolic == null || !concolic.getConcreteValue().equals(concrete)) {
                    if (concolic != null) {
                        if (Logger.compileLog) {
                            Logger.DEBUG("concolic: " + concolic.getConcreteValue() + ", concrete: " + String.valueOf(concrete));
                        }
                    }
                    concolic = ConcolicByte.createWithoutConstraints(concrete);
                    ConcolicObjectImpl.putField(concolicReceiver, field.getSlot(), concolic);
                }
                putConcolicByte(frame, resultAt, concolic);
                break;
            }
            case 'C' : {
                // putInt(frame, resultAt, InterpreterToVM.getFieldChar(receiver, field));
                char concrete = InterpreterToVM.getFieldChar(receiver, field);
                ConcolicChar concolic = (ConcolicChar) ConcolicObjectImpl.getField(concolicReceiver, field.getSlot());
                if (Logger.compileLog) {
                    Logger.DEBUG("Get value: " + concolic);
                }
                if (concolic == null || !concolic.getConcreteValue().equals(concrete)) {
                    if (concolic != null) {
                        if (Logger.compileLog) {
                            Logger.DEBUG("concolic: " + concolic.getConcreteValue() + ", concrete: " + String.valueOf(concrete));
                        }
                    }
                    concolic = ConcolicChar.createWithoutConstraints(concrete);
                    ConcolicObjectImpl.putField(concolicReceiver, field.getSlot(), concolic);
                }
                putConcolicChar(frame, resultAt, concolic);
                break;
            }
            case 'S' : {
                // putInt(frame, resultAt, InterpreterToVM.getFieldShort(receiver, field));
                short concrete = InterpreterToVM.getFieldShort(receiver, field);
                ConcolicShort concolic = (ConcolicShort) ConcolicObjectImpl.getField(concolicReceiver, field.getSlot());
                if (Logger.compileLog) {
                    Logger.DEBUG("Get value: " + concolic);
                }
                if (concolic == null || !concolic.getConcreteValue().equals(concrete)) {
                    if (concolic != null) {
                        if (Logger.compileLog) {
                            Logger.DEBUG("concolic: " + concolic.getConcreteValue() + ", concrete: " + String.valueOf(concrete));
                        }
                    }
                    concolic = ConcolicShort.createWithoutConstraints(concrete);
                    ConcolicObjectImpl.putField(concolicReceiver, field.getSlot(), concolic);
                }
                putConcolicShort(frame, resultAt, concolic);
                break;
            }
            case 'I' : {
                // putInt(frame, resultAt, InterpreterToVM.getFieldInt(receiver, field));
                int concrete = InterpreterToVM.getFieldInt(receiver, field);
                ConcolicInt concolic = (ConcolicInt) ConcolicObjectImpl.getField(concolicReceiver, field.getSlot());
                if (Logger.compileLog) {
                    Logger.DEBUG("Get value: " + concolic);
                }
                if (concolic == null || !concolic.getConcreteValue().equals(concrete)) {
                    if (concolic != null) {
                        if (Logger.compileLog) {
                            Logger.DEBUG("concolic: " + concolic.getConcreteValue() + ", concrete: " + String.valueOf(concrete));
                        }
                    }
                    concolic = ConcolicInt.createWithoutConstraints(concrete);
                    ConcolicObjectImpl.putField(concolicReceiver, field.getSlot(), concolic);
                }
                putConcolicInt(frame, resultAt, concolic);
                break;
            }
            case 'D' : {
                // putDouble(frame, resultAt, InterpreterToVM.getFieldDouble(receiver, field));
                double concrete = InterpreterToVM.getFieldDouble(receiver, field);
                ConcolicDouble concolic = (ConcolicDouble) ConcolicObjectImpl.getField(concolicReceiver, field.getSlot());
                if (Logger.compileLog) {
                    Logger.DEBUG("Get value: " + concolic);
                }
                if (concolic == null || !concolic.getConcreteValue().equals(concrete)) {
                    if (concolic != null) {
                        if (Logger.compileLog) {
                            Logger.DEBUG("concolic: " + concolic.getConcreteValue() + ", concrete: " + String.valueOf(concrete));
                        }
                    }
                    concolic = ConcolicDouble.createWithoutConstraints(concrete);
                    ConcolicObjectImpl.putField(concolicReceiver, field.getSlot(), concolic);
                }
                putConcolicDouble(frame, resultAt, concolic);
                break;
            }
            case 'F' : {
                // putFloat(frame, resultAt, InterpreterToVM.getFieldFloat(receiver, field));
                float concrete = InterpreterToVM.getFieldFloat(receiver, field);
                ConcolicFloat concolic = (ConcolicFloat) ConcolicObjectImpl.getField(concolicReceiver, field.getSlot());
                if (Logger.compileLog) {
                    Logger.DEBUG("Get value: " + concolic);
                }
                if (concolic == null || !concolic.getConcreteValue().equals(concrete)) {
                    if (concolic != null) {
                        if (Logger.compileLog) {
                            Logger.DEBUG("concolic: " + concolic.getConcreteValue() + ", concrete: " + String.valueOf(concrete));
                        }
                    }
                    concolic = ConcolicFloat.createWithoutConstraints(concrete);
                    ConcolicObjectImpl.putField(concolicReceiver, field.getSlot(), concolic);
                }
                putConcolicFloat(frame, resultAt, concolic);
                break;
            }
            case 'J' : {
                // putLong(frame, resultAt, InterpreterToVM.getFieldLong(receiver, field));
                long concrete = InterpreterToVM.getFieldLong(receiver, field);
                ConcolicLong concolic = (ConcolicLong) ConcolicObjectImpl.getField(concolicReceiver, field.getSlot());
                if (Logger.compileLog) {
                    Logger.DEBUG("Get value: " + concolic);
                }
                if (concolic == null || !concolic.getConcreteValue().equals(concrete)) {
                    if (concolic != null) {
                        if (Logger.compileLog) {
                            Logger.DEBUG("concolic: " + concolic.getConcreteValue() + ", concrete: " + String.valueOf(concrete));
                        }
                    }
                    concolic = ConcolicLong.createWithoutConstraints(concrete);
                    ConcolicObjectImpl.putField(concolicReceiver, field.getSlot(), concolic);
                }
                putConcolicLong(frame, resultAt, concolic);
                break;
            }
            case '[' : // fall through
            case 'L' : {
                // StaticObject value = InterpreterToVM.getFieldObject(receiver, field);
                // putObject(frame, resultAt, value);
                // checkNoForeignObjectAssumption(value);
                StaticObject concrete = InterpreterToVM.getFieldObject(receiver, field);
                ConcolicObject concolic = (ConcolicObject) ConcolicObjectImpl.getField(concolicReceiver, field.getSlot());
                boolean isEqual = false;
                if (concolic != null) {
                    isEqual = InterpreterToVM.referenceIdentityEqual(concrete, (StaticObject) concolic.getConcreteValue(), getLanguage());
                }
                if (Logger.compileLog) {
                    Logger.DEBUG("Get value (concolic): " + concolic + ": " + isEqual);
                    Logger.DEBUG("Get value (concrete): " + concrete);
                }
                if (concolic == null || !isEqual) {
                    if (concolic != null) {
                        if (Logger.compileLog) {
                            Logger.DEBUG("concolic: " + concolic.getConcreteValue() + ", concrete: " + String.valueOf(concrete));
                        }
                    }
                    concolic = ConcolicObjectFactory.createWithoutConstraints(concrete);
                    ConcolicObjectImpl.putField(concolicReceiver, field.getSlot(), concolic);
                }
                putConcolicObject(frame, resultAt, concolic);
                checkNoForeignObjectAssumption(concrete);
                break;
            }
            default:
                CompilerDirectives.transferToInterpreterAndInvalidate();
                throw EspressoError.shouldNotReachHere("unexpected kind");
        }
        // @formatter:on
        int slotCount = (typeHeader == 'J' || typeHeader == 'D') ? 2 : 1;
        assert slotCount == field.getKind().getSlotCount();
        return slotCount;
    }

    @SuppressWarnings("try")
    private StaticObject initializeAndGetStatics(Field field) {
        ObjectKlass declaringKlass = field.getDeclaringKlass();
        if (!declaringKlass.isInitialized()) {
            CompilerDirectives.transferToInterpreterAndInvalidate();
            try (EspressoLanguage.DisableSingleStepping ignored = getLanguage().disableStepping()) {
                declaringKlass.safeInitialize();
            }
        }
        return declaringKlass.getStatics();
    }

    // endregion Field read/write

    @Override
    public String toString() {
        return getRootNode().getQualifiedName();
    }

    public void notifyFieldModification(VirtualFrame frame, int index, Field field, StaticObject receiver, Object value) {
        // Notifications are only for Espresso objects
        if (instrumentation != null && (noForeignObjects.isValid() || receiver.isEspressoObject())) {
            instrumentation.notifyFieldModification(frame, index, field, receiver, value);
        }
    }

    public void notifyFieldAccess(VirtualFrame frame, int index, Field field, StaticObject receiver) {
        // Notifications are only for Espresso objects
        if (instrumentation != null && (noForeignObjects.isValid() || receiver.isEspressoObject())) {
            instrumentation.notifyFieldAccess(frame, index, field, receiver);
        }
    }

    private boolean lockIsHeld() {
        return ((ReentrantLock) getLock()).isHeldByCurrentThread();
    }

    static final class InstrumentationSupport extends EspressoNode {
        static final int NO_STATEMENT = -1;

        @Children private final EspressoBaseStatementNode[] statementNodes;
        @Child private MapperBCI hookBCIToNodeIndex;

        private final EspressoContext context;
        private final MethodVersion method;

        InstrumentationSupport(MethodVersion method) {
            this.method = method;
            this.context = method.getMethod().getContext();

            LineNumberTableAttribute table = method.getLineNumberTableAttribute();

            if (table != LineNumberTableAttribute.EMPTY) {
                List<LineNumberTableAttribute.Entry> entries = table.getEntries();
                // don't allow multiple entries with same line, keep only the first one
                // reduce the checks needed heavily by keeping track of max seen line number
                int[] seenLines = new int[entries.size()];
                Arrays.fill(seenLines, -1);
                int maxSeenLine = -1;

                this.statementNodes = new EspressoBaseStatementNode[entries.size()];
                this.hookBCIToNodeIndex = new MapperBCI(table);

                for (int i = 0; i < entries.size(); i++) {
                    LineNumberTableAttribute.Entry entry = entries.get(i);
                    int lineNumber = entry.getLineNumber();
                    boolean seen = false;
                    boolean checkSeen = !(maxSeenLine < lineNumber);
                    if (checkSeen) {
                        for (int seenLine : seenLines) {
                            if (seenLine == lineNumber) {
                                seen = true;
                                break;
                            }
                        }
                    }
                    if (!seen) {
                        statementNodes[hookBCIToNodeIndex.initIndex(i, entry.getBCI())] = new EspressoStatementNode(entry.getBCI(), lineNumber);
                        seenLines[i] = lineNumber;
                        maxSeenLine = Math.max(maxSeenLine, lineNumber);
                    }
                }
            } else {
                this.statementNodes = null;
                this.hookBCIToNodeIndex = null;
            }
        }

        /**
         * If transitioning between two statements, exits the current one, and enter the new one.
         */
        void notifyStatementChange(VirtualFrame frame, int statementIndex, int nextStatementIndex, int targetBci) {
            assert statementIndex != nextStatementIndex;
            notifyStatementExit(frame, statementIndex);
            setBCI(frame, targetBci);
            notifyStatementEnter(frame, nextStatementIndex);
        }

        void notifyStatementEnter(VirtualFrame frame, int statementIndex) {
            CompilerAsserts.partialEvaluationConstant(statementIndex);
            enterAt(frame, statementIndex);
        }

        void notifyStatementResume(VirtualFrame frame, int statementIndex) {
            CompilerAsserts.partialEvaluationConstant(statementIndex);
            resumeAt(frame, statementIndex);
        }

        void notifyStatementExit(VirtualFrame frame, int statementIndex) {
            CompilerAsserts.partialEvaluationConstant(statementIndex);
            exitAt(frame, statementIndex, StaticObject.NULL);
        }

        public void notifyEntry(VirtualFrame frame, AbstractInstrumentableBytecodeNode instrumentableNode) {
            if (context.shouldReportVMEvents() && method.getMethod().hasActiveHook()) {
                context.reportOnMethodEntry(method, instrumentableNode.getScope(frame, true));
            }
        }

        public void notifyResume(VirtualFrame frame, AbstractInstrumentableBytecodeNode instrumentableNode) {
            if (context.shouldReportVMEvents() && method.getMethod().hasActiveHook()) {
                context.reportOnMethodEntry(method, instrumentableNode.getScope(frame, true));
            }
        }

        public void notifyReturn(VirtualFrame frame, int statementIndex, Object returnValue) {
            if (context.shouldReportVMEvents() && method.getMethod().hasActiveHook()) {
                if (context.reportOnMethodReturn(method, returnValue)) {
                    exitAt(frame, statementIndex, returnValue);
                }
            }
        }

        void notifyExceptionAt(VirtualFrame frame, Throwable t, int statementIndex) {
            WrapperNode wrapperNode = getWrapperAt(statementIndex);
            if (wrapperNode == null) {
                return;
            }
            ProbeNode probeNode = wrapperNode.getProbeNode();
            probeNode.onReturnExceptionalOrUnwind(frame, t, false);
        }

        void notifyYieldAt(VirtualFrame frame, Object o, int statementIndex) {
            WrapperNode wrapperNode = getWrapperAt(statementIndex);
            if (wrapperNode == null) {
                return;
            }
            ProbeNode probeNode = wrapperNode.getProbeNode();
            probeNode.onYield(frame, o);
        }

        public void notifyFieldModification(VirtualFrame frame, int index, Field field, StaticObject receiver, Object value) {
            if (context.shouldReportVMEvents() && field.hasActiveBreakpoint()) {
                if (context.reportOnFieldModification(field, receiver, value)) {
                    enterAt(frame, index);
                }
            }
        }

        public void notifyFieldAccess(VirtualFrame frame, int index, Field field, StaticObject receiver) {
            if (context.shouldReportVMEvents() && field.hasActiveBreakpoint()) {
                if (context.reportOnFieldAccess(field, receiver)) {
                    enterAt(frame, index);
                }
            }
        }

        private void enterAt(VirtualFrame frame, int index) {
            WrapperNode wrapperNode = getWrapperAt(index);
            if (wrapperNode == null) {
                return;
            }
            ProbeNode probeNode = wrapperNode.getProbeNode();
            try {
                probeNode.onEnter(frame);
            } catch (Throwable t) {
                Object result = probeNode.onReturnExceptionalOrUnwind(frame, t, false);
                if (result == ProbeNode.UNWIND_ACTION_REENTER) {
                    // TODO maybe support this by returning a new bci?
                    CompilerDirectives.transferToInterpreter();
                    throw new UnsupportedOperationException();
                } else if (result != null) {
                    // ignore result values;
                    // we are instrumentation statements only.
                    return;
                }
                throw t;
            }
        }

        private void resumeAt(VirtualFrame frame, int index) {
            WrapperNode wrapperNode = getWrapperAt(index);
            if (wrapperNode == null) {
                return;
            }
            ProbeNode probeNode = wrapperNode.getProbeNode();
            try {
                probeNode.onResume(frame);
            } catch (Throwable t) {
                Object result = probeNode.onReturnExceptionalOrUnwind(frame, t, false);
                if (result == ProbeNode.UNWIND_ACTION_REENTER) {
                    // TODO maybe support this by returning a new bci?
                    CompilerDirectives.transferToInterpreter();
                    throw new UnsupportedOperationException();
                } else if (result != null) {
                    // ignore result values;
                    // we are instrumentation statements only.
                    return;
                }
                throw t;
            }
        }

        private void exitAt(VirtualFrame frame, int index, Object returnValue) {
            WrapperNode wrapperNode = getWrapperAt(index);
            if (wrapperNode == null) {
                return;
            }
            ProbeNode probeNode = wrapperNode.getProbeNode();
            try {
                probeNode.onReturnValue(frame, returnValue);
            } catch (Throwable t) {
                Object result = probeNode.onReturnExceptionalOrUnwind(frame, t, true);
                if (result == ProbeNode.UNWIND_ACTION_REENTER) {
                    // TODO maybe support this by returning a new bci?
                    CompilerDirectives.transferToInterpreter();
                    throw new UnsupportedOperationException();
                } else if (result != null) {
                    // ignore result values;
                    // we are instrumentation statements only.
                    return;
                }
                throw t;
            }
        }

        int getStatementIndexAfterJump(int statementIndex, int curBCI, int targetBCI) {
            if (hookBCIToNodeIndex == null) {
                return NO_STATEMENT;
            }
            return hookBCIToNodeIndex.lookup(statementIndex, curBCI, targetBCI);
        }

        int getNextStatementIndex(int statementIndex, int nextBCI) {
            if (hookBCIToNodeIndex == null) {
                return NO_STATEMENT;
            }
            return hookBCIToNodeIndex.checkNext(statementIndex, nextBCI);
        }

        int getStartStatementIndex(int startBci) {
            if (hookBCIToNodeIndex == null) {
                return NO_STATEMENT;
            }
            if (startBci == 0) {
                assert hookBCIToNodeIndex.lookupBucket(0) == 0;
                return 0;
            }
            return hookBCIToNodeIndex.lookupBucket(startBci);
        }

        private WrapperNode getWrapperAt(int index) {
            if (statementNodes == null || index < 0) {
                return null;
            }
            EspressoBaseStatementNode node = statementNodes[index];
            if (!(node instanceof WrapperNode)) {
                return null;
            }
            CompilerAsserts.partialEvaluationConstant(node);
            return ((WrapperNode) node);
        }
    }

    private boolean trivialBytecodes() {
        if (getMethod().isSynchronized()) {
            return false;
        }
        byte[] originalCode = getMethodVersion().getOriginalCode();
        /*
         * originalCode.length < TrivialMethodSize is checked in the constructor because this method
         * is called from a compiler thread where the context is not accessible.
         */
        BytecodeStream stream = new BytecodeStream(originalCode);
        for (int bci = 0; bci < stream.endBCI(); bci = stream.nextBCI(bci)) {
            int bc = stream.currentBC(bci);
            // Trivial methods should be leaves.
            if (Bytecodes.isInvoke(bc)) {
                return false;
            }
            if (Bytecodes.LOOKUPSWITCH == bc || Bytecodes.TABLESWITCH == bc) {
                return false;
            }
            if (Bytecodes.MONITORENTER == bc || Bytecodes.MONITOREXIT == bc) {
                return false;
            }
            if (Bytecodes.ANEWARRAY == bc || MULTIANEWARRAY == bc) {
                // The allocated array is Arrays.fill-ed with StaticObject.NULL but loops are not
                // allowed in trivial methods.
                return false;
            }
            if (Bytecodes.isBranch(bc)) {
                int dest = stream.readBranchDest(bci);
                if (dest <= bci) {
                    // Back-edge (probably a loop) but loops are not allowed in trivial methods.
                    return false;
                }
            }
        }
        return true;
    }

    @Override
    protected boolean isTrivial() {
        CompilerAsserts.neverPartOfCompilation();
        /**
         * These two checks are dynamic and must be performed on every compilation. In the worst
         * case (a race):
         *
         * - A trivial "block" (interop operation or implicit exception creation and throw) is
         * introduced => the method will be inlined, which may or may not blow-up compilation. The
         * compiler checks that trivial methods have <= 500 Graal nodes, which reduces the chances
         * of choking the compiler with huge graphs.
         *
         * - A non-trivial "block" (interop operation or implicit exception creation and throw) is
         * introduced => the compiler "triviality" checks fail, the call is not inlined and a
         * warning is printed.
         *
         * The compiler checks that trivial methods have no guest calls, no loops and a have <= 500
         * Graal nodes.
         */
        if (!noForeignObjects.isValid() || implicitExceptionProfile) {
            return false;
        }
        if (instrumentation != null) {
            return false;
        }
        if (trivialBytecodesCache == TRIVIAL_UNINITIALIZED) {
            // Cache "triviality" of original bytecodes.
            trivialBytecodesCache = trivialBytecodes() ? TRIVIAL_YES : TRIVIAL_NO;
        }
        return trivialBytecodesCache == TRIVIAL_YES;
    }
}
