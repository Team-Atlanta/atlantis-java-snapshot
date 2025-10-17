package org.gts3.atlantis.staticanalysis.utils;

import soot.Scene;
import soot.SootClass;
import soot.SootMethod;

import java.util.LinkedList;
import java.util.List;

/**
 * Utility class for handling method signatures and other signature-related operations.
 */
public class SignatureUtils {

    /**
     * Sanitizes the method signature by ensuring it starts and ends with angle brackets.
     *
     * @param methodSignature The method signature to sanitize
     * @return The sanitized method signature
     */
    public static String sanitizeMethodSignature(String methodSignature) {
        if (!methodSignature.startsWith("<")) {
            methodSignature = "<" + methodSignature;
        }
        if (!methodSignature.endsWith(">")) {
            methodSignature = methodSignature + ">";
        }
        return methodSignature;
    }

    /**
     * Gets all implementations of a method, including the method itself if it's not an interface method.
     *
     * If the method is declared in an interface, this method finds all concrete implementations
     * of that interface method in the class hierarchy. If the method is not an interface method,
     * it simply returns the method itself.
     *
     * @param sootMethod The method to find implementations for
     * @return A list of methods that implement the specified method
     */
    public static List<SootMethod> getImplementationsOf(SootMethod sootMethod) {
        List<SootMethod> result = new LinkedList<>();

        if (sootMethod.getDeclaringClass().isInterface()) {
            // If the target method is an interface, add all the implementations to the result
            for (SootClass implementation : Scene.v().getActiveHierarchy().getImplementersOf(sootMethod.getDeclaringClass())) {
                try {
                    SootMethod implementationMethod = implementation.getMethod(sootMethod.getSubSignature());
                    if (implementationMethod != null) {
                        result.add(implementationMethod);
                    }
                } catch (RuntimeException e) {
                }
            }
        } else {
            // Otherwise, add the target method itself
            result.add(sootMethod);
        }

        return result;
    }

    /**
     * Gets the bytecode signature of a method in the format "(ParamTypes)ReturnType".
     *
     * This method extracts the parameter and return type portion of a method's bytecode signature,
     * removing the class and method name prefix and any trailing angle bracket.
     *
     * @param sootMethod The method to get the bytecode signature for
     * @return The bytecode signature in the format "(ParamTypes)ReturnType"
     */
    public static String bytecodeSignature(SootMethod sootMethod) {
        String bytecodeSignature = sootMethod.getBytecodeSignature();

        int startIndex = bytecodeSignature.indexOf('(');
        bytecodeSignature = bytecodeSignature.substring(startIndex);

        if (bytecodeSignature.endsWith(">")) {
            bytecodeSignature = bytecodeSignature.substring(0, bytecodeSignature.length() - 1);
        }

        return bytecodeSignature;
    }
}
