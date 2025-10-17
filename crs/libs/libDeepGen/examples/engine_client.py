#!/usr/bin/env python3

import logging
import asyncio
from pathlib import Path

from libDeepGen.engine import DeepGenEngine
from libDeepGen.submit import MockEnsemblerSubmit
from libDeepGen.tasks.task_base import Task
from libDeepGen.developers.developer_base import Developer

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


class SimpleTask(Task):
    def __init__(self):
        super().__init__(
            cp_name="simple-example",
            cp_src=Path("./"),
            fuzz_tooling_src=Path("./"),
            harness_src=Path("./example_harness.c"),
            harness_entrypoint_func="LLVMFuzzerTestOneInput",
            dev_attempts=3,
            dev_cost=10.0
        )
    
    def get_cp_lang(self) -> str:
        return "python"
    
    def desc_to_developer(self) -> str:
        return """
Write a python function (gen_one_seed) that returns b"Hello, World!" (in bytes).

You need to put the script inside the <script></script> tag.

For example:
<script>
def gen_one_seed():
    return xxx
</script>
"""
    
    def post_process(self, script: str) -> str:
        # Extract content between <script> and </script> tags
        print("script: ", script)
        script_start = script.find("<script>")
        script_end = script.find("</script>")
        if script_start != -1 and script_end != -1:
            # Return the extracted script content directly
            return script[script_start + len("<script>"):script_end].strip()
        return None


class MockDeveloper(Developer):
    def __init__(self, model="mock-model"):
        super().__init__(model)
        self.gen_count = 0
    
    async def async_gen(self, task) -> tuple[str, float]:
        self.gen_count += 1
        script_number = self.gen_count
        
        content = f"""
<script>
import time
def gen_one_seed():
    # Add CPU burning code (runs for < 0.1s)
    start = time.time()
    counter = 0
    while time.time() - start < 0.05:
        counter += 1
        # Do some computational work
        for i in range(1000):
            _ = i * i
    
    return b"Hello from Script {script_number}! Burned CPU for " + str(counter).encode()
</script>
"""
        # Extract and return the content directly
        processed_content = task.post_process(content)
        # Token cost for tracking
        token_cost = 0
        return processed_content, token_cost


async def main():
    # Define cores to use
    core_ids = [0, 1, 2, 3]
    
    # Create a task
    task = SimpleTask()
    
    # Track seed counts per script
    script_seed_counts = {}
    
    # Create a custom Submit class to track seed counts
    class TrackingSubmit(MockEnsemblerSubmit):
        def request_seed_submit(self, proc_id, script_id, script, seed_ids):
            if seed_ids:
                script_id = script.sha256
                script_seed_counts[script_id] = script_seed_counts.get(script_id, 0) + len(seed_ids)
            # Call parent method to handle actual submission
            super().request_seed_submit(proc_id, script_id, script, seed_ids)
    
    # Run the engine
    logger.info("Starting DeepGenEngine...")
    with DeepGenEngine(core_ids=core_ids, model="mock-model", submit_class=TrackingSubmit, n_exec_per_task=100) as engine:
        # Add a developer
        engine.add_developer(MockDeveloper(model="mock-model"))
        
        # Run the engine
        await engine.run(
            tasks=[task],
            time_limit=10  # Run for 10 seconds
        )
    
    # Print summary of seed counts
    logger.info("Engine execution completed.")
    logger.info("Seed count summary:")
    for script_id, count in script_seed_counts.items():
        logger.info(f"Script {script_id}: {count} seeds")


if __name__ == "__main__":
    asyncio.run(main())