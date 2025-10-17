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

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
CRS_HOME=$(realpath $SCRIPT_DIR/../..)
MODULE_BAZEL=${SCRIPT_DIR}/MODULE.bazel

# Function to update a jar file and return its SHA256 checksum
update_jar() {
    local src_jar=$1
    local dest_jar=$2

    if [ ! -f "$src_jar" ]; then
        echo "Jar not found at $src_jar" >&2
        exit 1
    fi

    cp "$src_jar" "$dest_jar"

    # Calculate and return SHA256 checksum
    sha256sum "$dest_jar" | cut -d ' ' -f 1
}

# Function to update SHA256 checksum in MODULE.bazel
update_module_bazel() {
    local name=$1
    local sha256=$2

    # Use awk to find the line number of the SHA256 entry
    local line=$(grep -n "name = \"$name\"" $MODULE_BAZEL | cut -d ':' -f 1)
    line=$((line + 1))  # Move to the next line which contains the sha256

    # Update the SHA256 checksum using the line number
    sed -i "${line}s/sha256 = \"[^\"]*\"/sha256 = \"${sha256}\"/" $MODULE_BAZEL

    echo "  $name: $sha256"
}

# Function to update Soot
update_soot() {
    local src_jar=${CRS_HOME}/prebuilt/atl-soot/target/sootclasses-trunk.jar
    local dest_jar=${SCRIPT_DIR}/third_party/soot/soot-4.7.0-atlantis.jar

    local sha256=$(update_jar "$src_jar" "$dest_jar")
    update_module_bazel "org_soot-oss_soot" "$sha256"
}

# Function to update Static Analysis
update_static_analysis() {
    local src_jar=${CRS_HOME}/static-analysis/target/static-analysis-1.0.jar
    local dest_jar=${SCRIPT_DIR}/third_party/static-analysis/static-analysis-1.0.jar

    local sha256=$(update_jar "$src_jar" "$dest_jar")
    update_module_bazel "atlantis_static-analysis" "$sha256"
}

# Function to update ASM jars
update_asm() {
    # Define ASM jar files
    local asm_jars=(
        "asm:org_ow2_asm_asm"
        "asm-commons:org_ow2_asm_asm_commons"
        "asm-tree:org_ow2_asm_asm_tree"
        "asm-util:org_ow2_asm_asm_util"
    )

    for jar_info in "${asm_jars[@]}"; do
        IFS=':' read -r jar_name module_name <<< "$jar_info"

        local src_jar=${CRS_HOME}/prebuilt/atl-asm/${jar_name}/build/libs/${jar_name}-9.8-atlantis.jar
        local dest_jar=${SCRIPT_DIR}/third_party/asm/${jar_name}-9.8-atlantis.jar

        local sha256=$(update_jar "$src_jar" "$dest_jar")
        update_module_bazel "$module_name" "$sha256"
    done
}

# Parse command line arguments
if [ $# -eq 0 ]; then
    # No arguments, update all components
    components=("soot" "static-analysis" "asm")
else
    # Update only specified components
    components=("$@")
fi

echo "Updating dependencies..."

for component in "${components[@]}"; do
    case "$component" in
        "soot")
            echo "Updating Soot..."
            update_soot
            ;;
        "static-analysis")
            echo "Updating Static Analysis..."
            update_static_analysis
            ;;
        "asm")
            echo "Updating ASM..."
            update_asm
            ;;
        *)
            echo "Unknown component: $component"
            echo "Valid components are: soot, static-analysis, asm"
            exit 1
            ;;
    esac
done

echo "MODULE.bazel updated successfully"
