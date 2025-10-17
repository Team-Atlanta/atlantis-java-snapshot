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


# This test verifies that Jazzer's OOFMutate functionality works end-to-end,
# able to receive seeds from ZMQ router and find crashes that are difficult
# to discover without value profile.

# --- begin runfiles.bash initialization v2 ---
# Copy-pasted from the Bazel Bash runfiles library v2.
set -uo pipefail; f=bazel_tools/tools/bash/runfiles/runfiles.bash
source "${RUNFILES_DIR:-/dev/null}/$f" 2>/dev/null || \
  source "$(grep -sm1 "^$f " "${RUNFILES_MANIFEST_FILE:-/dev/null}" | cut -f2- -d' ')" 2>/dev/null || \
  source "$0.runfiles/$f" 2>/dev/null || \
  source "$(grep -sm1 "^$f " "$0.runfiles_manifest" | cut -f2- -d' ')" 2>/dev/null || \
  source "$(grep -sm1 "^$f " "$0.exe.runfiles_manifest" | cut -f2- -d' ')" 2>/dev/null || \
  { echo>&2 "ERROR: cannot find $f"; exit 1; }; f=; set -e
# --- end runfiles.bash initialization v2 ---

function fail() {
  echo "FAILED: $1"
  exit 1
}

# Maximum time to wait for the fuzzer with OOFMutate
MAX_TIME_WITH_OOF=180  # 3 minutes

# Create test directories
corpus_dir=$TEST_TMPDIR/corpus
mkdir -p "$corpus_dir"

# Create crash log directories
logs_dir=$TEST_TMPDIR/logs
mkdir -p "$logs_dir"

echo "Running Jazzer with OOFMutate..."

# Set up router and seed directories
router_dir="$TEST_TMPDIR/router"
mkdir -p "$router_dir/seeds"
corpus_dir_oof=$TEST_TMPDIR/corpus_oof
mkdir -p "$corpus_dir_oof"

# Run with OOFMutate (but still without value profile)

# Create the crash seed that should be found by OOF Mutate
echo -ne 'Jazzer value profiling' >> "$router_dir/seeds/crash_seed"

# Get the path to the router script using Bazel runfiles
ROUTER_SCRIPT_PATH="$(rlocation jazzer/tests/router_py)"
SHM_POOL_PATH="$(rlocation jazzer/tests/shm_pool_py)"

echo "Router script: $ROUTER_SCRIPT_PATH"
echo "SHM Pool script: $SHM_POOL_PATH"

# Copy the Python files to the router directory to ensure they can find each other
cp -v "$ROUTER_SCRIPT_PATH" "$router_dir/router.py"
cp -v "$SHM_POOL_PATH" "$router_dir/shm_pool.py"

# Change to the router directory so the router can find its files
cd "$router_dir"

# Set up Python env
echo "Python version:"
python3 --version
echo "Python executable:"
which python3
python3 -m pip --version
python3 -m pip install pyzmq || fail "Failed to install required Python packages"

# Start the router in the background
echo "Starting ZMQ router for seed distribution..."
python3 ./router.py >> "$logs_dir/router.log" 2>&1 &
ROUTER_PID=$!
echo "Wait for router to start (PID: $ROUTER_PID)"
sleep 1

# Actually run the fuzzer with OOFMutate enabled
echo "Running Jazzer with OOFMutate via ZMQ router..."
ATLJAZZER_ZMQ_ROUTER_ADDR="ipc:///tmp/haha" \
ATLJAZZER_ZMQ_HARNESS_ID="oof_mutate_test" \
timeout $MAX_TIME_WITH_OOF "$(rlocation jazzer/launcher/jazzer)" \
  --cp="$(rlocation jazzer/tests/OOFMutateFuzzTarget_deploy.jar)" \
  --target_class=com.example.OOFMutateFuzzTarget \
  -use_value_profile=0 \
  -max_len=4096 \
  -len_control=0 \
  -max_total_time=10 \
  "$corpus_dir_oof" > "$logs_dir/with_oof.log" 2>&1 || true

# Kill the router
echo "Stopping router (PID: $ROUTER_PID)"
kill $ROUTER_PID || true
# Ensure any shared memory is cleaned up
rm -f /dev/shm/minimal-router-shm

echo =====
echo "Router log:"
cat "$logs_dir/router.log"
echo =====

# Output test information for debugging
echo "With OOFMutate run output (tail):"
cat "$logs_dir/with_oof.log"

# Check if crash was found (should be found with OOFMutate)
if grep -q "mustNeverBeCalled has been called" "$logs_dir/with_oof.log"; then
  echo "Test passed: Crash was found with OOFMutate, as expected"
else
  fail "With OOFMutate, should have found the crash"
fi

echo "OOF Mutate workflow test passed successfully!"
