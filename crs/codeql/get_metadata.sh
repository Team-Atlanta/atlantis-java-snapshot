#!/bin/bash

set -e
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# Usage: ./get_metadata.sh <sink_id>

if [ $# -ne 1 ]; then
    echo "Usage: $0 <sink_id>"
    echo "Example: $0 'Sink: java.io; File; false; <init>; (String); ; Argument[0]; path-injection; manual'"
    exit 1
fi

SINK_ID="$1"

cd "$SCRIPT_DIR"

# Retrieve metadata for the given sink ID
python3 scripts/get_metadata.py "$SINK_ID"
