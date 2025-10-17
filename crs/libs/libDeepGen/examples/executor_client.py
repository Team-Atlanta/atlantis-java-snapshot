#!/usr/bin/env python3

import os
import time
import logging
import argparse
from pathlib import Path

from libDeepGen.executor import Executor
from libDeepGen.executor.executor import ExecTask
from libDeepGen.script import Script
from libDeepGen.ipc_utils.shm_pool import ScriptShmemPoolProducer

# Force the root logger to use stdout
root = logging.getLogger()
if not root.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    root.addHandler(handler)
root.setLevel(logging.INFO)

# Configure our module logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Debug prints to verify logging is working
print("SETUP: Logger initialized")

def main():
    parser = argparse.ArgumentParser(description='Executor Client for libDeepGen')
    parser.add_argument('--script', type=str, default='seeds_generator.txt',
                        help='Script file (relative to data/ directory) to execute (default: seeds_generator.txt)')
    parser.add_argument('--cores', type=int, nargs='+', default=[1,2,3,4],
                        help='CPU core IDs to use (default: 1,2,3,4)')
    parser.add_argument('--runtime', type=int, default=20,
                        help='Runtime in seconds (default: 20)')
    parser.add_argument('--workdir', type=str, default='./executor_workdir',
                        help='Working directory for executor (default: ./executor_workdir)')
    args = parser.parse_args()

    script_dir = os.path.dirname(__file__)
    script_path = os.path.abspath(os.path.join(script_dir, "data", args.script))
    
    # Read the script content
    with open(script_path, 'r') as f:
        script_content = f.read()
    
    script = Script.new(
        content=script_content,
        task_label="seed_generation",
        harness_name="general_harness",
        workdir=Path(args.workdir) / "scripts"
    )
    
    print('DEBUG: Starting execution process')
    # set affinity of the main process to the first core
    worker_cores = args.cores[:]
    logger.info(f"Setting CPU affinity to core {args.cores[0]} for main process, "
                f"and cores {worker_cores} for worker processes.")

    shm_label = "aaaaa"
    script_pool_name = f"test-executor-shmem-{shm_label}"
    script_pool = ScriptShmemPoolProducer(shm_name=script_pool_name, item_num=16, create=True)
    script_id = script_pool.add_script(script)
    logger.info(f"Added script to pool with ID: {script_id}")

    workdir = Path(args.workdir)

    logger.info(f"Using working directory: {workdir}")
    logger.info(f"Initializing executor with CPU cores: {worker_cores}")
    
    with Executor(shm_label, script_pool_name, worker_cores, workdir=workdir, stat_rb_slot_bytes=4096, n_exec_per_task=400) as executor:

        exec_task = ExecTask.from_script(script_id=script_id, script=script)
        
        # Preload tasks before starting the executor
        for _ in range(100000):
            executor.try_add_task(exec_task)

        logger.info("Starting executor...")
        executor.start()

        start_time = time.time()
        total_executions = 0
        total_valid_seeds = 0
        total_gen_seeds = 0
        total_traffic = 0

        logger.info(f"Running for {args.runtime} seconds...")

        last_log_time = start_time
        period_executions = 0
        period_valid_seeds = 0
        period_gen_seeds = 0
        
        try:
            while time.time() - start_time < args.runtime:
                executor.try_add_task(exec_task)
                
                stats = executor.try_get_stats()
                for stat in stats:
                    total_executions += 1
                    period_executions += 1
                    
                    valid_seed_count = len(stat.seed_ids) if hasattr(stat, 'seed_ids') and stat.seed_ids else 0
                    gen_seed_count = stat.ttl_gen_seeds
                    total_traffic += stat.ttl_traffic
                    total_valid_seeds += valid_seed_count
                    total_gen_seeds += gen_seed_count
                    period_valid_seeds += valid_seed_count
                    period_gen_seeds += gen_seed_count
                
                cur_time = time.time()
                elapsed_period = cur_time - last_log_time
                
                if elapsed_period >= 1.0:
                    period_rate = period_executions / elapsed_period if elapsed_period > 0 else 0
                    
                    logger.info(f"Period: {period_executions} executions, {period_valid_seeds}/{period_gen_seeds} seeds in {elapsed_period:.2f}s, "
                              f"Rate: {period_rate:.2f} exec/s")
                    
                    last_log_time = cur_time
                    period_executions = 0
                    period_valid_seeds = 0
                    period_gen_seeds = 0

        except KeyboardInterrupt:
            logger.info("Execution interrupted by user.")

        finally:
            end_time = time.time()
            elapsed = end_time - start_time
            exec_rate = total_executions / elapsed if elapsed > 0 else 0
            valid_seed_rate = total_valid_seeds / elapsed if elapsed > 0 else 0
            gen_seed_rate = total_gen_seeds / elapsed if elapsed > 0 else 0
            
            logger.info("=" * 50)
            logger.info(f"Execution completed after {elapsed:.2f} seconds")
            logger.info(f"Total executions: {total_executions}")
            logger.info(f"Total seeds: {total_valid_seeds}/{total_gen_seeds} (valid/gen)")
            logger.info(f"Execution rate: {exec_rate:.2f} exec/s")
            logger.info(f"Seed generation rates: {valid_seed_rate:.2f}/{gen_seed_rate:.2f} (valid/gen) seeds/s")
            logger.info(f"Total traffic: {total_traffic/(1024 * 1024 * 1024)} GB")
            logger.info("=" * 50)

            logger.info("Stopping executor...")
            executor.stop()
    
    try:
        workdir.rmdir()
        logger.info(f"Working directory {workdir} removed.")
    except OSError as e:
        logger.warning(f"Could not remove working directory {workdir} with error {e}.")

if __name__ == "__main__":
    main()