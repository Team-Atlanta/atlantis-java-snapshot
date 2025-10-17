/*
 * Copyright 2025 Code Intelligence GmbH
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

/**
 * Tests that CodeMarkerInstrumentor correctly instruments security-sensitive methods (sinkpoints).
 * For each sinkpoint in SINKPOINT_CALLEES, we verify proper instrumentation of methods that call it.
 */

package com.code_intelligence.jazzer.instrumentor

import com.code_intelligence.jazzer.instrumentor.PatchTestUtils.classToBytecode
import org.junit.Test
import org.objectweb.asm.ClassReader
import org.objectweb.asm.ClassVisitor
import org.objectweb.asm.MethodVisitor
import org.objectweb.asm.Opcodes
import org.objectweb.asm.tree.ClassNode
import org.objectweb.asm.tree.MethodInsnNode
import java.io.ByteArrayOutputStream
import java.io.File
import kotlin.test.assertEquals
import kotlin.test.assertTrue

// Constants to avoid repetition and typos
private const val JAZZER_INTERNAL_CLASS = "com/code_intelligence/jazzer/api/Jazzer"
private const val REPORT_CODE_MARKER_HIT = "reportCodeMarkerHit"
private const val REPORT_CODE_MARKER_DESC = "(I)V"

/**
 * Represents a sinkpoint test case with all the information needed to test its instrumentation
 */
data class SinkpointTestCase(
    val name: String, // Name for the test case (e.g., "ClassForName")
    val targetMethodName: String, // Method name in CodeMarkerInstrumentationTarget to test (e.g., "testClassForName")
    val className: String, // Internal class name (e.g., "java/lang/Class")
    val methodName: String, // Method name (e.g., "forName")
    val methodDesc: String?, // Method descriptor or null for wildcard (e.g., "(Ljava/lang/String;)Ljava/lang/Class;")
    val calledFrom: String = "test${name.take(1).uppercase() + name.drop(1)}", // Default to test + capitalized name
)

/**
 * Finds the bytecode offset of a sinkpoint method call in the original bytecode
 *
 * @param bytecode The original class bytecode
 * @param sinkpoint The sinkpoint test case to look for
 * @return The bytecode offset of the sinkpoint method call
 * @throws IllegalStateException if the sinkpoint instruction cannot be found
 */
fun findSinkpointBytecodeOffset(
    bytecode: ByteArray,
    sinkpoint: SinkpointTestCase,
): Int {
    val classNode = ClassNode()
    val reader = ClassReader(bytecode)
    reader.accept(classNode, 0)

    for (method in classNode.methods) {
        if (method.name == sinkpoint.targetMethodName) {
            val instructions = method.instructions.toArray()
            for (insn in instructions) {
                if (insn is MethodInsnNode &&
                    insn.owner == sinkpoint.className &&
                    insn.name == sinkpoint.methodName &&
                    (sinkpoint.methodDesc == null || sinkpoint.methodDesc == insn.desc)
                ) {
                    // Found the target instruction, get its bytecode offset
                    val bytecodeOffset = insn.getBytecodeOffset()
                    println("Found sinkpoint ${sinkpoint.name} call in ${method.name} with bytecode offset: $bytecodeOffset")
                    return bytecodeOffset
                }
            }
        }
    }

    throw IllegalStateException("Could not find sinkpoint ${sinkpoint.name} call in ${sinkpoint.targetMethodName}")
}

// List of sinkpoint test cases to use in the tests
val SINKPOINT_TEST_CASES =
    listOf(
        // REFLECTION SINKPOINTS
        SinkpointTestCase(
            name = "ClassForName",
            targetMethodName = "testClassForName",
            className = "java/lang/Class",
            methodName = "forName",
            methodDesc = "(Ljava/lang/String;)Ljava/lang/Class;",
        ),
        SinkpointTestCase(
            name = "ClassForNameWithLoader",
            targetMethodName = "testClassForNameWithLoader",
            className = "java/lang/Class",
            methodName = "forName",
            methodDesc = "(Ljava/lang/String;ZLjava/lang/ClassLoader;)Ljava/lang/Class;",
        ),
        SinkpointTestCase(
            name = "ClassForNameWithModule",
            targetMethodName = "testClassForNameWithModule",
            className = "java/lang/Class",
            methodName = "forName",
            methodDesc = "(Ljava/lang/Module;Ljava/lang/String;)Ljava/lang/Class;",
        ),
        SinkpointTestCase(
            name = "ClassLoaderLoadClass",
            targetMethodName = "testClassLoaderLoadClass",
            className = "java/lang/ClassLoader",
            methodName = "loadClass",
            methodDesc = "(Ljava/lang/String;)Ljava/lang/Class;",
        ),
        SinkpointTestCase(
            name = "ClassLoaderLoadClassWithFlag",
            targetMethodName = "testClassLoaderLoadClassWithFlag",
            className = "java/lang/ClassLoader",
            methodName = "loadClass",
            methodDesc = "(Ljava/lang/String;Z)Ljava/lang/Class;",
        ),
        SinkpointTestCase(
            name = "ClassLoaderLoadClassWithModule",
            targetMethodName = "testClassLoaderLoadClassWithModule",
            className = "java/lang/ClassLoader",
            methodName = "loadClass",
            methodDesc = "(Ljava/lang/Module;Ljava/lang/String;)Ljava/lang/Class;",
        ),
        // NATIVE CODE LOADING SINKPOINTS
        SinkpointTestCase(
            name = "SystemMapLibraryName",
            targetMethodName = "testRuntimeLoad",
            className = "java/lang/System",
            methodName = "mapLibraryName",
            methodDesc = null,
        ),
        SinkpointTestCase(
            name = "RuntimeLoad",
            targetMethodName = "testRuntimeLoadExplicit",
            className = "java/lang/Runtime",
            methodName = "load",
            methodDesc = null,
        ),
        SinkpointTestCase(
            name = "RuntimeLoadLibrary",
            targetMethodName = "testRuntimeLoadLibrary",
            className = "java/lang/Runtime",
            methodName = "loadLibrary",
            methodDesc = null,
        ),
        SinkpointTestCase(
            name = "SystemLoad",
            targetMethodName = "testSystemLoad",
            className = "java/lang/System",
            methodName = "load",
            methodDesc = null,
        ),
        SinkpointTestCase(
            name = "SystemLoadLibrary",
            targetMethodName = "testSystemLoadLibrary",
            className = "java/lang/System",
            methodName = "loadLibrary",
            methodDesc = null,
        ),
        SinkpointTestCase(
            name = "ClassLoaderFindLibrary",
            targetMethodName = "testClassLoaderFindLibrary",
            className = "java/lang/ClassLoader",
            methodName = "findLibrary",
            methodDesc = null,
        ),
        // PROCESS EXECUTION SINKPOINTS
        SinkpointTestCase(
            name = "ProcessBuilderStart",
            targetMethodName = "testProcessBuilderStart",
            className = "java/lang/ProcessBuilder",
            methodName = "start",
            methodDesc = null,
        ),
        SinkpointTestCase(
            name = "ProcessImplStart",
            targetMethodName = "testProcessImplStart",
            className = "java/lang/ProcessImpl",
            methodName = "start",
            methodDesc = null,
        ),
        // JNDI CONTEXT LOOKUP SINKPOINTS
        SinkpointTestCase(
            name = "ContextLookup",
            targetMethodName = "testContextLookup",
            className = "javax/naming/Context",
            methodName = "lookup",
            methodDesc = "(Ljava/lang/String;)Ljava/lang/Object;",
        ),
        SinkpointTestCase(
            name = "ContextLookupLink",
            targetMethodName = "testContextLookupLink",
            className = "javax/naming/Context",
            methodName = "lookupLink",
            methodDesc = "(Ljava/lang/String;)Ljava/lang/Object;",
        ),
        // LDAP DIRECTORY SEARCH SINKPOINTS
        SinkpointTestCase(
            name = "DirContextSearch",
            targetMethodName = "testDirContextSearch",
            className = "javax/naming/directory/DirContext",
            methodName = "search",
            methodDesc = null, // We use null to match all overloads
        ),
        SinkpointTestCase(
            name = "InitialDirContextSearch",
            targetMethodName = "testInitialDirContextSearch",
            className = "javax/naming/directory/InitialDirContext",
            methodName = "search",
            methodDesc = null, // We use null to match all overloads
        ),
        // EXPRESSION LANGUAGE SINKPOINTS
        SinkpointTestCase(
            name = "ExpressionFactoryCreateValueExpression",
            targetMethodName = "testExpressionFactoryCreateValueExpression",
            className = "javax/el/ExpressionFactory",
            methodName = "createValueExpression",
            methodDesc = null,
        ),
        SinkpointTestCase(
            name = "ExpressionFactoryCreateMethodExpression",
            targetMethodName = "testExpressionFactoryCreateMethodExpression",
            className = "javax/el/ExpressionFactory",
            methodName = "createMethodExpression",
            methodDesc = null,
        ),
        SinkpointTestCase(
            name = "JakartaExpressionFactoryCreateValueExpression",
            targetMethodName = "testJakartaExpressionFactoryCreateValueExpression",
            className = "jakarta/el/ExpressionFactory",
            methodName = "createValueExpression",
            methodDesc = null,
        ),
        SinkpointTestCase(
            name = "JakartaExpressionFactoryCreateMethodExpression",
            targetMethodName = "testJakartaExpressionFactoryCreateMethodExpression",
            className = "jakarta/el/ExpressionFactory",
            methodName = "createMethodExpression",
            methodDesc = null,
        ),
        // SKIPPED: Implementation differences between validation frameworks
        SinkpointTestCase(
            name = "ConstraintViolationTemplate",
            targetMethodName = "testConstraintViolationTemplate",
            className = "javax/validation/ConstraintValidatorContext",
            methodName = "buildConstraintViolationWithTemplate",
            methodDesc = null,
        ),
        // DESERIALIZATION SINKPOINTS
        SinkpointTestCase(
            name = "ObjectInputStreamInit",
            targetMethodName = "testObjectInputStream",
            className = "java/io/ObjectInputStream",
            methodName = "<init>",
            methodDesc = "(Ljava/io/InputStream;)V",
        ),
        SinkpointTestCase(
            name = "ObjectInputStreamReadObject",
            targetMethodName = "testObjectInputStreamReadObject",
            className = "java/io/ObjectInputStream",
            methodName = "readObject",
            methodDesc = null,
        ),
        SinkpointTestCase(
            name = "ObjectInputStreamReadUnshared",
            targetMethodName = "testObjectInputStreamReadUnshared",
            className = "java/io/ObjectInputStream",
            methodName = "readUnshared",
            methodDesc = null,
        ),
        SinkpointTestCase(
            name = "ObjectInputStreamReadObjectOverride",
            targetMethodName = "testObjectInputStreamReadObjectOverride",
            className = "java/io/ObjectInputStream",
            methodName = "readObjectOverride",
            methodDesc = null,
        ),
        // XPATH SINKPOINTS
        SinkpointTestCase(
            name = "XPathCompile",
            targetMethodName = "testXPathCompile",
            className = "javax/xml/xpath/XPath",
            methodName = "compile",
            methodDesc = null,
        ),
        SinkpointTestCase(
            name = "XPathEvaluate",
            targetMethodName = "testXPathEvaluate",
            className = "javax/xml/xpath/XPath",
            methodName = "evaluate",
            methodDesc = null,
        ),
        SinkpointTestCase(
            name = "XPathEvaluateExpression",
            targetMethodName = "testXPathEvaluateExpression",
            className = "javax/xml/xpath/XPath",
            methodName = "evaluateExpression",
            methodDesc = null,
        ),
        // REGEX SINKPOINTS
        SinkpointTestCase(
            name = "PatternCompile",
            targetMethodName = "testPatternCompile",
            className = "java/util/regex/Pattern",
            methodName = "compile",
            methodDesc = "(Ljava/lang/String;)Ljava/util/regex/Pattern;",
        ),
        SinkpointTestCase(
            name = "PatternCompileWithFlags",
            targetMethodName = "testPatternCompileWithFlags",
            className = "java/util/regex/Pattern",
            methodName = "compile",
            methodDesc = "(Ljava/lang/String;I)Ljava/util/regex/Pattern;",
        ),
        SinkpointTestCase(
            name = "PatternMatches",
            targetMethodName = "testPatternMatches",
            className = "java/util/regex/Pattern",
            methodName = "matches",
            methodDesc = "(Ljava/lang/String;Ljava/lang/CharSequence;)Z",
        ),
        SinkpointTestCase(
            name = "StringMatches",
            targetMethodName = "testStringMatches",
            className = "java/lang/String",
            methodName = "matches",
            methodDesc = "(Ljava/lang/String;)Z",
        ),
        SinkpointTestCase(
            name = "StringReplaceAll",
            targetMethodName = "testStringReplaceAll",
            className = "java/lang/String",
            methodName = "replaceAll",
            methodDesc = "(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;",
        ),
        SinkpointTestCase(
            name = "StringReplaceFirst",
            targetMethodName = "testStringReplaceFirst",
            className = "java/lang/String",
            methodName = "replaceFirst",
            methodDesc = "(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;",
        ),
        SinkpointTestCase(
            name = "StringSplit",
            targetMethodName = "testStringSplit",
            className = "java/lang/String",
            methodName = "split",
            methodDesc = "(Ljava/lang/String;)[Ljava/lang/String;",
        ),
        SinkpointTestCase(
            name = "StringSplitWithLimit",
            targetMethodName = "testStringSplitWithLimit",
            className = "java/lang/String",
            methodName = "split",
            methodDesc = "(Ljava/lang/String;I)[Ljava/lang/String;",
        ),
    )

/**
 * Visitor that counts calls and collects basic information about where they occur
 *
 * @param bytecode The bytecode to analyze
 * @param sinkpoint Optional sinkpoint test case to specifically look for (if null, looks for any markers)
 * @return List of marker calls found in the bytecode with relevant information
 */
fun analyzeCodeMarkerCalls(
    bytecode: ByteArray,
    sinkpoint: SinkpointTestCase? = null,
): List<Map<String, Any>> {
    val reader = ClassReader(bytecode)
    val result = mutableListOf<Map<String, Any>>()

    val visitor =
        object : ClassVisitor(Opcodes.ASM9) {
            private var currentClassName = ""

            override fun visit(
                version: Int,
                access: Int,
                name: String,
                signature: String?,
                superName: String?,
                interfaces: Array<out String>?,
            ) {
                currentClassName = name.replace('/', '.')
                super.visit(version, access, name, signature, superName, interfaces)
            }

            override fun visitMethod(
                access: Int,
                name: String,
                descriptor: String,
                signature: String?,
                exceptions: Array<out String>?,
            ): MethodVisitor {
                val methodName = name
                var currentLine = -1

                return object : MethodVisitor(Opcodes.ASM9) {
                    override fun visitLineNumber(
                        line: Int,
                        start: org.objectweb.asm.Label?,
                    ) {
                        currentLine = line
                        super.visitLineNumber(line, start)
                    }

                    override fun visitMethodInsn(
                        opcode: Int,
                        owner: String,
                        name: String,
                        descriptor: String,
                        isInterface: Boolean,
                    ) {
                        // Check for code marker calls
                        if (opcode == Opcodes.INVOKESTATIC &&
                            owner == JAZZER_INTERNAL_CLASS &&
                            name == REPORT_CODE_MARKER_HIT &&
                            descriptor == REPORT_CODE_MARKER_DESC
                        ) {
                            // Get target method name based on sinkpoint information
                            val targetMethod =
                                sinkpoint?.let { "${it.className.replace('/', '.')}.${it.methodName}" }
                                    ?: "Unknown"

                            // Record this code marker call
                            result.add(
                                mapOf(
                                    "class_name" to currentClassName,
                                    "method_name" to methodName,
                                    "line_num" to currentLine,
                                    "target_method" to targetMethod,
                                    "opcode" to "INVOKESTATIC",
                                    "owner" to owner,
                                    "name" to name,
                                    "descriptor" to descriptor,
                                ),
                            )
                        }

                        // Record target sinkpoint calls for debugging
                        if (sinkpoint != null &&
                            (
                                opcode == Opcodes.INVOKESTATIC ||
                                    opcode == Opcodes.INVOKEINTERFACE ||
                                    opcode == Opcodes.INVOKESPECIAL ||
                                    opcode == Opcodes.INVOKEVIRTUAL
                            ) &&
                            owner == sinkpoint.className &&
                            name == sinkpoint.methodName
                        ) {
                            val matches =
                                sinkpoint.methodDesc == null ||
                                    sinkpoint.methodDesc == descriptor

                            if (matches) {
                                println("Found ${sinkpoint.name} call at line $currentLine in $currentClassName.$methodName")
                            }
                        }

                        super.visitMethodInsn(opcode, owner, name, descriptor, isInterface)
                    }
                }
            }
        }

    reader.accept(visitor, 0)
    return result
}

/**
 * Helper function to run javap on a class file and return the output
 */
fun runJavap(
    bytecode: ByteArray,
    className: String,
): String {
    // Save the bytecode to a temporary file
    val tempFile = File.createTempFile(className, ".class")
    tempFile.deleteOnExit()
    tempFile.writeBytes(bytecode)

    // Get javap path from JAVA_HOME
    val javaHome = System.getenv("JAVA_HOME") ?: "/usr/lib/jvm/java-17-openjdk-amd64"
    val javapPath = "$javaHome/bin/javap"

    // Run javap command
    val process =
        ProcessBuilder(javapPath, "-c", "-p", tempFile.absolutePath)
            .redirectErrorStream(true)
            .start()

    // Capture output
    val output = ByteArrayOutputStream()
    process.inputStream.copyTo(output)
    process.waitFor()

    // Delete the temp file
    tempFile.delete()

    // Return the output
    return output.toString(Charsets.UTF_8)
}

/**
 * Helper function to extract a method's bytecode from javap output
 */
fun extractMethodBytecode(
    javapOutput: String,
    methodName: String,
): String? {
    val methodStart = javapOutput.indexOf("$methodName()")
    if (methodStart < 0) return null

    // Find the end of this method (either the start of the next method, or the end of class)
    val nextMethodStart = javapOutput.indexOf("private boolean test", methodStart + methodName.length + 10)
    val classEnd = javapOutput.indexOf("}", methodStart)

    // Use whichever comes first - the next method or the end of class
    val methodEnd =
        if (nextMethodStart > 0 && nextMethodStart < classEnd) {
            nextMethodStart
        } else {
            classEnd
        }

    if (methodEnd < 0) return null

    return javapOutput.substring(methodStart, methodEnd).trim()
}

/**
 * Print method bytecode using javap for both original and instrumented versions
 *
 * @param originalBytecode The original bytecode before instrumentation (can be null)
 * @param instrumentedBytecode The bytecode after instrumentation
 * @param targetClassName The class name
 * @param methodName The method name to extract and print
 * @param instrumentationType A description of the instrumentation type (e.g., "CodeMarker-only", "full")
 */
fun printMethodBytecode(
    originalBytecode: ByteArray?,
    instrumentedBytecode: ByteArray,
    targetClassName: String,
    methodName: String,
    instrumentationType: String,
) {
    try {
        // Print original bytecode if available
        if (originalBytecode != null) {
            val originalJavapOutput = runJavap(originalBytecode, targetClassName)
            val originalMethodCode = extractMethodBytecode(originalJavapOutput, methodName)
            if (originalMethodCode != null) {
                println("\n===== Original Javap Output for $methodName method =====")
                println(originalMethodCode)
            }
        }

        // Print instrumented bytecode
        val instrumentedJavapOutput = runJavap(instrumentedBytecode, targetClassName)
        val instrumentedMethodCode = extractMethodBytecode(instrumentedJavapOutput, methodName)
        if (instrumentedMethodCode != null) {
            println("\n===== $instrumentationType Instrumented Javap Output for $methodName method =====")
            println(instrumentedMethodCode)
        }
    } catch (e: Exception) {
        println("Warning: javap analysis skipped: ${e.message}")
    }
}

/**
 * Amends the instrumentation performed by [strategy] to call the map's public static void method
 * updated() after every update to coverage counters.
 *
 * (This is copied from CoverageInstrumentationTest.kt to support mock coverage)
 */
fun makeTestable(strategy: EdgeCoverageStrategy): EdgeCoverageStrategy =
    object : EdgeCoverageStrategy by strategy {
        override fun instrumentControlFlowEdge(
            mv: MethodVisitor,
            edgeId: Int,
            variable: Int,
            coverageMapInternalClassName: String,
        ) {
            strategy.instrumentControlFlowEdge(mv, edgeId, variable, coverageMapInternalClassName)
        }
    }

class CodeMarkerInstrumentationTest {
    // Helper method to reset marker state between tests
    fun resetMarkerState() {
        // Get marker count before reset
        val markerCount = CodeMarkerInstrumentor.getMarkedNodesNum()

        // Reset all markers
        CodeMarkerInstrumentor.resetMarkersForTesting()

        println("Reset marker state. Previous marker count: $markerCount, New count: ${CodeMarkerInstrumentor.getMarkedNodesNum()}")
    }

    @Test
    fun testNoInstrumentationInOriginalClass() {
        // Verify no instrumentation in original class
        val originalBytecode = classToBytecode(CodeMarkerInstrumentationTarget::class.java)
        val markerCalls = analyzeCodeMarkerCalls(originalBytecode)

        assertEquals(0, markerCalls.size, "Original class should have no calls to reportCodeMarkerHit")
    }

    // REFLECTION SINKPOINTS

    /**
     * Test for Class.forName sinkpoint instrumentation
     */
    @Test
    fun testClassForNameSinkpoint() {
        // Test with CodeMarker-only instrumentation (original behavior)
        testSinkpointInstrumentation(SINKPOINT_TEST_CASES.find { it.name == "ClassForName" }!!)

        // Also test with full instrumentation
        resetMarkerState()
        MockCoverageMap.clear() // Reset the mock coverage map
        testSinkpointInstrumentation(SINKPOINT_TEST_CASES.find { it.name == "ClassForName" }!!, useFullInstrumentation = true)
    }

    /**
     * Apply instrumentation to the target class using either full or CodeMarker-only instrumentation
     *
     * @param targetInternalName Internal name of the class to instrument
     * @param originalBytecode Original bytecode to instrument
     * @param useFullInstrumentation If true, apply all instrumentations in sequence; if false, only CodeMarker
     * @return The instrumented bytecode
     */
    fun applyInstrumentation(
        targetInternalName: String,
        originalBytecode: ByteArray,
        useFullInstrumentation: Boolean,
    ): ByteArray {
        // If we're not doing full instrumentation, just apply CodeMarker instrumentation
        if (!useFullInstrumentation) {
            return CodeMarkerInstrumentor().instrument(targetInternalName, originalBytecode)
        }

        // Otherwise, apply the full instrumentation sequence like in RuntimeInstrumentor

        // 1. Apply code marker instrumentation with hasCovInstr=true
        var bytecode =
            CodeMarkerInstrumentor(
                suppMockCovAPI = true, // Enable MockCoverageMap support
            ).instrument(targetInternalName, originalBytecode)

        // 2. Apply coverage instrumentation first
        // Use MockCoverageMap instead of the real CoverageMap to avoid native dependencies
        val edgeCoverageInstrumentor =
            EdgeCoverageInstrumentor(
                makeTestable(ClassInstrumentor.defaultEdgeCoverageStrategy),
                MockCoverageMap::class.java,
                initialEdgeId = 1,
            )
        bytecode = edgeCoverageInstrumentor.instrument(targetInternalName, bytecode)

        // 3. Apply data flow tracing with all instrumentation types from the enum
        // Ensure we're using exactly what's used in the actual code
        val instrumentations =
            setOf(
                InstrumentationType.CMP, // Comparison instrumentation
                InstrumentationType.DIV, // Division instrumentation
                InstrumentationType.GEP, // GetElementPointer-like operations
                InstrumentationType.INDIR, // Indirect calls
                // InstrumentationType.NATIVE // Native method calls
            )
        bytecode =
            TraceDataFlowInstrumentor(
                instrumentations,
                "com/code_intelligence/jazzer/runtime/TraceDataFlowNativeCallbacks",
            ).instrument(targetInternalName, bytecode)

        // 4. Apply hook instrumentation (with empty hooks for our test)
        bytecode =
            HookInstrumentor(
                emptyList(),
                java6Mode = false,
                classWithHooksEnabledField = null,
            ).instrument(targetInternalName, bytecode)

        return bytecode
    }

    /**
     * Test for Class.forName with 3 args sinkpoint instrumentation
     */
    @Test
    fun testClassForNameWithLoaderSinkpoint() {
        // Test with CodeMarker-only instrumentation (original behavior)
        testSinkpointInstrumentation(SINKPOINT_TEST_CASES.find { it.name == "ClassForNameWithLoader" }!!)

        // Also test with full instrumentation
        resetMarkerState()
        MockCoverageMap.clear() // Reset the mock coverage map
        testSinkpointInstrumentation(SINKPOINT_TEST_CASES.find { it.name == "ClassForNameWithLoader" }!!, useFullInstrumentation = true)
    }

    // Test for Class.forName with Module sinkpoint instrumentation
    // Requires Java 9+ to compile
    @Test
    fun testClassForNameWithModuleJava9PlusSinkpoint() {
        // Test with CodeMarker-only instrumentation (original behavior)
        testSinkpointInstrumentation(SINKPOINT_TEST_CASES.find { it.name == "ClassForNameWithModule" }!!)

        // Also test with full instrumentation
        resetMarkerState()
        MockCoverageMap.clear() // Reset the mock coverage map
        testSinkpointInstrumentation(SINKPOINT_TEST_CASES.find { it.name == "ClassForNameWithModule" }!!, useFullInstrumentation = true)
    }

    // Test for ClassLoader.loadClass sinkpoint instrumentation
    @Test
    fun testClassLoaderLoadClassSinkpoint() {
        // Test with CodeMarker-only instrumentation (original behavior)
        testSinkpointInstrumentation(SINKPOINT_TEST_CASES.find { it.name == "ClassLoaderLoadClass" }!!)

        // Also test with full instrumentation
        resetMarkerState()
        MockCoverageMap.clear() // Reset the mock coverage map
        testSinkpointInstrumentation(SINKPOINT_TEST_CASES.find { it.name == "ClassLoaderLoadClass" }!!, useFullInstrumentation = true)
    }

    // Test for ClassLoader.loadClass with flag sinkpoint instrumentation
    // SKIPPED: Protected method access issues
    @Test
    fun testClassLoaderLoadClassWithFlagSkippedSinkpoint() {
        println("SKIPPED: protected method - ClassLoader.loadClass(String, boolean)")
    }

    // Test for ClassLoader.loadClass with Module sinkpoint instrumentation
    // SKIPPED: Java 9+ API and protected method issues
    @Test
    fun testClassLoaderLoadClassWithModuleJava9PlusSkippedSinkpoint() {
        println("SKIPPED: Java 9+ protected method - ClassLoader.loadClass(Module, String)")
    }

    // NATIVE CODE LOADING SINKPOINTS

    /**
     * Test for System.mapLibraryName sinkpoint instrumentation
     */
    @Test
    fun testSystemMapLibraryNameSinkpoint() {
        // Test with CodeMarker-only instrumentation (original behavior)
        testSinkpointInstrumentation(SINKPOINT_TEST_CASES.find { it.name == "SystemMapLibraryName" }!!)

        // Also test with full instrumentation
        resetMarkerState()
        MockCoverageMap.clear() // Reset the mock coverage map
        testSinkpointInstrumentation(SINKPOINT_TEST_CASES.find { it.name == "SystemMapLibraryName" }!!, useFullInstrumentation = true)
    }

    /**
     * Test for Runtime.load sinkpoint instrumentation
     */
    @Test
    fun testRuntimeLoadSinkpoint() {
        // Test with CodeMarker-only instrumentation (original behavior)
        testSinkpointInstrumentation(SINKPOINT_TEST_CASES.find { it.name == "RuntimeLoad" }!!)

        // Also test with full instrumentation
        resetMarkerState()
        MockCoverageMap.clear() // Reset the mock coverage map
        testSinkpointInstrumentation(SINKPOINT_TEST_CASES.find { it.name == "RuntimeLoad" }!!, useFullInstrumentation = true)
    }

    /**
     * Test for Runtime.loadLibrary sinkpoint instrumentation
     */
    @Test
    fun testRuntimeLoadLibrarySinkpoint() {
        // Test with CodeMarker-only instrumentation (original behavior)
        testSinkpointInstrumentation(SINKPOINT_TEST_CASES.find { it.name == "RuntimeLoadLibrary" }!!)

        // Also test with full instrumentation
        resetMarkerState()
        MockCoverageMap.clear() // Reset the mock coverage map
        testSinkpointInstrumentation(SINKPOINT_TEST_CASES.find { it.name == "RuntimeLoadLibrary" }!!, useFullInstrumentation = true)
    }

    /**
     * Test for System.load sinkpoint instrumentation
     */
    @Test
    fun testSystemLoadSinkpoint() {
        // Test with CodeMarker-only instrumentation (original behavior)
        testSinkpointInstrumentation(SINKPOINT_TEST_CASES.find { it.name == "SystemLoad" }!!)

        // Also test with full instrumentation
        resetMarkerState()
        MockCoverageMap.clear() // Reset the mock coverage map
        testSinkpointInstrumentation(SINKPOINT_TEST_CASES.find { it.name == "SystemLoad" }!!, useFullInstrumentation = true)
    }

    /**
     * Test for System.loadLibrary sinkpoint instrumentation
     */
    @Test
    fun testSystemLoadLibrarySinkpoint() {
        // Test with CodeMarker-only instrumentation (original behavior)
        testSinkpointInstrumentation(SINKPOINT_TEST_CASES.find { it.name == "SystemLoadLibrary" }!!)

        // Also test with full instrumentation
        resetMarkerState()
        MockCoverageMap.clear() // Reset the mock coverage map
        testSinkpointInstrumentation(SINKPOINT_TEST_CASES.find { it.name == "SystemLoadLibrary" }!!, useFullInstrumentation = true)
    }

    // Test for ClassLoader.findLibrary sinkpoint instrumentation
    // SKIPPED: Protected method access issues
    @Test
    fun testClassLoaderFindLibrarySkippedSinkpoint() {
        println("SKIPPED: protected method - ClassLoader.findLibrary(String)")
    }

    // PROCESS EXECUTION SINKPOINTS

    // Test for ProcessBuilder.start sinkpoint instrumentation
    @Test
    fun testProcessBuilderStartSinkpoint() {
        // Test with CodeMarker-only instrumentation (original behavior)
        testSinkpointInstrumentation(SINKPOINT_TEST_CASES.find { it.name == "ProcessBuilderStart" }!!)

        // Also test with full instrumentation
        resetMarkerState()
        MockCoverageMap.clear() // Reset the mock coverage map
        testSinkpointInstrumentation(SINKPOINT_TEST_CASES.find { it.name == "ProcessBuilderStart" }!!, useFullInstrumentation = true)
    }

    // Test for ProcessImpl.start sinkpoint instrumentation
    // SKIPPED: JDK internal implementation class
    @Test
    fun testProcessImplStartSkippedSinkpoint() {
        println("SKIPPED: JDK internal implementation class - ProcessImpl.start()")
    }

    // JNDI CONTEXT LOOKUP SINKPOINTS

    /**
     * Test for Context.lookup sinkpoint instrumentation
     */
    @Test
    fun testContextLookupSinkpoint() {
        // Test with CodeMarker-only instrumentation (original behavior)
        testSinkpointInstrumentation(SINKPOINT_TEST_CASES.find { it.name == "ContextLookup" }!!)

        // Also test with full instrumentation
        resetMarkerState()
        MockCoverageMap.clear() // Reset the mock coverage map
        testSinkpointInstrumentation(SINKPOINT_TEST_CASES.find { it.name == "ContextLookup" }!!, useFullInstrumentation = true)
    }

    /**
     * Test for Context.lookupLink sinkpoint instrumentation
     */
    @Test
    fun testContextLookupLinkSinkpoint() {
        // Test with CodeMarker-only instrumentation (original behavior)
        testSinkpointInstrumentation(SINKPOINT_TEST_CASES.find { it.name == "ContextLookupLink" }!!)

        // Also test with full instrumentation
        resetMarkerState()
        MockCoverageMap.clear() // Reset the mock coverage map
        testSinkpointInstrumentation(SINKPOINT_TEST_CASES.find { it.name == "ContextLookupLink" }!!, useFullInstrumentation = true)
    }

    // LDAP DIRECTORY SEARCH SINKPOINTS

    @Test
    fun testDirContextSearchSinkpoint() {
        // Test with CodeMarker-only instrumentation (original behavior)
        testSinkpointInstrumentation(SINKPOINT_TEST_CASES.find { it.name == "DirContextSearch" }!!)

        // Also test with full instrumentation
        resetMarkerState()
        MockCoverageMap.clear() // Reset the mock coverage map
        testSinkpointInstrumentation(SINKPOINT_TEST_CASES.find { it.name == "DirContextSearch" }!!, useFullInstrumentation = true)
    }

    @Test
    fun testInitialDirContextSearchSinkpoint() {
        // Test with CodeMarker-only instrumentation (original behavior)
        testSinkpointInstrumentation(SINKPOINT_TEST_CASES.find { it.name == "InitialDirContextSearch" }!!)

        // Also test with full instrumentation
        resetMarkerState()
        MockCoverageMap.clear() // Reset the mock coverage map
        testSinkpointInstrumentation(SINKPOINT_TEST_CASES.find { it.name == "InitialDirContextSearch" }!!, useFullInstrumentation = true)
    }

    // EXPRESSION LANGUAGE SINKPOINTS

    @Test
    fun testExpressionFactoryCreateValueExpressionSinkpoint() {
        // Test with CodeMarker-only instrumentation (original behavior)
        testSinkpointInstrumentation(SINKPOINT_TEST_CASES.find { it.name == "ExpressionFactoryCreateValueExpression" }!!)

        // Also test with full instrumentation
        resetMarkerState()
        MockCoverageMap.clear() // Reset the mock coverage map
        testSinkpointInstrumentation(
            SINKPOINT_TEST_CASES.find {
                it.name == "ExpressionFactoryCreateValueExpression"
            }!!,
            useFullInstrumentation = true,
        )
    }

    @Test
    fun testExpressionFactoryCreateMethodExpressionSinkpoint() {
        // Test with CodeMarker-only instrumentation (original behavior)
        testSinkpointInstrumentation(SINKPOINT_TEST_CASES.find { it.name == "ExpressionFactoryCreateMethodExpression" }!!)

        // Also test with full instrumentation
        resetMarkerState()
        MockCoverageMap.clear() // Reset the mock coverage map
        testSinkpointInstrumentation(
            SINKPOINT_TEST_CASES.find {
                it.name == "ExpressionFactoryCreateMethodExpression"
            }!!,
            useFullInstrumentation = true,
        )
    }

    // Test for Jakarta EL ExpressionFactory.createValueExpression sinkpoint instrumentation
    @Test
    fun testJakartaExpressionFactoryCreateValueExpressionSinkpoint() {
        try {
            Class.forName("jakarta.el.ExpressionFactory")

            // Test with CodeMarker-only instrumentation (original behavior)
            testSinkpointInstrumentation(SINKPOINT_TEST_CASES.find { it.name == "JakartaExpressionFactoryCreateValueExpression" }!!)

            // Also test with full instrumentation
            resetMarkerState()
            MockCoverageMap.clear() // Reset the mock coverage map
            testSinkpointInstrumentation(
                SINKPOINT_TEST_CASES.find {
                    it.name == "JakartaExpressionFactoryCreateValueExpression"
                }!!,
                useFullInstrumentation = true,
            )
        } catch (e: ClassNotFoundException) {
            println("SKIPPED: Jakarta EL not available - jakarta/el/ExpressionFactory.createValueExpression")
        }
    }

    @Test
    fun testJakartaExpressionFactoryCreateMethodExpressionSinkpoint() {
        try {
            Class.forName("jakarta.el.ExpressionFactory")

            // Test with CodeMarker-only instrumentation (original behavior)
            testSinkpointInstrumentation(SINKPOINT_TEST_CASES.find { it.name == "JakartaExpressionFactoryCreateMethodExpression" }!!)

            // Also test with full instrumentation
            resetMarkerState()
            MockCoverageMap.clear() // Reset the mock coverage map
            testSinkpointInstrumentation(
                SINKPOINT_TEST_CASES.find {
                    it.name == "JakartaExpressionFactoryCreateMethodExpression"
                }!!,
                useFullInstrumentation = true,
            )
        } catch (e: ClassNotFoundException) {
            println("SKIPPED: Jakarta EL not available - jakarta/el/ExpressionFactory.createMethodExpression")
        }
    }

    // SKIPPED: Implementation differences
    @Test
    fun testConstraintViolationTemplateSkippedSinkpoint() {
        println("SKIPPED: implementation differences - ConstraintValidatorContext.buildConstraintViolationWithTemplate")
    }

    // DESERIALIZATION SINKPOINTS

    // Test for ObjectInputStream.<init> sinkpoint instrumentation
    @Test
    fun testObjectInputStreamInitSinkpoint() {
        // Test with CodeMarker-only instrumentation (original behavior)
        testSinkpointInstrumentation(SINKPOINT_TEST_CASES.find { it.name == "ObjectInputStreamInit" }!!)

        // Also test with full instrumentation
        resetMarkerState()
        MockCoverageMap.clear() // Reset the mock coverage map
        testSinkpointInstrumentation(SINKPOINT_TEST_CASES.find { it.name == "ObjectInputStreamInit" }!!, useFullInstrumentation = true)
    }

    // Test for ObjectInputStream.readObject sinkpoint instrumentation
    // Note: Expects 2 markers (constructor + readObject method)
    @Test
    fun testObjectInputStreamReadObjectSinkpoint() {
        // Create a custom secondary sinkpoint for the constructor, with the same targetMethodName
        val readObjectSinkpoint = SINKPOINT_TEST_CASES.find { it.name == "ObjectInputStreamReadObject" }!!
        val secondarySinkpoint =
            SinkpointTestCase(
                name = "ObjectInputStreamInit-ForReadObject",
                targetMethodName = readObjectSinkpoint.targetMethodName, // Same target method
                className = "java/io/ObjectInputStream",
                methodName = "<init>",
                methodDesc = "(Ljava/io/InputStream;)V",
            )

        // Test with CodeMarker-only instrumentation (original behavior)
        testSinkpointInstrumentation(
            readObjectSinkpoint,
            expectedMarkerCount = 2,
            secondarySinkpoint = secondarySinkpoint,
        )

        // Also test with full instrumentation
        resetMarkerState()
        MockCoverageMap.clear() // Reset the mock coverage map
        testSinkpointInstrumentation(
            readObjectSinkpoint,
            expectedMarkerCount = 2,
            secondarySinkpoint = secondarySinkpoint,
            useFullInstrumentation = true,
        )
    }

    // Test for ObjectInputStream.readUnshared sinkpoint instrumentation
    // Note: Expects 2 markers (constructor + readUnshared method)
    @Test
    fun testObjectInputStreamReadUnsharedSinkpoint() {
        // Create a custom secondary sinkpoint for the constructor, with the same targetMethodName
        val readUnsharedSinkpoint = SINKPOINT_TEST_CASES.find { it.name == "ObjectInputStreamReadUnshared" }!!
        val secondarySinkpoint =
            SinkpointTestCase(
                name = "ObjectInputStreamInit-ForReadUnshared",
                targetMethodName = readUnsharedSinkpoint.targetMethodName, // Same target method
                className = "java/io/ObjectInputStream",
                methodName = "<init>",
                methodDesc = "(Ljava/io/InputStream;)V",
            )

        // Test with CodeMarker-only instrumentation (original behavior)
        testSinkpointInstrumentation(
            readUnsharedSinkpoint,
            expectedMarkerCount = 2,
            secondarySinkpoint = secondarySinkpoint,
        )

        // Also test with full instrumentation
        resetMarkerState()
        MockCoverageMap.clear() // Reset the mock coverage map
        testSinkpointInstrumentation(
            readUnsharedSinkpoint,
            expectedMarkerCount = 2,
            secondarySinkpoint = secondarySinkpoint,
            useFullInstrumentation = true,
        )
    }

    // Test for ObjectInputStream.readObjectOverride sinkpoint instrumentation
    // SKIPPED: Protected method access issues
    @Test
    fun testObjectInputStreamReadObjectOverrideSkippedSinkpoint() {
        println("SKIPPED: protected method - ObjectInputStream.readObjectOverride()")
    }

    // XPATH SINKPOINTS

    // Test for XPath.compile sinkpoint instrumentation
    @Test
    fun testXPathCompileSinkpoint() {
        // Test with CodeMarker-only instrumentation (original behavior)
        testSinkpointInstrumentation(SINKPOINT_TEST_CASES.find { it.name == "XPathCompile" }!!)

        // Also test with full instrumentation
        resetMarkerState()
        MockCoverageMap.clear() // Reset the mock coverage map
        testSinkpointInstrumentation(SINKPOINT_TEST_CASES.find { it.name == "XPathCompile" }!!, useFullInstrumentation = true)
    }

    // Test for XPath.evaluate sinkpoint instrumentation
    @Test
    fun testXPathEvaluateSinkpoint() {
        // Test with CodeMarker-only instrumentation (original behavior)
        testSinkpointInstrumentation(SINKPOINT_TEST_CASES.find { it.name == "XPathEvaluate" }!!)

        // Also test with full instrumentation
        resetMarkerState()
        MockCoverageMap.clear() // Reset the mock coverage map
        testSinkpointInstrumentation(SINKPOINT_TEST_CASES.find { it.name == "XPathEvaluate" }!!, useFullInstrumentation = true)
    }

    // Test for XPath.evaluateExpression sinkpoint instrumentation (Java 9+ API)
    @Test
    fun testXPathEvaluateExpressionJava9PlusSinkpoint() {
        // Test with CodeMarker-only instrumentation (original behavior)
        testSinkpointInstrumentation(SINKPOINT_TEST_CASES.find { it.name == "XPathEvaluateExpression" }!!)

        // Also test with full instrumentation
        resetMarkerState()
        MockCoverageMap.clear() // Reset the mock coverage map
        testSinkpointInstrumentation(SINKPOINT_TEST_CASES.find { it.name == "XPathEvaluateExpression" }!!, useFullInstrumentation = true)
    }

    // REGEX SINKPOINTS

    // Test for Pattern.compile sinkpoint instrumentation
    @Test
    fun testPatternCompileSinkpoint() {
        // Test with CodeMarker-only instrumentation (original behavior)
        testSinkpointInstrumentation(SINKPOINT_TEST_CASES.find { it.name == "PatternCompile" }!!)

        // Also test with full instrumentation
        resetMarkerState()
        MockCoverageMap.clear() // Reset the mock coverage map
        testSinkpointInstrumentation(SINKPOINT_TEST_CASES.find { it.name == "PatternCompile" }!!, useFullInstrumentation = true)
    }

    // Test for Pattern.compile with flags sinkpoint instrumentation
    @Test
    fun testPatternCompileWithFlagsSinkpoint() {
        // Test with CodeMarker-only instrumentation (original behavior)
        testSinkpointInstrumentation(SINKPOINT_TEST_CASES.find { it.name == "PatternCompileWithFlags" }!!)

        // Also test with full instrumentation
        resetMarkerState()
        MockCoverageMap.clear() // Reset the mock coverage map
        testSinkpointInstrumentation(SINKPOINT_TEST_CASES.find { it.name == "PatternCompileWithFlags" }!!, useFullInstrumentation = true)
    }

    // Test for Pattern.matches static method sinkpoint instrumentation
    @Test
    fun testPatternMatchesSinkpoint() {
        // Test with CodeMarker-only instrumentation (original behavior)
        testSinkpointInstrumentation(SINKPOINT_TEST_CASES.find { it.name == "PatternMatches" }!!)

        // Also test with full instrumentation
        resetMarkerState()
        MockCoverageMap.clear() // Reset the mock coverage map
        testSinkpointInstrumentation(SINKPOINT_TEST_CASES.find { it.name == "PatternMatches" }!!, useFullInstrumentation = true)
    }

    /**
     * Test for String.matches sinkpoint instrumentation
     */
    @Test
    fun testStringMatchesSinkpoint() {
        // Test with CodeMarker-only instrumentation (original behavior)
        testSinkpointInstrumentation(SINKPOINT_TEST_CASES.find { it.name == "StringMatches" }!!)

        // Also test with full instrumentation
        resetMarkerState()
        MockCoverageMap.clear() // Reset the mock coverage map
        testSinkpointInstrumentation(SINKPOINT_TEST_CASES.find { it.name == "StringMatches" }!!, useFullInstrumentation = true)
    }

    /**
     * Test for String.replaceAll sinkpoint instrumentation
     */
    @Test
    fun testStringReplaceAllSinkpoint() {
        // Test with CodeMarker-only instrumentation (original behavior)
        testSinkpointInstrumentation(SINKPOINT_TEST_CASES.find { it.name == "StringReplaceAll" }!!)

        // Also test with full instrumentation
        resetMarkerState()
        MockCoverageMap.clear() // Reset the mock coverage map
        testSinkpointInstrumentation(SINKPOINT_TEST_CASES.find { it.name == "StringReplaceAll" }!!, useFullInstrumentation = true)
    }

    /**
     * Test for String.replaceFirst sinkpoint instrumentation
     */
    @Test
    fun testStringReplaceFirstSinkpoint() {
        // Test with CodeMarker-only instrumentation (original behavior)
        testSinkpointInstrumentation(SINKPOINT_TEST_CASES.find { it.name == "StringReplaceFirst" }!!)

        // Also test with full instrumentation
        resetMarkerState()
        MockCoverageMap.clear() // Reset the mock coverage map
        testSinkpointInstrumentation(SINKPOINT_TEST_CASES.find { it.name == "StringReplaceFirst" }!!, useFullInstrumentation = true)
    }

    /**
     * Test for String.split sinkpoint instrumentation
     */
    @Test
    fun testStringSplitSinkpoint() {
        // Test with CodeMarker-only instrumentation (original behavior)
        testSinkpointInstrumentation(SINKPOINT_TEST_CASES.find { it.name == "StringSplit" }!!)

        // Also test with full instrumentation
        resetMarkerState()
        MockCoverageMap.clear() // Reset the mock coverage map
        testSinkpointInstrumentation(SINKPOINT_TEST_CASES.find { it.name == "StringSplit" }!!, useFullInstrumentation = true)
    }

    /**
     * Test for String.split with limit sinkpoint instrumentation
     */
    @Test
    fun testStringSplitWithLimitSinkpoint() {
        // Test with CodeMarker-only instrumentation (original behavior)
        testSinkpointInstrumentation(SINKPOINT_TEST_CASES.find { it.name == "StringSplitWithLimit" }!!)

        // Also test with full instrumentation
        resetMarkerState()
        MockCoverageMap.clear() // Reset the mock coverage map
        testSinkpointInstrumentation(SINKPOINT_TEST_CASES.find { it.name == "StringSplitWithLimit" }!!, useFullInstrumentation = true)
    }

    // Test a specific sinkpoint's instrumentation
    //
    // @param sinkpoint The primary sinkpoint test case to check
    // @param expectedMarkerCount The number of marker calls expected (default: 1)
    // @param secondarySinkpoint An optional secondary sinkpoint that's also part of the test
    // @param useFullInstrumentation If true, apply all instrumentations in sequence; if false, only CodeMarker
    fun testSinkpointInstrumentation(
        sinkpoint: SinkpointTestCase,
        expectedMarkerCount: Int = 1,
        secondarySinkpoint: SinkpointTestCase? = null,
        useFullInstrumentation: Boolean = false,
    ) {
        val instrumentationType = if (useFullInstrumentation) "full" else "CodeMarker-only"
        println("\n===== Testing ${sinkpoint.name} sinkpoint with $instrumentationType instrumentation =====")

        // Reset marker state to avoid accumulation between tests
        resetMarkerState()

        // Get marker info BEFORE running the test
        val markerInfoBefore = CodeMarkerInstrumentor.dumpMarkedNodesInfo()
        val markerCountBefore = markerInfoBefore.size

        // Instrument the class
        val targetClass = CodeMarkerInstrumentationTarget::class.java
        val targetClassName = targetClass.simpleName
        val targetInternalName = targetClass.name.replace('.', '/')
        val originalBytecode = classToBytecode(targetClass)

        // Find the bytecode offset(s) of the sinkpoint method call(s) in the original bytecode
        val expectedBytecodeOffset = findSinkpointBytecodeOffset(originalBytecode, sinkpoint)
        println("Expected bytecode offset for ${sinkpoint.name}: $expectedBytecodeOffset")

        // If there's a secondary sinkpoint, find its bytecode offset too
        val secondaryBytecodeOffset =
            secondarySinkpoint?.let {
                val offset = findSinkpointBytecodeOffset(originalBytecode, it)
                println("Expected bytecode offset for ${it.name}: $offset")
                offset
            }

        // Apply either full or CodeMarker-only instrumentation
        val instrumentedBytecode =
            applyInstrumentation(
                targetInternalName,
                originalBytecode,
                useFullInstrumentation,
            )

        // Analyze the instrumented bytecode for this specific sinkpoint
        val markerCalls = analyzeCodeMarkerCalls(instrumentedBytecode, sinkpoint)

        // We filter to only look at markers in the method we're testing
        val methodMarkers = markerCalls.filter { it["method_name"] == sinkpoint.targetMethodName }

        // Print detailed instrumentation info
        println("===== Instrumentation Details =====")
        methodMarkers.forEach { info ->
            println("Marker inserted in ${info["class_name"]}.${info["method_name"]} at line ${info["line_num"]}")
            println("  Call: ${info["opcode"]} ${info["owner"]}.${info["name"]}${info["descriptor"]}")
        }

        // Print bytecode disassembly for both original and instrumented versions
        printMethodBytecode(
            originalBytecode = originalBytecode,
            instrumentedBytecode = instrumentedBytecode,
            targetClassName = targetClassName,
            methodName = sinkpoint.targetMethodName,
            instrumentationType = instrumentationType,
        )

        // Verify instrumentation has the expected number of markers in the target method
        assertEquals(
            expectedMarkerCount,
            methodMarkers.size,
            "Instrumented ${sinkpoint.name} method should have exactly $expectedMarkerCount call(s) to reportCodeMarkerHit",
        )

        // Get marker info AFTER instrumentation
        val markerInfoAfter = CodeMarkerInstrumentor.dumpMarkedNodesInfo()

        // We need at least the expected number of new marker IDs
        assertTrue(
            markerInfoAfter.size >= markerCountBefore + expectedMarkerCount,
            "Expected at least $expectedMarkerCount new marker(s) to be created for ${sinkpoint.name}",
        )

        // Find all markers for our method
        val markers =
            markerInfoAfter.entries
                .filter {
                    (it.value["method_name"] as String) == sinkpoint.targetMethodName
                }.sortedBy { it.value["bytecode_offset"] as Int }

        // Verify we found enough markers
        assertEquals(
            expectedMarkerCount,
            markers.size,
            "Should find exactly $expectedMarkerCount marker(s) for method ${sinkpoint.targetMethodName}",
        )

        // Print all the bytecode offsets found
        val bytecodeOffsets = markers.map { it.value["bytecode_offset"] as Int }
        println("Found bytecode offsets for ${sinkpoint.name}: $bytecodeOffsets")

        // For each marker, verify basic properties
        markers.forEach { marker ->
            val markerDetails = marker.value

            // Verify marker identifies the correct class
            val className = markerDetails["class_name"] as String
            assertTrue(
                className.endsWith(targetClassName),
                "Expected className to end with $targetClassName, got $className",
            )

            // Verify marker identifies the correct method
            val methodName = markerDetails["method_name"] as String
            assertEquals(
                sinkpoint.targetMethodName,
                methodName,
                "Expected methodName to be ${sinkpoint.targetMethodName}, got $methodName",
            )

            // Verify bytecodeOffset is present in marker details
            assertTrue(
                markerDetails.containsKey("bytecode_offset"),
                "Expected marker details to contain bytecodeOffset field",
            )

            // Verify the bytecode offset is a non-negative integer
            val bytecodeOffset = markerDetails["bytecode_offset"]
            assertTrue(
                bytecodeOffset is Int && bytecodeOffset >= 0,
                "Expected bytecodeOffset to be a non-negative integer, got $bytecodeOffset",
            )

            // Verify the mark_desc value is not null
            assertTrue(
                markerDetails.containsKey("mark_desc") && markerDetails["mark_desc"] != null,
                "Expected marker details to contain non-null mark_desc field",
            )
        }

        // Verify the bytecode offsets match the expected values
        if (expectedMarkerCount == 1) {
            // Simple case with one marker - verify it directly
            val markerDetails = markers.first().value
            val actualBytecodeOffset = markerDetails["bytecode_offset"] as Int
            println("Comparing with expected bytecodeOffset: $expectedBytecodeOffset")

            assertEquals(
                expectedBytecodeOffset,
                actualBytecodeOffset,
                "Bytecode offset in marker details should match the original instruction's bytecode offset",
            )
        } else if (expectedMarkerCount == 2 && secondarySinkpoint != null) {
            // Case with two markers - verify both offsets are present
            val actualOffsets = markers.map { it.value["bytecode_offset"] as Int }.sorted()
            println("Comparing with expected bytecodeOffsets: [$expectedBytecodeOffset, $secondaryBytecodeOffset]")

            // Check that the set of expected offsets matches the set of actual offsets
            val expectedOffsets = setOf(expectedBytecodeOffset, secondaryBytecodeOffset!!)
            val actualOffsetsSet = actualOffsets.toSet()

            assertEquals(
                expectedOffsets,
                actualOffsetsSet,
                "Bytecode offsets in marker details should match the original instructions' bytecode offsets",
            )
        }
    }
}
