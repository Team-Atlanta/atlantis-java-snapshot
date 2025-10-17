package sr;

import org.objectweb.asm.*;
import org.objectweb.asm.commons.AdviceAdapter;

import java.lang.instrument.ClassFileTransformer;
import java.security.ProtectionDomain;
import java.util.Set;

public class ASMTransformer implements ClassFileTransformer {

    Set<String> targetClasses = null;

    public ASMTransformer(Set<String> targetClasses) {
        this.targetClasses = targetClasses;
    }

    @Override
    public byte[] transform(ClassLoader loader, String className, Class<?> classBeingRedefined,
                                ProtectionDomain protectionDomain, byte[] classfileBuffer) {
        if (!targetClasses.contains(className)) {
            return null;
        }

        try {
            ClassReader classReader = new ClassReader(classfileBuffer);
            ClassWriter classWriter = new ClassWriter(ClassWriter.COMPUTE_FRAMES);
            ClassVisitor classVisitor = new LineLoggingClassVisitor(Opcodes.ASM9, classWriter, className);
            classReader.accept(classVisitor, ClassReader.EXPAND_FRAMES);
            return classWriter.toByteArray();
        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;
    }

    static class LineLoggingClassVisitor extends ClassVisitor {
        String className;
        public LineLoggingClassVisitor(int api, ClassVisitor classVisitor, String className) {
            super(api, classVisitor);
            this.className = className;
        }

        @Override
        public MethodVisitor visitMethod(int access, String name, String descriptor, String signature, String[] exceptions) {
            MethodVisitor methodVisitor = super.visitMethod(access, name, descriptor, signature, exceptions);
            return new LineLoggingMethodVisitor(Opcodes.ASM9, methodVisitor, access, name, descriptor, this.className);
        }
    }

    static class LineLoggingMethodVisitor extends AdviceAdapter {
        String className;
        protected LineLoggingMethodVisitor(int api, MethodVisitor methodVisitor, int access, String name, String descriptor, String className) {
            super(api, methodVisitor, access, name, descriptor);
            this.className = className;
        }

        @Override
        public void visitLineNumber(int line, Label start) {
            super.visitLineNumber(line, start);
            mv.visitFieldInsn(Opcodes.GETSTATIC, "java/lang/System", "out", "Ljava/io/PrintStream;");
            mv.visitLdcInsn("[BB] " + this.className + ":" + line);
            mv.visitMethodInsn(Opcodes.INVOKEVIRTUAL, "java/io/PrintStream", "println", "(Ljava/lang/String;)V", false);
        }
    }
}
