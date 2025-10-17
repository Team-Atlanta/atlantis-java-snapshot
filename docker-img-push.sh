#!/bin/bash
set -e

if [ "$#" -ne 2 ]; then
  echo "Usage: $0 <registry-url> <image-tag>"
  exit 1
fi

IMG_NAME="crs-java"
REGISTRY="$1"
IMG_TAG="$2"

docker image tag "${IMG_NAME}" "${REGISTRY}/${IMG_NAME}:${IMG_TAG}"
docker image push "${REGISTRY}/${IMG_NAME}:${IMG_TAG}"
