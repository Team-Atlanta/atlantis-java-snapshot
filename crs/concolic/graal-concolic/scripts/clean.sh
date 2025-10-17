#!/bin/bash
docker compose run --rm espresso-dev bash -c "pushd /graal-jdk/espresso; mx clean"
docker compose run --rm espresso-dev find /graal-jdk/ -name mxbuild -type d -exec rm -rf {} \;
docker volume rm mx_cache
