#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Define the directory containing the scripts
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"

# List of scripts to run
scripts=(
  "sanity-check.py"
  "ls-cwd.py"
  "ls-non-exisit.py"
  "diff_analyze.py"
  "read-etc-passwd.py"
  "grep-answer-plugin.py"
  "grep-sed.py"
  "xref-ngx-decode.py"
  "simple-coding.py"
  "simple-coding-model-override.py"
)

# Loop through the scripts and run them with uv
for script in "${scripts[@]}"; do
  echo "Running $script..."
  uv run python "$SCRIPT_DIR/$script"
  echo "$script finished successfully."
  echo "----------------------------------------"
done

echo "All example scripts executed successfully."
