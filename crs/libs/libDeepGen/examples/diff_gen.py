#!/usr/bin/env python3

import subprocess
import yaml
import logging
import argparse
import asyncio
from pathlib import Path

from libDeepGen.engine import DeepGenEngine
from libDeepGen.submit import MockSubmit, LocalFSSubmit, ZeroMQSubmit
from libDeepGen.tasks import DiffAnalysisTask
from libDeepGen.tasks.script_loader import ScriptLoaderTask
from libAgents.utils import Project

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


def load_config(oss_fuzz_path, project_name):
    project_yaml = oss_fuzz_path / 'projects' / project_name / 'project.yaml'
    if not project_yaml.exists():
        raise ValueError(f'Could not find {project_yaml}')
    
    with open(project_yaml) as f:
        project_dict = yaml.safe_load(f)

    if "main_repo" not in project_dict:
        raise ValueError(f'Unable to find main_repo key in {project_yaml}')
    
    return project_dict

def get_src_dir(oss_fuzz_path, project_name, dst_dir):
    """Fetch or clone the repository for the given project name."""

    project_dict = load_config(oss_fuzz_path, project_name)
    main_repo = project_dict["main_repo"]

    repo_path = Path(dst_dir) / project_name
    if not repo_path.exists():
        subprocess.run(["git", "clone", main_repo, repo_path], check=True)

    return repo_path

# Usage: python3.12 examples/any_harness_engine_client.py --lang java --submit zmq [--script-load-path path/to/script.py]

async def main():
    parser = argparse.ArgumentParser(description='General Harness Seed Generator Engine Client with LibAgents')
    parser.add_argument('--cores', type=int, nargs='+', default=[1],
                        help='CPU core IDs to use (default: 1)')
    parser.add_argument('--runtime', type=int, default=10,
                        help='Runtime in seconds (default: 10)')
    parser.add_argument('--model', type=str, default='gpt-4.1',
                        help='Model to use for generation (default: gpt-4.1)')
    parser.add_argument('--submit', type=str, default='mock',
                        help='Submit mode (default: mock)')
    parser.add_argument('--lang', type=str, help='c or java')
    parser.add_argument('--add-delay', type=int, default=1,
                        help='Delay in seconds before adding task (default: 1)')
    parser.add_argument('--script-load-path', '-s', type=str, default='',
                        help='Path to a seed generation script to load directly (default: empty to generate new script)')
    args = parser.parse_args()

    if args.model == "gemini":
        args.model = "gemini-2.5-pro"
    elif args.model == "claude":
        args.model = "claude-opus-4-20250514"
    elif args.model == "grok":
        args.model = "grok-3-beta"
    
    this_dir = Path(__file__).parent.parent
    print(f"Using this directory: {this_dir}")

    workdir = this_dir / "workdir"
    workdir.mkdir(parents=True, exist_ok=True)

    if args.lang == "c":
        home_dir = this_dir / "oss-fuzz"
        project_name = "aixcc/c/r2-sqlite3-diff-1"
        local_repo_dir = get_src_dir(home_dir, project_name, this_dir / "cloned-repos")
        harness_name = "customfuzz3"
        entry_func = "LLVMFuzzerTestOneInput"
    elif args.lang == "java":
        home_dir = this_dir / "cps"
        project_name = "aixcc/jvm/rdf4j"
        local_repo_dir = this_dir / "cps/build/repos/aixcc/jvm/rdf4j"
        harness_name = "Rdf4jOne"
        entry_func = "fuzzerTestOneInput"
    else:
        raise ValueError(f"Unsupported language: {args.lang}, and please use --lang [c or java]")

    bundle = Project(
        oss_fuzz_home=home_dir,
        project_name=project_name,
        local_repo_path=local_repo_dir,
    ).prepare_project_bundle(workdir) # pack the source code and fuzz-tooling into a bundle

    harness_path = bundle.harness_path_by_name(harness_name)

    logger.info(f"Original repo_path: {local_repo_dir}")
    logger.info(f"Bundled repo_path: {bundle.repo_path}")
    logger.info(f"Harness path: {harness_path}")

    # Create weighted models dictionary
    weighted_models = {
        "gemini-2.5-pro": 20,
        "claude-opus-4-20250514": 40,
    }

    # Determine whether to create a script loader task or a seed generation task
    if args.script_load_path:
        # Load script from the specified file
        try:
            script_path = Path(args.script_load_path)
            if not script_path.exists():
                raise FileNotFoundError(f"Script file not found: {args.script_load_path}")
            
            with open(script_path, 'r') as f:
                script_content = f.read()
            
            # Create a script loader task
            task = ScriptLoaderTask(
                script_content=script_content,
                harness_name=harness_name,
                label=script_path.name,
                priority=1,
                dev_attempts=1,
                dev_cost=0.0,  # No generation cost for loading scripts
                num_repeat=1
            )
            logger.info(f"Created ScriptLoaderTask with script from: {args.script_load_path}")
        except Exception as e:
            logger.error(f"Error loading script from {args.script_load_path}: {e}")
            raise
    else:
        # Create a seed generation task
        task = DiffAnalysisTask(
            project_bundle=bundle,
            harness_id=harness_name,
            weighted_models=weighted_models,
            priority=1,
            dev_attempts=1,
            dev_cost=5.0,
            num_repeat=1,
            cache_type="disk",
            cache_expire_time=1800,
        )
        logger.info("Created OneShotTask to generate new script")
    
    # Track seed counts per script
    script_seed_counts = {}
    last_seed_counts = {}
    
    # Create a custom Submit class to track seed counts
    class SeedCountingMockSubmit(MockSubmit):
        async def request_seed_submit(self, proc_id, script_id, script, seed_ids):
            # Call parent method to handle actual submission
            await super().request_seed_submit(proc_id, script_id, script, seed_ids)
            if seed_ids:
                script_id = script.sha256
                script_seed_counts[script_id] = script_seed_counts.get(script_id, 0) + len(seed_ids)
                if script_seed_counts[script_id] - last_seed_counts.get(script_id, 0) >= 3000:
                    logger.info(f"MockSubmit Script {script_id} generated {script_seed_counts[script_id]} seeds.")
                    last_seed_counts[script_id] = script_seed_counts[script_id]

    class SeedCountingLocalFSSubmit(LocalFSSubmit):
        async def request_seed_submit(self, proc_id, script_id, script, seed_ids):
            # Call parent method to handle actual submission
            await super().request_seed_submit(proc_id, script_id, script, seed_ids)
            if seed_ids:
                script_id = script.sha256
                script_seed_counts[script_id] = script_seed_counts.get(script_id, 0) + len(seed_ids)
                if script_seed_counts[script_id] - last_seed_counts.get(script_id, 0) >= 3000:
                    logger.info(f"LocalFSSubmit Script {script_id} generated {script_seed_counts[script_id]} seeds.")
                    last_seed_counts[script_id] = script_seed_counts[script_id]

    class SeedCountingZeroMQSubmit(ZeroMQSubmit):
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
        logger.info(f"Adding task: {task.get_label()}")
        task_id = await engine.add_task(task)
        if task_id:
            logger.info(f"Successfully added task with ID: {task_id}")
        else:
            logger.error("Failed to add task")

    logger.info("Starting DeepGenEngine with Any Harness task...")
    logger.info(f"Using weighted models: {weighted_models}")

    submit_cls = None 
    if args.submit == "mock":
        submit_cls = SeedCountingMockSubmit
    elif args.submit == "local":
        submit_cls = SeedCountingLocalFSSubmit
    elif args.submit == "zmq":
        submit_cls = SeedCountingZeroMQSubmit

    try:
        async with DeepGenEngine(
            core_ids=args.cores,
            submit_class=submit_cls,
            n_exec=500,
            task_para=4  # Number of parallel tasks
        ) as engine:
            # Start task addition coroutine
            add_task_coro = add_task_after_delay(engine, task, args.add_delay)
            
            # Run the engine with an empty task list, and the add_task coroutine
            await asyncio.gather(
                engine.run(time_limit=args.runtime),
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