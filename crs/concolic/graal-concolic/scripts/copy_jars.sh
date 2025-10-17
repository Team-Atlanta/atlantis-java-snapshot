#!/bin/bash

# Usage: copy_jars.sh HOST_JAVA_HOME

# Copy jars into executor/lib/jars, for concolic execution engine
# First argument is the path to the root of the host built JAVA_HOME
HOST_JAVA_HOME=$1
SCRIPT_DIR=$(readlink -f $(dirname $0))

mkdir -p $SCRIPT_DIR/../executor/app/lib/jars > /dev/null 2>&1

HOST_TRUFFLE_API_PATH=$HOST_JAVA_HOME/lib/truffle/truffle-api.jar
HOST_ESPRESSO_PATH=$HOST_JAVA_HOME/languages/java/espresso.jar
HOST_GRAAL_SDK_PATH=$HOST_JAVA_HOME/../../../jdk21/dists/jdk17/polyglot.jar

# Check whether GRAAL_SDK_PATH is file
if [ ! -f $HOST_GRAAL_SDK_PATH ]; then
    echo "Error: GRAAL_SDK_PATH is not a file."
    exit 1
fi
echo $SCRIPT_DIR
cp $HOST_TRUFFLE_API_PATH $SCRIPT_DIR/../executor/app/lib/jars/
cp $HOST_ESPRESSO_PATH $SCRIPT_DIR/../executor/app/lib/jars/
cp $HOST_GRAAL_SDK_PATH $SCRIPT_DIR/../executor/app/lib/jars/
