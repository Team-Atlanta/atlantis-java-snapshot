#!/use/bin/env python3

import os
import shutil
import subprocess
import time

from pathlib import Path

OSS_FUZZ_PROJ_DIR = Path("/oss-fuzz-proj")
CRS_PROJ_DIR = Path("/out/crs/proj")
OSS_SRC_DIR = Path(os.getenv("SRC", "/src"))
CRS_SRC_DIR = Path("/out/crs/src")

def run_ossfuzz_build():
    env = os.environ.copy()
    subprocess.run(["/usr/local/bin/compile"], env=env, check=True)

def prepare_crs_src():
    if CRS_SRC_DIR.exists():
        shutil.rmtree(CRS_SRC_DIR)
    shutil.copytree(OSS_FUZZ_PROJ_DIR, CRS_PROJ_DIR, symlinks=True)
    shutil.copytree(OSS_SRC_DIR, CRS_SRC_DIR, symlinks=True)

def main():
    run_ossfuzz_build()
    prepare_crs_src()

if __name__ == "__main__":
    main()