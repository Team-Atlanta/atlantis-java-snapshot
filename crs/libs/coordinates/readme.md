# Intro

Create mapping between `source code lvl coordinate` with `bytecode lvl coordinate`.

## Requirements

- Java
- maven
- pytest (for dev/test only)

## Install

```bash
pip install .
```

For development:

```bash
pip install -e ".[dev]"
```

## Usage

```python
from coordinates import BytecodeInspector

inspector = BytecodeInspector()
inspector.init_mapping(
    pkg_list=["<default>"],
    cp_list=[
        "/data/workspace/CRS-java/crs/coordinates/coordinates/bytecode-parser.jar"
    ],
)

# Query by class name and line number
coord = inspector.query("BytecodeInspector", 128)
if coord:
    print(
        f"Found in {coord.jar_file}, class {coord.class_name}, source {coord.file_name}, method {coord.method_name}"
    )
else:
    print("No matching coordinates found.")
```

## Development

### Testing

Run the tests:

```bash
pytest
```

### Package

Build a distribution package:

```bash
python setup.py sdist
```

## TODO

- tests for java & python
- compact string inside json
- parallel bytecode parsing
