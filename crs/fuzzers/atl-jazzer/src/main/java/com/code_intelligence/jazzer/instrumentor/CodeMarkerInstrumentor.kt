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

import com.code_intelligence.jazzer.utils.Log
import org.objectweb.asm.ClassReader
import org.objectweb.asm.ClassWriter
import org.objectweb.asm.Opcodes
import org.objectweb.asm.tree.AbstractInsnNode
import org.objectweb.asm.tree.ClassNode
import org.objectweb.asm.tree.InsnList
import org.objectweb.asm.tree.InsnNode
import org.objectweb.asm.tree.IntInsnNode
import org.objectweb.asm.tree.LdcInsnNode
import org.objectweb.asm.tree.LineNumberNode
import org.objectweb.asm.tree.MethodInsnNode
import org.objectweb.asm.tree.MethodNode

internal class CodeMarkerInstrumentor(
    private val suppMockCovAPI: Boolean = false, // for unit test
) : Instrumentor {
    override fun instrument(
        internalClassName: String,
        bytecode: ByteArray,
    ): ByteArray {
        val node = ClassNode()
        val reader = ClassReader(bytecode)
        reader.accept(node, 0)
        val className = node.name
        val sourceFile = node.sourceFile
        for (method in node.methods) {
            if (shouldInstrument(method)) {
                doInstrumentation(className, sourceFile, method)
            }
        }

        val writer = ClassWriter(ClassWriter.COMPUTE_MAXS)
        node.accept(writer)
        return writer.toByteArray()
    }

    /**
     * Checks if the given instruction is at coordinates that should be marked
     * (i.e., is a method call that matches a sinkpoint)
     *
     * @return a copy of the coordinate with markDesc set if it should be marked, null otherwise
     */
    private fun matchMarkedCoordinate(
        insn: AbstractInsnNode,
        coord: InsnCoordinate,
    ): InsnCoordinate? {
        // if ATLJAZZER_INFER_CPMETA_OUTPUT is set, we mark the 1st insn of entry points
        // TODO: supp custom fuzzer entry points
        if (shouldMarkFuzzerTestOneInput && insn.getBytecodeOffset() == 0) {
            if (coord.methodName == "fuzzerTestOneInput") {
                Log.info("Found first instruction of fuzzerTestOneInput method, adding cpmeta marker")
                return coord.copy(markDesc = "cpmeta-fuzzerTestOneInput")
            } else if (coord.methodName == "fuzzerInitialize") {
                Log.info("Found first instruction of fuzzerInitialize method, adding cpmeta marker")
                return coord.copy(markDesc = "cpmeta-fuzzerInitialize")
            }
        }

        // Check for exact sinkpoint coordinates
        val exactCoordKey = "${coord.className}#${coord.methodName}#${coord.methodDesc}#${coord.bytecodeOffset}"
        val matchingCoord = SINKPOINT_COORDS_MAP[exactCoordKey]
        if (matchingCoord != null) {
            return coord.copy(markDesc = matchingCoord.markDesc)
        }

        // Check for method insn invoking sinkpoint CALLEE API
        if (insn !is MethodInsnNode ||
            insn.opcode !in
            listOf(
                Opcodes.INVOKEINTERFACE,
                Opcodes.INVOKESPECIAL,
                Opcodes.INVOKESTATIC,
                Opcodes.INVOKEVIRTUAL,
            )
        ) {
            return null
        }

        val exactMatch =
            SINKPOINT_CALLEES.find {
                it.calleeClassName == insn.owner &&
                    it.calleeMethodName == insn.name &&
                    it.calleeMethodDesc == insn.desc
            }

        if (exactMatch != null) {
            return coord.copy(markDesc = exactMatch.markDesc)
        }

        val anyDescMatch =
            SINKPOINT_CALLEES.find {
                it.calleeClassName == insn.owner &&
                    it.calleeMethodName == insn.name &&
                    it.calleeMethodDesc == null
            }

        if (anyDescMatch != null) {
            return coord.copy(markDesc = anyDescMatch.markDesc)
        }

        return null
    }

    /**
     * Assign a new markId for a unprocessed coordinate
     * Returns the new markId, or null if has processed already
     */
    private fun assignMarkIdForCoord(
        insn: AbstractInsnNode,
        coord: InsnCoordinate,
    ): Int? {
        if (insn2MarkId.containsKey(insn)) {
            // Insn has already been assigned, return null
            return null
        }

        val markId = insn2MarkId.size + 1
        insn2MarkId[insn] = markId
        markId2Coord[markId] = coord
        return markId
    }

    private fun doInstrumentation(
        className: String,
        fileName: String?,
        method: MethodNode,
    ) {
        var curLineNO: Int? = null

        for (insn in method.instructions.toArray()) {
            if (insn is LineNumberNode) {
                curLineNO = insn.line
                continue
            }

            val curCoord =
                InsnCoordinate(
                    className = className,
                    methodName = method.name,
                    methodDesc = method.desc,
                    fileName = fileName,
                    lineNumber = curLineNO,
                    bytecodeOffset = insn.getBytecodeOffset(),
                    markDesc = null,
                )

            val markedCoord = matchMarkedCoordinate(insn, curCoord)
            if (markedCoord != null) {
                val markId = assignMarkIdForCoord(insn, markedCoord)
                if (markId != null) {
                    method.instructions.insertBefore(insn, instrumentCodeMarker(markId))
                } else {
                    Log.warn("Skip duplicate assign of markId for ${curCoord.toStr()}")
                }
            }
        }
    }

    private fun instrumentCodeMarker(markId: Int) =
        InsnList().apply {
            // Push the int markId onto the stack
            when {
                // impossible, warn
                markId < 0 -> {
                    Log.warn("Invalid markId: $markId")
                }
                // [0, 5] <=> ICONST_0 .. ICONST_5
                markId <= 5 -> {
                    add(InsnNode(Opcodes.ICONST_0 + markId))
                }
                // [0, 127] <=> BIPUSH
                markId <= Byte.MAX_VALUE -> {
                    add(IntInsnNode(Opcodes.BIPUSH, markId))
                }
                // [0, 32767] <=> SIPUSH
                markId >= Short.MIN_VALUE && markId <= Short.MAX_VALUE -> {
                    add(IntInsnNode(Opcodes.SIPUSH, markId))
                }
                // [32768, ..] <=> LDC/LDC_W/LDC2_W
                else -> {
                    // N.B.: ASM will automatically use LDC, LDC_W, or LDC2_W
                    add(LdcInsnNode(markId))
                }
            }

            // Invoke the static method reportCodeMarkerHit(int)
            add(
                MethodInsnNode(
                    Opcodes.INVOKESTATIC,
                    "com/code_intelligence/jazzer/api/Jazzer",
                    "reportCodeMarkerHit",
                    "(I)V",
                    false,
                ),
            )
        }

    companion object {
        // Assigning mark IDs
        private val insn2MarkId = mutableMapOf<AbstractInsnNode, Int>()

        // Mapping mark IDs to insn coordinate & meta info
        private val markId2Coord = mutableMapOf<Int, InsnCoordinate>()

        // Flag for ATLJAZZER_INFER_CPMETA_OUTPUT environment variable
        // Public for testing purposes and mutable to allow testing different states
        @JvmStatic
        var shouldMarkFuzzerTestOneInput = System.getenv("ATLJAZZER_INFER_CPMETA_OUTPUT") != null

        // Config file path for ATLJAZZER_CUSTOM_SINKPOINT_CONF environment variable
        // Package-private for testing purposes
        @JvmStatic
        var sinkConfigFile = System.getenv("ATLJAZZER_CUSTOM_SINKPOINT_CONF")

        data class InsnCoordinate(
            val className: String,
            val methodName: String,
            // N.B. method.signature is NOT used as it is mostly null in testing
            val methodDesc: String,
            val fileName: String?,
            val lineNumber: Int?,
            val bytecodeOffset: Int,
            // Never null for marked coordination
            val markDesc: String? = null,
        ) {
            fun toMap(): Map<String, Any?> =
                mapOf(
                    "class_name" to className,
                    "method_name" to methodName,
                    "method_desc" to methodDesc,
                    "bytecode_offset" to bytecodeOffset,
                    "mark_desc" to markDesc,
                    "file_name" to fileName,
                    "line_num" to lineNumber,
                    "sha256" to sha256(),
                )

            fun toStr(): String =
                "insn @ <$className $methodName $methodDesc $bytecodeOffset> ($fileName:$lineNumber)" +
                    (markDesc?.let { " [desc: $it]" } ?: "")

            fun sha256(): String {
                val input = listOf(className, methodName, methodDesc, bytecodeOffset.toString(), markDesc ?: "").joinToString("#")
                val bytes = input.toByteArray(Charsets.UTF_8)
                val md = java.security.MessageDigest.getInstance("SHA-256")
                val digest = md.digest(bytes)
                return digest.joinToString("") { "%02x".format(it) }
            }
        }

        // Public static APIs to dump code marker info
        @JvmStatic
        fun dumpMarkedNodesInfo(): Map<Int, Map<String, Any?>> = markId2Coord.mapValues { (_, info) -> info.toMap() }

        /**
         * Get coordinate info for a specific mark ID
         * Returns a map with all coordinate info or empty map if mark ID not found
         */
        @JvmStatic
        fun getCoordinateInfoForMarkId(markId: Int): Map<String, Any?> {
            val info = markId2Coord[markId] ?: return emptyMap()
            return info.toMap()
        }

        @JvmStatic
        fun getMarkedNodesNum(): Int = markId2Coord.size

        // N.B. currently testing purpose only
        @JvmStatic
        fun resetMarkersForTesting() {
            insn2MarkId.clear()
            markId2Coord.clear()
        }

        data class CodeLocation(
            val calleeClassName: String,
            val calleeMethodName: String,
            val calleeMethodDesc: String? = null,
            val markDesc: String,
        )

        /**
         * Loads sinkpoint definitions from a file.
         * The file can contain two types of sinkpoint definitions:
         * 1. API-based sinkpoints (format: api#calleeClassName#calleeMethodName#calleeMethodDesc#markDesc)
         *    Empty string in calleeMethodDesc means null (match any descriptor).
         * 2. Coordinate-based sinkpoints (format: caller#className#methodName#methodDesc#fileName#lineNumber#bytecodeOffset#markDesc)
         *    - className, methodName, methodDesc, bytecodeOffset, and markDesc are required and must be valid
         *    - bytecodeOffset must be a valid non-negative integer specifying the exact instruction offset to mark
         *    - fileName can be empty (since debug info can be stripped in jars)
         *    - lineNumber can be empty (since debug info can be stripped)
         * Lines starting with # are treated as comments and ignored.
         */
        private fun loadConfigFromFile(filePath: String): Pair<Set<CodeLocation>, Set<InsnCoordinate>> {
            val apiLocations = mutableSetOf<CodeLocation>()
            val coordLocations = mutableSetOf<InsnCoordinate>()

            try {
                val file = java.io.File(filePath)
                if (file.exists() && file.isFile) {
                    file.forEachLine { line ->
                        if (line.isNotBlank() && !line.startsWith("#")) { // Skip comments and empty lines
                            if (line.startsWith("api#")) {
                                // Parse api-based sinkpoint
                                val parts = line.substring(4).split("#", limit = 4)
                                if (parts.size == 4) {
                                    val calleeMethodDesc = if (parts[2].isEmpty()) null else parts[2]
                                    apiLocations.add(
                                        CodeLocation(
                                            calleeClassName = parts[0],
                                            calleeMethodName = parts[1],
                                            calleeMethodDesc = calleeMethodDesc,
                                            markDesc = parts[3],
                                        ),
                                    )
                                } else {
                                    Log.warn("Invalid api line format in sink config file: $line")
                                }
                            } else if (line.startsWith("caller#")) {
                                // Parse caller-based sinkpoint
                                val parts = line.substring(7).split("#", limit = 7)
                                if (parts.size == 7) {
                                    // Validate required fields
                                    val bytecodeOffset = parts[5].toIntOrNull()
                                    if (parts[0].isEmpty() ||
                                        parts[1].isEmpty() ||
                                        parts[2].isEmpty() ||
                                        bytecodeOffset == null ||
                                        bytecodeOffset < 0 ||
                                        parts[6].isEmpty()
                                    ) {
                                        Log.warn(
                                            "Invalid caller entry: className, methodName, methodDesc must not be empty, bytecodeOffset must be a valid non-negative integer, and markDesc must not be empty: $line",
                                        )
                                    } else {
                                        coordLocations.add(
                                            InsnCoordinate(
                                                className = parts[0],
                                                methodName = parts[1],
                                                methodDesc = parts[2],
                                                fileName = if (parts[3].isEmpty()) null else parts[3],
                                                lineNumber = if (parts[4].isEmpty()) null else parts[4].toIntOrNull(),
                                                bytecodeOffset = bytecodeOffset,
                                                markDesc = parts[6],
                                            ),
                                        )
                                    }
                                } else {
                                    Log.warn("Invalid caller line format in sink config file: $line")
                                }
                            } else {
                                Log.warn("Invalid line format in sink config file, must start with api# or caller#: $line")
                            }
                        }
                    }
                    Log.info("Loaded ${apiLocations.size} API sinkpoints and ${coordLocations.size} coordinate sinkpoints from $filePath")
                } else {
                    Log.warn("Sink config file not found or not a regular file: $filePath")
                }
            } catch (e: Exception) {
                Log.warn("Error reading sink config file: ${e.message}")
            }
            return Pair(apiLocations, coordLocations)
        }

        // Make this configurable through ATLJAZZER_CUSTOM_SINKPOINT_CONF environment variable
        // Changed from lazy property to nullable property with initialization on access
        @JvmStatic
        private var sinkpointCallees: Set<CodeLocation>? = null

        @JvmStatic
        private var sinkpointCoords: Set<InsnCoordinate>? = null

        // Map for quick lookups: "className#methodName#methodDesc#bytecodeOffset" -> InsnCoordinate
        @JvmStatic
        private var sinkpointCoordsMap: Map<String, InsnCoordinate>? = null

        // Synchronized initialization for all sinkpoint-related properties
        @Synchronized
        private fun initializeSinkpointsIfNeeded() {
            if (sinkpointCallees == null || sinkpointCoords == null) {
                val (callees, coords) = initializeSinkpoints()
                sinkpointCallees = callees
                sinkpointCoords = coords
                // No need to initialize sinkpointCoordsMap here as it depends on SINKPOINT_COORDS
                // and will be initialized when first accessed
            }
        }

        @JvmStatic
        val SINKPOINT_CALLEES: Set<CodeLocation>
            get() {
                initializeSinkpointsIfNeeded()
                return sinkpointCallees!!
            }

        @JvmStatic
        val SINKPOINT_COORDS: Set<InsnCoordinate>
            get() {
                initializeSinkpointsIfNeeded()
                return sinkpointCoords!!
            }

        @JvmStatic
        val SINKPOINT_COORDS_MAP: Map<String, InsnCoordinate>
            get() {
                // Initialize if null
                if (sinkpointCoordsMap == null) {
                    // Ensure SINKPOINT_COORDS is initialized
                    val coords = SINKPOINT_COORDS
                    // Create a map with className#methodName#methodDesc#bytecodeOffset as key for exact matching
                    sinkpointCoordsMap =
                        coords.associateBy {
                            "${it.className}#${it.methodName}#${it.methodDesc}#${it.bytecodeOffset}"
                        }
                }
                return sinkpointCoordsMap!!
            }

        @JvmStatic
        private fun initializeSinkpoints(): Pair<Set<CodeLocation>, Set<InsnCoordinate>> {
            val hardcodedSinkpoints =
                setOf(
                    // crs/fuzzers/atl-jazzer/sanitizers/src/main/java/com/code_intelligence/jazzer/sanitizers/ReflectiveCall.kt
                    // From lines 33-45
                    CodeLocation(
                        "java/lang/Class",
                        "forName",
                        "(Ljava/lang/String;)Ljava/lang/Class;",
                        "sink-UnsafeReflectiveCall",
                    ),
                    CodeLocation(
                        "java/lang/Class",
                        "forName",
                        "(Ljava/lang/String;ZLjava/lang/ClassLoader;)Ljava/lang/Class;",
                        "sink-UnsafeReflectiveCall",
                    ),
                    // From lines 46-57
                    CodeLocation(
                        "java/lang/ClassLoader",
                        "loadClass",
                        "(Ljava/lang/String;)Ljava/lang/Class;",
                        "sink-UnsafeReflectiveCall",
                    ),
                    CodeLocation(
                        "java/lang/ClassLoader",
                        "loadClass",
                        "(Ljava/lang/String;Z)Ljava/lang/Class;",
                        "sink-UnsafeReflectiveCall",
                    ),
                    // From lines 70-82
                    CodeLocation(
                        "java/lang/Class",
                        "forName",
                        "(Ljava/lang/Module;Ljava/lang/String;)Ljava/lang/Class;",
                        "sink-UnsafeReflectiveCall",
                    ),
                    CodeLocation(
                        "java/lang/ClassLoader",
                        "loadClass",
                        "(Ljava/lang/Module;Ljava/lang/String;)Ljava/lang/Class;",
                        "sink-UnsafeReflectiveCall",
                    ),
                    // From lines 95-102, calleeMethodDesc is not present in the source code
                    // Using null descriptors to match all overloads, just like in the original sanitizer
                    CodeLocation(
                        "java/lang/Runtime",
                        "load",
                        null,
                        "sink-LoadArbitraryLibrary",
                    ),
                    CodeLocation(
                        "java/lang/Runtime",
                        "loadLibrary",
                        null,
                        "sink-LoadArbitraryLibrary",
                    ),
                    CodeLocation(
                        "java/lang/System",
                        "load",
                        null,
                        "sink-LoadArbitraryLibrary",
                    ),
                    CodeLocation(
                        "java/lang/System",
                        "loadLibrary",
                        null,
                        "sink-LoadArbitraryLibrary",
                    ),
                    CodeLocation(
                        "java/lang/System",
                        "mapLibraryName",
                        null,
                        "sink-LoadArbitraryLibrary",
                    ),
                    CodeLocation(
                        "java/lang/ClassLoader",
                        "findLibrary",
                        null,
                        "sink-LoadArbitraryLibrary",
                    ),
                    // crs/fuzzers/atl-jazzer/sanitizers/src/main/java/com/code_intelligence/jazzer/sanitizers/OsCommandInjection.kt
                    // From lines 39-44, calleeMethodDesc is not present in the source code
                    // Also adding additionalClassesToHook entry for ProcessBuilder
                    CodeLocation(
                        "java/lang/ProcessImpl",
                        "start",
                        null,
                        "sink-OsCommandInjection",
                    ),
                    CodeLocation(
                        "java/lang/ProcessBuilder",
                        "start",
                        null,
                        "sink-OsCommandInjection",
                    ),
                    // crs/fuzzers/atl-jazzer/sanitizers/src/main/java/com/code_intelligence/jazzer/sanitizers/NamingContextLookup.kt
                    // From lines 37-49
                    CodeLocation(
                        "javax/naming/Context",
                        "lookup",
                        "(Ljava/lang/String;)Ljava/lang/Object;",
                        "sink-RemoteJNDILookup",
                    ),
                    CodeLocation(
                        "javax/naming/Context",
                        "lookupLink",
                        "(Ljava/lang/String;)Ljava/lang/Object;",
                        "sink-RemoteJNDILookup",
                    ),
                    // crs/fuzzers/atl-jazzer/sanitizers/src/main/java/com/code_intelligence/jazzer/sanitizers/LdapInjection.kt
                    // From lines 54-91
                    // Fixing typos in descriptors from original sanitizer
                    CodeLocation(
                        "javax/naming/directory/DirContext",
                        "search",
                        "(Ljava/lang/String;Ljavax/naming/directory/Attributes;)Ljavax/naming/NamingEnumeration;",
                        "sink-LdapInjection",
                    ),
                    CodeLocation(
                        "javax/naming/directory/DirContext",
                        "search",
                        "(Ljava/lang/String;Ljavax/naming/directory/Attributes;[Ljava/lang/String;)Ljavax/naming/NamingEnumeration;",
                        "sink-LdapInjection",
                    ),
                    CodeLocation(
                        "javax/naming/directory/DirContext",
                        "search",
                        "(Ljava/lang/String;Ljava/lang/String;Ljavax/naming/directory/SearchControls;)Ljavax/naming/NamingEnumeration;",
                        "sink-LdapInjection",
                    ),
                    CodeLocation(
                        "javax/naming/directory/DirContext",
                        "search",
                        "(Ljavax/naming/Name;Ljava/lang/String;[Ljava/lang/Object;Ljavax/naming/directory/SearchControls;)Ljavax/naming/NamingEnumeration;",
                        "sink-LdapInjection",
                    ),
                    CodeLocation(
                        "javax/naming/directory/DirContext",
                        "search",
                        "(Ljava/lang/String;Ljava/lang/String;[Ljava/lang/Object;Ljavax/naming/directory/SearchControls;)Ljavax/naming/NamingEnumeration;",
                        "sink-LdapInjection",
                    ),
                    // Adding entries for InitialDirContext from additionalClassesToHook
                    CodeLocation(
                        "javax/naming/directory/InitialDirContext",
                        "search",
                        "(Ljava/lang/String;Ljavax/naming/directory/Attributes;)Ljavax/naming/NamingEnumeration;",
                        "sink-LdapInjection",
                    ),
                    CodeLocation(
                        "javax/naming/directory/InitialDirContext",
                        "search",
                        "(Ljava/lang/String;Ljavax/naming/directory/Attributes;[Ljava/lang/String;)Ljavax/naming/NamingEnumeration;",
                        "sink-LdapInjection",
                    ),
                    CodeLocation(
                        "javax/naming/directory/InitialDirContext",
                        "search",
                        "(Ljava/lang/String;Ljava/lang/String;Ljavax/naming/directory/SearchControls;)Ljavax/naming/NamingEnumeration;",
                        "sink-LdapInjection",
                    ),
                    CodeLocation(
                        "javax/naming/directory/InitialDirContext",
                        "search",
                        "(Ljavax/naming/Name;Ljava/lang/String;[Ljava/lang/Object;Ljavax/naming/directory/SearchControls;)Ljavax/naming/NamingEnumeration;",
                        "sink-LdapInjection",
                    ),
                    CodeLocation(
                        "javax/naming/directory/InitialDirContext",
                        "search",
                        "(Ljava/lang/String;Ljava/lang/String;[Ljava/lang/Object;Ljavax/naming/directory/SearchControls;)Ljavax/naming/NamingEnumeration;",
                        "sink-LdapInjection",
                    ),
                    // crs/fuzzers/atl-jazzer/sanitizers/src/main/java/com/code_intelligence/jazzer/sanitizers/ExpressionLanguageInjection.kt
                    // From lines 43-63, calleeMethodDesc is not present in the source code
                    // Using null descriptors to match all overloads, just like in the original sanitizer
                    CodeLocation(
                        "javax/el/ExpressionFactory",
                        "createValueExpression",
                        null,
                        "sink-ExpressionLanguageInjection",
                    ),
                    CodeLocation(
                        "javax/el/ExpressionFactory",
                        "createMethodExpression",
                        null,
                        "sink-ExpressionLanguageInjection",
                    ),
                    CodeLocation(
                        "jakarta/el/ExpressionFactory",
                        "createValueExpression",
                        null,
                        "sink-ExpressionLanguageInjection",
                    ),
                    CodeLocation(
                        "jakarta/el/ExpressionFactory",
                        "createMethodExpression",
                        null,
                        "sink-ExpressionLanguageInjection",
                    ),
                    // From lines 87-91, calleeMethodDesc is not present in the source code
                    CodeLocation(
                        "javax/validation/ConstraintValidatorContext",
                        "buildConstraintViolationWithTemplate",
                        null,
                        "sink-ExpressionLanguageInjection",
                    ),
                    // crs/fuzzers/atl-jazzer/sanitizers/src/main/java/com/code_intelligence/jazzer/sanitizers/Deserialization.kt
                    // From lines 83-89 - ObjectInputStream constructor hook
                    CodeLocation(
                        "java/io/ObjectInputStream",
                        "<init>",
                        "(Ljava/io/InputStream;)V",
                        "sink-UnsafeDeserialization",
                    ),
                    // From lines 110-116 - ObjectInputStream init after hook
                    // No need to add this as it's the same method signature as above
                    // From lines 134-149, calleeMethodDesc is not present in the source code
                    // Using null descriptors to match all overloads, just like in the original sanitizer
                    CodeLocation(
                        "java/io/ObjectInputStream",
                        "readObject",
                        null,
                        "sink-UnsafeDeserialization",
                    ),
                    CodeLocation(
                        "java/io/ObjectInputStream",
                        "readObjectOverride",
                        null,
                        "sink-UnsafeDeserialization",
                    ),
                    CodeLocation(
                        "java/io/ObjectInputStream",
                        "readUnshared",
                        null,
                        "sink-UnsafeDeserialization",
                    ),
                    // crs/fuzzers/atl-jazzer/sanitizers/src/main/java/com/code_intelligence/jazzer/sanitizers/XPathInjection.kt
                    // From lines 45-48, calleeMethodDesc is not present in the source code
                    // Using null descriptors to match all overloads, just like in the original sanitizer
                    CodeLocation(
                        "javax/xml/xpath/XPath",
                        "compile",
                        null,
                        "sink-XPathInjection",
                    ),
                    CodeLocation(
                        "javax/xml/xpath/XPath",
                        "evaluate",
                        null,
                        "sink-XPathInjection",
                    ),
                    CodeLocation(
                        "javax/xml/xpath/XPath",
                        "evaluateExpression",
                        null,
                        "sink-XPathInjection",
                    ),
                    // crs/fuzzers/atl-jazzer/sanitizers/src/main/java/com/code_intelligence/jazzer/sanitizers/RegexInjection.kt
                    // From lines 47-52
                    CodeLocation(
                        "java/util/regex/Pattern",
                        "compile",
                        "(Ljava/lang/String;I)Ljava/util/regex/Pattern;",
                        "sink-RegexInjection",
                    ),
                    // From lines 65-77
                    CodeLocation(
                        "java/util/regex/Pattern",
                        "compile",
                        "(Ljava/lang/String;)Ljava/util/regex/Pattern;",
                        "sink-RegexInjection",
                    ),
                    CodeLocation(
                        "java/util/regex/Pattern",
                        "matches",
                        "(Ljava/lang/String;Ljava/lang/CharSequence;)Z",
                        "sink-RegexInjection",
                    ),
                    // From lines 87-117
                    CodeLocation(
                        "java/lang/String",
                        "matches",
                        "(Ljava/lang/String;)Z",
                        "sink-RegexInjection",
                    ),
                    CodeLocation(
                        "java/lang/String",
                        "replaceAll",
                        "(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;",
                        "sink-RegexInjection",
                    ),
                    CodeLocation(
                        "java/lang/String",
                        "replaceFirst",
                        "(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;",
                        "sink-RegexInjection",
                    ),
                    CodeLocation(
                        "java/lang/String",
                        "split",
                        "(Ljava/lang/String;)[Ljava/lang/String;",
                        "sink-RegexInjection",
                    ),
                    CodeLocation(
                        "java/lang/String",
                        "split",
                        "(Ljava/lang/String;I)[Ljava/lang/String;",
                        "sink-RegexInjection",
                    ),
                    // crs/fuzzers/atl-jazzer/sanitizers/src/main/java/com/code_intelligence/jazzer/sanitizers/SqlInjection.java
                    // From lines 73-99
                    CodeLocation(
                        "java/sql/Statement",
                        "execute",
                        null,
                        "sink-SqlInjection",
                    ),
                    CodeLocation(
                        "java/sql/Statement",
                        "executeBatch",
                        null,
                        "sink-SqlInjection",
                    ),
                    CodeLocation(
                        "java/sql/Statement",
                        "executeLargeBatch",
                        null,
                        "sink-SqlInjection",
                    ),
                    CodeLocation(
                        "java/sql/Statement",
                        "executeLargeUpdate",
                        null,
                        "sink-SqlInjection",
                    ),
                    CodeLocation(
                        "java/sql/Statement",
                        "executeQuery",
                        null,
                        "sink-SqlInjection",
                    ),
                    CodeLocation(
                        "java/sql/Statement",
                        "executeUpdate",
                        null,
                        "sink-SqlInjection",
                    ),
                    CodeLocation(
                        "javax/persistence/EntityManager",
                        "createNativeQuery",
                        null,
                        "sink-SqlInjection",
                    ),
                    // crs/fuzzers/atl-jazzer/sanitizers/src/main/java/com/code_intelligence/jazzer/sanitizers/ServerSideRequestForgery.java
                    // From lines 61-72 and 86-89 (additionalClassesToHook)
                    CodeLocation(
                        "java/net/SocketImpl",
                        "connect",
                        null,
                        "sink-ServerSideRequestForgery",
                    ),
                    CodeLocation(
                        "java/net/Socket",
                        "connect",
                        null,
                        "sink-ServerSideRequestForgery",
                    ),
                    CodeLocation(
                        "java/net/SocksSocketImpl",
                        "connect",
                        null,
                        "sink-ServerSideRequestForgery",
                    ),
                    CodeLocation(
                        "java/nio/channels/SocketChannel",
                        "connect",
                        null,
                        "sink-ServerSideRequestForgery",
                    ),
                    CodeLocation(
                        "sun/nio/ch/SocketAdaptor",
                        "connect",
                        null,
                        "sink-ServerSideRequestForgery",
                    ),
                    CodeLocation(
                        "jdk/internal/net/http/PlainHttpConnection",
                        "connect",
                        null,
                        "sink-ServerSideRequestForgery",
                    ),
                    // crs/fuzzers/atl-jazzer/sanitizers/src/main/java/com/code_intelligence/jazzer/sanitizers/FilePathTraversal.java
                    // From lines 84-171 - java.nio.file.Files methods
                    CodeLocation(
                        "java/nio/file/Files",
                        "createDirectory",
                        null,
                        "sink-FilePathTraversal",
                    ),
                    CodeLocation(
                        "java/nio/file/Files",
                        "createDirectories",
                        null,
                        "sink-FilePathTraversal",
                    ),
                    CodeLocation(
                        "java/nio/file/Files",
                        "createFile",
                        null,
                        "sink-FilePathTraversal",
                    ),
                    CodeLocation(
                        "java/nio/file/Files",
                        "createTempDirectory",
                        null,
                        "sink-FilePathTraversal",
                    ),
                    CodeLocation(
                        "java/nio/file/Files",
                        "createTempFile",
                        null,
                        "sink-FilePathTraversal",
                    ),
                    CodeLocation(
                        "java/nio/file/Files",
                        "delete",
                        null,
                        "sink-FilePathTraversal",
                    ),
                    CodeLocation(
                        "java/nio/file/Files",
                        "deleteIfExists",
                        null,
                        "sink-FilePathTraversal",
                    ),
                    CodeLocation(
                        "java/nio/file/Files",
                        "lines",
                        null,
                        "sink-FilePathTraversal",
                    ),
                    CodeLocation(
                        "java/nio/file/Files",
                        "newByteChannel",
                        null,
                        "sink-FilePathTraversal",
                    ),
                    CodeLocation(
                        "java/nio/file/Files",
                        "newBufferedReader",
                        null,
                        "sink-FilePathTraversal",
                    ),
                    CodeLocation(
                        "java/nio/file/Files",
                        "newBufferedWriter",
                        null,
                        "sink-FilePathTraversal",
                    ),
                    CodeLocation(
                        "java/nio/file/Files",
                        "readString",
                        null,
                        "sink-FilePathTraversal",
                    ),
                    CodeLocation(
                        "java/nio/file/Files",
                        "readAllBytes",
                        null,
                        "sink-FilePathTraversal",
                    ),
                    CodeLocation(
                        "java/nio/file/Files",
                        "readAllLines",
                        null,
                        "sink-FilePathTraversal",
                    ),
                    CodeLocation(
                        "java/nio/file/Files",
                        "readSymbolicLink",
                        null,
                        "sink-FilePathTraversal",
                    ),
                    CodeLocation(
                        "java/nio/file/Files",
                        "write",
                        null,
                        "sink-FilePathTraversal",
                    ),
                    CodeLocation(
                        "java/nio/file/Files",
                        "writeString",
                        null,
                        "sink-FilePathTraversal",
                    ),
                    CodeLocation(
                        "java/nio/file/Files",
                        "newInputStream",
                        null,
                        "sink-FilePathTraversal",
                    ),
                    CodeLocation(
                        "java/nio/file/Files",
                        "newOutputStream",
                        null,
                        "sink-FilePathTraversal",
                    ),
                    CodeLocation(
                        "java/nio/file/probeContentType",
                        "open",
                        null,
                        "sink-FilePathTraversal",
                    ),
                    CodeLocation(
                        "java/nio/channels/FileChannel",
                        "open",
                        null,
                        "sink-FilePathTraversal",
                    ),
                    // From lines 190-202 - copy/move operations
                    CodeLocation(
                        "java/nio/file/Files",
                        "copy",
                        null,
                        "sink-FilePathTraversal",
                    ),
                    CodeLocation(
                        "java/nio/file/Files",
                        "mismatch",
                        null,
                        "sink-FilePathTraversal",
                    ),
                    CodeLocation(
                        "java/nio/file/Files",
                        "move",
                        null,
                        "sink-FilePathTraversal",
                    ),
                    // From lines 216-280 - File I/O constructors
                    CodeLocation(
                        "java/io/FileReader",
                        "<init>",
                        null,
                        "sink-FilePathTraversal",
                    ),
                    CodeLocation(
                        "java/io/FileWriter",
                        "<init>",
                        null,
                        "sink-FilePathTraversal",
                    ),
                    CodeLocation(
                        "java/io/FileInputStream",
                        "<init>",
                        null,
                        "sink-FilePathTraversal",
                    ),
                    CodeLocation(
                        "java/io/FileOutputStream",
                        "<init>",
                        null,
                        "sink-FilePathTraversal",
                    ),
                    CodeLocation(
                        "java/util/Scanner",
                        "<init>",
                        null,
                        "sink-FilePathTraversal",
                    ),
                )

            // Empty set for coordinate sinkpoints (these only come from config files)
            val emptyCoordSinkpoints = emptySet<InsnCoordinate>()

            // Check for config file path and load additional sinkpoints if present
            val configFilePath = sinkConfigFile
            if (configFilePath != null) {
                Log.info("Loading additional sink points from: $configFilePath")
                val (apiSinkpoints, coordSinkpoints) = loadConfigFromFile(configFilePath)
                // Check if FUZZ_SSMODE is enabled
                val ssmodeEnabled = System.getenv("FUZZ_SSMODE") == "on"
                return if (ssmodeEnabled) {
                    Pair(apiSinkpoints, coordSinkpoints)
                } else {
                    Pair(hardcodedSinkpoints + apiSinkpoints, coordSinkpoints)
                }
            } else {
                // Check if FUZZ_SSMODE is enabled
                val ssmodeEnabled = System.getenv("FUZZ_SSMODE") == "on"
                return if (ssmodeEnabled) {
                    Pair(emptySet(), emptyCoordSinkpoints)
                } else {
                    Pair(hardcodedSinkpoints, emptyCoordSinkpoints)
                }
            }
        }

        /**
         * Test-only method to force re-initialization of all sinkpoints
         */
        @JvmStatic
        fun reinitializeSinkpointsForTesting() {
            sinkpointCallees = null
            sinkpointCoords = null
            sinkpointCoordsMap = null
            Log.info("All sinkpoints will be reinitialized on next access")
        }
    }
}
