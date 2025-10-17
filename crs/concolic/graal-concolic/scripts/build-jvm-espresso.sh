#!/bin/bash
MODE=jvm
BUILD_CMD="pushd /graal-jdk/espresso; MX_BUILD_EXPLODED=$MX_BUILD_EXPLODED mx --env $MODE build --projects GRAALVM_ESPRESSO_JVM_JAVA21"
GET_JAVA_HOME_CMD="(cd /graal-jdk/espresso; echo \$(mx --env $MODE graalvm-home))"

docker compose run --rm espresso-dev /bin/bash -c "$BUILD_CMD"
INTERNAL_JAVA_HOME=$(docker compose run --rm espresso-dev /bin/bash -c "$GET_JAVA_HOME_CMD")
HOST_JAVA_HOME=$(pwd)$(echo $INTERNAL_JAVA_HOME | sed 's/graal-jdk/graal-jdk-25-14/')

# Copy jars into executor/lib/jars, for concolic execution engine
SCRIPT_DIR=$(dirname $0)
$SCRIPT_DIR/copy_jars.sh $HOST_JAVA_HOME

echo "INTERNAL_JAVA_HOME:"
echo $INTERNAL_JAVA_HOME

echo "HOST_JAVA_HOME:"
echo $HOST_JAVA_HOME
