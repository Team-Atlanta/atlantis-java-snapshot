#!/usr/bin/env bash

set -ex

LIB_PATH=$(dirname -- "$(readlink -f -- "${BASH_SOURCE[0]}")")
LIB_PATH+="/libfdp"

pip3 install "maturin >= 1.8, < 2.0"
pip3 install --force-reinstall "$LIB_PATH"
