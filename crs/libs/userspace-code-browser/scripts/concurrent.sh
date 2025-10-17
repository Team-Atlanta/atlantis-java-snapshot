#!/usr/bin/env bash


n_procs=$(seq 1 100)
pids=()
for i in $n_procs; do
    # target/release/code-browser -c xref vlc_custom_create > /dev/null &
    target/release/code-browser -c definition aout_volume_New &
    pids[${i}]=$!
done

# wait for all pids
for pid in ${pids[*]}; do
    wait $pid
done
