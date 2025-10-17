import time
import logging
import signal
import atomics
import json
import traceback
import uuid
import asyncio

from collections import defaultdict
from datetime import datetime
from pathlib import Path

from .tasks.task_base import Task
from .tasks.task_board import TaskBoard
from .executor import Executor
from .executor.executor import ExecTask, ExecStat
from .script import Script
from .ipc_utils.shm_pool import ScriptShmemPoolProducer
from .submit import SubmitBase


logger = logging.getLogger(__name__)

class DeepGenEngine:
    """
    In libDeepGen:
      - API caller specifies seed generation task
      - Developer writes seed generator script based on the task
      - Executor executes script and submit the generated seeds to outside world
    
    DeepGenEngine implements the above workflow in the style of continuous script generation and elimination.
    """

    def __init__(self, core_ids: list[int],
                 workdir: str | None = None,
                 submit_class: type[SubmitBase] | None = None,
                 submit_kwargs: dict | None = None,
                 seed_max_size: int = 65536,
                 seed_pool_size: int = 65536,
                 n_exec: int = 100,
                 shm_label: str | None = None,
                 task_para: int = 4,
                 ):
        """
        Initialize the DeepGenEngine.
        
        Args:
            core_ids: List of CPU core IDs to use for execution
            workdir: Working directory path
            submit_class: Submit class to use for submitting seeds (default: MockSubmit)
            seed_max_size: Max size of each seed in bytes
            seed_pool_size: Number of items in seed pool
            n_exec: Number of exec of script per scheduling
            shm_label: Shared memory label for IPC
            task_para: Number of parallel tasks for task board
        """
        # script id -> (mask_status, sched_cnt, script_id, script)
        self.scripts = {}
        self._script_lock = asyncio.Lock()

        self.shm_label = str(uuid.uuid4())[0:8] if shm_label is None else shm_label
        self.script_pool_name = f'libDeepGen-seed-shmem-pool-{self.shm_label}'
        self.script_pool = ScriptShmemPoolProducer(shm_name=self.script_pool_name, create=True)

        logger.info(f"Using shmem name label: {self.shm_label}, passed arg is {shm_label}")
        
        # Statistics tracking
        # {script_id: {(proc_id, core_id): {"ttl_execs": 0, "ttl_errors": 0, "ttl_gen_seeds": 0, "stored_seeds": 0, "ttl_traffic": 0}}}
        self._stat_lock = asyncio.Lock()
        self.stats = defaultdict(lambda: defaultdict(lambda: {"ttl_execs": 0, "ttl_errors": 0, "ttl_gen_seeds": 0, "stored_seeds": 0, "ttl_traffic": 0}))

        self._should_exit = atomics.atomic(width=4, atype=atomics.INT)
        self._should_exit.store(0)
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        self.workdir = Path(workdir) if workdir else Path.cwd() / "workdir-libDeepGen"
        self.workdir.mkdir(parents=True, exist_ok=True)
        self.task_board = TaskBoard(self.workdir / "task-board", task_para)

        self.pre_alloc_exec = 500
        # By default, for each ExecProc, around 1GB mem usage:
        #  pre_alloc_exec = 500
        #  n_exec = 100
        #  seed_pool_size = 65536
        # - task_rb => 4 * 500/100 * 0.5K = 10KB
        # - stat_rb > 65536 * 4K = 256MB
        # - recycle_rb > 65536 * 4K = 256MB
        # - seed_pool => 65536 * 8K = 512MB
        self.executor = Executor(
            shm_label=self.shm_label,
            script_pool_name=self.script_pool_name,
            core_ids=core_ids, 
            workdir=self.workdir / "executor",
            task_rb_size=((self.pre_alloc_exec + n_exec - 1) // n_exec),
            task_rb_slot_bytes=512,
            stat_rb_size=seed_pool_size,
            stat_rb_slot_bytes=4096 + 4 * n_exec,
            recycle_rb_size=seed_pool_size,
            recycle_rb_slot_bytes=4096 + 4 * n_exec,
            seed_max_size=seed_max_size,
            seed_pool_size=seed_pool_size,
            n_exec=n_exec,
        )

        if submit_class is None or not issubclass(submit_class, SubmitBase):
            raise ValueError("submit_class must be a subclass of SubmitBase")
        self.submit = submit_class(
            proc_map=self.executor.get_proc_map(),
            workdir=self.workdir / "submit",
            **(submit_kwargs if submit_kwargs else {}),
        )

    async def __aenter__(self):
        await self.submit.__aenter__()
        await self.executor.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.submit.__aexit__(exc_type, exc_val, exc_tb)
        await self.executor.__aexit__(exc_type, exc_val, exc_tb)
        try:
            self.script_pool.close()
        except Exception:
            pass
        logger.info("DeepGenEngine resources cleaned up")
        
    async def print_and_save_stats(self, print_summary=False):
        """Print execution statistics and save them to a JSON file."""
        summary_file = self.workdir / "summary.json"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # defaultdict => regular dict for JSON dump
        stats_dict = {}
        async with self._stat_lock:
            for script_id, proc_stats in self.stats.items():
                script = await self.get_script(script_id)
                if script:
                    script_hash = script.sha256
                    script_path = script.file_path
                else:
                    script_hash = "unknown"
                    script_path = "unknown"
                
                stats_dict[str(script_id)] = {
                    "script_id": script_id,
                    "script_hash": script_hash,
                    "script_path": script_path,
                    "proc_stats": {str(k): v for k, v in proc_stats.items() if k != ("summary", None)},
                    "summary": {
                        "ttl_execs": proc_stats[("summary", None)]["ttl_execs"],
                        "ttl_errors": proc_stats[("summary", None)]["ttl_errors"],
                        "ttl_gen_seeds": proc_stats[("summary", None)]["ttl_gen_seeds"],
                        "ttl_stored_seeds": proc_stats[("summary", None)]["stored_seeds"],
                        "ttl_traffic": proc_stats[("summary", None)]["ttl_traffic"],
                    }
                }
        
        total_exec_time = time.time() - self.start_time
        summary = {
            "timestamp": timestamp,
            "total_execution_time": total_exec_time,
            "time_limit": self.time_limit,
            "scripts": stats_dict,
            "script_scheduler": await self._dump_scheduler_stats(),
        }
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        logger.info(f"Statistics saved to {summary_file}")
        
        if not print_summary:
            return

        logger.info("=== Execution Statistics Summary ===")
        logger.info(f"Total Execution Time: {total_exec_time:.2f} seconds")
        if self.time_limit > 0:
            logger.info(f"Time Limit: {self.time_limit} seconds")
        logger.info("---")
        for script_id, script_data in stats_dict.items():
            logger.info(f"Script ID: {script_id}")
            logger.info(f"  Path: {script_data['script_path']}")
            logger.info(f"  Hash: {script_data['script_hash']}")
            logger.info("  Summary:")
            logger.info(f"    Total Executions: {script_data['summary']['ttl_execs']}")
            logger.info(f"    Total Errors: {script_data['summary']['ttl_errors']}")
            logger.info(f"    Total Generated Seeds: {script_data['summary']['ttl_gen_seeds']}")
            logger.info(f"    Total Stored Seeds: {script_data['summary']['ttl_stored_seeds']}")
            logger.info(f"    Total Traffic: {script_data['summary']['ttl_traffic']} bytes")
            logger.info("  Processor Details:")
            
            for proc_tuple, proc_data in script_data['proc_stats'].items():
                proc_id, core_id = eval(proc_tuple)  # Convert string tuple back to tuple
                logger.info(f"    Processor {proc_id} (Core {core_id}):")
                logger.info(f"      Executions: {proc_data['ttl_execs']}")
                logger.info(f"      Errors: {proc_data['ttl_errors']}")
                logger.info(f"      Generated Seeds: {proc_data['ttl_gen_seeds']}")
                logger.info(f"      Stored Seeds: {proc_data['stored_seeds']}")
                logger.info(f"      Traffic: {proc_data['ttl_traffic']} bytes")

    def _signal_handler(self, signum, frame):
        logger.info(f"Received signal {signum}, ignore it...")
        # logger.info(f"Received signal {signum}, initiating shutdown...")
        # self._should_exit.store(1)

    def _should_continue(self):
        return self._should_exit.load() == 0

    async def _stop_signal_monitor(self, time_limit: int):
        """Monitor for stop signals, either from time limit or external signals."""
        logger.info("Stop signal monitor started")
        if time_limit > 0:
            logger.info(f"Engine will run for {time_limit} seconds")
        else:
            logger.info("Engine will run indefinitely until manually stopped")

        last_save_time = 0
        while self._should_continue():
            elasped_time = time.time() - self.start_time
            if elasped_time - last_save_time >= 60:
                last_save_time = elasped_time
                await self.print_and_save_stats(print_summary=False)
            if time_limit > 0 and elasped_time >= time_limit:
                logger.info(f"Time limit of {time_limit} seconds reached, initiating shutdown")
                self._should_exit.store(1)
                await self.print_and_save_stats(print_summary=True)
                break
            await asyncio.sleep(1)

        logger.info("Stop signal monitor terminated")

    async def get_script(self, script_id: int):
        """Get a script from the pool by script_id."""
        async with self._script_lock:
            if script_id in self.scripts:
                return self.scripts[script_id][3]
            return None

    async def add_script(self, script: Script) -> bool:
        logger.info(f"Adding script {script.file_path} to the pool")
        async with self._script_lock:
            try:
                script_id = self.script_pool.add_script(script)
                if script_id is None:
                    # Script pool is full
                    logger.error("ERROR: Script pool is full, cannot add new script")
                    return False
                elif script_id == -1:
                    # Script already exists in the pool
                    logger.warning("WARN: Exact same hash script already exists in the pool")
                    return False
                elif script_id == -2:
                    # Script is invalid
                    logger.warning("WARN: Invalid script, cannot add to the pool")
                    return False
                if script_id in self.scripts:
                    # Script already exists in the scheduler
                    logger.error(f"ERROR: Script {script_id} already exists in the scheduler")
                    return False
                self.scripts[script_id] = (False, 0, script_id, script)
                return True
            except Exception as e:
                logger.error(f"Error add_script {script.file_path}: {e}", exc_info=True)
                return False

    async def _schedule_next_script(self):
        async with self._script_lock:
            try:
                if not self.scripts:
                    return None, None

                unmasked_scripts = [s for s in self.scripts.values() if not s[0]]
                if not unmasked_scripts:
                    return None, None

                # Select the least sched script to run
                mask_stat, sched_cnt, script_id, least_sched_script = min(unmasked_scripts, key=lambda s: s[1])
                #logger.info(f"Scheduling script ID {script_id} for execution, current sched count: {sched_cnt}, mask status: {mask_stat}")
                self.scripts[script_id] = mask_stat, sched_cnt + 1, script_id, least_sched_script
                return script_id, least_sched_script
            except Exception as e:
                logger.error(f"Error _schedule_next_script: {e}", exc_info=True)
                return None, None

    async def _dump_scheduler_stats(self):
        async with self._script_lock:
            try:
                scheduler_stats = {
                    script_id: (mask_status, sched_cnt, script.to_dict()) 
                    for script_id, (mask_status, sched_cnt, _, script) in 
                    self.scripts.items()
                }
                return scheduler_stats
            except Exception as e:
                logger.error(f"Error _dump_scheduler_stats: {e}", exc_info=True)
                return None

    async def _update_stats(self, script: Script, stat: ExecStat):
        """Update statistics for a given execution."""
        script_id = stat.script_id
        proc_id = stat.proc_id
        core_id = stat.core_id

        async with self._stat_lock:
            proc_stat = self.stats[script_id][(proc_id, core_id)]
            proc_stat["ttl_execs"] += stat.ttl_execs
            proc_stat["ttl_errors"] += stat.ttl_errors
            proc_stat["ttl_gen_seeds"] += stat.ttl_gen_seeds
            proc_stat["stored_seeds"] += len(stat.seed_ids)
            proc_stat["ttl_traffic"] += stat.ttl_traffic

            sum_stat = self.stats[script_id][("summary", None)]
            sum_stat["ttl_execs"] += stat.ttl_execs
            sum_stat["ttl_errors"] += stat.ttl_errors
            sum_stat["ttl_gen_seeds"] += stat.ttl_gen_seeds
            sum_stat["stored_seeds"] += len(stat.seed_ids)
            sum_stat["ttl_traffic"] += stat.ttl_traffic

        if await self.is_masked(script_id):
            #logger.debug(f"Script {script_id} is masked, skipping further checks")
            return

        # check if need mask the script
        ttl_execs = sum_stat["ttl_execs"]
        if ttl_execs >= script.max_exec:
            logger.info(f"Script {script_id} has reached max execs {ttl_execs}, masking it")
            await self.mask_script(script_id)
        if ttl_execs < 100:
            return
        ttl_err, ttl_gen = sum_stat["ttl_errors"], sum_stat["ttl_gen_seeds"]
        err_rate = ttl_err / ttl_execs
        gen_rate = ttl_gen / ttl_execs
        if err_rate >= 0.5:
            logger.info(f"Script {script_id} has high err rate {err_rate}:{ttl_err}/{ttl_execs}, masking it")
            await self.mask_script(script_id)
        elif gen_rate < 0.5:
            logger.info(f"Script {script_id} has low succ gen rate {gen_rate}:{ttl_gen}/{ttl_execs}, masking it")
            await self.mask_script(script_id)

    async def _executor_task_loop(self):
        logger.info("Executor task loop started")
        while self._should_continue():
            succ = False
            try:
                # NOTE: to make lock-free => block-free, we always assign a bit more exec tasks 
                #        than executor can handle. Now it is max(self.pre_alloc_exec, n_exec) execs.
                proc_ids = self.executor.need_add_task(self.pre_alloc_exec)
                if not proc_ids:
                    logger.debug("Executor task queue is full, waiting for space")
                for proc_id in proc_ids:
                    script_id, next_script = await self._schedule_next_script()
                    if script_id is not None and next_script is not None:
                        added = self.executor.try_add_task(proc_id, ExecTask.from_script(script_id, next_script))
                        if added:
                            logger.debug(f"Added script ID {script_id} to execution queue")
                            succ = True
                        else:
                            logger.debug(f"Failed to add script ID {script_id} to execution queue")
                    else:
                        logger.debug("No script available for execution scheduling")
            except Exception as e:
                logger.error(f"Error _executor_task_loop: {e}", exc_info=True)
            finally:
                if not succ:
                    # Only sleep when no task is added
                    await asyncio.sleep(1)
                else:
                    await asyncio.sleep(0)

        logger.info("Executor task loop terminated")

    async def _executor_stat_loop(self):
        logger.info("Executor stat loop started")
        while self._should_continue():
            exec_stats = self.executor.try_get_stats()
            for stat in exec_stats:
                try:
                    script_id = stat.script_id
                    script = await self.get_script(script_id)
                    proc_id = stat.proc_id
                    seed_ids = stat.seed_ids
                    await self._update_stats(script, stat)
                    await self.submit.request_seed_submit(proc_id, script_id, script, seed_ids)
                except Exception as e:
                    logger.error(f"Error _executor_stat_loop: {e}", exc_info=True)
            if len(exec_stats) == 0:
                # Only sleep when no stat is received
                await asyncio.sleep(1)
            else:
                await asyncio.sleep(0)
        logger.info("Executor stat loop terminated")

    async def add_task(self, task: Task) -> str:
        """Add a new task to the engine during execution."""
        return await self.task_board.add_task(task)

    async def remove_task(self, task_id: str) -> bool:
        """Remove a task from the engine."""
        return await self.task_board.remove_task(task_id)

    async def run(self, time_limit: int = -1):
        """Run the engine with the given tasks using a thread pool."""
        self.start_time = time.time()
        self.time_limit = time_limit

        await self.executor.start()
        logger.info("Executor started")

        try:
            async_tasks = [
                # Task board loop
                self.task_board.run(self.add_script, self._should_continue),
                # Executor loops
                self._executor_task_loop(),
                self._executor_stat_loop(),
                # Submit seed recycle loop
                self.submit.recycle_loop(self._should_continue),
                # Stop signal monitor
                self._stop_signal_monitor(time_limit),
            ]
    
            results = await asyncio.gather(*async_tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Error during execution: {result}", exc_info=True)
            logger.info("Engine all tasks completed")
        except Exception as e:
            logger.error(f"Error during execution: {e} {traceback.format_exc()}")
        finally:
            self._should_exit.store(1)
            await self.executor.stop()
            logger.info("Executor stopped")

        logger.info("Engine shutdown complete")

    async def mask_script(self, script_id: int) -> bool:
        """Mask a bad performance script."""
        async with self._script_lock:
            if script_id in self.scripts:
                mask_status, sched_cnt, _, script = self.scripts[script_id]
                if not mask_status:
                    self.scripts[script_id] = (True, sched_cnt, script_id, script)
                    return True
            return False

    async def is_masked(self, script_id: int) -> bool:
        """Check if a script is masked."""
        async with self._script_lock:
            if script_id in self.scripts:
                mask_status, a, b, c = self.scripts[script_id]
                return mask_status
            return False
