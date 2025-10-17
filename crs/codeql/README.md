# CodeQL Sink Analysis Tool

This tool runs a CodeQL query to identify additional security sinks in Java code and transforms the results into a coordinate-based format suitable for further analysis.

## Setup

Before running the analysis, you need to initialize the project:

```bash
./init.sh
```

This will:
1. Install required Python dependencies (PyYAML, Jinja2)
2. Generate CodeQL model and query files from centralized sink definitions
3. Install the CodeQL pack

This requires:
1. CodeQL CLI installed and available in PATH
2. Python 3.x

## Usage

### Basic Usage

```bash
./run.sh <database_path> <output_json_path>
```

**Parameters:**
- `database_path` - Path to the CodeQL database to analyze
- `output_json_path` - Path where the transformed coordinate format JSON will be saved

**Example:**
```bash
./run.sh test-db results.json
```

### What the Script Does

1. **Runs CodeQL Query**: Executes the sink detection query against the specified database
2. **Decodes Results**: Converts BQRS output to JSON format (temporarily)
3. **Transforms Format**: Converts the CodeQL JSON format to coordinate format
4. **Outputs Results**: Saves the final coordinate format to the specified output file

### Output Format

The script outputs JSON in coordinate format where each entry looks like:

```json
{
  "coord": {
    "line_num": 342,
    "method_name": "tokenizeRow",
    "file_name": "BasicCParser.java",
    "bytecode_offset": -1,
    "method_desc": "(Ljava/lang/String;)[Ljava/lang/String;",
    "mark_desc": "sink-RegexInjection",
    "method_signature": "org.apache.commons.imaging.common.BasicCParser: java.lang.String[] tokenizeRow(java.lang.String)",
    "class_name": "org/apache/commons/imaging/common/BasicCParser"
  },
  "id": "Sink: java.util.regex; Pattern; false; compile; (String); static; Argument[0]; regex-use; manual"
}
```

## Metadata Retrieval

You can retrieve metadata for any sink definition using its ID:

```bash
./get_metadata.sh "<sink_id>"
```

**Example:**
```bash
./get_metadata.sh "Sink: java.io; File; false; <init>; (String); ; Argument[0]; path-injection; manual"
```

This will output whatever metadata is defined in the sink_definitions.yml file in YAML format, for example:
```yaml
category: file-system
cwe: CWE-22
description: File constructor that accepts a pathname string
severity: medium
```

The sink ID can be retrieved from the analysis output file.

## Architecture

This project uses a centralized approach for managing sink definitions with separated model and metadata components.

### File Structure

```
├── sink_definitions.yml          # Central sink definitions with model and metadata
├── scripts/                     # Python scripts
│   ├── generate_models.py       # Generates CodeQL model and query files
│   ├── get_metadata.py          # Retrieves metadata by sink ID
│   └── transform_results.py     # Transforms CodeQL results to coordinate format
├── templates/                   # Jinja2 templates for code generation
│   ├── model.yml.j2            # Template for CodeQL model files
│   └── sinks.ql.j2             # Template for CodeQL query file
├── sinks-pack/                 # Generated CodeQL pack
│   ├── models/                 # Generated model files (one per package)
│   │   ├── java.io.model.yml
│   │   ├── java.lang.model.yml
│   │   └── ...
│   └── queries/
│       └── sinks.ql            # Generated query file
├── init.sh                     # Initialization script
├── run.sh                      # Analysis script
└── get_metadata.sh             # Metadata retrieval script
```

### Adding New Sink Definitions

Edit `sink_definitions.yml` and add entries with `model` (CodeQL fields) and `metadata` (additional info) sections:

```yaml
sink_definitions:
  - model:
      package: "java.example"
      type: "ExampleClass"
      subtypes: false
      name: "vulnerableMethod"
      signature: "(String)"
      ext: ""
      input: "Argument[0]"
      kind: "example-injection"
      provenance: "manual"
    metadata:
      description: "Description of the sink"
      category: "example-category"
      severity: "medium"
      cwe: "CWE-XXX"
```

After adding definitions, run `./init.sh` to regenerate the pack.

For more information on CodeQL model definitions, see the [CodeQL documentation](https://codeql.github.com/docs/codeql-language-guides/customizing-library-models-for-java-and-kotlin/).
