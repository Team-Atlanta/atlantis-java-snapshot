from enum import IntFlag

class TaintRequirement(IntFlag):
    THIS_OBJECT = 1 << 0
    ARG1 = 1 << 1
    ARG2 = 1 << 2
    ARG3 = 1 << 3
    ARG4 = 1 << 4
    ARG5 = 1 << 5
    ARG6 = 1 << 6
    ARG7 = 1 << 7
    ARG8 = 1 << 8


class SinkCalleeAPI:

    def __init__(self, className, methodName, methodDesc, markDesc, taintRequirement):
        self.className = className
        self.methodName = methodName
        self.methodDesc = methodDesc
        self.markDesc = markDesc
        self.taintRequirement = taintRequirement

    def __repr__(self):
        return f"SinkCalleeAPI({self.className}, {self.methodName}, {self.methodDesc}, {self.markDesc})"

    def to_dict(self):
        return {
            "class_name": self.className,
            "method_name": self.methodName,
            "method_desc": self.methodDesc,
            "mark_desc": self.markDesc,
        }

    def to_cfg(self):
        """API-based sinkpoints (format: api#calleeClassName#methodName#methodDesc#markDesc)"""
        return f"api#{self.className}#{self.methodName}#{self.methodDesc if self.methodDesc else ""}#{self.markDesc}"


JazzerDefaultSinkCalleeAPIs = [
    # crs/fuzzers/atl-jazzer/sanitizers/src/main/java/com/code_intelligence/jazzer/sanitizers/ReflectiveCall.kt
    # From lines 33-45
    SinkCalleeAPI(
        "java/lang/Class",
        "forName",
        "(Ljava/lang/String;)Ljava/lang/Class;",
        "sink-UnsafeReflectiveCall",
        TaintRequirement.ARG1,
    ),
    SinkCalleeAPI(
        "java/lang/Class",
        "forName",
        "(Ljava/lang/String;ZLjava/lang/ClassLoader;)Ljava/lang/Class;",
        "sink-UnsafeReflectiveCall",
        TaintRequirement.ARG1,
    ),
    # From lines 46-57
    SinkCalleeAPI(
        "java/lang/ClassLoader",
        "loadClass",
        "(Ljava/lang/String;)Ljava/lang/Class;",
        "sink-UnsafeReflectiveCall",
        TaintRequirement.ARG1,
    ),
    SinkCalleeAPI(
        "java/lang/ClassLoader",
        "loadClass",
        "(Ljava/lang/String;Z)Ljava/lang/Class;",
        "sink-UnsafeReflectiveCall",
        TaintRequirement.ARG1,
    ),
    # From lines 70-82
    SinkCalleeAPI(
        "java/lang/Class",
        "forName",
        "(Ljava/lang/Module;Ljava/lang/String;)Ljava/lang/Class;",
        "sink-UnsafeReflectiveCall",
        TaintRequirement.ARG2,
    ),
    SinkCalleeAPI(
        "java/lang/ClassLoader",
        "loadClass",
        "(Ljava/lang/Module;Ljava/lang/String;)Ljava/lang/Class;",
        "sink-UnsafeReflectiveCall",
        TaintRequirement.ARG2,
    ),
    # From lines 95-102, methodDesc is not present in the source code
    # Using null descriptors to match all overloads, just like in the original sanitizer
    SinkCalleeAPI(
        "java/lang/Runtime",
        "load",
        None,
        "sink-LoadArbitraryLibrary",
        TaintRequirement.ARG1,
    ),
    SinkCalleeAPI(
        "java/lang/Runtime",
        "loadLibrary",
        None,
        "sink-LoadArbitraryLibrary",
        TaintRequirement.ARG1,
    ),
    SinkCalleeAPI(
        "java/lang/System",
        "load",
        None,
        "sink-LoadArbitraryLibrary",
        TaintRequirement.ARG1,
    ),
    SinkCalleeAPI(
        "java/lang/System",
        "loadLibrary",
        None,
        "sink-LoadArbitraryLibrary",
        TaintRequirement.ARG1,
    ),
    SinkCalleeAPI(
        "java/lang/System",
        "mapLibraryName",
        None,
        "sink-LoadArbitraryLibrary",
        TaintRequirement.ARG1,
    ),
    SinkCalleeAPI(
        "java/lang/ClassLoader",
        "findLibrary",
        None,
        "sink-LoadArbitraryLibrary",
        TaintRequirement.ARG1,
    ),
    # crs/fuzzers/atl-jazzer/sanitizers/src/main/java/com/code_intelligence/jazzer/sanitizers/OsCommandInjection.kt
    # From lines 39-44, methodDesc is not present in the source code
    # Also adding additionalClassesToHook entry for ProcessBuilder
    SinkCalleeAPI(
        "java/lang/ProcessImpl",
        "start",
        None,
        "sink-OsCommandInjection",
        TaintRequirement.ARG1,
    ),
    SinkCalleeAPI(
        "java/lang/ProcessBuilder",
        "start",
        None,
        "sink-OsCommandInjection",
        TaintRequirement.ARG1,
    ),
    # crs/fuzzers/atl-jazzer/sanitizers/src/main/java/com/code_intelligence/jazzer/sanitizers/NamingContextLookup.kt
    # From lines 37-49
    SinkCalleeAPI(
        "javax/naming/Context",
        "lookup",
        "(Ljava/lang/String;)Ljava/lang/Object;",
        "sink-RemoteJNDILookup",
        TaintRequirement.ARG1,
    ),
    SinkCalleeAPI(
        "javax/naming/Context",
        "lookupLink",
        "(Ljava/lang/String;)Ljava/lang/Object;",
        "sink-RemoteJNDILookup",
        TaintRequirement.ARG1,
    ),
    # crs/fuzzers/atl-jazzer/sanitizers/src/main/java/com/code_intelligence/jazzer/sanitizers/LdapInjection.kt
    # From lines 54-91
    # Fixing typos in descriptors from original sanitizer
    SinkCalleeAPI(
        "javax/naming/directory/DirContext",
        "search",
        "(Ljava/lang/String;Ljavax/naming/directory/Attributes;)Ljavax/naming/NamingEnumeration;",
        "sink-LdapInjection",
        TaintRequirement.ARG1 | TaintRequirement.ARG2,
    ),
    SinkCalleeAPI(
        "javax/naming/directory/DirContext",
        "search",
        "(Ljava/lang/String;Ljavax/naming/directory/Attributes;[Ljava/lang/String;)Ljavax/naming/NamingEnumeration;",
        "sink-LdapInjection",
        TaintRequirement.ARG1 | TaintRequirement.ARG2,
    ),
    SinkCalleeAPI(
        "javax/naming/directory/DirContext",
        "search",
        "(Ljava/lang/String;Ljava/lang/String;Ljavax/naming/directory/SearchControls;)Ljavax/naming/NamingEnumeration;",
        "sink-LdapInjection",
        TaintRequirement.ARG1 | TaintRequirement.ARG2,
    ),
    SinkCalleeAPI(
        "javax/naming/directory/DirContext",
        "search",
        "(Ljavax/naming/Name;Ljava/lang/String;[Ljava/lang/Object;Ljavax/naming/directory/SearchControls;)Ljavax/naming/NamingEnumeration;",
        "sink-LdapInjection",
        TaintRequirement.ARG1 | TaintRequirement.ARG2,
    ),
    SinkCalleeAPI(
        "javax/naming/directory/DirContext",
        "search",
        "(Ljava/lang/String;Ljava/lang/String;[Ljava/lang/Object;Ljavax/naming/directory/SearchControls;)Ljavax/naming/NamingEnumeration;",
        "sink-LdapInjection",
        TaintRequirement.ARG1 | TaintRequirement.ARG2,
    ),
    # Adding entries for InitialDirContext from additionalClassesToHook
    SinkCalleeAPI(
        "javax/naming/directory/InitialDirContext",
        "search",
        "(Ljava/lang/String;Ljavax/naming/directory/Attributes;)Ljavax/naming/NamingEnumeration;",
        "sink-LdapInjection",
        TaintRequirement.ARG1 | TaintRequirement.ARG2,
    ),
    SinkCalleeAPI(
        "javax/naming/directory/InitialDirContext",
        "search",
        "(Ljava/lang/String;Ljavax/naming/directory/Attributes;[Ljava/lang/String;)Ljavax/naming/NamingEnumeration;",
        "sink-LdapInjection",
        TaintRequirement.ARG1 | TaintRequirement.ARG2,
    ),
    SinkCalleeAPI(
        "javax/naming/directory/InitialDirContext",
        "search",
        "(Ljava/lang/String;Ljava/lang/String;Ljavax/naming/directory/SearchControls;)Ljavax/naming/NamingEnumeration;",
        "sink-LdapInjection",
        TaintRequirement.ARG1 | TaintRequirement.ARG2,
    ),
    SinkCalleeAPI(
        "javax/naming/directory/InitialDirContext",
        "search",
        "(Ljavax/naming/Name;Ljava/lang/String;[Ljava/lang/Object;Ljavax/naming/directory/SearchControls;)Ljavax/naming/NamingEnumeration;",
        "sink-LdapInjection",
        TaintRequirement.ARG1 | TaintRequirement.ARG2,
    ),
    SinkCalleeAPI(
        "javax/naming/directory/InitialDirContext",
        "search",
        "(Ljava/lang/String;Ljava/lang/String;[Ljava/lang/Object;Ljavax/naming/directory/SearchControls;)Ljavax/naming/NamingEnumeration;",
        "sink-LdapInjection",
        TaintRequirement.ARG1 | TaintRequirement.ARG2,
    ),
    # crs/fuzzers/atl-jazzer/sanitizers/src/main/java/com/code_intelligence/jazzer/sanitizers/ExpressionLanguageInjection.kt
    # From lines 43-63, methodDesc is not present in the source code
    # Using null descriptors to match all overloads, just like in the original sanitizer
    SinkCalleeAPI(
        "javax/el/ExpressionFactory",
        "createValueExpression",
        None,
        "sink-ExpressionLanguageInjection",
        TaintRequirement.ARG2,
    ),
    SinkCalleeAPI(
        "javax/el/ExpressionFactory",
        "createMethodExpression",
        None,
        "sink-ExpressionLanguageInjection",
        TaintRequirement.ARG2,
    ),
    SinkCalleeAPI(
        "jakarta/el/ExpressionFactory",
        "createValueExpression",
        None,
        "sink-ExpressionLanguageInjection",
        TaintRequirement.ARG2,
    ),
    SinkCalleeAPI(
        "jakarta/el/ExpressionFactory",
        "createMethodExpression",
        None,
        "sink-ExpressionLanguageInjection",
        TaintRequirement.ARG2,
    ),
    # From lines 87-91, methodDesc is not present in the source code
    SinkCalleeAPI(
        "javax/validation/ConstraintValidatorContext",
        "buildConstraintViolationWithTemplate",
        None,
        "sink-ExpressionLanguageInjection",
        TaintRequirement.ARG1,
    ),
    # crs/fuzzers/atl-jazzer/sanitizers/src/main/java/com/code_intelligence/jazzer/sanitizers/Deserialization.kt
    # From lines 83-89 - ObjectInputStream constructor hook
    SinkCalleeAPI(
        "java/io/ObjectInputStream",
        "<init>",
        "(Ljava/io/InputStream;)V",
        "sink-UnsafeDeserialization",
        TaintRequirement.ARG1,
    ),
    # From lines 110-116 - ObjectInputStream init after hook
    # No need to add this as it's the same method signature as above
    # From lines 134-149, methodDesc is not present in the source code
    # Using null descriptors to match all overloads, just like in the original sanitizer
    SinkCalleeAPI(
        "java/io/ObjectInputStream",
        "readObject",
        None,
        "sink-UnsafeDeserialization",
        TaintRequirement.THIS_OBJECT,
    ),
    SinkCalleeAPI(
        "java/io/ObjectInputStream",
        "readObjectOverride",
        None,
        "sink-UnsafeDeserialization",
        TaintRequirement.THIS_OBJECT,
    ),
    SinkCalleeAPI(
        "java/io/ObjectInputStream",
        "readUnshared",
        None,
        "sink-UnsafeDeserialization",
        TaintRequirement.THIS_OBJECT,
    ),
    # crs/fuzzers/atl-jazzer/sanitizers/src/main/java/com/code_intelligence/jazzer/sanitizers/XPathInjection.kt
    # From lines 45-48, methodDesc is not present in the source code
    # Using null descriptors to match all overloads, just like in the original sanitizer
    SinkCalleeAPI(
        "javax/xml/xpath/XPath",
        "compile",
        None,
        "sink-XPathInjection",
        TaintRequirement.ARG1,
    ),
    SinkCalleeAPI(
        "javax/xml/xpath/XPath",
        "evaluate",
        None,
        "sink-XPathInjection",
        TaintRequirement.ARG1,
    ),
    SinkCalleeAPI(
        "javax/xml/xpath/XPath",
        "evaluateExpression",
        None,
        "sink-XPathInjection",
        TaintRequirement.ARG1,
    ),
    # crs/fuzzers/atl-jazzer/sanitizers/src/main/java/com/code_intelligence/jazzer/sanitizers/RegexInjection.kt
    # From lines 47-52
    SinkCalleeAPI(
        "java/util/regex/Pattern",
        "compile",
        "(Ljava/lang/String;I)Ljava/util/regex/Pattern;",
        "sink-RegexInjection",
        TaintRequirement.ARG1 | TaintRequirement.ARG2,
    ),
    # From lines 65-77
    SinkCalleeAPI(
        "java/util/regex/Pattern",
        "compile",
        "(Ljava/lang/String;)Ljava/util/regex/Pattern;",
        "sink-RegexInjection",
        TaintRequirement.ARG1,
    ),
    SinkCalleeAPI(
        "java/util/regex/Pattern",
        "matches",
        "(Ljava/lang/String;Ljava/lang/CharSequence;)Z",
        "sink-RegexInjection",
        TaintRequirement.ARG1,
    ),
    # From lines 87-117
    SinkCalleeAPI(
        "java/lang/String",
        "matches",
        "(Ljava/lang/String;)Z",
        "sink-RegexInjection",
        TaintRequirement.ARG1,
    ),
    SinkCalleeAPI(
        "java/lang/String",
        "replaceAll",
        "(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;",
        "sink-RegexInjection",
        TaintRequirement.ARG1,
    ),
    SinkCalleeAPI(
        "java/lang/String",
        "replaceFirst",
        "(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;",
        "sink-RegexInjection",
        TaintRequirement.ARG1,
    ),
    SinkCalleeAPI(
        "java/lang/String",
        "split",
        "(Ljava/lang/String;)[Ljava/lang/String;",
        "sink-RegexInjection",
        TaintRequirement.ARG1,
    ),
    SinkCalleeAPI(
        "java/lang/String",
        "split",
        "(Ljava/lang/String;I)[Ljava/lang/String;",
        "sink-RegexInjection",
        TaintRequirement.ARG1,
    ),
    # crs/fuzzers/atl-jazzer/sanitizers/src/main/java/com/code_intelligence/jazzer/sanitizers/SqlInjection.java
    # From lines 73-99
    SinkCalleeAPI(
        "java/sql/Statement",
        "execute",
        None,
        "sink-SqlInjection",
        TaintRequirement.ARG1,
    ),
    SinkCalleeAPI(
        "java/sql/Statement",
        "executeBatch",
        None,
        "sink-SqlInjection",
        TaintRequirement.ARG1,
    ),
    SinkCalleeAPI(
        "java/sql/Statement",
        "executeLargeBatch",
        None,
        "sink-SqlInjection",
        TaintRequirement.ARG1,
    ),
    SinkCalleeAPI(
        "java/sql/Statement",
        "executeLargeUpdate",
        None,
        "sink-SqlInjection",
        TaintRequirement.ARG1,
    ),
    SinkCalleeAPI(
        "java/sql/Statement",
        "executeQuery",
        None,
        "sink-SqlInjection",
        TaintRequirement.ARG1,
    ),
    SinkCalleeAPI(
        "java/sql/Statement",
        "executeUpdate",
        None,
        "sink-SqlInjection",
        TaintRequirement.ARG1,
    ),
    SinkCalleeAPI(
        "javax/persistence/EntityManager",
        "createNativeQuery",
        None,
        "sink-SqlInjection",
        TaintRequirement.ARG1,
    ),
    # crs/fuzzers/atl-jazzer/sanitizers/src/main/java/com/code_intelligence/jazzer/sanitizers/ServerSideRequestForgery.java
    # From lines 61-72 and 86-89 (additionalClassesToHook)
    SinkCalleeAPI(
        "java/net/SocketImpl",
        "connect",
        None,
        "sink-ServerSideRequestForgery",
        TaintRequirement.ARG1 | TaintRequirement.ARG2,
    ),
    SinkCalleeAPI(
        "java/net/Socket",
        "connect",
        None,
        "sink-ServerSideRequestForgery",
        TaintRequirement.ARG1 | TaintRequirement.ARG2,
    ),
    SinkCalleeAPI(
        "java/net/SocksSocketImpl",
        "connect",
        None,
        "sink-ServerSideRequestForgery",
        TaintRequirement.ARG1 | TaintRequirement.ARG2,
    ),
    SinkCalleeAPI(
        "java/nio/channels/SocketChannel",
        "connect",
        None,
        "sink-ServerSideRequestForgery",
        TaintRequirement.ARG1 | TaintRequirement.ARG2,
    ),
    SinkCalleeAPI(
        "sun/nio/ch/SocketAdaptor",
        "connect",
        None,
        "sink-ServerSideRequestForgery",
        TaintRequirement.ARG1 | TaintRequirement.ARG2,
    ),
    SinkCalleeAPI(
        "jdk/internal/net/http/PlainHttpConnection",
        "connect",
        None,
        "sink-ServerSideRequestForgery",
        TaintRequirement.ARG1 | TaintRequirement.ARG2,
    ),
    # crs/fuzzers/atl-jazzer/sanitizers/src/main/java/com/code_intelligence/jazzer/sanitizers/FilePathTraversal.java
    # From lines 84-171 - java.nio.file.Files methods
    SinkCalleeAPI(
        "java/nio/file/Files",
        "createDirectory",
        None,
        "sink-FilePathTraversal",
        TaintRequirement.ARG1,
    ),
    SinkCalleeAPI(
        "java/nio/file/Files",
        "createDirectories",
        None,
        "sink-FilePathTraversal",
        TaintRequirement.ARG1,
    ),
    SinkCalleeAPI(
        "java/nio/file/Files",
        "createFile",
        None,
        "sink-FilePathTraversal",
        TaintRequirement.ARG1,
    ),
    SinkCalleeAPI(
        "java/nio/file/Files",
        "createTempDirectory",
        None,
        "sink-FilePathTraversal",
        TaintRequirement.ARG1,
    ),
    SinkCalleeAPI(
        "java/nio/file/Files",
        "createTempFile",
        None,
        "sink-FilePathTraversal",
        TaintRequirement.ARG1,
    ),
    SinkCalleeAPI(
        "java/nio/file/Files",
        "delete",
        None,
        "sink-FilePathTraversal",
        TaintRequirement.ARG1,
    ),
    SinkCalleeAPI(
        "java/nio/file/Files",
        "deleteIfExists",
        None,
        "sink-FilePathTraversal",
        TaintRequirement.ARG1,
    ),
    SinkCalleeAPI(
        "java/nio/file/Files",
        "lines",
        None,
        "sink-FilePathTraversal",
        TaintRequirement.ARG1,
    ),
    SinkCalleeAPI(
        "java/nio/file/Files",
        "newByteChannel",
        None,
        "sink-FilePathTraversal",
        TaintRequirement.ARG1,
    ),
    SinkCalleeAPI(
        "java/nio/file/Files",
        "newBufferedReader",
        None,
        "sink-FilePathTraversal",
        TaintRequirement.ARG1,
    ),
    SinkCalleeAPI(
        "java/nio/file/Files",
        "newBufferedWriter",
        None,
        "sink-FilePathTraversal",
        TaintRequirement.ARG1,
    ),
    SinkCalleeAPI(
        "java/nio/file/Files",
        "readString",
        None,
        "sink-FilePathTraversal",
        TaintRequirement.ARG1,
    ),
    SinkCalleeAPI(
        "java/nio/file/Files",
        "readAllBytes",
        None,
        "sink-FilePathTraversal",
        TaintRequirement.ARG1,
    ),
    SinkCalleeAPI(
        "java/nio/file/Files",
        "readAllLines",
        None,
        "sink-FilePathTraversal",
        TaintRequirement.ARG1,
    ),
    SinkCalleeAPI(
        "java/nio/file/Files",
        "readSymbolicLink",
        None,
        "sink-FilePathTraversal",
        TaintRequirement.ARG1,
    ),
    SinkCalleeAPI(
        "java/nio/file/Files",
        "write",
        None,
        "sink-FilePathTraversal",
        TaintRequirement.ARG1,
    ),
    SinkCalleeAPI(
        "java/nio/file/Files",
        "writeString",
        None,
        "sink-FilePathTraversal",
        TaintRequirement.ARG1,
    ),
    SinkCalleeAPI(
        "java/nio/file/Files",
        "newInputStream",
        None,
        "sink-FilePathTraversal",
        TaintRequirement.ARG1,
    ),
    SinkCalleeAPI(
        "java/nio/file/Files",
        "newOutputStream",
        None,
        "sink-FilePathTraversal",
        TaintRequirement.ARG1,
    ),
    SinkCalleeAPI(
        "java/nio/file/probeContentType",
        "open",
        None,
        "sink-FilePathTraversal",
        TaintRequirement.ARG1,
    ),
    SinkCalleeAPI(
        "java/nio/channels/FileChannel",
        "open",
        None,
        "sink-FilePathTraversal",
        TaintRequirement.ARG1,
    ),
    # From lines 190-202 - copy/move operations
    SinkCalleeAPI(
        "java/nio/file/Files",
        "copy",
        None,
        "sink-FilePathTraversal",
        TaintRequirement.ARG1 | TaintRequirement.ARG2,
    ),
    SinkCalleeAPI(
        "java/nio/file/Files",
        "mismatch",
        None,
        "sink-FilePathTraversal",
        TaintRequirement.ARG1 | TaintRequirement.ARG2,
    ),
    SinkCalleeAPI(
        "java/nio/file/Files",
        "move",
        None,
        "sink-FilePathTraversal",
        TaintRequirement.ARG1 | TaintRequirement.ARG2,
    ),
    # From lines 216-280 - File I/O constructors
    SinkCalleeAPI(
        "java/io/FileReader",
        "<init>",
        None,
        "sink-FilePathTraversal",
        TaintRequirement.ARG1,
    ),
    SinkCalleeAPI(
        "java/io/FileWriter",
        "<init>",
        None,
        "sink-FilePathTraversal",
        TaintRequirement.ARG1,
    ),
    SinkCalleeAPI(
        "java/io/FileInputStream",
        "<init>",
        None,
        "sink-FilePathTraversal",
        TaintRequirement.ARG1,
    ),
    SinkCalleeAPI(
        "java/io/FileOutputStream",
        "<init>",
        None,
        "sink-FilePathTraversal",
        TaintRequirement.ARG1,
    ),
    SinkCalleeAPI(
        "java/util/Scanner",
        "<init>",
        None,
        "sink-FilePathTraversal",
        TaintRequirement.ARG1,
    ),
]

print(
    """########
# Generated by crs/assets/sink-callee-apis/gen.py
# API-based sinkpoints (format: api#calleeClassName#methodName#methodDesc#markDesc)
# Coordinate-based sinkpoints (format: caller#className#methodName#methodDesc#fileName#lineNumber#bytecodeOffset#markDesc)
########
"""
)
for api in JazzerDefaultSinkCalleeAPIs:
    print(api.to_cfg())
