#!/bin/bash

set -e

mvn clean package

echo "Standalone jar file is located in target directory"

ls target/static-analysis-*-jar-with-dependencies.jar
