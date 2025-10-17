#!/usr/bin/env bash
#
# Copyright 2024 Code Intelligence GmbH
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#


# Run the benchmark given by $TEST_SUITE_LABEL, then get all "stat::number_of_executed_units: 12345"
# lines printed by libFuzzer from the logs for the tests passed in on the command line in the form
# "path/to/pkg/name" and compute statistics.
#
# Requires jq to be installed locally.

set -e

normal_targets="$1"
directed_targets="$2"

cd "$BUILD_WORKSPACE_DIRECTORY" || exit 1

compute_statistics() {
    local pattern=$1
    local targets=$2

    echo "$targets" \
        | xargs -L1 printf "bazel-testlogs/%s/test.log " \
        | xargs -L1 cat \
        | grep "^${pattern}" \
        | cut -d' ' -f2- \
        | jq -s '{values:(sort | join(" ")),minimum:min,maximum:max,average:(add/length),median:(sort|if length%2==1 then.[length/2|floor]else[.[length/2-1,length/2]]|add/2 end)}'
}

run_benchmark() {
    local targets=$1
    local suffix=$2

    echo -e "\nNumber of executed units (${suffix}):"
    compute_statistics 'stat::number_of_executed_units' "$targets"

    echo -e "\nAverage exec per sec (${suffix}):"
    compute_statistics 'stat::average_exec_per_sec' "$targets"

    echo -e "\nWall clock time to discovery (${suffix}):"
    compute_statistics 'stat::overall_time' "$targets"
}

run_bazel_test() {
    local label=$1
    # Remove the -runs limit to collect statistics even if the current run limit is too low.
    bazel test "$label" --test_arg=-runs=999999999 --cache_test_results=no
}

run_bazel_test "${TEST_SUITE_LABEL}"

# Run directed only if $DIRECTED is set
if [ -n "$DIRECTED" ]; then
    run_bazel_test "${TEST_SUITE_LABEL}_directed"
fi

run_benchmark "$normal_targets" "normal"

# Run directed benchmarks if $DIRECTED is set
if [ -n "$DIRECTED" ]; then
    run_benchmark "$directed_targets" "directed"
fi
