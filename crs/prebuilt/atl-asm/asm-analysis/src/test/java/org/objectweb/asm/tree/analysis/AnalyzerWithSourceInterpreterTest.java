// ASM: a very small and fast Java bytecode manipulation framework
// Copyright (c) 2000-2011 INRIA, France Telecom
// All rights reserved.
//
// Redistribution and use in source and binary forms, with or without
// modification, are permitted provided that the following conditions
// are met:
// 1. Redistributions of source code must retain the above copyright
//    notice, this list of conditions and the following disclaimer.
// 2. Redistributions in binary form must reproduce the above copyright
//    notice, this list of conditions and the following disclaimer in the
//    documentation and/or other materials provided with the distribution.
// 3. Neither the name of the copyright holders nor the names of its
//    contributors may be used to endorse or promote products derived from
//    this software without specific prior written permission.
//
// THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
// AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
// IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
// ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
// LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
// CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
// SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
// INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
// CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
// ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF
// THE POSSIBILITY OF SUCH DAMAGE.
package org.objectweb.asm.tree.analysis;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import java.util.Arrays;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.MethodSource;
import org.objectweb.asm.ClassReader;
import org.objectweb.asm.Label;
import org.objectweb.asm.Opcodes;
import org.objectweb.asm.test.AsmTest;
import org.objectweb.asm.tree.AbstractInsnNode;
import org.objectweb.asm.tree.ClassNode;
import org.objectweb.asm.tree.MethodNode;

/**
 * Unit tests for {@link Analyzer}, when used with a {@link SourceInterpreter}.
 *
 * @author Eric Bruneton
 */
class AnalyzerWithSourceInterpreterTest extends AsmTest {

  @Test
  void testConstructor() {
    assertDoesNotThrow(() -> new SourceInterpreter());
    assertThrows(IllegalStateException.class, () -> new SourceInterpreter() {});
  }

  /**
   * Tests that the precompiled classes can be successfully analyzed with a SourceInterpreter.
   *
   * @throws AnalyzerException if the test class can't be analyzed.
   */
  @ParameterizedTest
  @MethodSource(ALL_CLASSES_AND_LATEST_API)
  void testAnalyze_sourceInterpreter(
      final PrecompiledClass classParameter, final Api apiParameter) {
    ClassNode classNode = new ClassNode();
    new ClassReader(classParameter.getBytes()).accept(classNode, 0);
    Analyzer<SourceValue> analyzer = new Analyzer<>(new SourceInterpreter());

    for (MethodNode methodNode : classNode.methods) {
      assertDoesNotThrow(() -> analyzer.analyze(classNode.name, methodNode));
    }
  }

  /** Checks if DUP_X2 producers are correct. */
  @Test
  void testAnalyze_dupx2Producers() throws AnalyzerException {
    Label label0 = new Label();
    Label label1 = new Label();
    MethodNode methodNode =
        new MethodNodeBuilder(4, 1)
            .push()
            .push()
            .iconst_0()
            .ifne(label0)
            // First case
            .insn(Opcodes.ICONST_M1)
            .go(label1)
            // Second case
            .label(label0)
            .iconst_0()
            // DUP_X2 value
            .label(label1)
            .insn(Opcodes.DUP_X2)
            .pop() // Point where the frame is checked
            .pop()
            .pop()
            .pop()
            .vreturn()
            .build();

    Analyzer<SourceValue> analyzer = new Analyzer<>(new SourceInterpreter());
    analyzer.analyze("C", methodNode);

    AbstractInsnNode firstPop =
        Arrays.stream(methodNode.instructions.toArray())
            .filter(insn -> insn.getOpcode() == Opcodes.POP)
            .findFirst()
            .get();
    AbstractInsnNode dupx2 =
        Arrays.stream(methodNode.instructions.toArray())
            .filter(insn -> insn.getOpcode() == Opcodes.DUP_X2)
            .findFirst()
            .get();
    Frame<SourceValue> frame = analyzer.getFrames()[methodNode.instructions.indexOf(firstPop)];
    // Check if all source values have the DUP_X2 as a producer
    SourceValue sourceValue1 = frame.getStack(frame.getStackSize() - 4);
    SourceValue sourceValue2 = frame.getStack(frame.getStackSize() - 3);
    SourceValue sourceValue3 = frame.getStack(frame.getStackSize() - 2);
    SourceValue sourceValue4 = frame.getStack(frame.getStackSize() - 1);
    assertEquals(sourceValue1.insns.iterator().next(), dupx2);
    assertEquals(sourceValue2.insns.iterator().next(), dupx2);
    assertEquals(sourceValue3.insns.iterator().next(), dupx2);
    assertEquals(sourceValue4.insns.iterator().next(), dupx2);
  }
}
