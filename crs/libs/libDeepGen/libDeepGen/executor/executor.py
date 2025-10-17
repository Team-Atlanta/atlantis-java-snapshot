import asyncio
import atomics
import collections
import json
import logging
import os
import psutil
import signal
import sys
import time
import traceback

from dataclasses import dataclass
from multiprocessing import Process
from pathlib import Path

from ..script import Script
from ..ipc_utils.shm_pool import ScriptShmemPoolConsumer, SeedShmemPoolProducer, SeedShmemPoolConsumer
from ..ipc_utils.ringbuffer import RingBufferProducer, RingBufferConsumer
from .exec_base import ExecResult
from .exec_inprocess import InProcessExec


logger = logging.getLogger(__name__)


@dataclass
class ExecTask:
    """ExecTask is a dataclass that holds the execution task information."""
    script_id: int
    script_hash: str

    @classmethod
    def from_script(cls, script_id: int, script: Script) -> "ExecTask":
        return cls(
            script_id=script_id,
            script_hash=script.sha256
        )


@dataclass
class ExecStat:
    """ExecStat is a dataclass that holds execution statistics for a script."""
    proc_id: str
    core_id: int
    script_id: int
    ttl_execs: int
    ttl_errors: int
    ttl_gen_seeds: int
    ttl_traffic: int
    seed_ids: list[int]


class ExecProc:

    def __init__(self, script_pool_name: str, workdir: Path, proc_id: str, core_id: int, task_rb_name: str, stat_rb_name: str, recycle_rb_name: str, seed_pool_name: str, n_exec: int):
        workdir.mkdir(parents=True, exist_ok=True)
        self.workdir_str = str(workdir)
        self.process = Process(target=self._main)
        self.running = False

        # Members will be used in subprocess 
        self.proc_id = proc_id
        self.core_id = core_id
        self.task_rb_name = task_rb_name
        self.stat_rb_name = stat_rb_name
        self.recycle_rb_name = recycle_rb_name
        self.seed_pool_name = seed_pool_name
        self.script_pool_name = script_pool_name
        self.n_exec = n_exec
        self.log_file = str(workdir / f"exec-proc-{proc_id}.log")
    
    def start(self):
        if not self.running:
            self.process.start()
            self.running = True
            logger.info(f"Executor {self.proc_id} started on core {self.core_id}")
        else:
            logger.warning(f"Executor {self.proc_id} is already running.")

    def stop(self):
        self.process.terminate()
        if not self.process.join(timeout=3):
            logger.debug(f"Process {self.proc_id} did not terminate gracefully, forcing kill")
            self.process.kill()

    #################################
    # Methods only used in subprocess
    #################################

    def _setup_logging(self):
        # Force unbuffered output for the process
        sys.stdout = open(1, 'w', buffering=1)
        sys.stderr = open(2, 'w', buffering=1)
        
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
            
        # Create a file handler that flushes immediately
        file_handler = logging.FileHandler(self.log_file, mode='a')
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        file_handler.setLevel(logging.INFO)
        
        self.logger = logging.getLogger(self.proc_id)
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(file_handler)
        
        # Add a console handler with immediate flush
        class UnbufferedStreamHandler(logging.StreamHandler):
            def emit(self, record):
                super().emit(record)
                self.flush()
                
        console_handler = UnbufferedStreamHandler()
        console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(console_handler)

    def _notify_cleanup(self, signum=None, frame=None):
        self.logger.info(f"Received signal {signum}, notifying cleanup...")
        self._should_exit.store(1)

    def _get_script_content(self, script_id: int) -> str | None:
        """Get the script content from the shared memory pool."""
        script_content = self.script_pool_consumer.get_script_content(script_id)
        if script_content is None:
            self.logger.error(f"Failed to get script content for ID {script_id}.")
            return None
        return script_content

    def _update_exec_stat(self, exec_stat: ExecStat, exec_rslt: ExecResult):
        exec_stat.ttl_execs += 1
        if exec_rslt is None or not exec_rslt.success:
            # failed execution
            exec_stat.ttl_errors += 1
            return
        seed_id = self.seed_pool.add_seed(exec_rslt.result)
        if seed_id is None:
            # invalid seed (None, or too large)
            exec_stat.ttl_errors += 1
        elif seed_id < 0:
            # Full seed pool
            pass
            #self.logger.error(f"Failed to add seed for script ID {exec_stat.script_id}.")
        else:
            exec_stat.seed_ids.append(seed_id)
            exec_stat.ttl_gen_seeds += 1
            exec_stat.ttl_traffic += len(exec_rslt.result)
            #self.logger.info(f"Added seed ID {seed_id} for script ID {exec_stat.script_id}.")

    def _should_continue(self):
        return self._should_exit.load() == 0

    def _merge_exec_stats(self, stat_list):
        """Merge multiple exec stats into one."""
        if not stat_list:
            return None

        merged = ExecStat(
            proc_id=stat_list[0].proc_id,
            core_id=stat_list[0].core_id,
            script_id=stat_list[0].script_id,
            ttl_execs=0,
            ttl_errors=0,
            ttl_gen_seeds=0,
            ttl_traffic=0,
            seed_ids=[]
        )

        for stat in stat_list:
            merged.ttl_execs += stat.ttl_execs
            merged.ttl_errors += stat.ttl_errors
            merged.ttl_gen_seeds += stat.ttl_gen_seeds
            merged.ttl_traffic += stat.ttl_traffic
            merged.seed_ids.extend(stat.seed_ids)

        return merged

    def _try_recycle_seeds(self):
        """Check if any seeds can be recycled to the pool."""
        while self._should_continue():
            try:
                seed_ids_ser = self.recycle_rb.try_get()
                if seed_ids_ser is None:
                    break
                seed_ids = json.loads(seed_ids_ser)
                if seed_ids:
                    for seed_id in seed_ids:
                        self.seed_pool.release_seed(seed_id)
                    #self.logger.info(f"Recycled {len(seed_ids)} seeds")
            except Exception as e:
                self.logger.error(f"Error when recycling seeds: {e}\n{traceback.format_exc()}")

    def _exec_loop(self):
        """Single-threaded execution loop."""
        precompiled = {}

        was_full = False

        while self._should_continue():
            # Check for recycled seeds first
            self._try_recycle_seeds()

            is_full = self.seed_pool.is_full()
            if was_full != is_full:
                if is_full:
                    self.logger.info("Seed pool is full, waiting for recycle...")
                else:
                    self.logger.info("Seed pool is not full, resuming execution...")
                was_full = is_full
            if is_full:
                time.sleep(0.01)
                continue

            task = self.task_rb.try_get(cls=ExecTask)
            if task is None:
                time.sleep(0.01)
                continue

            # Precompile to boost performance
            script_hash, script_id = task.script_hash, task.script_id
            if script_hash not in precompiled:
                script_content = self._get_script_content(script_id)
                if script_content is None:
                    self.logger.error(f"Failed to get script content for ID {script_id}.")
                    exec_stat = ExecStat(self.proc_id, self.core_id, script_id, self.n_exec, self.n_exec, 0, 0, [])
                    self.stat_rb.put(exec_stat)
                    continue
                try:
                    precompiled[script_hash] = InProcessExec(script_content)
                except Exception as e:
                    self.logger.error(f"Error in precompilation (single-thread): {e}\n{traceback.format_exc()}")
                    exec_stat = ExecStat(self.proc_id, self.core_id, script_id, self.n_exec, self.n_exec, 0, 0, [])
                    self.stat_rb.put(exec_stat)
                    continue

            # Exec N times for the task script
            precompiled_exec = precompiled[script_hash]
            exec_stat = ExecStat(self.proc_id, self.core_id, script_id, 0, 0, 0, 0, [])
            for i in range(self.n_exec):
                exec_rslt = None
                try:
                    exec_rslt = precompiled_exec.exec()
                except Exception as e:
                    self.logger.error(f"Error in single-threaded execution: {e}\n{traceback.format_exc()}")
                self._update_exec_stat(exec_stat, exec_rslt)
            self.stat_rb.put(exec_stat)

        self.logger.info(f"Process {self.proc_id} exiting...")

    def _main(self):
        # NOTE: this is executed in a separate process
        try:
            self._setup_logging()
            self.logger.info(f"ExecProc {self.proc_id} started with PID {os.getpid()}.")

            self._should_exit = atomics.atomic(width=4, atype=atomics.INT)
            self._should_exit.store(0)
            signal.signal(signal.SIGTERM, self._notify_cleanup)
            signal.signal(signal.SIGINT, self._notify_cleanup)
            self.logger.info(f"Signal handler set for {self.proc_id}.")

            psutil.Process().cpu_affinity([self.core_id])
            self.logger.info(f"Bound to core {self.core_id}.")

            with RingBufferConsumer(self.task_rb_name, create=False) as task_rb, \
                 RingBufferProducer(self.stat_rb_name, create=False) as stat_rb, \
                 RingBufferConsumer(self.recycle_rb_name, create=False) as recycle_rb, \
                 ScriptShmemPoolConsumer(shm_name=self.script_pool_name, create=False) as script_pool_consumer, \
                 SeedShmemPoolProducer(shm_name=self.seed_pool_name, create=False) as seed_pool:
                
                self.task_rb = task_rb
                self.logger.info(f"Attached to ringbuffer {self.task_rb_name}.")
                
                self.stat_rb = stat_rb
                self.logger.info(f"Attached to ringbuffer {self.stat_rb_name}.")
                
                self.recycle_rb = recycle_rb
                self.logger.info(f"Attached to recycle ringbuffer {self.recycle_rb_name}.")
                
                self.script_pool_consumer = script_pool_consumer
                self.logger.info(f"Attached to script pool consumer {script_pool_consumer.shm_name}.")
                
                self.seed_pool = seed_pool
                self.logger.info(f"Attached to seed pool {self.seed_pool_name}")

                # Avoid meaningless CPU burning, wait for at least one task to be available
                # This is because developers are slow to generate scripts
                while self._should_continue() and self.task_rb.guess_never_put():
                    time.sleep(0.1)

                self.logger.info("Using single-threaded execution")
                self._exec_loop()
                
        except Exception as e:
            self.logger.error(f"Error in process {self.proc_id}: {e}\n{traceback.format_exc()}")
            

class Executor:
    """Executor manages multi-process parallel script execution, it receives exec script task from outside scheduler and execute them."""

    _WATCHDOG_INTERVAL = 1.0      # seconds
    _MAX_RESTART       = None     # per-process, None → unlimited

    def __init__(self,
                 shm_label: str,
                 script_pool_name: str,
                 core_ids: list[int],
                 workdir: Path, 
                 task_rb_size,
                 task_rb_slot_bytes,
                 stat_rb_size,
                 stat_rb_slot_bytes,
                 recycle_rb_size,
                 recycle_rb_slot_bytes,
                 seed_max_size,
                 seed_pool_size,
                 n_exec):
        """
        Initialize the Executor with configurable buffer sizes.
        
        Args:
            shm_label: Label for shared memory
            script_pool_name: Name of the script shared memory pool
            core_ids: List of CPU core IDs to use for execution
            workdir: Working directory path
            task_rb_size: Size of task ring buffer (slots)
            task_rb_slot_bytes: Bytes per slot in task ring buffer
            stat_rb_size: Size of stat ring buffer (slots)
            stat_rb_slot_bytes: Bytes per slot in stat ring buffer
            recycle_rb_size: Size of recycle ring buffer (slots)
            recycle_rb_slot_bytes: Bytes per slot in recycle ring buffer
            seed_max_size: Maximum size of a seed
            seed_pool_size: Number of items in seed pool
            n_exec: Number of exec for a script per exec
        """
        self.core_map: dict[str, int] = {}
        self.procs: dict[str, ExecProc] = {}
        self._proc_factories: dict[str, callable[[], ExecProc]] = {}
        self._restart_cnt: dict[str, int] = collections.defaultdict(int)
        self.task_rbs: dict[str, RingBufferProducer] = {}
        self.stat_rbs: dict[str, RingBufferConsumer] = {}
        self.recycle_rbs: dict[str, RingBufferConsumer] = {}
        self.seed_pool_consumers: dict[str, SeedShmemPoolConsumer] = {}
        self.proc_map: dict[str, tuple[str, str]] = {}

        self.workdir = workdir
        self.workdir.mkdir(parents=True, exist_ok=True)
        self.script_pool_name = script_pool_name
        self.n_exec = n_exec

        self._stopped = False
        self._stop_evt: asyncio.Event | None = None
        self._wd_task: asyncio.Task | None = None

        for core_id in core_ids:
            proc_id = f"ExecProc-{shm_label}-{core_id}"
            task_rb_nm = f"task-rb-{shm_label}-{proc_id}"
            stat_rb_nm = f"stat-rb-{shm_label}-{proc_id}"
            recycle_rb_nm = f"recycle-rb-{shm_label}-{proc_id}"
            seed_pool_name = f"libDeepGen-exec-proc-seed-pool-{shm_label}-{proc_id}"
            
            self.proc_map[proc_id] = (recycle_rb_nm, seed_pool_name)
            
            task_rb = RingBufferProducer(task_rb_nm, create=True, size=task_rb_size, bytes_per_slot=task_rb_slot_bytes)
            stat_rb = RingBufferConsumer(stat_rb_nm, create=True, size=stat_rb_size, bytes_per_slot=stat_rb_slot_bytes)
            recycle_rb = RingBufferConsumer(recycle_rb_nm, create=True, size=recycle_rb_size, bytes_per_slot=recycle_rb_slot_bytes)
            
            seed_pool_consumer = SeedShmemPoolConsumer(
                shm_name=seed_pool_name, 
                item_size=seed_max_size,
                item_num=seed_pool_size, 
                create=True
            )
            
            def _make_proc(proc_id=proc_id, core_id=core_id,
                           task_rb_nm=task_rb_nm, stat_rb_nm=stat_rb_nm,
                           recycle_rb_nm=recycle_rb_nm,
                           seed_pool_name=seed_pool_name):
                return ExecProc(
                    script_pool_name=script_pool_name,
                    workdir=workdir,
                    proc_id=proc_id,
                    core_id=core_id,
                    task_rb_name=task_rb_nm,
                    stat_rb_name=stat_rb_nm,
                    recycle_rb_name=recycle_rb_nm,
                    seed_pool_name=seed_pool_name,
                    n_exec=n_exec
                )

            proc = _make_proc()
            self.core_map[proc_id] = core_id
            self.procs[proc_id] = proc
            self._proc_factories[proc_id] = _make_proc
            self.task_rbs[proc_id] = task_rb
            self.stat_rbs[proc_id] = stat_rb
            self.recycle_rbs[proc_id] = recycle_rb
            self.seed_pool_consumers[proc_id] = seed_pool_consumer
    
    async def __aenter__(self):
        # NOTE: we don't start executor here, wait manual start
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()

    def try_add_task(self, proc_id: str, task: ExecTask) -> bool:
        """Try to add a task to the exec proc which has least task."""
        if proc_id in self.task_rbs:
            task_rb = self.task_rbs[proc_id]
            return task_rb.try_put(task)
        return False

    def need_add_task(self, pre_alloc_exec: int) -> list[str]:
        """Check if any task ring buffer is not full."""
        n_task = (pre_alloc_exec + self.n_exec - 1) // self.n_exec
        return [proc_id for proc_id, rb in self.task_rbs.items() if rb.length() <= n_task]

    def try_get_stats(self) -> list[ExecStat]:
        """Try to get stats from the executor, return None if no stats are available."""
        stats = []
        for proc_id, stat_rb in self.stat_rbs.items():
            if not stat_rb.is_empty():
                stat = stat_rb.try_get(cls=ExecStat)
                if stat:
                    stats.append(stat)
        return stats
        
    def get_proc_map(self) -> dict:
        """Return the proc_map for the Submit class."""
        return self.proc_map
    
    async def start(self):
        for proc in self.procs.values():
            proc.start()
        logger.info("All exec procs started.")

        self._stop_evt = asyncio.Event()
        self._wd_task  = asyncio.create_task(self._watchdog(), name="ExecWatchdog")
        logger.info("Executor: watchdog sleeping...")

    async def stop(self):
        if self._stopped:
            return
        self._stopped = True

        if self._stop_evt and not self._stop_evt.is_set():
            self._stop_evt.set()

        if self._wd_task:
            try:
                await self._wd_task
            except Exception:
                logger.info("Executor: watchdog stopped with exception.", exc_info=True)

        for p in list(self.procs.values()):
            try:
                p.stop()
            except Exception:
                logger.error(f"Executor: failed to stop process {p.proc_id}.", exc_info=True)
        self.procs.clear()

        for rb in self.task_rbs.values():
            rb.close()
        for rb in self.stat_rbs.values():
            rb.close()
        for rb in self.recycle_rbs.values():
            rb.close()
        for consumer in self.seed_pool_consumers.values():
            consumer.close()

        logger.info("Executor: shutdown complete.")

    async def _watchdog(self):
        assert self._stop_evt is not None
        interval = self._WATCHDOG_INTERVAL

        while not self._stop_evt.is_set():
            for proc_id, proc in list(self.procs.items()):
                try:
                    if proc.process.is_alive():
                        continue

                    exitcode = proc.process.exitcode
                    logger.warning(f"Executor: {proc_id} died (exit={exitcode}).")

                    if (self._MAX_RESTART is not None and self._restart_cnt[proc_id] >= self._MAX_RESTART):
                        logger.error(f"Executor: {proc_id} exceeds restart limit, skipping.")
                        continue

                    logger.info(f"Executor: {proc_id} restarting...")
                    self._restart_cnt[proc_id] += 1

                    # Ensure the process is stopped before respawning
                    try:
                        proc.stop()
                    except Exception:
                        logger.error(f"Executor: failed to stop process {proc_id}.", exc_info=True)

                    logger.info(f"Executor: {proc_id} respawning (#{self._restart_cnt[proc_id]}).")
                    try:
                        new_proc = self._proc_factories[proc_id]()
                        new_proc.start()
                        self.procs[proc_id] = new_proc
                        logger.info(f"Executor: {proc_id} respawned (#{self._restart_cnt[proc_id]}).")
                    except Exception as e:
                        logger.error(f"Executor: Failed to respawn {proc_id}: {e}")
                except Exception as e:
                    logger.error(f"Executor: Error in watchdog for {proc_id}: {e}", exc_info=True)

            try:
                await asyncio.wait_for(self._stop_evt.wait(), timeout=interval)
            except asyncio.TimeoutError:
                pass
