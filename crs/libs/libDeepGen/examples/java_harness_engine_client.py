#!/usr/bin/env python3

import asyncio
import argparse
import logging

from pathlib import Path

from libDeepGen.engine import DeepGenEngine
from libDeepGen.submit import ZeroMQSubmit
from libDeepGen.tasks.harness_seedgen import JavaHarnessSeedGen
from libDeepGen.developers.libagents import LibAgentsDeveloper

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


async def main():
    parser = argparse.ArgumentParser(description='Java Harness Seed Generator Engine Client with LibAgents')
    parser.add_argument('--cores', type=int, nargs='+', default=[0, 1, 2, 3],
                        help='CPU core IDs to use (default: 0,1,2,3)')
    parser.add_argument('--runtime', type=int, default=30,
                        help='Runtime in seconds (default: 1000)')
    parser.add_argument('--model', type=str, default='claude-3-7-sonnet-20250219',
                        help='Model to use for generation (default: claude-3-7-sonnet-20250219)')
    parser.add_argument('--add-delay', type=int, default=1,
                        help='Delay in seconds before adding task (default: 5)')
    args = parser.parse_args()

    this_dir = Path(__file__).parent.parent

    # Create the JavaHarnessSeedGen task - we'll add this to the engine after it starts
    task = JavaHarnessSeedGen(
        cp_name="rdf4j",
        cp_src="./cps/build/repos/aixcc/jvm/rdf4j",
        fuzz_tooling_src="./cps/projects/aixcc/jvm/rdf4j",
        harness_name="Rdf4jOne",
        harness_src="./cps/projects/aixcc/jvm/rdf4j/fuzz/rdf4j-harness-one/src/main/java/com/aixcc/rdf4j/harnesses/one/Rdf4jOne.java",
        harness_entrypoint_func="fuzzerTestOneInput",
        dev_attempts=5,
        dev_cost=20.0
    )
    
    # Track seed counts per script
    script_seed_counts = {}
    last_seed_counts = {}
    
    # Create a custom Submit class to track seed counts
    class SeedCountingSubmit(ZeroMQSubmit):
        async def request_seed_submit(self, proc_id, script_id, script, seed_ids):
            # Call parent method to handle actual submission
            await super().request_seed_submit(proc_id, script_id, script, seed_ids)
            if seed_ids:
                script_id = script.sha256
                script_seed_counts[script_id] = script_seed_counts.get(script_id, 0) + len(seed_ids)
                if script_seed_counts[script_id] - last_seed_counts.get(script_id, 0) >= 3000:
                    logger.info(f"ZeroMQSubmit Script {script_id} generated {script_seed_counts[script_id]} seeds.")
                    last_seed_counts[script_id] = script_seed_counts[script_id]

    # Create a task to add the main task after a delay
    async def add_task_after_delay(engine, task, delay):
        logger.info(f"Will add task after {delay} seconds")
        await asyncio.sleep(delay)
        logger.info(f"Adding task: {task.cp_name}")
        success = await engine.add_task(task)
        if success:
            logger.info("Successfully added task")
        else:
            logger.error("Failed to add task")

    # Run the engine
    logger.info("Starting DeepGenEngine with dynamic task addition...")
    logger.info(f"Using model: {args.model}")

    try:
        async with DeepGenEngine(core_ids=args.cores, model=args.model, 
                          submit_class=SeedCountingSubmit, n_exec=500) as engine:
            # Create and add the LibAgentsDeveloper - still need to add one for initialization
            developer = LibAgentsDeveloper(model=args.model)
            engine.add_developer(developer)
            
            # Start task addition coroutine
            add_task_coro = add_task_after_delay(engine, task, args.add_delay)
            
            # Run the engine with an empty task list, and the add_task coroutine
            await asyncio.gather(
                engine.run(tasks=[], time_limit=args.runtime),
                add_task_coro
            )
        
        # Print summary of seed counts
        logger.info("Engine execution completed.")
        logger.info("Seed count summary:")
        for script_id, count in script_seed_counts.items():
            logger.info(f"Script {script_id}: {count} seeds")
            
    except Exception as e:
        logger.error(f"Error during execution: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
