#!/bin/bash
# Copyright 2025 Code Intelligence GmbH
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


set -e
set -x

if ! command -v bazelisk &> /dev/null; then
  echo "bazelisk not found, installing"
  wget https://github.com/bazelbuild/bazelisk/releases/download/v1.25.0/bazelisk-linux-amd64
  chmod +x bazelisk-linux-amd64
  mv bazelisk-linux-amd64 /usr/bin/bazelisk
fi

if ! command -v clang &> /dev/null; then
  echo "clang not found, installing"
  apt update
  apt install -y clang
fi

# builder user not found
if ! id -u builder &>/dev/null; then
  yes | adduser --disabled-password builder
fi

CURRENT_DIR=$(pwd)

chown -R builder:builder .

run_as_builder() {
  su builder -c "export JAVA_HOME=\"$JAVA_HOME\" && export PATH=\"$PATH\":\"$JAVA_HOME\"/bin && source /home/builder/.cargo/env && $*"
}

run_as_builder "which rustc || curl https://sh.rustup.rs -sSf | sh -s -- --component llvm-tools --default-toolchain nightly -y"
run_as_builder "bash format.sh"
#run_as_builder "bazelisk clean"
run_as_builder "bazelisk build //..."
#run_as_builder "bazelisk test --nocache_test_results //... --verbose_failures --flaky_test_attempts=3 --test_summary=detailed"
#run_as_builder "bazelisk test --nocache_test_results --test_output=all //..."
#run_as_builder "bazelisk test --test_output=all //..."
run_as_builder "bazelisk test --test_output=all //tests:code_marker_workflow_test"
#run_as_builder "bazelisk test --test_output=all //src/test/java/com/code_intelligence/jazzer/instrumentor:code_marker_instrumentation_test2 --test_filter=testFuzzerTestOneInputSinkpoint "


#OUT_DIR=./out
OUT_DIR=/classpath/atl-libafl-jazzer

rm -rf ${OUT_DIR} && mkdir -p ${OUT_DIR}

cp bazel-bin/jazzer_release.tar.gz ${OUT_DIR}/
cp bazel-out/k8-opt/bin/src/main/java/com/code_intelligence/jazzer/utils/libunsafe_provider.jar ${OUT_DIR}/
cp bazel-bin/src/main/java/com/code_intelligence/jazzer/jazzer_standalone_deploy.jar ${OUT_DIR}/
cp bazel-out/k8-opt/bin/deploy/jazzer-api-project.jar ${OUT_DIR}/ 
(cd ${OUT_DIR}/ && tar -xzvf jazzer_release.tar.gz && rm jazzer_standalone.jar && rm jazzer_release.tar.gz && cd -)
