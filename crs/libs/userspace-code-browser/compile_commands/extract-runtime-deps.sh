#!/bin/sh

set -eu

all_paths=""
for b in $@; do
    BIN=$(which $b)
    # bindir=$(echo "$BIN" | cut -d/ -f1-4)
    runs=$(readelf -d $BIN | grep \(RUNPATH\) | sed 's;^.*\[\(.*\)\].*$;\1;' | tr ':' ' ' || "")
    store_paths=$(nix-store -q --references $BIN 2>/dev/null || :)
    all_paths=$(echo $all_paths; echo $store_paths; echo $BIN)
    for r in $runs $store_paths; do
        store_paths=$(nix-store -q --references $r 2>/dev/null || :)
        all_paths=$(echo $all_paths; echo $store_paths; echo $r)
    done
done

trim_paths=""
for p in $all_paths; do
    trimmed=$(echo $p | cut -d/ -f1-4)
    trim_paths=$(echo $trim_paths; echo $trimmed)
done

deps=$(echo $trim_paths | tr ' ' '\n' | sort | uniq)

mkdir -p nix/store
for d in $deps; do
    base=$(basename $d)
    if ! [ -d $d ]; then
       echo "Not a directory: $d"
    elif [ -d nix/store/$base ]; then
        echo "Already exists: $d"
    else
        echo "Copying $d to nix/store/$base"
        cp -r $d nix/store/
    fi
done
