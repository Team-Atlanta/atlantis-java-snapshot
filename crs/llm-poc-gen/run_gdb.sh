#!/bin/bash
set -e

if [ $# -lt 4 ]; then
  exit 1
fi

BASEDIR=$(dirname $0)

BINARY=$1
INPUT=$2
GDB_CMD=$3
shift 3

BREAKPOINTS=()
SRC_DIRS=()
SRC_MODE=0

for arg in "$@"; do
  if [[ "$arg" == "--dir" ]]; then
    SRC_MODE=1
    continue
  fi

  if [[ $SRC_MODE -eq 1 ]]; then
    SRC_DIRS+=("$arg")
  else
    BREAKPOINTS+=("$arg")
  fi
done

# === GDB command script ===
echo "set pagination off" > "$GDB_CMD"
echo "set filename-display absolute" >> "$GDB_CMD"

for dir in "${SRC_DIRS[@]}"; do
  echo "directory $dir" >> "$GDB_CMD"
done

for bp in "${BREAKPOINTS[@]}"; do
  echo "break $bp" >> "$GDB_CMD"
done

echo "run $INPUT" >> "$GDB_CMD"
echo "while 1" >> "$GDB_CMD"
echo "  continue" >> "$GDB_CMD"
echo "end" >> "$GDB_CMD"
echo "quit" >> "$GDB_CMD"

# === Run GDB ===
gdb -q -batch -x "$GDB_CMD" --args "$BINARY" -runs=1 "$INPUT"
