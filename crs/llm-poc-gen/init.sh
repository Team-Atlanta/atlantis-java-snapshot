#!/bin/bash
curdir=$(dirname $0)
jazzer_path=$1
if [ -z "$jazzer_path" ]; then
    jazzer_path=$AIXCC_JAZZER_DIR
fi

# Prepare libjazzer_fuzzed_data_provider.so
jar xf $jazzer_path/jazzer_standalone_deploy.jar com/code_intelligence/jazzer/driver/jazzer_fuzzed_data_provider_linux_x86_64/libjazzer_fuzzed_data_provider.so
mv com/code_intelligence/jazzer/driver/jazzer_fuzzed_data_provider_linux_x86_64/libjazzer_fuzzed_data_provider.so $curdir
rm -rf com/code_intelligence/jazzer/driver/jazzer_fuzzed_data_provider_linux_x86_64

# Prepare JavaAgent
cd $curdir/javaagent && mvn package
