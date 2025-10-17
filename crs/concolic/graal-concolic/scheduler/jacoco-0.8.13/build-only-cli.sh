#!/bin/bash

mvn install -DskipTests -Dmaven.javadoc.skip=true -Dspotless.check.skip=true -pl org.jacoco.cli
