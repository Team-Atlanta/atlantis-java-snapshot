#!/usr/bin/env bash
set -euo pipefail

MAX_RETRIES=5
SLEEP_SECONDS=5
BACKOFF_FACTOR=3

SCRIPT_DIR="$(dirname "$(realpath "${BASH_SOURCE[0]}")")"
CRS_SRC="${SCRIPT_DIR}/crs"
IMG_NAME="crs-java"

docker_build_with_retry() {
  local attempt=0
  local wait=${SLEEP_SECONDS}

  while :; do
    attempt=$(( attempt + 1 ))
    echo "[$(date +'%F %T')] docker build attempt ${attempt} …"
    if docker build \
      --file "${CRS_SRC}/Dockerfile.crs" \
      --tag  "${IMG_NAME}" \
      "${CRS_SRC}"; then
      echo "[$(date +'%F %T')] build succeeded on attempt ${attempt}"
      return 0
    fi

    if [[ $attempt -gt $MAX_RETRIES ]]; then
      echo "[$(date +'%F %T')] build failed after $MAX_RETRIES retries, aborting."
      return 1
    fi

    echo "[$(date +'%F %T')] build failed, will retry in ${wait}s …"
    sleep "$wait"

    wait=$(( wait * BACKOFF_FACTOR ))
  done
}

docker_build_with_retry
