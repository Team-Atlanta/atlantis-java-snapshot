# jazzer-llm-augmented

Augmented jazzer with an LLM to help out during coverage plateaus.


## Usage

Run as a python module:

```bash
python -m jazzer_llm \
    --cp ...
    --target_class ... 
    --source-directory ...
    --jazzer-directory ...
    [--stuck-wait-time int]
    [--debug True|False]
```

* `--cp` - classpath to run the target program.
* `--target_class` - The name of the main class/fuzzing harness.
* `--jazzer-directory` - The directory jazzer is running in.
* `--source-directory` - Source code directory of both harness & project.


## Building

1. Build the `ProgramExecutionTracer` with `mvn package`.

2. Install python dependencies.


## Testing

```bash
python -m pytest
```
