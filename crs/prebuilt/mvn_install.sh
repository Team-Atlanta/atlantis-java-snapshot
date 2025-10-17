#!/bin/bash

set -e

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

mvn install:install-file -Dfile="$SCRIPT_DIR/tmp-jars/asm-9.8-atlantis.jar" -DgroupId=org.ow2.asm -DartifactId=asm -Dversion=9.8-atlantis -Dpackaging=jar
mvn install:install-file -Dfile="$SCRIPT_DIR/tmp-jars/asm-commons-9.8-atlantis.jar" -DgroupId=org.ow2.asm -DartifactId=asm-commons -Dversion=9.8-atlantis -Dpackaging=jar
mvn install:install-file -Dfile="$SCRIPT_DIR/tmp-jars/asm-tree-9.8-atlantis.jar" -DgroupId=org.ow2.asm -DartifactId=asm-tree -Dversion=9.8-atlantis -Dpackaging=jar
mvn install:install-file -Dfile="$SCRIPT_DIR/tmp-jars/asm-util-9.8-atlantis.jar" -DgroupId=org.ow2.asm -DartifactId=asm-util -Dversion=9.8-atlantis -Dpackaging=jar
mvn install:install-file -Dfile="$SCRIPT_DIR/tmp-jars/soot-4.7.0-atlantis.jar" -DgroupId=org.soot-oss -DartifactId=soot -Dversion=4.7.0-atlantis -Dpackaging=jar
mvn install:install-file -Dfile="$SCRIPT_DIR/tmp-jars/TaintAnalysis-1.0-atlantis.jar" -DgroupId=de.upb.sse -DartifactId=TaintAnalysis -Dversion=1.0-atlantis -Dpackaging=jar
