# JaCoCo Examples

This directory contains examples demonstrating how to use the JaCoCo Java code coverage library. These examples show how to analyze JaCoCo execution data files (`.exec`) and generate detailed coverage reports.

## Overview

JaCoCo is a free code coverage library for Java that provides detailed information about which parts of your code are executed during tests. This directory includes both original JaCoCo examples and custom coverage dumpers for advanced analysis.

## Files

### Original JaCoCo Examples
- `ClassInfo.java` - Analyzes class files and displays coverage information
- `CoreTutorial.java` - Demonstrates JaCoCo core API usage with in-memory instrumentation
- `ExecDump.java` - Basic execution data dumper showing class-level coverage
- `ExecutionDataClient.java` - TCP client for collecting execution data
- `ExecutionDataServer.java` - TCP server for execution data collection
- `MBeanClient.java` - JMX client for execution data collection
- `ReportGenerator.java` - Generates HTML coverage reports

### Custom Coverage Dumpers
- **`DetailedExecDumper.java`** - Detailed text-based coverage dumper with line-level information
- **`JsonExecDumper.java`** - JSON-based coverage dumper for programmatic analysis

## Prerequisites

- Java 8 or higher
- JaCoCo JAR files (included in `lib/` directory)

## Compilation

All examples can be compiled using the following command:

```bash
javac -cp "lib/*" -d . *.java
```

This will:
- Include all JaCoCo JAR files from the `lib` directory in the classpath
- Compile all Java files with proper package structure
- Place compiled classes in the correct `org/jacoco/examples/` directory structure

## Usage

### DetailedExecDumper

The `DetailedExecDumper` provides comprehensive text-based coverage analysis with line-by-line details.

**Command:**
```bash
java -cp ".:lib/*" org.jacoco.examples.DetailedExecDumper <exec_file> <class_file_or_directory> [<class_file_or_directory> ...]
```

**Parameters:**
- `<exec_file>` - Path to JaCoCo execution data file (.exec)
- `<class_file_or_directory>` - Path to compiled class files or directories containing them

**Examples:**
```bash
# Analyze coverage with single class directory
java -cp ".:lib/*" org.jacoco.examples.DetailedExecDumper coverage.exec target/classes

# Analyze coverage with multiple class paths
java -cp ".:lib/*" org.jacoco.examples.DetailedExecDumper jacoco.exec build/classes/java/main lib/external.jar
```

**Sample Output:**
```
=== JaCoCo Detailed Coverage Report ===
Execution file: coverage.exec
Generated: Wed Jul 25 12:34:56 UTC 2025

FORMAT: FQN | FileName | LineNumber | CoverageStatus
================================================================================

--- Class: com.example.Calculator ---
Source file: Calculator.java
Instructions: 45/60 covered
Branches: 8/12 covered
Lines: 15/20 covered

com.example.Calculator | Calculator.java | 10 | FULLY_COVERED
com.example.Calculator | Calculator.java | 11 | FULLY_COVERED
com.example.Calculator | Calculator.java | 15 | PARTLY_COVERED
com.example.Calculator | Calculator.java | 16 | NOT_COVERED
com.example.Calculator | Calculator.java | 20 | FULLY_COVERED

=== Summary ===
Total classes analyzed: 5
```

### JsonExecDumper

The `JsonExecDumper` generates structured JSON output suitable for programmatic analysis and integration with other tools.

**Command:**
```bash
java -cp ".:lib/*" org.jacoco.examples.JsonExecDumper <exec_file> <output_json_file> <class_file_or_directory> [<class_file_or_directory> ...]
```

**Parameters:**
- `<exec_file>` - Path to JaCoCo execution data file (.exec)
- `<output_json_file>` - Path where JSON report will be saved
- `<class_file_or_directory>` - Path to compiled class files or directories containing them

**Examples:**
```bash
# Generate JSON report
java -cp ".:lib/*" org.jacoco.examples.JsonExecDumper coverage.exec report.json target/classes

# Generate JSON report with multiple class paths
java -cp ".:lib/*" org.jacoco.examples.JsonExecDumper jacoco.exec coverage-report.json build/classes/java/main lib/external.jar
```

**Sample JSON Output:**
```json
{
  "metadata": {
    "execFile": "coverage.exec",
    "generatedAt": "Wed Jul 25 12:34:56 UTC 2025",
    "totalClasses": 5
  },
  "summary": {
    "instructions": { "total": 1250, "covered": 890, "missed": 360 },
    "branches": { "total": 180, "covered": 125, "missed": 55 },
    "lines": { "total": 320, "covered": 240, "missed": 80 },
    "methods": { "total": 45, "covered": 38, "missed": 7 }
  },
  "classes": [
    {
      "fqn": "com.example.Calculator",
      "fileName": "Calculator.java",
      "classId": "0123456789abcdef",
      "counters": {
        "instructions": { "total": 60, "covered": 45, "missed": 15 },
        "branches": { "total": 12, "covered": 8, "missed": 4 },
        "lines": { "total": 20, "covered": 15, "missed": 5 },
        "methods": { "total": 4, "covered": 3, "missed": 1 }
      },
      "lineCoverage": [
        {
          "line": 10,
          "status": "FULLY_COVERED",
          "instructions": { "total": 2, "covered": 2 },
          "branches": { "total": 0, "covered": 0 }
        },
        {
          "line": 15,
          "status": "PARTLY_COVERED",
          "instructions": { "total": 4, "covered": 2 },
          "branches": { "total": 2, "covered": 1 }
        },
        {
          "line": 16,
          "status": "NOT_COVERED",
          "instructions": { "total": 3, "covered": 0 },
          "branches": { "total": 1, "covered": 0 }
        }
      ]
    }
  ]
}
```

## JSON Data Structure

The JSON output from `JsonExecDumper` follows this structure:

### Root Object
- **`metadata`** - Report generation information
  - `execFile` - Path to the analyzed .exec file
  - `generatedAt` - Timestamp when report was generated
  - `totalClasses` - Number of classes analyzed
  
- **`summary`** - Overall project coverage statistics
  - Each metric has `total`, `covered`, and `missed` counts
  - Metrics: `instructions`, `branches`, `lines`, `methods`
  
- **`classes`** - Array of per-class coverage details

### Class Object
- **`fqn`** - Fully qualified class name (e.g., "com.example.MyClass")
- **`fileName`** - Source file name (e.g., "MyClass.java")
- **`classId`** - Unique identifier for the class (hexadecimal)
- **`counters`** - Class-level coverage statistics
- **`lineCoverage`** - Array of line-level coverage details

### Line Coverage Object
- **`line`** - Line number in source file
- **`status`** - Coverage status: `"FULLY_COVERED"`, `"PARTLY_COVERED"`, or `"NOT_COVERED"`
- **`instructions`** - Instruction-level coverage for this line
- **`branches`** - Branch coverage for this line (if applicable)

## Coverage Status Definitions

- **`FULLY_COVERED`** - All instructions on the line were executed
- **`PARTLY_COVERED`** - Some but not all instructions on the line were executed
- **`NOT_COVERED`** - No instructions on the line were executed

## Troubleshooting

### ClassNotFoundException or NoClassDefFoundError
If you encounter these errors, ensure:
1. All required JAR files are in the `lib/` directory
2. You're using the correct classpath: `-cp ".:lib/*"`
3. Classes are compiled with proper package structure
4. You're running from the correct directory

### Missing ASM Dependencies
If you see `NoClassDefFoundError` for ASM classes, you may need to download additional dependencies:
```bash
wget https://repo1.maven.org/maven2/org/ow2/asm/asm/9.4/asm-9.4.jar -P lib/
```

### Empty Coverage Reports
If reports show no coverage data:
1. Verify the .exec file contains data (check file size > 0)
2. Ensure class files match the ones that were instrumented
3. Check that class paths point to the correct compiled classes

## Integration Examples

### Using JSON Output in Scripts

**Python example:**
```python
import json

with open('coverage-report.json', 'r') as f:
    coverage = json.load(f)

# Get overall line coverage percentage
summary = coverage['summary']
line_coverage = (summary['lines']['covered'] / summary['lines']['total']) * 100
print(f"Overall line coverage: {line_coverage:.1f}%")

# Find classes with low coverage
for cls in coverage['classes']:
    cls_coverage = (cls['counters']['lines']['covered'] / cls['counters']['lines']['total']) * 100
    if cls_coverage < 80:
        print(f"Low coverage: {cls['fqn']} ({cls_coverage:.1f}%)")
```

**Shell script example:**
```bash
#!/bin/bash
# Generate coverage report and extract summary
java -cp ".:lib/*" org.jacoco.examples.JsonExecDumper jacoco.exec report.json target/classes

# Extract line coverage percentage using jq
LINE_COVERAGE=$(jq -r '.summary.lines | (.covered / .total * 100)' report.json)
echo "Line coverage: ${LINE_COVERAGE}%"
```

## License

These examples are based on JaCoCo examples and follow the Eclipse Public License 2.0.