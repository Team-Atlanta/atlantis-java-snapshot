#!/bin/bash

if [ -n "$1" ]; then
    export PREFERRED_PROVIDER="$1"
else
    export PREFERRED_PROVIDER="google"
fi
uv run uvicorn anthropic_proxy_server:app --host 0.0.0.0 --port 8082 --reload
