# Tests for the coordinates package

This directory contains pytest tests for the coordinates package.

## Structure

- `test_inspector.py`: Tests for the `BytecodeInspector` class in the `inspector.py` module

## Running the tests

From the project root, run:

```
pytest
```

Or to run with verbose output:

```
pytest -v
```

## Notes

- The tests depend on the bytecode-parser JAR being built. If it's not built, some tests will be skipped.

- For most reliable results, build the bytecode-parser before running the tests:

  ```
  cd bytecode-parser
  mvn clean package
  cd ..
  ```
