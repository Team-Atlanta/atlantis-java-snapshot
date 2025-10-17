#!/bin/bash

# Prepare the environment for Expresso development
export LD_DEBUG=unused
echo 0 | /mx/select_jdk.py -p /graal-jdk/espresso > /dev/null

# Run the command passed from args
exec "$@"
