# Fuzzer Stuck Point Analyzer

A tool that identifies fuzzing stuck points by analyzing JaCoCo coverage data and calculating reachability scores using SootUp static analysis. It finds lines with partial coverage where fuzzers get blocked and prioritizes them for analysis.

## Prerequisites

- Java 11 or higher
- Maven 3.6 or higher
- JaCoCo execution data (`.exec` files)
- Compiled class files or JAR files to analyze

## Build

```bash
cd stuck-point-analyzer
mvn clean compile package
```

This creates a shaded JAR with all dependencies: `target/stuck-point-analyzer-1.0.0.jar`

## Usage

```bash
java -jar stuck-point-analyzer-1.0.0.jar \
  -e coverage.exec \
  -j app.jar \
  -j lib.jar \
  --entrypoint com.example.FuzzTarget.fuzz \
  --metadata metadata.json \
  --source-dir /project/src \
  --annotated-output-dir /tmp/annotated-src \
  -o results.json
```

### Real-World Example

```bash
java -jar target/stuck-point-analyzer-1.0.0.jar \
  -e /app/crs-cp-java/deepgen/jvm/stuck-point-analyzer/test/imaging/jacoco.exec \
  -j /cp_root/build/out/aixcc/jvm/imaging/jars/one/commons-imaging-1.0.0-alpha6-aixcc.jar \
  -j /cp_root/build/out/aixcc/jvm/imaging/jars/one/imaging-harness-one.jar \
  --entrypoint com.aixcc.imaging.harnesses.one.fuzzerTestOneInput \
  -o test-results.json \
  -v \
  -m /crs-workdir/worker-0/metadata/aixcc/jvm/imaging/cpmeta.json \
  --source-dir /src-imaging \
  --annotated-output-dir /tmp/src-imaging
```

This example analyzes the Apache Commons Imaging library with:
- **Input**: JaCoCo execution data from fuzzing runs
- **Target**: Commons Imaging JAR and test harness
- **Entry Point**: Fuzzer entry method
- **Metadata**: CP metadata file containing source file mappings
- **Source Directory**: Original source code directory for reading actual code
- **Annotated Output**: Creates annotated source code copy with coverage annotations
- **Output**: Comprehensive analysis with stuck points, scores, and detailed summaries including source code context

### Command Line Options

| Option | Description | Required |
|--------|-------------|----------|
| `-e, --exec` | Path to JaCoCo execution data file (.exec) | Yes |
| `-j, --jars` | Paths to JAR files or class directories | Yes |
| `--entrypoint` | Entry point method signature | Yes |
| `-m, --metadata` | Path to CP metadata JSON file | Yes |
| `-s, --source-dir` | Original source directory root path | Yes |
| `-a, --annotated-output-dir` | Directory for annotated source code output | Yes |
| `-o, --output` | Output JSON file path (default: stuck-points.json) | No |
| `-v, --verbose` | Enable verbose output | No |
| `-h, --help` | Show help message | No |

The entry point should be specified as: `com.example.ClassName.methodName`

## Output Format

The tool generates a JSON report with the following structure:

```json
{
  "metadata": {
    "tool": "stuck-point-analyzer",
    "version": "1.0.0",
    "analysisTimestamp": "Wed Jul 25 12:34:56 UTC 2025",
    "execFile": "coverage.exec",
    "entryPoint": "com.example.Main.main",
    "jarFiles": ["target/classes"]
  },
  "summary": {
    "totalCoverageLines": 1250,
    "stuckPointsFound": 45,
    "analysisType": "jacoco-coverage + sootup-icfg",
    "highestScore": 100,
    "lowestScore": 5,
    "averageScore": 32.4
  },
  "stuckPoints": [
    {
      "classFqn": "com.example.Parser",
      "fileName": "Parser.java",
      "lineNumber": 123,
      "coverageStatus": "PARTLY_COVERED",
      "instructionCoverage": {
        "total": 8,
        "covered": 3,
        "missed": 5,
        "ratio": 0.375
      },
      "branchCoverage": {
        "total": 2,
        "covered": 1,
        "missed": 1,
        "ratio": 0.5
      },
      "stuckPointScore": 100,
      "analysisMetadata": {
        "analysisType": "sootup-icfg",
        "scoreCalculated": true,
        "notes": "Score calculation using SootUp ICFG analysis"
      },
      "summary": "## Basic Information\n\n- **File**: Parser.java\n- **Class**: com.example.Parser\n- **Line Number**: 123\n- **Stuck Point Score**: 100\n- **Coverage Status**: PARTLY_COVERED\n\n## Source Code Context\n\n### Source Code with Coverage\n\n*Source: /src/repo/src/main/java/com/example/Parser.java*\n\n```java\n    118: [✓]     public void parse() {\n    119: [✓]         if (input != null) {\n    120: [~]             switch (type) {\n>>> 123: [~]                 case TOKEN: processToken(); break;\n    124: [✗]                 case EOF: return;\n    125: [ ]             }\n    126: [✓]         }\n    127: [✓]     }\n```\n\n### Stuck Point Details\n\n- **Instructions**: 3 covered / 8 total (37.5%)\n- **Branches**: 1 covered / 2 total (50.0%)\n\n**Legend**: [✓] Fully Covered, [~] Partially Covered (Stuck Point), [✗] Not Covered, [ ] No Executable Instructions"
    }
  ]
}
```

### Output Fields

#### Metadata
- `tool`: Tool name and version
- `analysisTimestamp`: When analysis was performed
- `execFile`: Input JaCoCo execution file
- `entryPoint`: Analysis entry point method
- `jarFiles`: Analyzed JAR files/directories

#### Summary
- `totalCoverageLines`: Total lines with coverage data
- `stuckPointsFound`: Number of partly covered lines identified
- `analysisType`: Type of analysis performed
- `highestScore`/`lowestScore`/`averageScore`: Score statistics

#### Stuck Point Entry
- `classFqn`: Fully qualified class name
- `fileName`: Source file name
- `lineNumber`: Line number in source
- `coverageStatus`: Always "PARTLY_COVERED" for stuck points
- `instructionCoverage`: Instruction-level coverage stats
- `branchCoverage`: Branch-level coverage stats  
- `stuckPointScore`: Calculated importance score
- `analysisMetadata`: Analysis process information

## Implementation Status

### ✅ Completed Components

1. **Project Structure**: Maven-based project with proper dependencies
2. **JaCoCo Integration**: Full coverage analysis using JaCoCo core API
3. **SootUp Integration**: ICFG initialization and setup
4. **Data Models**: Complete data structures for coverage and results
5. **CLI Interface**: Command line argument parsing and validation
6. **JSON Output**: Structured reporting with Jackson
7. **Workflow Orchestration**: End-to-end analysis pipeline

### ✅ Recently Completed

8. **ICFG Score Calculation**: **COMPLETED** - Full implementation of stuck point scoring algorithm in `SootUpICFGAnalyzer.calculateStuckPointScore()`

**Implementation Details**:
1. **Statement Mapping**: Maps line numbers to corresponding SootUp statements using position information
2. **ICFG Traversal**: BFS traversal of interprocedural control flow graph including method calls
3. **Reachability Analysis**: Finds all statements reachable from stuck point locations
4. **Coverage Integration**: Filters out already covered statements using JaCoCo data
5. **Score Calculation**: Returns count of uncovered but reachable statements as priority score

**Scoring Algorithm**:
- Locates all statements at the target line number
- Performs breadth-first search through ICFG starting from those statements
- Includes interprocedural calls using SootUp's call graph analysis
- Excludes statements that are already fully covered according to JaCoCo data
- Higher scores indicate more uncovered code reachable from the stuck point

## Test Results

The tool has been successfully tested on real-world data with excellent results:

**Test Data**: Apache Commons Imaging library fuzzing analysis
**Input**: JaCoCo execution data from 17,013 coverage lines
**Results**: 120 stuck points identified and scored

**Top Stuck Points Discovered**:
```
=== Top 10 Stuck Points ===
Rank | Score | Location
-----|-------|----------
   1 |    44 | org.apache.commons.imaging.Imaging:812
   2 |    29 | org.apache.commons.imaging.formats.pnm.PnmImageParser:271
   3 |    22 | org.apache.commons.imaging.internal.ImageParserFactory:53
   4 |    14 | org.apache.commons.imaging.bytesource.InputStreamByteSource$BlockInputStream:92
   5 |    14 | org.apache.commons.imaging.formats.dcx.DcxImageParser:104
   6 |    13 | org.apache.commons.imaging.formats.tiff.TiffDirectory:142
   7 |    12 | org.apache.commons.imaging.formats.tiff.TiffReader:417
   8 |    11 | org.apache.commons.imaging.formats.dcx.DcxImageParser:93
   9 |    11 | org.apache.commons.imaging.common.ImageBuilder:243
  10 |    11 | org.apache.commons.imaging.formats.tiff.TiffReader:277
... and 110 more stuck points
```

**Analysis Statistics**:
- Score range: 1 to 44 uncovered reachable statements
- Average score: 5.36 uncovered reachable statements per stuck point
- Processing time: ~3 minutes for 120 stuck points
- Success rate: 100% (all stuck points successfully analyzed)

## Architecture

The tool consists of several key components:

1. **StuckPointAnalyzer**: Main entry point and CLI handling
2. **StuckPointAnalyzerCore**: Orchestrates the analysis workflow  
3. **JacocoCoverageAnalyzer**: Processes JaCoCo execution data
4. **SootUpICFGAnalyzer**: Handles SootUp setup and ICFG analysis
5. **CoverageLineInfo**: Data model for coverage information
6. **StuckPointResult**: Data model for analysis results

## Dependencies

- **SootUp**: Static analysis framework for ICFG generation
- **JaCoCo**: Code coverage analysis library
- **ASM**: Bytecode manipulation (required by JaCoCo)
- **Apache Commons CLI**: Command line argument parsing
- **Jackson**: JSON processing for output generation

## Troubleshooting

### Common Issues

1. **ClassNotFoundException**
   - Ensure all required JARs are included in `--jars`
   - Check that class paths are correct

2. **Invalid Entry Point**
   - Verify entry point method exists in the analyzed classes
   - Use fully qualified class names

3. **Empty Results**
   - Check that JaCoCo execution file contains data
   - Ensure analyzed classes match those that were instrumented

4. **Memory Issues**
   - Large projects may require increased heap size: `-Xmx4g`

### Debug Mode

Run with system property for detailed error information:
```bash
java -Ddebug=true -jar stuck-point-analyzer-1.0.0.jar ...
```

## Future Enhancements

1. **Advanced Scoring**: Implement sophisticated ICFG-based scoring algorithms
2. **Multiple Entry Points**: Support analysis from multiple entry points
3. **Configuration Files**: Support configuration files for complex setups
4. **Integration APIs**: Programmatic APIs for tool integration
5. **Visualization**: Generate visual representations of stuck points
6. **Filtering**: Advanced filtering options for results
7. **Caching**: Cache analysis results for faster subsequent runs

## License

This project follows the same license terms as the parent CRS-java project.