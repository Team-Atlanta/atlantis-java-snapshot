#!/usr/bin/env bash


n_procs=$(seq 1 1000)
pids=()
for i in $n_procs; do
    target/release/code-browser -v xref vlc_custom_create > /dev/null &
    pids[${i}]=$!
done

# wait for all pids
for pid in ${pids[*]}; do
    wait $pid
done
