/*******************************************************************************
 * Copyright (c) 2009, 2025 Mountainminds GmbH & Co. KG and Contributors
 * This program and the accompanying materials are made available under
 * the terms of the Eclipse Public License 2.0 which is available at
 * http://www.eclipse.org/legal/epl-2.0
 *
 * SPDX-License-Identifier: EPL-2.0
 *
 * Contributors:
 *    Marc R. Hoffmann - initial API and implementation
 *
 *******************************************************************************/
package org.jacoco.core.internal.flow;

import org.jacoco.core.internal.instr.InstrSupport;
import org.objectweb.asm.Label;
import org.objectweb.asm.MethodVisitor;
import org.objectweb.asm.commons.JSRInlinerAdapter;
import java.util.ArrayList;
import org.jacoco.core.internal.instr.InstrSupport.ClassReaderWithOffset;
import org.objectweb.asm.ClassReader;
import org.objectweb.asm.Handle;

/**
 * This method visitor fixes two potential issues with Java byte code:
 *
 * <ul>
 * <li>Remove JSR/RET instructions by inlining subroutines which are deprecated
 * since Java 6. The RET statement complicates control flow analysis as the jump
 * target is not explicitly given.</li>
 * <li>Remove code attributes line number and local variable name if they point
 * to invalid offsets which some tools create. When writing out such invalid
 * labels with ASM class files do not verify any more.</li>
 * </ul>
 */
public class MethodSanitizer extends JSRInlinerAdapter {
	private ClassReaderWithOffset classReader = null;
	public ArrayList<Integer> offsets = new ArrayList<>();

	public int getCurrentOffset() {
		if (classReader == null) {
			return -1;
		}
		return classReader.getCurrentOffset();
	}

	public void setClassReader(final ClassReader classReader) {
		if (classReader instanceof ClassReaderWithOffset) {
			this.classReader = (ClassReaderWithOffset) classReader;
		}
	}

	MethodSanitizer(final MethodVisitor mv, final int access, final String name,
			final String desc, final String signature,
			final String[] exceptions) {
		super(InstrSupport.ASM_API_VERSION, mv, access, name, desc, signature,
				exceptions);
	}

	@Override
	public void visitLocalVariable(final String name, final String desc,
			final String signature, final Label start, final Label end,
			final int index) {
		// Here we rely on the usage of the info fields by the tree API. If the
		// labels have been properly used before the info field contains a
		// reference to the LabelNode, otherwise null.
		if (start.info != null && end.info != null) {
			super.visitLocalVariable(name, desc, signature, start, end, index);
		}
	}

	@Override
	public void visitLineNumber(final int line, final Label start) {
		// Here we rely on the usage of the info fields by the tree API. If the
		// labels have been properly used before the info field contains a
		// reference to the LabelNode, otherwise null.
		if (start.info != null) {
			super.visitLineNumber(line, start);
			offsets.add(getCurrentOffset());
			if (instructions.size() != offsets.size()) {
				throw new RuntimeException("Offsets and instructions size mismatch");
			}
		}
	}

	///////

	@Override
	public void visitFrame(final int type, final int numLocal,
			final Object[] local, final int numStack, final Object[] stack) {
		super.visitFrame(type, numLocal, local, numStack, stack);
		offsets.add(getCurrentOffset());
		if (instructions.size() != offsets.size()) {
			throw new RuntimeException("Offsets and instructions size mismatch");
		}
	}

	@Override
	public void visitInsn(final int opcode) {
		super.visitInsn(opcode);
		offsets.add(getCurrentOffset());
		if (instructions.size() != offsets.size()) {
			throw new RuntimeException("Offsets and instructions size mismatch");
		}
	}

	@Override
	public void visitIntInsn(final int opcode, final int operand) {
		super.visitIntInsn(opcode, operand);
		offsets.add(getCurrentOffset());
		if (instructions.size() != offsets.size()) {
			throw new RuntimeException("Offsets and instructions size mismatch");
		}
	}

	@Override
	public void visitVarInsn(final int opcode, final int varIndex) {
		super.visitVarInsn(opcode, varIndex);
		offsets.add(getCurrentOffset());
		if (instructions.size() != offsets.size()) {
			throw new RuntimeException("Offsets and instructions size mismatch");
		}
	}

	@Override
	public void visitTypeInsn(final int opcode, final String type) {
		super.visitTypeInsn(opcode, type);
		offsets.add(getCurrentOffset());
		if (instructions.size() != offsets.size()) {
			throw new RuntimeException("Offsets and instructions size mismatch");
		}
	}

	@Override
	public void visitFieldInsn(
			final int opcode, final String owner, final String name, final String descriptor) {
		super.visitFieldInsn(opcode, owner, name, descriptor);
		offsets.add(getCurrentOffset());
		if (instructions.size() != offsets.size()) {
			throw new RuntimeException("Offsets and instructions size mismatch");
		}
	}

	@Override
	public void visitMethodInsn(
			final int opcodeAndSource,
			final String owner,
			final String name,
			final String descriptor,
			final boolean isInterface) {
		super.visitMethodInsn(opcodeAndSource, owner, name, descriptor, isInterface);
		offsets.add(getCurrentOffset());
		if (instructions.size() != offsets.size()) {
			throw new RuntimeException("Offsets and instructions size mismatch");
		}
	}

  	@Override
	public void visitInvokeDynamicInsn(
			final String name,
			final String descriptor,
			final Handle bootstrapMethodHandle,
			final Object... bootstrapMethodArguments) {
		super.visitInvokeDynamicInsn(name, descriptor, bootstrapMethodHandle, bootstrapMethodArguments);
		offsets.add(getCurrentOffset());
		if (instructions.size() != offsets.size()) {
			throw new RuntimeException("Offsets and instructions size mismatch");
		}
	}

	@Override
	public void visitJumpInsn(final int opcode, final Label label) {
		super.visitJumpInsn(opcode, label);
		offsets.add(getCurrentOffset());
		if (instructions.size() != offsets.size()) {
			throw new RuntimeException("Offsets and instructions size mismatch");
		}
	}

	@Override
	public void visitLabel(final Label label) {
		super.visitLabel(label);
		offsets.add(getCurrentOffset());
		if (instructions.size() != offsets.size()) {
			throw new RuntimeException("Offsets and instructions size mismatch");
		}
	}

	@Override
	public void visitLdcInsn(final Object cst) {
		super.visitLdcInsn(cst);
		offsets.add(getCurrentOffset());
		if (instructions.size() != offsets.size()) {
			throw new RuntimeException("Offsets and instructions size mismatch");
		}
	}

	@Override
	public void visitIincInsn(final int var, final int increment) {
		super.visitIincInsn(var, increment);
		offsets.add(getCurrentOffset());
		if (instructions.size() != offsets.size()) {
			throw new RuntimeException("Offsets and instructions size mismatch");
		}
	}

	@Override
	public void visitTableSwitchInsn(final int min, final int max, final Label dflt, final Label... labels) {
		super.visitTableSwitchInsn(min, max, dflt, labels);
		offsets.add(getCurrentOffset());
		if (instructions.size() != offsets.size()) {
			throw new RuntimeException("Offsets and instructions size mismatch");
		}
	}

	@Override
	public void visitLookupSwitchInsn(final Label dflt, final int[] keys, final Label[] labels) {
		super.visitLookupSwitchInsn(dflt, keys, labels);
		offsets.add(getCurrentOffset());
		if (instructions.size() != offsets.size()) {
			throw new RuntimeException("Offsets and instructions size mismatch");
		}
	}

	@Override
	public void visitMultiANewArrayInsn(final String descriptor, final int numDimensions) {
		super.visitMultiANewArrayInsn(descriptor, numDimensions);
		offsets.add(getCurrentOffset());
		if (instructions.size() != offsets.size()) {
			throw new RuntimeException("Offsets and instructions size mismatch");
		}
	}
}