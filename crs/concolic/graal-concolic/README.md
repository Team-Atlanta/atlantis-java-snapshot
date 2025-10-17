# Graal-based JAVA concolic execution
## Build
### Executor
It runs on GraalVM JVM and executes the target code (guest application). See `executor` folder for more details.

### Graal(Espresso) Development
#### Build whole project
If you are building this project for the first time, you have to build the whole project.
```bash
docker compose build espresso-dev
```

And you can get a shell in the container by running the following command.
```bash
docker compose run --rm espresso-dev /bin/bash
```

To build the project with MX, run the following command.
```bash
cd /workspace/espresso
mx --env native-ce build
```

You can also change `--env` options to build the project with different configurations.
```bash
mx --env jvm build       # GraalVM CE + Espresso jars (interpreter only)
mx --env jvm-ce build    # GraalVM CE + Espresso jars (JIT)
mx --env native-ce build # GraalVM CE + Espresso native (JIT)
```
- For performance, you should use `native-ce` configuration.
- For testing, you should use `jvm` configuration. Other configurations require linking process which takes too much time.
- You may need to copy jars into the executor if you build the project manually.

You may need to install some dependencies before building the proeject:
```bash
./scripts/prepare-jvm.sh       # GraalVM CE + Espresso jars (interpreter only)
./scripts/prepare-jvm-ce.sh    # GraalVM CE + Espresso jars (JIT)
./scripts/prepare-native-ce.sh # GraalVM CE + Espresso native (JIT)
```

- Here are some helper scripts for building the project.
```bash
./scripts/build-jvm-whole.sh # Build JVM whole project
./scripts/build-jvm-ce-whole.sh # Build JVM CE whole project
./scripts/build-native-ce-whole.sh # Build native CE whole project
```

> IMPORTANT NOTE: Do not use  `MX_BUILD_EXPLODED=true` right now. It may cause undefined symbol error.
Exploded mode is disabled by default. You can enable it by setting `MX_BUILD_EXPLODED` environment variable to `true`.
It can be used to speed up the build process: Without this, mx will link files so the build process is slower.
```bash
MX_BUILD_EXPLODED=true mx --env native-ce build
```

After building the project, you can run the tests with the following command.
```bash
# jvm
mx --env jvm espresso -version
# jvm-ce
mx --env jvm-ce espresso -version
# native-ce
mx --env native-ce espresso -version
```

or directly run the espresso binary for more speed.
```bash
# jvm
export ESPRESSO=`mx --env jvm graalvm-home`/bin/java
$ESPRESSO -version
# jvm-ce
export ESPRESSO=`mx --env jvm-ce graalvm-home`/bin/java
$ESPRESSO -version
# native-ce
export ESPRESSO=`mx --env native-ce graalvm-home`/bin/java
$ESPRESSO -version
```

From outside the container, you can run the espresso binary by running the following command.
```bash
# THIS IS AN EXAMPLE. YOUR PATH MAY BE DIFFERENT.
# native-ce
./graal-jdk-17.0.9/sdk/mxbuild/linux-amd64/GRAALVM_ESPRESSO_NATIVE_CE_JAVA17/graalvm-espresso-native-ce-openjdk-17.0.7+4.1/bin/java -version
```

Sometimes espresso meets `undefined symbol bug`, especially handling nio-related libraries. Below command may help to solve(https://github.com/oracle/graal/blob/master/espresso/docs/hacking.md#limitations):
```bash
export LD_DEBUG=unused
```

#### Build espresso only
For concolic execution, you've mostly modified espresso code only like `BytecodeNode.java`.
If you have already built the whole project, you can build espresso only by running the following command.
For development, you should use `jvm` env option rather than other options.
```bash
./scripts/build-jvm-espresso.sh
```

## Version info
- Graal base version: https://github.com/oracle/graal/blob/jdk-17.0.9
- MX base version: https://github.com/graalvm/mx/tree/fb4e48e61e11ebee84ea4c4fc71d486c6e74b56b

## ETC
### Remove the container cache
MX cache is stored in the `mx_cache` volume. You can remove it by running the following command.
```bash
# Host: Outside of the container
docker volume rm mx_cache
```
or you can remove cache files inside of the container by running the following command.
```bash
# Container: Inside of the container
rm -rf /root/.mx/*
```

Also you may want to remove existing build cache files too:
```bash
# Host: Outside of the container
docker compose run --rm espresso-dev find /workspace/espresso -name mxbuild -type d -exec rm -rf {} \;

# Container: Inside of the container
find /workspace/espresso -name mxbuild -type d -exec rm -rf {} \;
```

You can also clean the cache by running the following helper script in host.
```bash
./scripts/clean.sh
```
