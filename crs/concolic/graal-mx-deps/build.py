#!/usr/bin/env python3

import os
import sys

if len(sys.argv) != 2:
    print("Usage: {} <version-tag, e.g., v1.0.0>".format(sys.argv[0]))
    sys.exit(1)

tag = sys.argv[1]

os.system(f"sudo docker build -t ghcr.io/blue9057/graal-deps:{tag} .")
