import asyncio
import psutil
import yaml
import subprocess
import logging
import time
import queue
from multiprocessing import Process, Queue, Event
from apscheduler.schedulers.background import BackgroundScheduler
from libDeepGen.engine import DeepGenEngine
from libDeepGen.developers import PassthroughDeveloper
from libDeepGen.submit import ZeroMQSubmit
from libDeepGen.tasks import Task, GrossDiffSeedGen, GrossMapReduceSeedGen, GrossBasicSeedGen
from libAgents.utils import Project
from pathlib import Path
from typing import Dict
root = logging.getLogger()
if not root.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    root.addHandler(handler)
root.setLevel(logging.INFO)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


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

class DummyTask(Task):
    def __init__(self, bundle: Project, harness_name: str):
        super().__init__(
            bundle.name,
            bundle.repo_path,
            bundle.oss_fuzz_home,
            harness_name,
            bundle.harness_path_by_name(harness_name),
            "LLVMFuzzerTestOneInput",
            1,
            100.0,
        )
        self.bundle = bundle
        self.harness_name = harness_name

    def get_cp_lang(self):
        return "c"
    
    def desc_to_developer(self):
        return f"Generate a fuzzing harness for {self.harness_name}"
    
    async def async_run(self):
        return f"""
def gen_one_seed():
    return b"1234567890" + {bytes(self.harness_name, 'utf-8')}
"""

script_seed_counts = {}
last_seed_counts = {}    

class SeedCountingZeroMQSubmit(ZeroMQSubmit):
    async def request_seed_submit(self, proc_id, script_id, script, seed_ids):
        # Call parent method to handle actual submission
        await super().request_seed_submit(proc_id, script_id, script, seed_ids)
        if seed_ids:
            script_id = script.sha256
            script_seed_counts[script_id] = script_seed_counts.get(script_id, 0) + len(seed_ids)
            if script_seed_counts[script_id] - last_seed_counts.get(script_id, 0) >= 3000:
                logger.info(f"ZeroMQSubmit Script {script_id} generated {script_seed_counts[script_id]} seeds.") 

class Scheduler:
    def __init__(self, bundle: Project, queue: Queue):
        self.bundle = bundle
        self.mode = bundle.mode
        self.queue = queue
        self.scheduler = BackgroundScheduler()
        self.active_harness_ids: Dict[str, int] = {}
        self.weighted_models = {
            "gpt-4.1": 10,
            "o4-mini": 10,
            "o3": 10,
            "gemini-2.5-pro": 20,
            "grok-3-mini-beta": 10,
        }
        self.task_registry = {
            "GrossDiffSeedGen": {
                "class": GrossDiffSeedGen,
                "param_func": lambda ctx: {
                    "project_bundle": self.bundle, 
                    "harness_id": ctx["harness_id"], 
                    "weighted_models": self.weighted_models,
                },
                "mode": "delta",
            },
            "GrossMapReduceSeedGen": {
                "class": GrossMapReduceSeedGen,
                "param_func": lambda ctx: {
                    "project_bundle": self.bundle, 
                    "harness_id": ctx["harness_id"], 
                    "weighted_models": self.weighted_models,
                },
                "mode": "all",
            },
            "GrossBasicSeedGen": {
                "class": GrossBasicSeedGen,
                "param_func": lambda ctx: {
                    "project_bundle": self.bundle, 
                    "harness_id": ctx["harness_id"], 
                    "weighted_models": self.weighted_models,
                },
                "mode": "all",
            },
        }
        logger.info(f"available tasks: {self.get_available_tasks()}")

    def register_harness(self, harness_id: str):
        self.active_harness_ids[harness_id] = 0

    def unregister_harness(self, harness_id: str):
        if harness_id in self.active_harness_ids:
            del self.active_harness_ids[harness_id]

    def get_harness_id(self):
        if not self.active_harness_ids:
            return None
        # Sort by count (value) in ascending order
        sorted_harnesses = sorted(self.active_harness_ids.items(), key=lambda item: item[1])
        return sorted_harnesses[0][0] if sorted_harnesses else None

    def get_available_tasks(self):
        return [k for k, v in self.task_registry.items() if v.get("mode") == "all" or self.mode == v.get("mode")]

    def dispatch(self):
        if self.queue.empty():
            logger.info("Empty queue, dispatching task")
            harness_id = self.get_harness_id()
            if harness_id is None:
                logger.info("No active harnesses")
                return
            # Increment count for the chosen harness
            self.active_harness_ids[harness_id] += 1
            
            # Instead of creating and sending Task objects, send task specifications
            for task_name in self.get_available_tasks():
                # Send tuple of (task_name, harness_id) instead of instantiated Task
                self.queue.put((task_name, harness_id))
                logger.info(f"Queued task specification: {task_name} for harness {harness_id}")

    def start(self):
        self.scheduler.add_job(self.dispatch, 'interval', seconds=5)
        self.scheduler.start()
        logger.info("Scheduler started")

def worker(q: Queue, project_info):
    asyncio.run(engine_worker(q, project_info))

async def add_task_after_delay(engine, q, project_info):
    logger.info("Will add task every 10 seconds")
    
    # Recreate the project bundle in the worker process
    ossfuzz_home_dir = Path(project_info["ossfuzz_home"])
    project_name = project_info["project_name"]
    local_repo_dir = Path(project_info["local_repo_dir"])
    workdir = Path(project_info["workdir"])
    
    bundle = Project(
        oss_fuzz_home=ossfuzz_home_dir,
        project_name=project_name,
        local_repo_path=local_repo_dir,
    ).prepare_project_bundle(workdir)
    
    # Define weighted models in the worker process
    weighted_models = {
        "gpt-4.1": 10,
        "o4-mini": 10,
        "o3": 10,
        "gemini-2.5-pro": 30,
        "grok-3-mini-beta": 10,
    }
    
    try:
        while True:
            await asyncio.sleep(5)
            try:
                # Get task specification instead of task object
                task_name, harness_id = q.get_nowait()
            except queue.Empty:
                logger.info("No task to add")
                continue
                
            logger.info(f"Creating task: {task_name} for harness {harness_id}")
            
            # Create the task object inside the worker process
            task_cls = None
            if task_name == "GrossDiffSeedGen":
                task_cls = GrossDiffSeedGen
            elif task_name == "GrossMapReduceSeedGen":
                task_cls = GrossMapReduceSeedGen
            elif task_name == "GrossBasicSeedGen":
                task_cls = GrossBasicSeedGen
            else:
                logger.error(f"Unknown task type: {task_name}")
                continue
                
            # Instantiate the task
            task = task_cls(
                project_bundle=bundle,
                harness_id=harness_id,
                weighted_models=weighted_models
            )
            
            while engine.dev_team.task_queue.qsize() > 4:
                await asyncio.sleep(5)

            success = await engine.add_task(task)
            if success:
                logger.info(f"Successfully added {task_name} task")
    except asyncio.CancelledError:
        logger.info("add_task_after_delay cancelled")
    except Exception as e:
        logger.error(f"Error during execution: {e}", exc_info=True)

async def engine_worker(q: Queue, project_info):
    try:
        psutil.Process().cpu_affinity([0])
        async with DeepGenEngine(core_ids=[1], model="gpt-4.1", 
                        submit_class=SeedCountingZeroMQSubmit, seed_max_size=262144, seed_pool_size=10000, n_exec=500) as engine:
            engine.add_developer(PassthroughDeveloper())
            await asyncio.gather(
                engine.run(tasks=[]),
                add_task_after_delay(engine, q, project_info)
            )
        
        # Print summary of seed counts
        logger.info("Engine execution completed.")
        logger.info("Seed count summary:")
        for script_id, count in script_seed_counts.items():
            logger.info(f"Script {script_id}: {count} seeds")

    except Exception as e:
        logger.error(f"Error during execution: {e}", exc_info=True)


async def main():
    q = Queue(maxsize=100)
    
    this_dir = Path(__file__).parent.parent
    print(f"Using this directory: {this_dir}")

    workdir = this_dir / "workdir"
    workdir.mkdir(parents=True, exist_ok=True)

    ossfuzz_home_dir = this_dir / "oss-fuzz"
    project_name = "aixcc/c/asc-nginx"
    local_repo_dir = get_src_dir(ossfuzz_home_dir, project_name, this_dir / "cloned-repos")
    harness_name = "pov_harness"
    
    # Pass serializable project information to worker
    project_info = {
        "ossfuzz_home": str(ossfuzz_home_dir),
        "project_name": project_name,
        "local_repo_dir": str(local_repo_dir),
        "workdir": str(workdir),
    }
    
    p = Process(target=worker, args=(q, project_info))
    p.start()

    bundle = Project(
        oss_fuzz_home=ossfuzz_home_dir,
        project_name=project_name,
        local_repo_path=local_repo_dir,
    ).prepare_project_bundle(workdir) # pack the source code and fuzz-tooling into a bundle
    
    sched = Scheduler(bundle, q)
    sched.register_harness(harness_name)

    try:
        sched.start()
        stop_event = Event()
        while not stop_event.is_set():
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Interrupt received, shutting down...")
    finally:
        logger.info("Initiating shutdown sequence...")

        # Shutdown APScheduler
        logger.info("Shutting down APScheduler...")
        if sched and sched.scheduler.running:
            sched.scheduler.shutdown(wait=True) # Wait for scheduler to clean up
        logger.info("APScheduler shutdown complete.")

        if p.is_alive():
            logger.error(f"Worker process {p.pid} did not exit after SIGTERM. Sending SIGKILL...")
            p.kill() # Sends SIGKILL (more forceful)
            p.join(timeout=5) # Wait for SIGKILL


    logger.info("Shutdown complete.")

if __name__ == "__main__":
    asyncio.run(main())