#!/bin/bash

set -e

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
CRS_HOME=$(realpath $SCRIPT_DIR/../..)

# Build atl-asm
cd $SCRIPT_DIR/atl-asm

./gradle/gradlew clean build
./gradle/gradlew publishToMavenLocal

# Build atl-soot
cd $SCRIPT_DIR/atl-soot

mvn clean compile package

# Build atl-TaintAnalysis
cd $SCRIPT_DIR/atl-TaintAnalysis

# The tests require a very old version of Java, so we need to skip them
mvn clean compile package -DskipTests

# Copy jars to tmp-jars
cd $SCRIPT_DIR

cp atl-asm/asm/build/libs/asm-9.8-atlantis.jar tmp-jars/asm-9.8-atlantis.jar
cp atl-asm/asm-commons/build/libs/asm-commons-9.8-atlantis.jar tmp-jars/asm-commons-9.8-atlantis.jar
cp atl-asm/asm-tree/build/libs/asm-tree-9.8-atlantis.jar tmp-jars/asm-tree-9.8-atlantis.jar
cp atl-asm/asm-util/build/libs/asm-util-9.8-atlantis.jar tmp-jars/asm-util-9.8-atlantis.jar

cp atl-soot/target/sootclasses-trunk.jar tmp-jars/soot-4.7.0-atlantis.jar

cp atl-TaintAnalysis/target/TaintAnalysis-1.0-atlantis.jar tmp-jars/TaintAnalysis-1.0-atlantis.jar
