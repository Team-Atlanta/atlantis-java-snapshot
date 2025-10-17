#!/bin/bash

set -x
set -e
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# Usage: ./run.sh <database_path> <json_output_path>

if [ $# -ne 2 ]; then
    echo "Usage: $0 <database_path> <json_output_path>"
    echo "Example: $0 test-db results.json"
    exit 1
fi

DATABASE_PATH="$1"
JSON_OUTPUT="$2"

cd "$SCRIPT_DIR"

# Create temporary files for BQRS and raw JSON output
TEMP_BQRS=$(mktemp --suffix=.bqrs)
trap "rm -f $TEMP_BQRS" EXIT

# Intermediate JSON file for decoding
interim_json="${JSON_OUTPUT%.json}_raw.json"

codeql query run --database="$DATABASE_PATH" sinks-pack/queries/sinks.ql --output="$TEMP_BQRS"

echo
# Decode to temporary JSON file first
codeql bqrs decode --format=json --output="$interim_json" "$TEMP_BQRS"
#codeql bqrs decode "$TEMP_BQRS"

echo
echo "Transforming results to coordinate format..."
# Transform the temporary JSON to the final coordinate format
python3 scripts/transform_results.py "$interim_json" "$JSON_OUTPUT"
