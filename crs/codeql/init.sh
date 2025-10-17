#!/bin/bash

set -e
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

cd "$SCRIPT_DIR"

# Install Python dependencies
echo "Installing Python dependencies..."
pip3 install -r requirements.txt

# Generate model and query files from sink definitions
echo "Generating CodeQL model and query files..."
python3 scripts/generate_models.py

# Install CodeQL pack
echo "Installing CodeQL pack..."
cd sinks-pack
codeql pack install

echo "Initialization complete!"
