## joern
cd ${JOERN_DIR} && \
    mvn dependency:get -DgroupId=com.google.j2objc -DartifactId=j2objc-annotations -Dversion=3.0.0 && \
    mvn dependency:get -DgroupId=com.google.guava -DartifactId=guava -Dversion=33.3.0-jre && \
    mvn dependency:get -DgroupId=com.google.guava -DartifactId=guava -Dversion=32.0.1-android && \
    mvn dependency:get -DgroupId=org.ow2.asm -DartifactId=asm -Dversion=9.7 && \
    SBT_OPTS="-Xmx12G" sbt clean update stage

## atl-asm and atl-soot
cd ${JAVA_CRS_SRC}/prebuilt && \
    ./mvn_install.sh

## crs python package deps
pip3.12 install ${JAVA_CRS_SRC}/libs/libCRS && \
    pip3.12 install ${JAVA_CRS_SRC}/libs/libLLM && \
    pip3.12 install ${JAVA_CRS_SRC}/libs/coordinates && \
    ${JAVA_CRS_SRC}/libs/libFDP/build_pymodule.sh

## jazzer-llm-augmented
cd ${JAVA_CRS_SRC}/jazzer-llm-augmented/ProgramExecutionTracer && \
    mvn -B clean package && \
    cd ${JAVA_CRS_SRC}/jazzer-llm-augmented && \
    pip3.12 install -r requirements.txt

## static analyzer
cd ${JAVA_CRS_SRC}/static-analysis && \
    ./build.sh

## llm-poc-gen
cd ${JAVA_CRS_SRC}/llm-poc-gen && \
    ./init.sh && \
    curl -sSL https://install.python-poetry.org | python3.12 - && \
    poetry install --with crs

## expkit
cd ${JAVA_CRS_SRC}/expkit && \
    pip3.12 install -r requirements.txt && \
    pip3.12 install -e .

## Build espresso-JDK-dependent components
cd /graal-jdk/concolic/graal-concolic/executor && \
    JAVA_HOME=/graal-jdk/sdk/mxbuild/linux-amd64/GRAALVM_ESPRESSO_JVM_CE_JAVA21/graalvm-espresso-jvm-ce-openjdk-21.0.2+13.1/ ./gradlew build
pip3.12 install -r /graal-jdk/concolic/graal-concolic/executor/scripts/requirements.txt
cd /graal-jdk/concolic/graal-concolic/provider && \
    JAVA_HOME=/graal-jdk/sdk/mxbuild/linux-amd64/GRAALVM_ESPRESSO_JVM_CE_JAVA21/graalvm-espresso-jvm-ce-openjdk-21.0.2+13.1/ ./gradlew build

cd ${JAVA_CRS_SRC}/libs/libAgents && pip3.12 install --no-deps .
cd ${JAVA_CRS_SRC}/libs/libDeepGen && pip3.12 install --no-deps .
cd ${JAVA_CRS_SRC}/deepgen && pip3.12 install --no-deps -e .
