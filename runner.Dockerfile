FROM ghcr.io/aixcc-finals/base-builder-jvm:v1.3.0 AS aixcc_afc_builder_base
FROM ghcr.io/aixcc-finals/base-runner:v1.3.0 AS aixcc_afc_runner_base
FROM ghcr.io/blue9057/graal-deps:v1.0.0 AS graal_deps
FROM ghcr.io/occia/common-deps:v1.3.0 AS crs_java_base

#################################################################################
## Staged Images - Prebuilt AIxCC AFC official Jazzer
#################################################################################
FROM aixcc_afc_builder_base AS aixcc_jazzer_builder

COPY crs/fuzzers/aixcc-jazzer /src/aixcc-jazzer
WORKDIR /src/aixcc-jazzer
RUN yes | adduser --disabled-password builder && \
    chown -R builder .

USER builder:builder
RUN echo "build --java_runtime_version=local_jdk_17" >> .bazelrc \
    && echo "build --cxxopt=-stdlib=libc++" >> .bazelrc \
    && echo "build --linkopt=-lc++" >> .bazelrc
RUN echo "build --experimental_repository_downloader_retries=5" >> .bazelrc \
    && echo "build --http_timeout_scaling=2" >> .bazelrc \
    && echo "build --repository_cache=/home/builder/.cache/bazel-repo" >> .bazelrc

RUN bazel build \
    //src/main/java/com/code_intelligence/jazzer:jazzer_standalone_deploy.jar \
    //deploy:jazzer-api \
    //deploy:jazzer-junit \
    //launcher:jazzer
RUN mkdir out && \
    cp $(bazel cquery --output=files //src/main/java/com/code_intelligence/jazzer:jazzer_standalone_deploy.jar) out/jazzer_agent_deploy.jar && \
    cp $(bazel cquery --output=files //launcher:jazzer) out/jazzer_driver && \
    cp $(bazel cquery --output=files //deploy:jazzer-api) out/jazzer_api_deploy.jar && \
    cp $(bazel cquery --output=files //deploy:jazzer-junit) out/jazzer_junit.jar

USER root
RUN mkdir /classpath && mkdir /classpath/aixcc-jazzer && \
    cp out/jazzer_agent_deploy.jar /classpath/aixcc-jazzer/jazzer_standalone_deploy.jar && \
    cp out/jazzer_driver /classpath/aixcc-jazzer/jazzer && \
    cp out/jazzer_junit.jar /classpath/aixcc-jazzer/ && \
    cp out/jazzer_api_deploy.jar /classpath/aixcc-jazzer/

#################################################################################
## Staged Images - Prebuilt atl-jazzer
#################################################################################
FROM aixcc_afc_builder_base AS atl_jazzer_builder

COPY crs/fuzzers/atl-jazzer /app/crs-cp-java/fuzzers/atl-jazzer
WORKDIR /app/crs-cp-java/fuzzers/atl-jazzer
RUN yes | adduser --disabled-password builder && \
    chown -R builder .

USER builder:builder
RUN echo "build --java_runtime_version=local_jdk_17" >> .bazelrc \
    && echo "build --cxxopt=-stdlib=libc++" >> .bazelrc \
    && echo "build --linkopt=-lc++" >> .bazelrc
RUN echo "build --experimental_repository_downloader_retries=5" >> .bazelrc \
    && echo "build --http_timeout_scaling=2" >> .bazelrc \
    && echo "build --repository_cache=/home/builder/.cache/bazel-repo" >> .bazelrc
RUN bazel build \
    //src/main/java/com/code_intelligence/jazzer:jazzer_standalone_deploy.jar \
    //deploy:jazzer-api \
    //deploy:jazzer-junit \
    //launcher:jazzer
RUN mkdir out && \
    cp $(bazel cquery --output=files //src/main/java/com/code_intelligence/jazzer:jazzer_standalone_deploy.jar) out/jazzer_agent_deploy.jar && \
    cp $(bazel cquery --output=files //launcher:jazzer) out/jazzer_driver && \
    cp $(bazel cquery --output=files //deploy:jazzer-api) out/jazzer_api_deploy.jar && \
    cp $(bazel cquery --output=files //deploy:jazzer-junit) out/jazzer_junit.jar

USER root
RUN mkdir /classpath && mkdir /classpath/atl-jazzer && \
    cp out/jazzer_agent_deploy.jar /classpath/atl-jazzer/jazzer_standalone_deploy.jar && \
    cp out/jazzer_driver /classpath/atl-jazzer/jazzer && \
    cp out/jazzer_junit.jar /classpath/atl-jazzer/ && \
    cp out/jazzer_api_deploy.jar /classpath/atl-jazzer/

#################################################################################
## Staged Images - Prebuilt atl-libafl-jazzer
#################################################################################
FROM aixcc_afc_builder_base AS atl_jazzer_libafl_builder

# libAFL requires bindgen which requires libclang.
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y libclang-dev

COPY crs/fuzzers/atl-libafl-jazzer /app/crs-cp-java/fuzzers/atl-libafl-jazzer
COPY crs/fuzzers/jazzer-libafl /app/crs-cp-java/fuzzers/jazzer-libafl
WORKDIR /app/crs-cp-java/fuzzers/atl-libafl-jazzer
RUN yes | adduser --disabled-password builder && \
    chown -R builder . && chown -R builder ../jazzer-libafl/

USER builder:builder
# Install Rust.
RUN curl https://sh.rustup.rs -sSf | sh -s -- --component llvm-tools --default-toolchain nightly-2025-06-04 -y
ENV PATH="/home/builder/.cargo/bin:${PATH}"
RUN ln -sf /home/builder/.rustup/toolchains/nightly-2025-06-04-x86_64-unknown-linux-gnu /home/builder/.rustup/toolchains/nightly-x86_64-unknown-linux-gnu
RUN echo "build --java_runtime_version=local_jdk_17" >> .bazelrc \
    && echo "build --cxxopt=-stdlib=libc++" >> .bazelrc \
    && echo "build --linkopt=-lc++" >> .bazelrc
RUN echo "build --experimental_repository_downloader_retries=5" >> .bazelrc \
    && echo "build --http_timeout_scaling=2" >> .bazelrc \
    && echo "build --repository_cache=/home/builder/.cache/bazel-repo" >> .bazelrc
RUN bazel build \
    //src/main/java/com/code_intelligence/jazzer:jazzer_standalone_deploy.jar \
    //deploy:jazzer-api \
    //deploy:jazzer-junit \
    //launcher:jazzer
RUN mkdir out && \
    cp $(bazel cquery --output=files //src/main/java/com/code_intelligence/jazzer:jazzer_standalone_deploy.jar) out/jazzer_agent_deploy.jar && \
    cp $(bazel cquery --output=files //launcher:jazzer) out/jazzer_driver && \
    cp $(bazel cquery --output=files //deploy:jazzer-api) out/jazzer_api_deploy.jar && \
    cp $(bazel cquery --output=files //deploy:jazzer-junit) out/jazzer_junit.jar

USER root
RUN mkdir /classpath && mkdir /classpath/atl-libafl-jazzer && \
    cp out/jazzer_agent_deploy.jar /classpath/atl-libafl-jazzer/jazzer_standalone_deploy.jar && \
    cp out/jazzer_driver /classpath/atl-libafl-jazzer/jazzer && \
    cp out/jazzer_junit.jar /classpath/atl-libafl-jazzer/ && \
    cp out/jazzer_api_deploy.jar /classpath/atl-libafl-jazzer/

#################################################################################
## Staged Images - Concolic Engine Build (/graal-jdk)
#################################################################################
FROM ubuntu:20.04 AS espresso_builder
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y \
    curl \
    python3.9 \
    python3-pip \
    git \
    zip \
    wget \
    build-essential \
    libstdc++-9-dev

# COPY crs/mx
COPY crs/concolic/graal-concolic/mx /mx

ENV PATH="/mx:$PATH"
RUN echo Y | mx fetch-jdk labsjdk-ce-21
RUN python3 -mpip install ninja_syntax

WORKDIR /graal-jdk
RUN wget https://github.com/Kitware/CMake/releases/download/v3.31.6/cmake-3.31.6-linux-x86_64.tar.gz && \
    tar -xzvf cmake-3.31.6-linux-x86_64.tar.gz && \
    cp -r cmake-3.31.6-linux-x86_64/* /usr/ && \
    rm -rf cmake-3.31.6-linux-x86_64

# graal espresso
COPY crs/concolic/graal-concolic/graal-jdk-25-14 /graal-jdk
COPY crs/concolic/graal-concolic/docker-scripts /docker-scripts
WORKDIR /graal-jdk
RUN chmod +x /docker-scripts/*

# put mx deps
COPY --from=graal_deps /root/.mx /root/.mx

ENV MODE="jvm-ce"
ENV PREPARE_CMD="pushd /graal-jdk/espresso && mx --env=$MODE build --targets LLVM_TOOLCHAIN && mx --env $MODE create-generated-sources"
RUN /docker-scripts/init_dev.sh /bin/bash -c "$PREPARE_CMD"
ENV BUILD_CMD="pushd /graal-jdk/espresso && export MX_BUILD_EXPLODED=$MX_BUILD_EXPLODED && mx --env $MODE create-generated-sources && mx --env $MODE build"
RUN /docker-scripts/init_dev.sh /bin/bash -c "$BUILD_CMD"

#################################################################################
## Staged Images - Prebuilt Joern (Public)
#################################################################################
FROM crs_java_base AS joern_builder

## joern
COPY ./crs/joern /opt/joern
ENV JOERN_DIR=/opt/joern/Joern
ENV JOERN_CLI=$JOERN_DIR/joern-cli
ENV JAVA2CPG=$JOERN_DIR/joern-cli/frontends/javasrc2cpg/bin
ENV PATH=$PATH:$JAVA_HOME/bin:$JOERN_CLI:$JAVA2CPG
RUN cd $JOERN_DIR && \
    mvn dependency:get -DgroupId=com.google.j2objc -DartifactId=j2objc-annotations -Dversion=3.0.0 && \
    mvn dependency:get -DgroupId=com.google.guava -DartifactId=guava -Dversion=33.3.0-jre && \
    mvn dependency:get -DgroupId=com.google.guava -DartifactId=guava -Dversion=32.0.1-android && \
    mvn dependency:get -DgroupId=org.ow2.asm -DartifactId=asm -Dversion=9.7 && \
    SBT_OPTS="-Xmx12G" sbt clean update stage && \
    rm -rf joern-cli/frontends/c2cpg joern-cli/frontends/csharpsrc2cpg \
        joern-cli/frontends/ghidra2cpg joern-cli/frontends/gosrc2cpg \
        joern-cli/frontends/jimple2cpg joern-cli/frontends/jssrc2cpg \
        joern-cli/frontends/kotlin2cpg joern-cli/frontends/php2cpg \
        joern-cli/frontends/pysrc2cpg joern-cli/frontends/rubysrc2cpg \
        joern-cli/frontends/swiftsrc2cpg joern-cli/frontends/x2cpg \
        joern-cli/target/universal/stage/frontends

# Base image already has the public dependencies installed

#################################################################################
## CRS Installation - Components
#################################################################################
FROM crs_java_base AS crs_java

## CRS-java commons
ENV JAVA_CRS_SRC=/app/crs-cp-java
RUN mkdir -p $JAVA_CRS_SRC && chmod -R 0755 $JAVA_CRS_SRC

## CRS-java fuzzer binaries
COPY --from=aixcc_jazzer_builder /classpath/aixcc-jazzer /classpath/aixcc-jazzer
COPY --from=atl_jazzer_builder /classpath/atl-jazzer /classpath/atl-jazzer
COPY --from=atl_jazzer_libafl_builder /classpath/atl-libafl-jazzer /classpath/atl-libafl-jazzer
COPY ./crs/fuzzers/mock-jazzer /classpath/mock-jazzer
ENV AIXCC_JAZZER_DIR=/classpath/aixcc-jazzer
ENV ATL_JAZZER_DIR=/classpath/atl-jazzer
ENV ATL_JAZZER_LIBAFL_DIR=/classpath/atl-libafl-jazzer
ENV ATL_MOCK_JAZZER_DIR=/classpath/mock-jazzer

## crs python package deps
COPY ./crs/libs ${JAVA_CRS_SRC}/libs
RUN /venv/bin/pip install --no-cache-dir \
        ${JAVA_CRS_SRC}/libs/libCRS \
        ${JAVA_CRS_SRC}/libs/libLLM \
        ${JAVA_CRS_SRC}/libs/coordinates \
        ${JAVA_CRS_SRC}/libs/anthropic-proxy \
        grpcio-tools==1.71.0 \
        protobuf==5.29.4 \
        protoletariat==3.3.9 \
        ${JAVA_CRS_SRC}/libs/userspace-code-browser/python-client && \
    bash ${JAVA_CRS_SRC}/libs/libFDP/build_pymodule.sh && \
    /venv/bin/pip install --no-cache-dir \
        ${JAVA_CRS_SRC}/libs/claude-code-sdk-python && \
    rm -rf /root/.cache/pip

## joern
COPY --from=joern_builder /opt/joern ${JAVA_CRS_SRC}/joern
ENV JOERN_DIR=${JAVA_CRS_SRC}/joern/Joern
ENV JOERN_CLI=$JOERN_DIR/joern-cli
ENV JAVA2CPG=$JOERN_DIR/joern-cli/frontends/javasrc2cpg/bin
ENV PATH=$PATH:$JAVA_HOME/bin:$JOERN_CLI:$JAVA2CPG

## CRS-java atl-asm and atl-soot
COPY ./crs/prebuilt ${JAVA_CRS_SRC}/prebuilt
RUN cd ${JAVA_CRS_SRC}/prebuilt && \
    ./mvn_install.sh
ENV JACOCO_CLI_DIR=${JAVA_CRS_SRC}/prebuilt/jacococli

## jazzer-llm-augmented
COPY ./crs/jazzer-llm-augmented ${JAVA_CRS_SRC}/jazzer-llm-augmented
#RUN cd ${JAVA_CRS_SRC}/jazzer-llm-augmented/ProgramExecutionTracer && \
#    mvn -B clean package && \
#    cd ${JAVA_CRS_SRC}/jazzer-llm-augmented && \
#    /venv/bin/pip install --no-cache-dir -r requirements.txt && \
#    rm -rf /root/.cache/pip

## static-analyzer
COPY ./crs/static-analysis ${JAVA_CRS_SRC}/static-analysis
RUN cd ${JAVA_CRS_SRC}/static-analysis && \
    ./build.sh

## codeql
COPY ./crs/codeql ${JAVA_CRS_SRC}/codeql
RUN cd ${JAVA_CRS_SRC}/codeql && \
    ./init.sh

## llm-poc-gen
COPY ./crs/llm-poc-gen ${JAVA_CRS_SRC}/llm-poc-gen
ENV PATH=${PATH}:/root/.local/bin
RUN cd ${JAVA_CRS_SRC}/llm-poc-gen && \
    ./init.sh && \
    /venv/bin/python -m pip install poetry==2.1.3 && \
    /venv/bin/poetry install --with crs && \
    /venv/bin/poetry cache clear --all pypi --no-interaction && \
    rm -rf /root/.cache/pip

## expkit
COPY ./crs/expkit ${JAVA_CRS_SRC}/expkit
RUN cd ${JAVA_CRS_SRC}/expkit && \
    /venv/bin/pip install --no-cache-dir -r requirements.txt && \
    /venv/bin/pip install -e . && \
    rm -rf /root/.cache/pip

## Build espresso-JDK-dependent components
## concolic executor engine (espresso-jdk & runtime)
# COPY crs/binary only
COPY --from=espresso_builder /graal-jdk/sdk/mxbuild/linux-amd64/GRAALVM_ESPRESSO_JVM_CE_JAVA21/ /graal-jdk/sdk/mxbuild/linux-amd64/GRAALVM_ESPRESSO_JVM_CE_JAVA21/
# COPY crs/only the executor and provider
COPY ./crs/concolic/graal-concolic/executor /graal-jdk/concolic/graal-concolic/executor
COPY ./crs/concolic/graal-concolic/provider /graal-jdk/concolic/graal-concolic/provider
COPY ./crs/concolic/graal-concolic/scheduler /graal-jdk/concolic/graal-concolic/scheduler
RUN cd /graal-jdk/concolic/graal-concolic/executor && \
        JAVA_HOME=/graal-jdk/sdk/mxbuild/linux-amd64/GRAALVM_ESPRESSO_JVM_CE_JAVA21/graalvm-espresso-jvm-ce-openjdk-21.0.2+13.1/ ./gradlew build && \
        /venv/bin/pip install --no-cache-dir -r /graal-jdk/concolic/graal-concolic/executor/scripts/requirements.txt && \
    cd /graal-jdk/concolic/graal-concolic/provider && \
        JAVA_HOME=/graal-jdk/sdk/mxbuild/linux-amd64/GRAALVM_ESPRESSO_JVM_CE_JAVA21/graalvm-espresso-jvm-ce-openjdk-21.0.2+13.1/ ./gradlew build && \
    rm -rf /root/.cache/coursier && \
    rm -rf /root/.cache/pip

## dictgen
COPY ./crs/dictgen ${JAVA_CRS_SRC}/dictgen
ENV DICTGEN_DIR=${JAVA_CRS_SRC}/dictgen
#RUN cd ${JAVA_CRS_SRC}/dictgen && \
#    /venv/bin/pip install --no-cache-dir -r requirements.txt && \
#    rm -rf /root/.cache/pip


## deepgen
COPY ./crs/deepgen ${JAVA_CRS_SRC}/deepgen
RUN cd ${JAVA_CRS_SRC}/deepgen/jvm/stuck-point-analyzer && \
    mvn -B clean package && \
    cd ${JAVA_CRS_SRC}/libs/libAgents && \
        /venv/bin/pip install --no-cache-dir \
            "anyio[trio]>=4.0.0" \
            apscheduler>=3.11.0 \
            aider-chat>=0.80.2 \
            aiofiles>=24.1.0 \
            dotenv>=0.9.9 \
            filelock>=3.12.0 \
            google-genai>=1.9.0 \
            litellm>=1.65.1 \
            pocketflow>=0.0.2 \
            psutil>=5.9.0 \
            pydantic>=2.11.1 \
            pytest-asyncio>=0.26.0 \
            tree-sitter==0.24.0 \
            tree-sitter-cpp==0.23.4 && \
        /venv/bin/pip install --no-deps . && \
    cd ${JAVA_CRS_SRC}/libs/libDeepGen && \
        /venv/bin/pip install --no-cache-dir \
            atomics>=1.0.3 \
            protobuf==5.29.4 \
            psutil>=7.0.0 \
            zmq>=pyzmq>=26.4.0 && \
        /venv/bin/pip install --no-cache-dir \
            git+https://github.com/renatahodovan/grammarinator.git@68b0350 && \
        /venv/bin/pip install --no-deps . && \
    cd ${JAVA_CRS_SRC}/deepgen && \
        /venv/bin/pip install --no-deps . && \
    rm -rf /root/.cache/pip

## crs-java main entry
COPY ./crs/*.sh ./crs/*.py ./crs/requirements.txt ./crs/jazzer_driver_stub ./crs/crs-java.config ./crs/sink-targets.txt ${JAVA_CRS_SRC}/
COPY ./crs/javacrs_modules ${JAVA_CRS_SRC}/javacrs_modules
COPY ./crs/tests ${JAVA_CRS_SRC}/tests
RUN /venv/bin/pip install --no-cache-dir -r ${JAVA_CRS_SRC}/requirements.txt && \
    rm -rf /root/.cache/pip
ENV JAVA_CRS_SINK_TARGET_CONF=${JAVA_CRS_SRC}/sink-targets.txt
ENV JAVA_CRS_CUSTOM_SINK_YAML=${JAVA_CRS_SRC}/codeql/sink_definitions.yml

## git setup
# git/python-git will not work if CP repo is of unknown user:
#   - fatal: detected dubious ownership in repository
RUN git config --global --add safe.directory '*'

## crs-e2e-checker
RUN ln -s ${JAVA_CRS_SRC}/tests/e2e_result_checker.py /usr/local/bin/crs-e2e-check

RUN mkdir -p /classpath/raw-jazzer
COPY --from=aixcc_afc_builder_base /usr/local/bin/jazzer_agent_deploy.jar /classpath/raw-jazzer/jazzer_standalone_deploy.jar
COPY --from=aixcc_afc_builder_base /usr/local/bin/jazzer_driver /classpath/raw-jazzer/jazzer
COPY --from=aixcc_afc_builder_base /usr/local/bin/jazzer_junit.jar /classpath/raw-jazzer/
COPY --from=aixcc_afc_builder_base /usr/local/lib/jazzer_api_deploy.jar /classpath/raw-jazzer/

### NOTE: exp only
COPY crs/ssmode-lpg.toml ${JAVA_CRS_SRC}/ssmode-lpg.toml
COPY crs/ssmode-sink.txt ${JAVA_CRS_SRC}/ssmode-sink.txt
RUN mkdir -p ${JAVA_CRS_SRC}/llm-poc-gen/eval/sheet && \
    cp ${JAVA_CRS_SRC}/ssmode-lpg.toml ${JAVA_CRS_SRC}/llm-poc-gen/eval/sheet/cpv.toml


WORKDIR ${JAVA_CRS_SRC}
ENTRYPOINT ["/bin/bash", "-c", "${JAVA_CRS_SRC}/run-crs-java.sh \"$@\"", "--"]
