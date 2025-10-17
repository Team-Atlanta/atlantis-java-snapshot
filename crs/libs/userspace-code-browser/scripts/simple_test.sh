#!/bin/sh

# check whether sandbox/vlc directory exists
if [ ! -d "sandbox/vlc" ]; then
    # clone vlc depth 1 from github
    git clone --depth 1 https://github.com/videolan/vlc.git sandbox/vlc
fi

# if ./project_db exists, rm -rf
if [ -d "./project_db" ]; then
    rm -rf project_db
fi

cargo run --release -- build sandbox/vlc
cargo run --release -- definition aout_volume_New
cargo run --release -- xref vlc_custom_create
