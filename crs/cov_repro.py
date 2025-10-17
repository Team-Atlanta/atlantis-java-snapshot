#!/usr/bin/env python3.12

import os
import sys
import re
import shutil
import asyncio
import traceback
from pathlib import Path

def parse_cp_and_harness(fuzz_path):
    """Parse CP name and harness name from fuzz path."""
    pattern = r'.*/HarnessRunner/(.+)/([^/]+)/fuzz$'
    match = re.match(pattern, fuzz_path)
    if not match:
        raise ValueError(f"Path doesn't match expected pattern: {fuzz_path}")
    cp_name = match.group(1)
    harness_name = match.group(2)
    return cp_name, harness_name

async def setup_repro_corpus(fuzz_dir):
    """Setup repro directory and collect corpus files."""
    repro_dir = os.path.join(fuzz_dir, "repro")
    
    if os.path.exists(repro_dir):
        await asyncio.to_thread(shutil.rmtree, repro_dir)
    os.makedirs(repro_dir)
    
    repro_corpus_dir = os.path.join(repro_dir, "corpus_dir")
    os.makedirs(repro_corpus_dir)
    
    for item in os.listdir(fuzz_dir):
        item_path = os.path.join(fuzz_dir, item)
        if os.path.isdir(item_path) and item != "repro":
            corpus_path = os.path.join(item_path, "corpus_dir")
            if os.path.exists(corpus_path):
                print(f"  Copying corpus from {corpus_path}")
                process = await asyncio.create_subprocess_exec(
                    "rsync", "-a", f"{corpus_path}/", f"{repro_corpus_dir}/",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
                if process.returncode != 0:
                    raise Exception(f"rsync failed: {stderr.decode()}")
    
    return repro_dir, repro_corpus_dir

def get_initial_timestamp(fuzz_dir):
    """Find initial timestamp from any subfolder/command.sh mtime."""
    for item in os.listdir(fuzz_dir):
        if item == "repro":
            continue
        command_sh = os.path.join(fuzz_dir, item, "command.sh")
        if os.path.exists(command_sh):
            return int(os.path.getmtime(command_sh))
    raise FileNotFoundError(f"No command.sh found in subdirectories of {fuzz_dir}")

async def run_coverage_repro(cp_name, harness_name, repro_dir, corpus_dir, timestamp):
    """Run the fuzzer with coverage reproduction."""
    env = os.environ.copy()
    env["ATLJAZZER_COV_REPRO_BASE_TIMESTAMP"] = str(timestamp)
    env["RUN_FUZZER_MODE"] = "interactive"
    env["FUZZING_ENGINE"] = "libfuzzer"
    env["OUT"] = f"/out-{os.path.basename(cp_name)}"
    env["JAZZER_DIR"] = os.environ.get("ATL_JAZZER_DIR", "/classpath/atl-jazzer")
    env["JACOCO_COV_DUMP_PERIOD"] = "300"
    
    result_json = os.path.join(repro_dir, "result.json")
    fuzz_log = os.path.join(repro_dir, "fuzz.log")
    jacoco_exec = os.path.join(repro_dir, "jacoco.exec")
    
    cmd = (
        f"run_fuzzer {harness_name} "
        f"--agent_path=/classpath/atl-jazzer/jazzer_standalone_deploy.jar "
        f"-runs=0 -rss_limit_mb=16384 -len_control=0 --keep_going=100000 "
        f"--coverage_dump={os.path.abspath(jacoco_exec)} "
        f"{corpus_dir}"
    )
    
    full_cmd = (
        f'{cmd} 2>&1 | ts "%s" | '
        f'python3.12 -u /app/crs-cp-java/javacrs_modules/scripts/jazzer_postprocessing.py '
        f'-o {result_json} --rolling-log {fuzz_log}'
    )
    
    print(f"  Running: {full_cmd}")
    
    process = await asyncio.create_subprocess_shell(
        full_cmd,
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT
    )
    
    while True:
        line = await process.stdout.readline()
        if not line:
            break
        sys.stdout.buffer.write(line)
        sys.stdout.flush()
    
    ret = await process.wait()
    if ret != 0:
        raise Exception(f"Command failed with return code {ret}")
    
    return result_json, fuzz_log

async def process_fuzz_dir(fuzz_dir, semaphore):
    """Process a single fuzz directory for coverage reproduction."""
    async with semaphore:
        print(f"\nProcessing: {fuzz_dir}")
        
        try:
            cp_name, harness_name = parse_cp_and_harness(fuzz_dir)
            print(f"  CP: {cp_name}, Harness: {harness_name}")
            
            repro_dir, corpus_dir = await setup_repro_corpus(fuzz_dir)
            print(f"  Created repro dir: {repro_dir}")
            
            timestamp = get_initial_timestamp(fuzz_dir)
            print(f"  Initial timestamp: {timestamp}")
            
            result_json, fuzz_log = await run_coverage_repro(cp_name, harness_name, repro_dir, corpus_dir, timestamp)
            print(f"  Generated: {result_json}, {fuzz_log}")
            
        except Exception as e:
            print(f"  ERROR: {e}")
            traceback.print_exc()
            return False
        
        return True

async def async_main():
    if len(sys.argv) < 3:
        print("Usage: cov_repro.py <repro_dir> <parallelism> [fuzz_dir1] [fuzz_dir2] ...")
        sys.exit(1)
    
    repro_dir = sys.argv[1]
    
    try:
        parallelism = int(sys.argv[2])
        if parallelism < 1:
            print(f"Invalid parallelism value: {sys.argv[2]} (must be >= 1)")
            sys.exit(1)
    except ValueError:
        print(f"Invalid parallelism value: {sys.argv[2]} (must be an integer)")
        sys.exit(1)
    
    fuzz_dirs = sys.argv[3:] if len(sys.argv) > 3 else []
    
    print(f"Coverage reproduction started")
    print(f"Reproduction directory: {repro_dir}")
    print(f"Parallelism: {parallelism}")
    print(f"Found {len(fuzz_dirs)} fuzz directories (before dedup)")
    
    unique_fuzz_dirs = list(dict.fromkeys(fuzz_dirs))
    if len(unique_fuzz_dirs) != len(fuzz_dirs):
        print(f"After deduplication: {len(unique_fuzz_dirs)} unique fuzz directories")
    else:
        print(f"No duplicates found")
    
    print(f"Processing {len(unique_fuzz_dirs)} fuzz directories")
    
    semaphore = asyncio.Semaphore(parallelism)
    
    tasks = [process_fuzz_dir(fuzz_dir, semaphore) for fuzz_dir in unique_fuzz_dirs]
    
    results = await asyncio.gather(*tasks, return_exceptions=False)
    
    success_count = sum(1 for r in results if r)
    
    print(f"\nCompleted: {success_count}/{len(unique_fuzz_dirs)} successful")

def main():
    asyncio.run(async_main())

if __name__ == "__main__":
    main()