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


# This test verifies that Jazzer's code marker instrumentation works end-to-end,
# correctly identifying sinkpoints and generating marker hits when running with -runs=0.

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

# Create test corpus with a seed that triggers the sinkpoint
corpus_dir=$TEST_TMPDIR/corpus
mkdir -p "$corpus_dir"
cp "$(rlocation jazzer/tests/src/test/data/code_marker_test/seed1)" "$corpus_dir/"

# Create beep seed collection directory
beep_seed_dir=$TEST_TMPDIR/beep_seeds
mkdir -p "$beep_seed_dir"

echo "Running Jazzer with code marker instrumentation..."

# Run jazzer with our test class and options for code marker instrumentation
"$(rlocation jazzer/launcher/jazzer)" \
  --cp="$(rlocation jazzer/tests/CodeMarkerFuzzTarget_deploy.jar)" \
  --target_class=com.example.CodeMarkerFuzzTarget \
  -runs=1 --xcode --beep_seed_dir="$beep_seed_dir" \
  "$corpus_dir"

# Verify marker hits were generated
[[ -d "$beep_seed_dir" ]] || fail "Beep seed directory does not exist"
[[ "$(ls -A "$beep_seed_dir")" ]] || fail "No marker hits were generated"

# Display the contents of the beep seed directory for debugging
echo "Beep seed directory contents:"
ls -la "$beep_seed_dir"

# Display the contents of each file in the beep seed directory
for file in "$beep_seed_dir"/*; do
  echo "Contents of $file:"
  cat "$file"
done

# Check for marker hits for different hook types
# The markers are on our test methods rather than the actual sinkpoint methods
# This is because the instrumentation adds code marker hits to our code that calls the sinkpoints

# Exclude xcode.json as it's just metadata, not actual beep seed information
# Look only in sink-*.json files which contain the actual marker hits

# Check for XPath marker (HookType.REPLACE)
grep -q "CodeMarkerFuzzTarget.*testXPathEvaluate" "$beep_seed_dir"/sink-*.json && echo "XPath marker hit found (HookType.REPLACE)" || fail "XPath marker hit not found (HookType.REPLACE)"

# Check for deserialization marker (HookType.BEFORE/AFTER)
grep -q "CodeMarkerFuzzTarget.*testDeserialization" "$beep_seed_dir"/sink-*.json && echo "Deserialization marker hit found (HookType.BEFORE/AFTER)" || fail "Deserialization marker hit not found (HookType.BEFORE/AFTER)"

# --- Testing fuzzerTestOneInput method detection when ATLJAZZER_INFER_CPMETA_OUTPUT is set ---
echo "Testing fuzzerTestOneInput method marking when ATLJAZZER_INFER_CPMETA_OUTPUT is set..."

# Save the current beep seed directory contents for comparison
mkdir -p "$TEST_TMPDIR/orig_beep_seeds"
cp -r "$beep_seed_dir"/* "$TEST_TMPDIR/orig_beep_seeds/" || true

# Create a fresh beep seed directory for the second test
beep_seed_dir_env="$TEST_TMPDIR/beep_seeds_with_env"
mkdir -p "$beep_seed_dir_env"

# Run jazzer again with ATLJAZZER_INFER_CPMETA_OUTPUT set
echo "Running Jazzer with ATLJAZZER_INFER_CPMETA_OUTPUT=1..."
ATLJAZZER_INFER_CPMETA_OUTPUT=1 "$(rlocation jazzer/launcher/jazzer)" \
  --cp="$(rlocation jazzer/tests/CodeMarkerFuzzTarget_deploy.jar)" \
  --target_class=com.example.CodeMarkerFuzzTarget \
  -runs=1 --xcode --beep_seed_dir="$beep_seed_dir_env" \
  "$corpus_dir"

# Verify marker hits were generated
[[ -d "$beep_seed_dir_env" ]] || fail "Beep seed directory with env var does not exist"
[[ "$(ls -A "$beep_seed_dir_env")" ]] || fail "No marker hits were generated with env var"

# Display the contents of the beep seed directory for debugging
echo "Beep seed directory contents with ATLJAZZER_INFER_CPMETA_OUTPUT=1:"
ls -la "$beep_seed_dir_env"

# Check xcode.json for fuzzerTestOneInput method with cpmeta marker
echo "Checking xcode.json for fuzzerTestOneInput method with cpmeta-fuzzerTestOneInput marker..."
echo HEHEHE
cat "$beep_seed_dir_env/xcode.json" || fail "Failed to read xcode.json with env var"
echo HEHEHE
[[ -f "$beep_seed_dir_env/xcode.json" ]] || fail "xcode.json not found in beep seed directory with env var"
grep -A 10 "\"method_name\": \"fuzzerTestOneInput\"" "$beep_seed_dir_env/xcode.json" | grep -q "\"mark_desc\": \"cpmeta-fuzzerTestOneInput\"" && echo "PASS: cpmeta-fuzzerTestOneInput marker found in xcode.json" || fail "cpmeta-fuzzerTestOneInput marker not found in xcode.json when ATLJAZZER_INFER_CPMETA_OUTPUT is set"

# Check for cpmeta-*.json files (files should be named with cpmeta- prefix instead of sink-)
echo "Checking for cpmeta-*.json files..."
ls "$beep_seed_dir_env"/cpmeta-*.json &>/dev/null && echo "PASS: cpmeta-*.json files found" || fail "No cpmeta-*.json files found when ATLJAZZER_INFER_CPMETA_OUTPUT is set"

# Verify that the original run (without env var) did NOT have cpmeta-*.json files
if ls "$TEST_TMPDIR/orig_beep_seeds"/cpmeta-*.json &>/dev/null; then
  fail "Unexpected cpmeta-*.json files found in original run without ATLJAZZER_INFER_CPMETA_OUTPUT"
else
  echo "PASS: Original run without env var correctly has no cpmeta-*.json files"
fi

# --- Testing custom API sinkpoint detection when ATLJAZZER_CUSTOM_SINKPOINT_CONF is set ---
echo "Testing custom API sinkpoint detection when ATLJAZZER_CUSTOM_SINKPOINT_CONF is set..."

# Create a custom sinkpoint configuration file
custom_conf_file="$TEST_TMPDIR/custom_sinkpoints.conf"
cat > "$custom_conf_file" << EOF
# Custom API sinkpoint for CodeMarkerFuzzTarget.testCustomAPI method or its invocation
api#com/example/CodeMarkerFuzzTarget#testCustomAPI##custom-api-sinkpoint
EOF

# Create a fresh beep seed directory for the custom API test
beep_seed_dir_custom="$TEST_TMPDIR/beep_seeds_custom"
mkdir -p "$beep_seed_dir_custom"

# Run jazzer with ATLJAZZER_CUSTOM_SINKPOINT_CONF set
echo "Running Jazzer with ATLJAZZER_CUSTOM_SINKPOINT_CONF=$custom_conf_file..."
ATLJAZZER_CUSTOM_SINKPOINT_CONF="$custom_conf_file" "$(rlocation jazzer/launcher/jazzer)" \
  --cp="$(rlocation jazzer/tests/CodeMarkerFuzzTarget_deploy.jar)" \
  --target_class=com.example.CodeMarkerFuzzTarget \
  -runs=1 --xcode --beep_seed_dir="$beep_seed_dir_custom" \
  "$corpus_dir"

# Verify marker hits were generated
[[ -d "$beep_seed_dir_custom" ]] || fail "Beep seed directory for custom API test does not exist"
[[ "$(ls -A "$beep_seed_dir_custom")" ]] || fail "No marker hits were generated for custom API test"

# Display the contents of the beep seed directory for debugging
echo "Beep seed directory contents with ATLJAZZER_CUSTOM_SINKPOINT_CONF:"
ls -la "$beep_seed_dir_custom"

# Display xcode.json content
echo "Contents of xcode.json for custom API test:"
cat "$beep_seed_dir_custom/xcode.json" || fail "Failed to read xcode.json for custom API test"

# Check xcode.json for custom-api-sinkpoint marker in either testCustomAPI or its invocation
echo "Checking xcode.json for custom-api-sinkpoint marker..."
[[ -f "$beep_seed_dir_custom/xcode.json" ]] || fail "xcode.json not found in beep seed directory for custom API test"
grep -q "\"mark_desc\": \"custom-api-sinkpoint\"" "$beep_seed_dir_custom/xcode.json" && echo "PASS: custom-api-sinkpoint marker found in xcode.json" || fail "custom-api-sinkpoint marker not found in xcode.json when ATLJAZZER_CUSTOM_SINKPOINT_CONF is set"

# Check for marker files containing invocation of our custom API sinkpoint
echo "Checking for marker files related to custom API sinkpoint..."
# Look for custom-api-sinkpoint in any JSON file in the beep_seed_dir_custom
grep -q "custom-api-sinkpoint" "$beep_seed_dir_custom"/*.json && echo "PASS: custom-api-sinkpoint marker found in marker files" || fail "custom-api-sinkpoint marker not found in any marker files"

echo "Code marker workflow test passed successfully!"