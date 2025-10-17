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
package org.jacoco.core.internal.analysis;

import org.jacoco.core.internal.flow.IFrame;
import org.jacoco.core.internal.flow.LabelInfo;
import org.jacoco.core.internal.flow.MethodProbesVisitor;
import org.objectweb.asm.Handle;
import org.objectweb.asm.Label;
import org.objectweb.asm.MethodVisitor;
import org.objectweb.asm.tree.AbstractInsnNode;
import org.objectweb.asm.tree.MethodNode;
import org.objectweb.asm.tree.TryCatchBlockNode;
import org.jacoco.core.internal.flow.MethodSanitizer;
/**
 * A {@link MethodProbesVisitor} that builds the {@link Instruction}s of a
 * method to calculate the detailed execution status.
 */
public class MethodAnalyzer extends MethodProbesVisitor {
	private int latestOffset = -1;

	private final InstructionsBuilder builder;

	/** Current node of the ASM tree API */
	private AbstractInsnNode currentNode;

	/**
	 * New instance that uses the given builder.
	 */
	MethodAnalyzer(final InstructionsBuilder builder) {
		this.builder = builder;
	}

	@Override
	public void accept(final MethodNode methodNode,
			final MethodVisitor methodVisitor) {
		methodVisitor.visitCode();
		for (final TryCatchBlockNode n : methodNode.tryCatchBlocks) {
			n.accept(methodVisitor);
		}

		int idx = 0;
		for (final AbstractInsnNode i : methodNode.instructions) {
			if (methodNode instanceof MethodSanitizer) {
				MethodSanitizer sanitizer = (MethodSanitizer) methodNode;
				latestOffset = sanitizer.offsets.get(idx);
			}

			currentNode = i;
			i.accept(methodVisitor);

			idx++;
		}
		methodVisitor.visitEnd();
	}

	@Override
	public void visitLabel(final Label label) {
		builder.addLabel(label);
	}

	@Override
	public void visitLineNumber(final int line, final Label start) {
		builder.setCurrentLine(line);
	}

	@Override
	public void visitInsn(final int opcode) {
		builder.addInstructionWithOffset(currentNode, latestOffset);
	}

	@Override
	public void visitIntInsn(final int opcode, final int operand) {
		builder.addInstructionWithOffset(currentNode, latestOffset);
	}

	@Override
	public void visitVarInsn(final int opcode, final int var) {
		builder.addInstructionWithOffset(currentNode, latestOffset);
	}

	@Override
	public void visitTypeInsn(final int opcode, final String type) {
		builder.addInstructionWithOffset(currentNode, latestOffset);
	}

	@Override
	public void visitFieldInsn(final int opcode, final String owner,
			final String name, final String desc) {
		builder.addInstructionWithOffset(currentNode, latestOffset);
	}

	@Override
	public void visitMethodInsn(final int opcode, final String owner,
			final String name, final String desc, final boolean itf) {
		builder.addInstructionWithOffset(currentNode, latestOffset);
	}

	@Override
	public void visitInvokeDynamicInsn(final String name, final String desc,
			final Handle bsm, final Object... bsmArgs) {
		builder.addInstructionWithOffset(currentNode, latestOffset);
	}

	@Override
	public void visitJumpInsn(final int opcode, final Label label) {
		builder.addInstructionWithOffset(currentNode, latestOffset);
		builder.addJump(label, 1);
	}

	@Override
	public void visitLdcInsn(final Object cst) {
		builder.addInstructionWithOffset(currentNode, latestOffset);
	}

	@Override
	public void visitIincInsn(final int var, final int increment) {
		builder.addInstructionWithOffset(currentNode, latestOffset);
	}

	@Override
	public void visitTableSwitchInsn(final int min, final int max,
			final Label dflt, final Label... labels) {
		visitSwitchInsn(dflt, labels);
	}

	@Override
	public void visitLookupSwitchInsn(final Label dflt, final int[] keys,
			final Label[] labels) {
		visitSwitchInsn(dflt, labels);
	}

	private void visitSwitchInsn(final Label dflt, final Label[] labels) {
		builder.addInstructionWithOffset(currentNode, latestOffset);
		LabelInfo.resetDone(labels);
		int branch = 0;
		builder.addJump(dflt, branch);
		LabelInfo.setDone(dflt);
		for (final Label l : labels) {
			if (!LabelInfo.isDone(l)) {
				branch++;
				builder.addJump(l, branch);
				LabelInfo.setDone(l);
			}
		}
	}

	@Override
	public void visitMultiANewArrayInsn(final String desc, final int dims) {
		builder.addInstructionWithOffset(currentNode, latestOffset);
	}

	@Override
	public void visitProbe(final int probeId) {
		builder.addProbe(probeId, 0);
		builder.noSuccessor();
	}

	@Override
	public void visitJumpInsnWithProbe(final int opcode, final Label label,
			final int probeId, final IFrame frame) {
		builder.addInstructionWithOffset(currentNode, latestOffset);
		builder.addProbe(probeId, 1);
	}

	@Override
	public void visitInsnWithProbe(final int opcode, final int probeId) {
		builder.addInstructionWithOffset(currentNode, latestOffset);
		builder.addProbe(probeId, 0);
	}

	@Override
	public void visitTableSwitchInsnWithProbes(final int min, final int max,
			final Label dflt, final Label[] labels, final IFrame frame) {
		visitSwitchInsnWithProbes(dflt, labels);
	}

	@Override
	public void visitLookupSwitchInsnWithProbes(final Label dflt,
			final int[] keys, final Label[] labels, final IFrame frame) {
		visitSwitchInsnWithProbes(dflt, labels);
	}

	private void visitSwitchInsnWithProbes(final Label dflt,
			final Label[] labels) {
		builder.addInstructionWithOffset(currentNode, latestOffset);
		LabelInfo.resetDone(dflt);
		LabelInfo.resetDone(labels);
		int branch = 0;
		visitSwitchTarget(dflt, branch);
		for (final Label l : labels) {
			branch++;
			visitSwitchTarget(l, branch);
		}
	}

	private void visitSwitchTarget(final Label label, final int branch) {
		final int id = LabelInfo.getProbeId(label);
		if (!LabelInfo.isDone(label)) {
			if (id == LabelInfo.NO_PROBE) {
				builder.addJump(label, branch);
			} else {
				builder.addProbe(id, branch);
			}
			LabelInfo.setDone(label);
		}
	}

}
