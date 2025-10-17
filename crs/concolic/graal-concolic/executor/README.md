# Concolic executor
## Build
```bash
./gradlew build
```
IMPORTANT NOTE:
- This project uses the graal sdk libraries(jars) from the local directory.
    - You have to build the graal architecture and copy the jars to the `app/lib/jars` directory.
        - See README.md of the our fork of the graal project
        - You may want to use the build script like `build-build-jvm-ce.sh`
- This project have to be executed with the graal compiled java binary(jvm 17)
    - It can be specified by gradle options like:
        - `./gradlew run -Dorg.gradle.java.home=<path-to-graal-jdk-17> --args="../../tests/Simple HelloWorld 1234"`
    - Or you can set `org.gradle.java.home` option of `gradle.properties` file.
    - If it is correctly set, `./gradlew -v` shows JVM version with GraalVM.
- The current path of the executor is `app` directory, not the root of gradle project.
- Don't forget to set `export LD_DEBUG=unused` before running the executor.

## Run
```bash
./gradlew run
# or
./gradlew run --args="ClassPaths MainArg"
```

Example:
```bash
$ ./gradlew run --args="../../tests/Simple HelloWorld 1234"
$ LOG_LEVEL=ERROR ./gradlew run -Dorg.gradle.java.home=`readlink -f ../graal-jdk-25-14/sdk/mxbuild/linux-amd64/GRAALVM_ESPRESSO_JVM_JAVA21/graalvm-espresso-jvm-openjdk-21.0.2+13.1` --args="../../tests/Simple IntegerObject 1234"

> Task :app:run
[Executor] Current java version: 17.0.7
[Executor] This will run the 'main' method of the target class with the given classpath and arguments.
[Executor] classpath: ../../tests/Simple
Hello, World!

BUILD SUCCESSFUL in 3s
2 actionable tasks: 1 executed, 1 up-to-date
```

## Server

### `/execution`
- It executes the concolie executor for the corpuses in `{input-corpus-dir}` for each harness, starting from the oldest one.
- When the execution is complete, the corpus is deleted, and output files are stored in `{output-corpus-dir}`.

### Run
```bash
# python scripts/server.py --help
usage: server.py [-h] --work-dir WORK_DIR --input-corpus-dir INPUT_CORPUS_DIR --output-corpus-dir OUTPUT_CORPUS_DIR --harness HARNESS [--executor-dir EXECUTOR_DIR] [--timeout TIMEOUT]
                 [--port PORT] [--do-execution]

graal-concolic server

options:
  -h, --help            show this help message and exit
  --work-dir WORK_DIR   working dir for the concolic execution
  --input-corpus-dir INPUT_CORPUS_DIR
                        corpus dir for the candidates for running concolic execution
  --output-corpus-dir OUTPUT_CORPUS_DIR
                        corpus dir for the output blobs as results of concolic execution
  --harness HARNESS     target harness id
  --executor-dir EXECUTOR_DIR
                        (option) executor dir for concolic execution (default: .)
  --timeout TIMEOUT     (option) timeout (default: 300)
  --port PORT           (option) port (default: 5005)
  --do-execution        (option) do-execution without flask
```

Example:
```bash
# pip install -r scripts/requirements.txt
python scripts/server.py --work-dir /path/to/cp --input-corpus-dir test/in --output-corpus-dir test/out --harness id_1
```
