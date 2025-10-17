# Intro

## Build

```bash
mvn clean compile assembly:single
```

## Usage

```bash
# Usage: java BytecodeInspector <output.json> [pkg-prefix-1 pkg-prefix-2 ...] -- <jar-or-class-file-1> [jar-or-class-file-2 ...]
java -cp target/bytecode-parser-1.0-SNAPSHOT-jar-with-dependencies.jar \
         BytecodeInspector \
	 output.json '<default>' \
	 -- target/bytecode-parser-1.0-SNAPSHOT-jar-with-dependencies.jar
```

## Output

```json
{
  "BytecodeInspector" : {
    "128" : [ {
      "jarFile" : "target/bytecode-parser-1.0-SNAPSHOT-jar-with-dependencies.jar",
      "classFilePath" : "BytecodeInspector.class",
      "className" : "BytecodeInspector",
      "sourceFileName" : "BytecodeInspector.java",
      "methodName" : "processClassFile",
      "methodDesc" : "(Ljava/nio/file/Path;)V",
      "bytecodeOffset" : 39,
      "lineNumber" : 128
    } ],
    "131" : [ {
      "jarFile" : "target/bytecode-parser-1.0-SNAPSHOT-jar-with-dependencies.jar",
      "classFilePath" : "BytecodeInspector.class",
      "className" : "BytecodeInspector",
      "sourceFileName" : "BytecodeInspector.java",
      "methodName" : "processClass",
      "methodDesc" : "(Ljava/io/InputStream;Ljava/lang/String;Ljava/lang/String;)V",
      "bytecodeOffset" : 0,
      "lineNumber" : 131
    } ],
    ...
  },
  ...
}
```
