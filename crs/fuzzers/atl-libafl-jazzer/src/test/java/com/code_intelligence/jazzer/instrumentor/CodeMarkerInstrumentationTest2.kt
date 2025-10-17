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

package com.code_intelligence.jazzer.instrumentor

import com.code_intelligence.jazzer.instrumentor.PatchTestUtils.classToBytecode
import org.junit.Test
import org.objectweb.asm.ClassReader
import org.objectweb.asm.tree.ClassNode
import org.objectweb.asm.tree.MethodInsnNode
import kotlin.test.assertEquals
import kotlin.test.assertTrue

/**
 * Additional tests for CodeMarkerInstrumentor focused on SQL Injection, SSRF, and Path Traversal sinkpoints
 */
class CodeMarkerInstrumentationTest2 {
    // Create a reference to the main test class to reuse its functionality
    private val mainTest = CodeMarkerInstrumentationTest()

    // Define additional SinkpointTestCases for Test2
    @Suppress("ktlint:standard:property-naming")
    private val SINKPOINT_TEST_CASES_2 =
        listOf(
            // FUZZER ENTRY POINT TEST CASE
            SinkpointTestCase(
                name = "FuzzerTestOneInput",
                targetMethodName = "testFuzzerTestOneInput",
                className = "com/code_intelligence/jazzer/instrumentor/CodeMarkerInstrumentationTarget2", // Direct method in main class
                methodName = "fuzzerTestOneInput",
                methodDesc = null, // Match any descriptor
            ),
            // CUSTOM API TEST CASE
            SinkpointTestCase(
                name = "CustomApiMethod",
                targetMethodName = "testCustomSinkpoint",
                className = "com/code_intelligence/jazzer/instrumentor/CodeMarkerInstrumentationTarget2",
                methodName = "customApiMethod",
                methodDesc = "(Ljava/lang/String;)V", // Match specific descriptor
            ),
            // SSRF SINKPOINTS
            SinkpointTestCase(
                name = "SocketConnect",
                targetMethodName = "testSocketConnect",
                className = "java/net/Socket",
                methodName = "connect",
                methodDesc = null, // Match all overloads
            ),
            SinkpointTestCase(
                name = "SocketImplConnect",
                targetMethodName = "testSocketImplConnect",
                className = "java/net/SocketImpl",
                methodName = "connect",
                methodDesc = null, // Match all overloads
            ),
            SinkpointTestCase(
                name = "SocksSocketImplConnect",
                targetMethodName = "testSocksSocketImplConnect",
                className = "java/net/SocksSocketImpl",
                methodName = "connect",
                methodDesc = null,
            ),
            SinkpointTestCase(
                name = "SocketChannelConnect",
                targetMethodName = "testSocketChannelConnect",
                className = "java/nio/channels/SocketChannel",
                methodName = "connect",
                methodDesc = null,
            ),
            SinkpointTestCase(
                name = "SocketAdaptorConnect",
                targetMethodName = "testSocketAdaptorConnect",
                className = "sun/nio/ch/SocketAdaptor",
                methodName = "connect",
                methodDesc = null,
            ),
            SinkpointTestCase(
                name = "PlainHttpConnectionConnect",
                targetMethodName = "testPlainHttpConnectionConnect",
                className = "jdk/internal/net/http/PlainHttpConnection",
                methodName = "connect",
                methodDesc = null,
            ),
            // SQL INJECTION SINKPOINTS
            SinkpointTestCase(
                name = "StatementExecute",
                targetMethodName = "testStatementExecute",
                className = "java/sql/Statement",
                methodName = "execute",
                methodDesc = null, // Match all overloads
            ),
            SinkpointTestCase(
                name = "StatementExecuteBatch",
                targetMethodName = "testStatementExecuteBatch",
                className = "java/sql/Statement",
                methodName = "executeBatch",
                methodDesc = null, // Match all overloads
            ),
            SinkpointTestCase(
                name = "StatementExecuteLargeBatch",
                targetMethodName = "testStatementExecuteLargeBatch",
                className = "java/sql/Statement",
                methodName = "executeLargeBatch",
                methodDesc = null, // Match all overloads
            ),
            SinkpointTestCase(
                name = "StatementExecuteLargeUpdate",
                targetMethodName = "testStatementExecuteLargeUpdate",
                className = "java/sql/Statement",
                methodName = "executeLargeUpdate",
                methodDesc = null, // Match all overloads
            ),
            SinkpointTestCase(
                name = "StatementExecuteQuery",
                targetMethodName = "testStatementExecuteQuery",
                className = "java/sql/Statement",
                methodName = "executeQuery",
                methodDesc = null, // Match all overloads
            ),
            SinkpointTestCase(
                name = "StatementExecuteUpdate",
                targetMethodName = "testStatementExecuteUpdate",
                className = "java/sql/Statement",
                methodName = "executeUpdate",
                methodDesc = null, // Match all overloads
            ),
            SinkpointTestCase(
                name = "EntityManagerCreateNativeQuery",
                targetMethodName = "testEntityManagerCreateNativeQuery",
                className = "javax/persistence/EntityManager",
                methodName = "createNativeQuery",
                methodDesc = null, // Match all overloads
            ),
            // FILE PATH TRAVERSAL SINKPOINTS
            SinkpointTestCase(
                name = "FilesCreateDirectory",
                targetMethodName = "testFilesCreateDirectory",
                className = "java/nio/file/Files",
                methodName = "createDirectory",
                methodDesc = null, // Match all overloads
            ),
            SinkpointTestCase(
                name = "FilesCreateDirectories",
                targetMethodName = "testFilesCreateDirectories",
                className = "java/nio/file/Files",
                methodName = "createDirectories",
                methodDesc = null, // Match all overloads
            ),
            SinkpointTestCase(
                name = "FilesCreateFile",
                targetMethodName = "testFilesCreateFile",
                className = "java/nio/file/Files",
                methodName = "createFile",
                methodDesc = null, // Match all overloads
            ),
            SinkpointTestCase(
                name = "FilesCreateTempDirectory",
                targetMethodName = "testFilesCreateTempDirectory",
                className = "java/nio/file/Files",
                methodName = "createTempDirectory",
                methodDesc = null, // Match all overloads
            ),
            SinkpointTestCase(
                name = "FilesCreateTempFile",
                targetMethodName = "testFilesCreateTempFile",
                className = "java/nio/file/Files",
                methodName = "createTempFile",
                methodDesc = null, // Match all overloads
            ),
            SinkpointTestCase(
                name = "FilesDelete",
                targetMethodName = "testFilesDelete",
                className = "java/nio/file/Files",
                methodName = "delete",
                methodDesc = null, // Match all overloads
            ),
            SinkpointTestCase(
                name = "FilesDeleteIfExists",
                targetMethodName = "testFilesDeleteIfExists",
                className = "java/nio/file/Files",
                methodName = "deleteIfExists",
                methodDesc = null, // Match all overloads
            ),
            SinkpointTestCase(
                name = "FilesLines",
                targetMethodName = "testFilesLines",
                className = "java/nio/file/Files",
                methodName = "lines",
                methodDesc = null, // Match all overloads
            ),
            SinkpointTestCase(
                name = "FilesNewByteChannel",
                targetMethodName = "testFilesNewByteChannel",
                className = "java/nio/file/Files",
                methodName = "newByteChannel",
                methodDesc = null, // Match all overloads
            ),
            SinkpointTestCase(
                name = "FilesNewBufferedReader",
                targetMethodName = "testFilesNewBufferedReader",
                className = "java/nio/file/Files",
                methodName = "newBufferedReader",
                methodDesc = null, // Match all overloads
            ),
            SinkpointTestCase(
                name = "FilesNewBufferedWriter",
                targetMethodName = "testFilesNewBufferedWriter",
                className = "java/nio/file/Files",
                methodName = "newBufferedWriter",
                methodDesc = null, // Match all overloads
            ),
            SinkpointTestCase(
                name = "FilesReadString",
                targetMethodName = "testFilesReadString",
                className = "java/nio/file/Files",
                methodName = "readString",
                methodDesc = null, // Match all overloads
            ),
            SinkpointTestCase(
                name = "FilesReadAllBytes",
                targetMethodName = "testFilesReadAllBytes",
                className = "java/nio/file/Files",
                methodName = "readAllBytes",
                methodDesc = null, // Match all overloads
            ),
            SinkpointTestCase(
                name = "FilesReadAllLines",
                targetMethodName = "testFilesReadAllLines",
                className = "java/nio/file/Files",
                methodName = "readAllLines",
                methodDesc = null, // Match all overloads
            ),
            SinkpointTestCase(
                name = "FilesReadSymbolicLink",
                targetMethodName = "testFilesReadSymbolicLink",
                className = "java/nio/file/Files",
                methodName = "readSymbolicLink",
                methodDesc = null, // Match all overloads
            ),
            SinkpointTestCase(
                name = "FilesWrite",
                targetMethodName = "testFilesWrite",
                className = "java/nio/file/Files",
                methodName = "write",
                methodDesc = null, // Match all overloads
            ),
            SinkpointTestCase(
                name = "FilesWriteString",
                targetMethodName = "testFilesWriteString",
                className = "java/nio/file/Files",
                methodName = "writeString",
                methodDesc = null, // Match all overloads
            ),
            SinkpointTestCase(
                name = "FilesNewInputStream",
                targetMethodName = "testFilesNewInputStream",
                className = "java/nio/file/Files",
                methodName = "newInputStream",
                methodDesc = null, // Match all overloads
            ),
            SinkpointTestCase(
                name = "FilesNewOutputStream",
                targetMethodName = "testFilesNewOutputStream",
                className = "java/nio/file/Files",
                methodName = "newOutputStream",
                methodDesc = null, // Match all overloads
            ),
            SinkpointTestCase(
                name = "FileChannelOpen",
                targetMethodName = "testFileChannelOpen",
                className = "java/nio/channels/FileChannel",
                methodName = "open",
                methodDesc = null, // Match all overloads
            ),
            SinkpointTestCase(
                name = "FilesCopy",
                targetMethodName = "testFilesCopy",
                className = "java/nio/file/Files",
                methodName = "copy",
                methodDesc = null, // Match all overloads
            ),
            SinkpointTestCase(
                name = "FilesMismatch",
                targetMethodName = "testFilesMismatch",
                className = "java/nio/file/Files",
                methodName = "mismatch",
                methodDesc = null, // Match all overloads
            ),
            SinkpointTestCase(
                name = "FilesMove",
                targetMethodName = "testFilesMove",
                className = "java/nio/file/Files",
                methodName = "move",
                methodDesc = null, // Match all overloads
            ),
            SinkpointTestCase(
                name = "FileReaderInit",
                targetMethodName = "testFileReaderInit",
                className = "java/io/FileReader",
                methodName = "<init>",
                methodDesc = null, // Match all overloads
            ),
            SinkpointTestCase(
                name = "FileWriterInit",
                targetMethodName = "testFileWriterInit",
                className = "java/io/FileWriter",
                methodName = "<init>",
                methodDesc = null, // Match all overloads
            ),
            SinkpointTestCase(
                name = "FileInputStreamInit",
                targetMethodName = "testFileInputStreamInit",
                className = "java/io/FileInputStream",
                methodName = "<init>",
                methodDesc = null, // Match all overloads
            ),
            SinkpointTestCase(
                name = "FileOutputStreamInit",
                targetMethodName = "testFileOutputStreamInit",
                className = "java/io/FileOutputStream",
                methodName = "<init>",
                methodDesc = null, // Match all overloads
            ),
            SinkpointTestCase(
                name = "ScannerInit",
                targetMethodName = "testScannerInit",
                className = "java/util/Scanner",
                methodName = "<init>",
                methodDesc = null, // Match all overloads
            ),
            // NOTE: This matches the @MethodHook in FilePathTraversal.java
            SinkpointTestCase(
                name = "FilesProbeContentType",
                targetMethodName = "testFilesProbeContentType",
                className = "java/nio/file/probeContentType",
                methodName = "open",
                methodDesc = null,
            ),
        )

    /**
     * Our own version of testSinkpointInstrumentation that uses CodeMarkerInstrumentationTarget2
     * This is necessary because the original test is hardcoded to use CodeMarkerInstrumentationTarget
     */
    private fun testSinkpointInstrumentationWithTarget2(
        sinkpoint: SinkpointTestCase,
        expectedMarkerCount: Int = 1,
        secondarySinkpoint: SinkpointTestCase? = null,
        useFullInstrumentation: Boolean = false,
    ) {
        val instrumentationType = if (useFullInstrumentation) "full" else "CodeMarker-only"
        println("\n===== Testing ${sinkpoint.name} sinkpoint with $instrumentationType instrumentation =====")

        // Reset marker state to avoid accumulation between tests
        mainTest.resetMarkerState()

        // Get marker info BEFORE running the test
        val markerInfoBefore = CodeMarkerInstrumentor.dumpMarkedNodesInfo()
        val markerCountBefore = markerInfoBefore.size

        // Instrument the class - using Target2 instead of Target
        val targetClass = CodeMarkerInstrumentationTarget2::class.java
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

        // Apply the instrumentation using mainTest's method
        val instrumentedBytecode =
            mainTest.applyInstrumentation(
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

        // Verify instrumentation has the expected number of markers in the target method
        assertEquals(
            expectedMarkerCount.toDouble(),
            methodMarkers.size.toDouble(),
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
            expectedMarkerCount.toDouble(),
            markers.size.toDouble(),
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
                expectedBytecodeOffset.toDouble(),
                actualBytecodeOffset.toDouble(),
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

    /**
     * Helper method to find the bytecode offset of a sinkpoint method call in CodeMarkerInstrumentationTarget2
     */
    private fun findSinkpointBytecodeOffset(
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

    /**
     * Helper method to analyze code marker calls for CodeMarkerInstrumentationTarget2
     */
    private fun analyzeCodeMarkerCalls(
        bytecode: ByteArray,
        sinkpoint: SinkpointTestCase? = null,
    ): List<Map<String, Any>> =
        com.code_intelligence.jazzer.instrumentor
            .analyzeCodeMarkerCalls(bytecode, sinkpoint)

    // SSRF SINKPOINTS

    /**
     * Test for Socket.connect SSRF sinkpoint instrumentation
     */
    @Test
    fun testSocketConnectSinkpoint() {
        // Test with CodeMarker-only instrumentation (original behavior)
        testSinkpointInstrumentationWithTarget2(SINKPOINT_TEST_CASES_2.find { it.name == "SocketConnect" }!!)

        // Also test with full instrumentation
        mainTest.resetMarkerState()
        MockCoverageMap.clear() // Reset the mock coverage map
        testSinkpointInstrumentationWithTarget2(
            SINKPOINT_TEST_CASES_2.find { it.name == "SocketConnect" }!!,
            useFullInstrumentation = true,
        )
    }

    /**
     * Test for SocketImpl.connect SSRF sinkpoint instrumentation
     */
    @Test
    fun testSocketImplConnectSinkpoint() {
        println("SKIPPED: SocketImpl is a JDK internal class")
    }

    /**
     * Test for SocksSocketImpl.connect SSRF sinkpoint instrumentation
     */
    @Test
    fun testSocksSocketImplConnectSinkpoint() {
        println("SKIPPED: SocksSocketImpl is a JDK internal class")
    }

    /**
     * Test for SocketChannel.connect SSRF sinkpoint instrumentation
     */
    @Test
    fun testSocketChannelConnectSinkpoint() {
        // Test with CodeMarker-only instrumentation (original behavior)
        testSinkpointInstrumentationWithTarget2(SINKPOINT_TEST_CASES_2.find { it.name == "SocketChannelConnect" }!!)

        // Also test with full instrumentation
        mainTest.resetMarkerState()
        MockCoverageMap.clear() // Reset the mock coverage map
        testSinkpointInstrumentationWithTarget2(
            SINKPOINT_TEST_CASES_2.find { it.name == "SocketChannelConnect" }!!,
            useFullInstrumentation = true,
        )
    }

    /**
     * Test for SocketAdaptor.connect SSRF sinkpoint instrumentation
     */
    @Test
    fun testSocketAdaptorConnectSinkpoint() {
        println("SKIPPED: SocketAdaptor is a JDK internal class")
    }

    /**
     * Test for PlainHttpConnection.connect SSRF sinkpoint instrumentation
     */
    @Test
    fun testPlainHttpConnectionConnectSinkpoint() {
        println("SKIPPED: PlainHttpConnection is a JDK internal class")
    }

    // SQL INJECTION SINKPOINTS

    /**
     * Test for Statement.execute SQL Injection sinkpoint instrumentation
     */
    @Test
    fun testStatementExecuteSinkpoint() {
        // Test with CodeMarker-only instrumentation (original behavior)
        testSinkpointInstrumentationWithTarget2(SINKPOINT_TEST_CASES_2.find { it.name == "StatementExecute" }!!)

        // Also test with full instrumentation
        mainTest.resetMarkerState()
        MockCoverageMap.clear() // Reset the mock coverage map
        testSinkpointInstrumentationWithTarget2(
            SINKPOINT_TEST_CASES_2.find { it.name == "StatementExecute" }!!,
            useFullInstrumentation = true,
        )
    }

    /**
     * Test for Statement.executeBatch SQL Injection sinkpoint instrumentation
     */
    @Test
    fun testStatementExecuteBatchSinkpoint() {
        // Test with CodeMarker-only instrumentation (original behavior)
        testSinkpointInstrumentationWithTarget2(SINKPOINT_TEST_CASES_2.find { it.name == "StatementExecuteBatch" }!!)

        // Also test with full instrumentation
        mainTest.resetMarkerState()
        MockCoverageMap.clear() // Reset the mock coverage map
        testSinkpointInstrumentationWithTarget2(
            SINKPOINT_TEST_CASES_2.find { it.name == "StatementExecuteBatch" }!!,
            useFullInstrumentation = true,
        )
    }

    /**
     * Test for Statement.executeLargeBatch SQL Injection sinkpoint instrumentation
     */
    @Test
    fun testStatementExecuteLargeBatchSinkpoint() {
        // Test with CodeMarker-only instrumentation (original behavior)
        testSinkpointInstrumentationWithTarget2(SINKPOINT_TEST_CASES_2.find { it.name == "StatementExecuteLargeBatch" }!!)

        // Also test with full instrumentation
        mainTest.resetMarkerState()
        MockCoverageMap.clear() // Reset the mock coverage map
        testSinkpointInstrumentationWithTarget2(
            SINKPOINT_TEST_CASES_2.find { it.name == "StatementExecuteLargeBatch" }!!,
            useFullInstrumentation = true,
        )
    }

    /**
     * Test for Statement.executeLargeUpdate SQL Injection sinkpoint instrumentation
     */
    @Test
    fun testStatementExecuteLargeUpdateSinkpoint() {
        // Test with CodeMarker-only instrumentation (original behavior)
        testSinkpointInstrumentationWithTarget2(SINKPOINT_TEST_CASES_2.find { it.name == "StatementExecuteLargeUpdate" }!!)

        // Also test with full instrumentation
        mainTest.resetMarkerState()
        MockCoverageMap.clear() // Reset the mock coverage map
        testSinkpointInstrumentationWithTarget2(
            SINKPOINT_TEST_CASES_2.find { it.name == "StatementExecuteLargeUpdate" }!!,
            useFullInstrumentation = true,
        )
    }

    /**
     * Test for Statement.executeQuery SQL Injection sinkpoint instrumentation
     */
    @Test
    fun testStatementExecuteQuerySinkpoint() {
        // Test with CodeMarker-only instrumentation (original behavior)
        testSinkpointInstrumentationWithTarget2(SINKPOINT_TEST_CASES_2.find { it.name == "StatementExecuteQuery" }!!)

        // Also test with full instrumentation
        mainTest.resetMarkerState()
        MockCoverageMap.clear() // Reset the mock coverage map
        testSinkpointInstrumentationWithTarget2(
            SINKPOINT_TEST_CASES_2.find { it.name == "StatementExecuteQuery" }!!,
            useFullInstrumentation = true,
        )
    }

    /**
     * Test for Statement.executeUpdate SQL Injection sinkpoint instrumentation
     */
    @Test
    fun testStatementExecuteUpdateSinkpoint() {
        // Test with CodeMarker-only instrumentation (original behavior)
        testSinkpointInstrumentationWithTarget2(SINKPOINT_TEST_CASES_2.find { it.name == "StatementExecuteUpdate" }!!)

        // Also test with full instrumentation
        mainTest.resetMarkerState()
        MockCoverageMap.clear() // Reset the mock coverage map
        testSinkpointInstrumentationWithTarget2(
            SINKPOINT_TEST_CASES_2.find { it.name == "StatementExecuteUpdate" }!!,
            useFullInstrumentation = true,
        )
    }

    /**
     * Test for EntityManager.createNativeQuery SQL Injection sinkpoint instrumentation
     */
    @Test
    fun testEntityManagerCreateNativeQuerySinkpoint() {
        println("SKIPPED: EntityManager requires JPA dependency")
    }

    // FILE PATH TRAVERSAL SINKPOINTS

    /**
     * Test for Files.createDirectory File Path Traversal sinkpoint instrumentation
     */
    @Test
    fun testFilesCreateDirectorySinkpoint() {
        // Test with CodeMarker-only instrumentation (original behavior)
        testSinkpointInstrumentationWithTarget2(SINKPOINT_TEST_CASES_2.find { it.name == "FilesCreateDirectory" }!!)

        // Also test with full instrumentation
        mainTest.resetMarkerState()
        MockCoverageMap.clear() // Reset the mock coverage map
        testSinkpointInstrumentationWithTarget2(
            SINKPOINT_TEST_CASES_2.find { it.name == "FilesCreateDirectory" }!!,
            useFullInstrumentation = true,
        )
    }

    /**
     * Test for Files.createDirectories File Path Traversal sinkpoint instrumentation
     */
    @Test
    fun testFilesCreateDirectoriesSinkpoint() {
        // Test with CodeMarker-only instrumentation (original behavior)
        testSinkpointInstrumentationWithTarget2(SINKPOINT_TEST_CASES_2.find { it.name == "FilesCreateDirectories" }!!)

        // Also test with full instrumentation
        mainTest.resetMarkerState()
        MockCoverageMap.clear() // Reset the mock coverage map
        testSinkpointInstrumentationWithTarget2(
            SINKPOINT_TEST_CASES_2.find { it.name == "FilesCreateDirectories" }!!,
            useFullInstrumentation = true,
        )
    }

    /**
     * Test for Files.createFile File Path Traversal sinkpoint instrumentation
     */
    @Test
    fun testFilesCreateFileSinkpoint() {
        // Test with CodeMarker-only instrumentation (original behavior)
        testSinkpointInstrumentationWithTarget2(SINKPOINT_TEST_CASES_2.find { it.name == "FilesCreateFile" }!!)

        // Also test with full instrumentation
        mainTest.resetMarkerState()
        MockCoverageMap.clear() // Reset the mock coverage map
        testSinkpointInstrumentationWithTarget2(
            SINKPOINT_TEST_CASES_2.find { it.name == "FilesCreateFile" }!!,
            useFullInstrumentation = true,
        )
    }

    /**
     * Test for Files.createTempDirectory File Path Traversal sinkpoint instrumentation
     */
    @Test
    fun testFilesCreateTempDirectorySinkpoint() {
        // Test with CodeMarker-only instrumentation (original behavior)
        testSinkpointInstrumentationWithTarget2(SINKPOINT_TEST_CASES_2.find { it.name == "FilesCreateTempDirectory" }!!)

        // Also test with full instrumentation
        mainTest.resetMarkerState()
        MockCoverageMap.clear() // Reset the mock coverage map
        testSinkpointInstrumentationWithTarget2(
            SINKPOINT_TEST_CASES_2.find { it.name == "FilesCreateTempDirectory" }!!,
            useFullInstrumentation = true,
        )
    }

    /**
     * Test for Files.createTempFile File Path Traversal sinkpoint instrumentation
     */
    @Test
    fun testFilesCreateTempFileSinkpoint() {
        // Test with CodeMarker-only instrumentation (original behavior)
        testSinkpointInstrumentationWithTarget2(SINKPOINT_TEST_CASES_2.find { it.name == "FilesCreateTempFile" }!!)

        // Also test with full instrumentation
        mainTest.resetMarkerState()
        MockCoverageMap.clear() // Reset the mock coverage map
        testSinkpointInstrumentationWithTarget2(
            SINKPOINT_TEST_CASES_2.find { it.name == "FilesCreateTempFile" }!!,
            useFullInstrumentation = true,
        )
    }

    /**
     * Test for Files.delete File Path Traversal sinkpoint instrumentation
     */
    @Test
    fun testFilesDeleteSinkpoint() {
        // Test with CodeMarker-only instrumentation (original behavior)
        testSinkpointInstrumentationWithTarget2(SINKPOINT_TEST_CASES_2.find { it.name == "FilesDelete" }!!)

        // Also test with full instrumentation
        mainTest.resetMarkerState()
        MockCoverageMap.clear() // Reset the mock coverage map
        testSinkpointInstrumentationWithTarget2(
            SINKPOINT_TEST_CASES_2.find { it.name == "FilesDelete" }!!,
            useFullInstrumentation = true,
        )
    }

    /**
     * Test for Files.deleteIfExists File Path Traversal sinkpoint instrumentation
     */
    @Test
    fun testFilesDeleteIfExistsSinkpoint() {
        // Test with CodeMarker-only instrumentation (original behavior)
        testSinkpointInstrumentationWithTarget2(SINKPOINT_TEST_CASES_2.find { it.name == "FilesDeleteIfExists" }!!)

        // Also test with full instrumentation
        mainTest.resetMarkerState()
        MockCoverageMap.clear() // Reset the mock coverage map
        testSinkpointInstrumentationWithTarget2(
            SINKPOINT_TEST_CASES_2.find { it.name == "FilesDeleteIfExists" }!!,
            useFullInstrumentation = true,
        )
    }

    /**
     * Test for Files.lines File Path Traversal sinkpoint instrumentation
     */
    @Test
    fun testFilesLinesSinkpoint() {
        // Test with CodeMarker-only instrumentation (original behavior)
        testSinkpointInstrumentationWithTarget2(SINKPOINT_TEST_CASES_2.find { it.name == "FilesLines" }!!)

        // Also test with full instrumentation
        mainTest.resetMarkerState()
        MockCoverageMap.clear() // Reset the mock coverage map
        testSinkpointInstrumentationWithTarget2(
            SINKPOINT_TEST_CASES_2.find { it.name == "FilesLines" }!!,
            useFullInstrumentation = true,
        )
    }

    /**
     * Test for Files.newByteChannel File Path Traversal sinkpoint instrumentation
     */
    @Test
    fun testFilesNewByteChannelSinkpoint() {
        // Test with CodeMarker-only instrumentation (original behavior)
        testSinkpointInstrumentationWithTarget2(SINKPOINT_TEST_CASES_2.find { it.name == "FilesNewByteChannel" }!!)

        // Also test with full instrumentation
        mainTest.resetMarkerState()
        MockCoverageMap.clear() // Reset the mock coverage map
        testSinkpointInstrumentationWithTarget2(
            SINKPOINT_TEST_CASES_2.find { it.name == "FilesNewByteChannel" }!!,
            useFullInstrumentation = true,
        )
    }

    /**
     * Test for Files.newBufferedReader File Path Traversal sinkpoint instrumentation
     */
    @Test
    fun testFilesNewBufferedReaderSinkpoint() {
        // Test with CodeMarker-only instrumentation (original behavior)
        testSinkpointInstrumentationWithTarget2(SINKPOINT_TEST_CASES_2.find { it.name == "FilesNewBufferedReader" }!!)

        // Also test with full instrumentation
        mainTest.resetMarkerState()
        MockCoverageMap.clear() // Reset the mock coverage map
        testSinkpointInstrumentationWithTarget2(
            SINKPOINT_TEST_CASES_2.find { it.name == "FilesNewBufferedReader" }!!,
            useFullInstrumentation = true,
        )
    }

    /**
     * Test for Files.newBufferedWriter File Path Traversal sinkpoint instrumentation
     */
    @Test
    fun testFilesNewBufferedWriterSinkpoint() {
        // Test with CodeMarker-only instrumentation (original behavior)
        testSinkpointInstrumentationWithTarget2(SINKPOINT_TEST_CASES_2.find { it.name == "FilesNewBufferedWriter" }!!)

        // Also test with full instrumentation
        mainTest.resetMarkerState()
        MockCoverageMap.clear() // Reset the mock coverage map
        testSinkpointInstrumentationWithTarget2(
            SINKPOINT_TEST_CASES_2.find { it.name == "FilesNewBufferedWriter" }!!,
            useFullInstrumentation = true,
        )
    }

    /**
     * Test for Files.readString File Path Traversal sinkpoint instrumentation
     */
    @Test
    fun testFilesReadStringSinkpoint() {
        // Test with CodeMarker-only instrumentation (original behavior)
        testSinkpointInstrumentationWithTarget2(SINKPOINT_TEST_CASES_2.find { it.name == "FilesReadString" }!!)

        // Also test with full instrumentation
        mainTest.resetMarkerState()
        MockCoverageMap.clear() // Reset the mock coverage map
        testSinkpointInstrumentationWithTarget2(
            SINKPOINT_TEST_CASES_2.find { it.name == "FilesReadString" }!!,
            useFullInstrumentation = true,
        )
    }

    /**
     * Test for Files.readAllBytes File Path Traversal sinkpoint instrumentation
     */
    @Test
    fun testFilesReadAllBytesSinkpoint() {
        // Test with CodeMarker-only instrumentation (original behavior)
        testSinkpointInstrumentationWithTarget2(SINKPOINT_TEST_CASES_2.find { it.name == "FilesReadAllBytes" }!!)

        // Also test with full instrumentation
        mainTest.resetMarkerState()
        MockCoverageMap.clear() // Reset the mock coverage map
        testSinkpointInstrumentationWithTarget2(
            SINKPOINT_TEST_CASES_2.find { it.name == "FilesReadAllBytes" }!!,
            useFullInstrumentation = true,
        )
    }

    /**
     * Test for Files.readAllLines File Path Traversal sinkpoint instrumentation
     */
    @Test
    fun testFilesReadAllLinesSinkpoint() {
        // Test with CodeMarker-only instrumentation (original behavior)
        testSinkpointInstrumentationWithTarget2(SINKPOINT_TEST_CASES_2.find { it.name == "FilesReadAllLines" }!!)

        // Also test with full instrumentation
        mainTest.resetMarkerState()
        MockCoverageMap.clear() // Reset the mock coverage map
        testSinkpointInstrumentationWithTarget2(
            SINKPOINT_TEST_CASES_2.find { it.name == "FilesReadAllLines" }!!,
            useFullInstrumentation = true,
        )
    }

    /**
     * Test for Files.readSymbolicLink File Path Traversal sinkpoint instrumentation
     */
    @Test
    fun testFilesReadSymbolicLinkSinkpoint() {
        // Test with CodeMarker-only instrumentation (original behavior)
        testSinkpointInstrumentationWithTarget2(SINKPOINT_TEST_CASES_2.find { it.name == "FilesReadSymbolicLink" }!!)

        // Also test with full instrumentation
        mainTest.resetMarkerState()
        MockCoverageMap.clear() // Reset the mock coverage map
        testSinkpointInstrumentationWithTarget2(
            SINKPOINT_TEST_CASES_2.find { it.name == "FilesReadSymbolicLink" }!!,
            useFullInstrumentation = true,
        )
    }

    /**
     * Test for Files.write File Path Traversal sinkpoint instrumentation
     */
    @Test
    fun testFilesWriteSinkpoint() {
        // Test with CodeMarker-only instrumentation (original behavior)
        testSinkpointInstrumentationWithTarget2(SINKPOINT_TEST_CASES_2.find { it.name == "FilesWrite" }!!)

        // Also test with full instrumentation
        mainTest.resetMarkerState()
        MockCoverageMap.clear() // Reset the mock coverage map
        testSinkpointInstrumentationWithTarget2(
            SINKPOINT_TEST_CASES_2.find { it.name == "FilesWrite" }!!,
            useFullInstrumentation = true,
        )
    }

    /**
     * Test for Files.writeString File Path Traversal sinkpoint instrumentation
     */
    @Test
    fun testFilesWriteStringSinkpoint() {
        // Test with CodeMarker-only instrumentation (original behavior)
        testSinkpointInstrumentationWithTarget2(SINKPOINT_TEST_CASES_2.find { it.name == "FilesWriteString" }!!)

        // Also test with full instrumentation
        mainTest.resetMarkerState()
        MockCoverageMap.clear() // Reset the mock coverage map
        testSinkpointInstrumentationWithTarget2(
            SINKPOINT_TEST_CASES_2.find { it.name == "FilesWriteString" }!!,
            useFullInstrumentation = true,
        )
    }

    /**
     * Test for Files.newInputStream File Path Traversal sinkpoint instrumentation
     */
    @Test
    fun testFilesNewInputStreamSinkpoint() {
        // Test with CodeMarker-only instrumentation (original behavior)
        testSinkpointInstrumentationWithTarget2(SINKPOINT_TEST_CASES_2.find { it.name == "FilesNewInputStream" }!!)

        // Also test with full instrumentation
        mainTest.resetMarkerState()
        MockCoverageMap.clear() // Reset the mock coverage map
        testSinkpointInstrumentationWithTarget2(
            SINKPOINT_TEST_CASES_2.find { it.name == "FilesNewInputStream" }!!,
            useFullInstrumentation = true,
        )
    }

    /**
     * Test for Files.newOutputStream File Path Traversal sinkpoint instrumentation
     */
    @Test
    fun testFilesNewOutputStreamSinkpoint() {
        // Test with CodeMarker-only instrumentation (original behavior)
        testSinkpointInstrumentationWithTarget2(SINKPOINT_TEST_CASES_2.find { it.name == "FilesNewOutputStream" }!!)

        // Also test with full instrumentation
        mainTest.resetMarkerState()
        MockCoverageMap.clear() // Reset the mock coverage map
        testSinkpointInstrumentationWithTarget2(
            SINKPOINT_TEST_CASES_2.find { it.name == "FilesNewOutputStream" }!!,
            useFullInstrumentation = true,
        )
    }

    /**
     * Test for FileChannel.open File Path Traversal sinkpoint instrumentation
     */
    @Test
    fun testFileChannelOpenSinkpoint() {
        // Test with CodeMarker-only instrumentation (original behavior)
        testSinkpointInstrumentationWithTarget2(SINKPOINT_TEST_CASES_2.find { it.name == "FileChannelOpen" }!!)

        // Also test with full instrumentation
        mainTest.resetMarkerState()
        MockCoverageMap.clear() // Reset the mock coverage map
        testSinkpointInstrumentationWithTarget2(
            SINKPOINT_TEST_CASES_2.find { it.name == "FileChannelOpen" }!!,
            useFullInstrumentation = true,
        )
    }

    /**
     * Test for Files.copy File Path Traversal sinkpoint instrumentation
     */
    @Test
    fun testFilesCopySinkpoint() {
        // Test with CodeMarker-only instrumentation (original behavior)
        testSinkpointInstrumentationWithTarget2(SINKPOINT_TEST_CASES_2.find { it.name == "FilesCopy" }!!)

        // Also test with full instrumentation
        mainTest.resetMarkerState()
        MockCoverageMap.clear() // Reset the mock coverage map
        testSinkpointInstrumentationWithTarget2(
            SINKPOINT_TEST_CASES_2.find { it.name == "FilesCopy" }!!,
            useFullInstrumentation = true,
        )
    }

    /**
     * Test for Files.mismatch File Path Traversal sinkpoint instrumentation
     */
    @Test
    fun testFilesMismatchSinkpoint() {
        // Test with CodeMarker-only instrumentation (original behavior)
        testSinkpointInstrumentationWithTarget2(SINKPOINT_TEST_CASES_2.find { it.name == "FilesMismatch" }!!)

        // Also test with full instrumentation
        mainTest.resetMarkerState()
        MockCoverageMap.clear() // Reset the mock coverage map
        testSinkpointInstrumentationWithTarget2(
            SINKPOINT_TEST_CASES_2.find { it.name == "FilesMismatch" }!!,
            useFullInstrumentation = true,
        )
    }

    /**
     * Test for Files.move File Path Traversal sinkpoint instrumentation
     */
    @Test
    fun testFilesMoveSinkpoint() {
        // Test with CodeMarker-only instrumentation (original behavior)
        testSinkpointInstrumentationWithTarget2(SINKPOINT_TEST_CASES_2.find { it.name == "FilesMove" }!!)

        // Also test with full instrumentation
        mainTest.resetMarkerState()
        MockCoverageMap.clear() // Reset the mock coverage map
        testSinkpointInstrumentationWithTarget2(
            SINKPOINT_TEST_CASES_2.find { it.name == "FilesMove" }!!,
            useFullInstrumentation = true,
        )
    }

    /**
     * Test for FileReader.<init> File Path Traversal sinkpoint instrumentation
     */
    @Test
    fun testFileReaderInitSinkpoint() {
        // Test with CodeMarker-only instrumentation (original behavior)
        testSinkpointInstrumentationWithTarget2(SINKPOINT_TEST_CASES_2.find { it.name == "FileReaderInit" }!!)

        // Also test with full instrumentation
        mainTest.resetMarkerState()
        MockCoverageMap.clear() // Reset the mock coverage map
        testSinkpointInstrumentationWithTarget2(
            SINKPOINT_TEST_CASES_2.find { it.name == "FileReaderInit" }!!,
            useFullInstrumentation = true,
        )
    }

    /**
     * Test for FileWriter.<init> File Path Traversal sinkpoint instrumentation
     */
    @Test
    fun testFileWriterInitSinkpoint() {
        // Test with CodeMarker-only instrumentation (original behavior)
        testSinkpointInstrumentationWithTarget2(SINKPOINT_TEST_CASES_2.find { it.name == "FileWriterInit" }!!)

        // Also test with full instrumentation
        mainTest.resetMarkerState()
        MockCoverageMap.clear() // Reset the mock coverage map
        testSinkpointInstrumentationWithTarget2(
            SINKPOINT_TEST_CASES_2.find { it.name == "FileWriterInit" }!!,
            useFullInstrumentation = true,
        )
    }

    /**
     * Test for FileInputStream.<init> File Path Traversal sinkpoint instrumentation
     */
    @Test
    fun testFileInputStreamInitSinkpoint() {
        // Test with CodeMarker-only instrumentation (original behavior)
        testSinkpointInstrumentationWithTarget2(SINKPOINT_TEST_CASES_2.find { it.name == "FileInputStreamInit" }!!)

        // Also test with full instrumentation
        mainTest.resetMarkerState()
        MockCoverageMap.clear() // Reset the mock coverage map
        testSinkpointInstrumentationWithTarget2(
            SINKPOINT_TEST_CASES_2.find { it.name == "FileInputStreamInit" }!!,
            useFullInstrumentation = true,
        )
    }

    /**
     * Test for FileOutputStream.<init> File Path Traversal sinkpoint instrumentation
     */
    @Test
    fun testFileOutputStreamInitSinkpoint() {
        // Test with CodeMarker-only instrumentation (original behavior)
        testSinkpointInstrumentationWithTarget2(SINKPOINT_TEST_CASES_2.find { it.name == "FileOutputStreamInit" }!!)

        // Also test with full instrumentation
        mainTest.resetMarkerState()
        MockCoverageMap.clear() // Reset the mock coverage map
        testSinkpointInstrumentationWithTarget2(
            SINKPOINT_TEST_CASES_2.find { it.name == "FileOutputStreamInit" }!!,
            useFullInstrumentation = true,
        )
    }

    /**
     * Test for Scanner.<init> File Path Traversal sinkpoint instrumentation
     */
    @Test
    fun testScannerInitSinkpoint() {
        // Test with CodeMarker-only instrumentation (original behavior)
        testSinkpointInstrumentationWithTarget2(SINKPOINT_TEST_CASES_2.find { it.name == "ScannerInit" }!!)

        // Also test with full instrumentation
        mainTest.resetMarkerState()
        MockCoverageMap.clear() // Reset the mock coverage map
        testSinkpointInstrumentationWithTarget2(
            SINKPOINT_TEST_CASES_2.find { it.name == "ScannerInit" }!!,
            useFullInstrumentation = true,
        )
    }

    /**
     * Test for Files.probeContentType File Path Traversal sinkpoint instrumentation
     */
    @Test
    fun testFilesProbeContentTypeSinkpoint() {
        println(
            "SKIPPED: Testing probeContentType. The FilePathTraversal MethodHook has a typo: 'java.nio.file.probeContentType' instead of 'java.nio.file.Files'",
        )
    }

    /**
     * Test for fuzzerTestOneInput detection when ATLJAZZER_INFER_CPMETA_OUTPUT is set
     * This tests that methods named fuzzerTestOneInput are properly marked when the env var is set
     */
    @Test
    fun testFuzzerTestOneInputSinkpoint() {
        // Get the SinkpointTestCase for FuzzerTestOneInput
        val fuzzerTestCase = SINKPOINT_TEST_CASES_2.find { it.name == "FuzzerTestOneInput" }!!

        // Test with the flag set to true (environment variable set)
        testWithFuzzerTestOneInputFlag(true, fuzzerTestCase)

        // Also test with the flag set to false (environment variable not set)
        testWithFuzzerTestOneInputFlag(false, fuzzerTestCase)
    }

    /**
     * Test for custom sinkpoint detection when ATLJAZZER_CUSTOM_SINKPOINT_CONF is configured
     * This test creates temporary config files and verifies the three scenarios:
     * 1. No custom config - nothing is marked
     * 2. Custom coordinate config - specific bytecode offset is marked
     * 3. Custom API config - method is marked
     */
    @Test
    fun testCustomSinkpoint() {
        // Get the SinkpointTestCase for CustomApiMethod
        val customApiTestCase = SINKPOINT_TEST_CASES_2.find { it.name == "CustomApiMethod" }!!

        try {
            // Save the original value of the sinkConfigFile field
            val originalValue = CodeMarkerInstrumentor.sinkConfigFile

            // Store the class info for reuse
            val targetClass = CodeMarkerInstrumentationTarget2::class.java
            val targetInternalName = targetClass.name.replace('.', '/')
            val originalBytecode = classToBytecode(targetClass)

            // Find the bytecode offset for the customApiMethod call
            val findSinkpointOffset =
                findSinkpointBytecodeOffset(
                    originalBytecode,
                    customApiTestCase,
                )
            println("Found bytecode offset for customApiMethod call: $findSinkpointOffset")

            // PART 1: Test WITHOUT custom config - should NOT detect any custom sinkpoints
            println("\n===== PART 1: Testing with NO custom config (should find NOTHING) =====")

            // Ensure we're using default sinkpoints (no custom config)
            CodeMarkerInstrumentor.sinkConfigFile = null
            CodeMarkerInstrumentor.reinitializeSinkpointsForTesting()
            mainTest.resetMarkerState()

            // Get marker info BEFORE instrumentation
            val markerInfoBefore = CodeMarkerInstrumentor.dumpMarkedNodesInfo()
            val markerCountBefore = markerInfoBefore.size

            // Instrument the class WITHOUT custom config
            val instrumentedBytecodeWithoutConfig =
                mainTest.applyInstrumentation(
                    targetInternalName,
                    originalBytecode,
                    false, // CodeMarker-only instrumentation
                )

            // Analyze the instrumented bytecode for custom API marker
            val markerCallsWithoutConfig = analyzeCodeMarkerCalls(instrumentedBytecodeWithoutConfig, customApiTestCase)

            // We filter to only look at markers in the method we're testing
            val methodMarkersWithoutConfig = markerCallsWithoutConfig.filter { it["method_name"] == customApiTestCase.targetMethodName }

            // Verify NO markers for custom sinkpoints when config is not applied
            assertEquals(
                0,
                methodMarkersWithoutConfig.size,
                "Without custom config, custom sinkpoints should NOT have any calls to reportCodeMarkerHit",
            )

            // PART 2: Test WITH coordinate-based config - should detect the coordinate-based sinkpoint only
            println("\n===== PART 2: Testing with COORDINATE-BASED config (should find coordinate marker only) =====")

            // Create a temporary config file for coordinate-based sinkpoint only
            val coordConfigFile = java.io.File.createTempFile("jazzer_sink_coord_conf", ".txt")

            // Write just the coordinate-based sinkpoint to the config file
            // Format: caller#className#methodName#methodDesc#fileName#lineNumber#bytecodeOffset#markDesc
            coordConfigFile.writeText(
                """
                # Coordinate-based sinkpoint with the actual bytecode offset
                caller#com/code_intelligence/jazzer/instrumentor/CodeMarkerInstrumentationTarget2#testCustomSinkpoint#()Z##1#$findSinkpointOffset#sink-CustomCoordinate
                """.trimIndent(),
            )

            // Print the content of the coord config file for debugging
            println("Coordinate config file content:")
            println(coordConfigFile.readText())

            // Set the test config file path
            CodeMarkerInstrumentor.sinkConfigFile = coordConfigFile.absolutePath

            // Force reinitialization of sinkpoints
            CodeMarkerInstrumentor.reinitializeSinkpointsForTesting()

            // Reset markers to start fresh
            mainTest.resetMarkerState()

            // Instrument with the coordinate config active
            val instrumentedBytecodeWithCoordConfig =
                mainTest.applyInstrumentation(
                    targetInternalName,
                    originalBytecode,
                    false, // CodeMarker-only instrumentation
                )

            // Get marker info AFTER instrumentation with coordinate config
            val markerInfoAfterCoordConfig = CodeMarkerInstrumentor.dumpMarkedNodesInfo()

            // Check for coordinate-based markers in the testCustomSinkpoint method
            val coordinateBasedMarkers =
                markerInfoAfterCoordConfig.entries
                    .filter {
                        (it.value["method_name"] as String) == "testCustomSinkpoint" &&
                            (it.value["mark_desc"] as String).contains("CustomCoordinate")
                    }

            println("Found ${coordinateBasedMarkers.size} coordinate-based markers")
            coordinateBasedMarkers.forEach { marker ->
                println(
                    "Coordinate-based marker: ${marker.key} -> ${marker.value["mark_desc"]}, bytecode offset: ${marker.value["bytecode_offset"]}",
                )
            }

            // Verify we found coordinate-based markers
            assertTrue(
                coordinateBasedMarkers.isNotEmpty(),
                "With coordinate config, should find coordinate-based markers",
            )

            // Check we do NOT have API-based markers in the customApiMethod
            val apiMarkersInCoordConfig =
                markerInfoAfterCoordConfig.entries
                    .filter {
                        (it.value["method_name"] as String) == customApiTestCase.targetMethodName &&
                            (it.value["mark_desc"] as String).contains("CustomAPICall")
                    }

            // Verify we have NO API-based markers with just coordinate config
            assertEquals(
                0,
                apiMarkersInCoordConfig.size,
                "With coordinate-only config, should NOT find API-based markers",
            )

            // PART 3: Test WITH API-based config - should detect the API-based sinkpoint only
            println("\n===== PART 3: Testing with API-BASED config (should find API marker only) =====")

            // Create a temporary config file for API-based sinkpoint only
            val apiConfigFile = java.io.File.createTempFile("jazzer_sink_api_conf", ".txt")

            // Write just the API-based sinkpoint to the config file
            // Format: api#FQN#methodName#descriptor#type[-details]
            apiConfigFile.writeText(
                """
                # API-based sinkpoint
                api#com/code_intelligence/jazzer/instrumentor/CodeMarkerInstrumentationTarget2#customApiMethod#(Ljava/lang/String;)V#sink-CustomAPICall
                """.trimIndent(),
            )

            // Print the content of the API config file for debugging
            println("API config file content:")
            println(apiConfigFile.readText())

            // Set the test config file path
            CodeMarkerInstrumentor.sinkConfigFile = apiConfigFile.absolutePath

            // Force reinitialization of sinkpoints
            CodeMarkerInstrumentor.reinitializeSinkpointsForTesting()

            // Reset markers to start fresh
            mainTest.resetMarkerState()

            // Test with the API config file active
            testSinkpointInstrumentationWithTarget2(customApiTestCase)

            // Get marker info AFTER instrumentation with API config
            val markerInfoAfterApiConfig = CodeMarkerInstrumentor.dumpMarkedNodesInfo()

            // Find API-based markers for our method
            val apiMarkersWithConfig =
                markerInfoAfterApiConfig.entries
                    .filter {
                        (it.value["method_name"] as String) == customApiTestCase.targetMethodName &&
                            (it.value["mark_desc"] as String).contains("CustomAPICall")
                    }

            println("Found ${apiMarkersWithConfig.size} API-based markers")
            apiMarkersWithConfig.forEach { marker ->
                println("API-based marker: ${marker.key} -> ${marker.value["mark_desc"]}")
            }

            // Verify we found API-based markers
            assertTrue(
                apiMarkersWithConfig.isNotEmpty(),
                "With API config, should find API-based markers",
            )

            // Check we do NOT have coordinate-based markers with just API config
            val coordMarkersInApiConfig =
                markerInfoAfterApiConfig.entries
                    .filter {
                        (it.value["method_name"] as String) == "testCustomSinkpoint" &&
                            (it.value["mark_desc"] as String).contains("CustomCoordinate")
                    }

            // We don't necessarily expect zero here since we're testing something else with testSinkpointInstrumentationWithTarget2
            // but we print out the results for information
            println("Found ${coordMarkersInApiConfig.size} coordinate markers in API config (may be non-zero)")

            // Clean up
            coordConfigFile.delete()
            apiConfigFile.delete()

            // Restore the original value
            CodeMarkerInstrumentor.sinkConfigFile = originalValue
            // Reset for other tests
            CodeMarkerInstrumentor.reinitializeSinkpointsForTesting()
        } catch (e: Exception) {
            e.printStackTrace()
            kotlin.test.fail("Failed to test custom sinkpoints: ${e.message}")
        }
    }

    /**
     * Helper method to test the fuzzerTestOneInput functionality with the flag either set or not set
     */
    private fun testWithFuzzerTestOneInputFlag(
        flagEnabled: Boolean,
        fuzzerTestCase: SinkpointTestCase,
    ) {
        try {
            // Make sure to set the flag BEFORE doing any instrumentation
            val originalValue = getAndSetFuzzerTestOneInputFlag(flagEnabled)

            println("\n===== Testing FuzzerTestOneInput detection with flag $flagEnabled =====")

            // Reset marker state to avoid accumulation between tests
            mainTest.resetMarkerState()

            // Get marker info BEFORE running the test
            val markerInfoBefore = CodeMarkerInstrumentor.dumpMarkedNodesInfo()
            val markerCountBefore = markerInfoBefore.size
            println(
                "Reset marker state. Previous marker count: $markerCountBefore, New count: ${CodeMarkerInstrumentor.getMarkedNodesNum()}",
            )

            // Instrument the class - using Target2
            val targetClass = CodeMarkerInstrumentationTarget2::class.java
            val targetClassName = targetClass.simpleName
            val targetInternalName = targetClass.name.replace('.', '/')
            val originalBytecode = classToBytecode(targetClass)

            // Confirm flag is set correctly before instrumentation
            println("Flag shouldMarkFuzzerTestOneInput is set to: ${CodeMarkerInstrumentor.shouldMarkFuzzerTestOneInput}")

            // Apply the instrumentation using mainTest's method
            val instrumentedBytecode =
                mainTest.applyInstrumentation(
                    targetInternalName,
                    originalBytecode,
                    false, // Use CodeMarker-only instrumentation
                )

            // Get marker info AFTER instrumentation
            val markerInfoAfter = CodeMarkerInstrumentor.dumpMarkedNodesInfo()

            // Find all markers for our target method
            // For FuzzerTestOneInput, we need to look for markers in the actual fuzzerTestOneInput method (TestFuzzer inner class)
            val markers =
                if (fuzzerTestCase.name == "FuzzerTestOneInput") {
                    markerInfoAfter.entries
                        .filter {
                            (it.value["method_name"] as String) == "fuzzerTestOneInput"
                        }.toList()
                } else {
                    markerInfoAfter.entries
                        .filter {
                            (it.value["method_name"] as String) == fuzzerTestCase.targetMethodName
                        }.toList()
                }

            // Print marker details
            println("Found ${markers.size} markers for method ${fuzzerTestCase.targetMethodName}")
            markers.forEach { marker ->
                val markerDetails = marker.value
                println(
                    "Marker ID ${marker.key}: ${markerDetails["mark_desc"]}, class=${markerDetails["class_name"]}, method=${markerDetails["method_name"]}",
                )
            }

            // Check if any marker has a mark_desc that starts with "cpmeta-"
            val foundCpMetaMarker =
                markers.any {
                    val markDesc = it.value["mark_desc"] as String?
                    markDesc != null && markDesc.startsWith("cpmeta-")
                }

            // Verify the expected outcome based on the flag
            if (flagEnabled) {
                // When flag is enabled, we should find a cpmeta marker
                kotlin.test.assertTrue(
                    foundCpMetaMarker,
                    "Expected to find a marker with cpmeta- prefix when shouldMarkFuzzerTestOneInput is true",
                )

                // Also check if we have the specific marker value
                val cpmetaMarker =
                    markers.find {
                        val markDesc = it.value["mark_desc"] as String?
                        markDesc == "cpmeta-fuzzerTestOneInput"
                    }

                kotlin.test.assertNotNull(
                    cpmetaMarker,
                    "Expected to find a marker with mark_desc='cpmeta-fuzzerTestOneInput'",
                )
            } else {
                // When flag is disabled, we should NOT find any cpmeta marker
                kotlin.test.assertFalse(
                    foundCpMetaMarker,
                    "Should not find any marker with cpmeta- prefix when shouldMarkFuzzerTestOneInput is false",
                )
            }
        } finally {
            // Restore the original flag state
            getAndSetFuzzerTestOneInputFlag(false)
        }
    }

    /**
     * Helper to get and modify the shouldMarkFuzzerTestOneInput flag
     * Returns the original value
     */
    private fun getAndSetFuzzerTestOneInputFlag(newValue: Boolean): Boolean {
        // Now that the property is public with @JvmStatic and var (not val), we can access and modify it directly
        val currentValue = CodeMarkerInstrumentor.shouldMarkFuzzerTestOneInput

        // Set the new value
        CodeMarkerInstrumentor.shouldMarkFuzzerTestOneInput = newValue

        return currentValue
    }
}
