import logging
import traceback
import itertools
import os
import asyncio
import random
from typing import Optional
from pathlib import Path

from ..tasks.task_base import Task
from ..script import Script


logger = logging.getLogger(__name__)


class TaskBoard:
    """
    Concurrency-safe task scheduler for Task objects.

    Scheduling strategy:
    1. Pick the least explored tasks
    2. Among those, pick the highest priority
    3. Invalid tasks (has_quota() == False) are removed
    """
    
    def __init__(self, workdir: Path, parallel_num: int):
        self.workdir = workdir
        os.makedirs(self.workdir, exist_ok=True)

        self.task_processors = parallel_num

        # {task_id -> (sched_cnt, priority, task)}
        self.task_board = {}
        self._task_id_counter = itertools.count(1)
        self._task_lock = asyncio.Lock()

    async def add_task(self, task: Task) -> str:
        """Add a new task to the task queue for processing, create and return a unique task id."""
        async with self._task_lock:
            task_id = f"task-{next(self._task_id_counter)}"
            self.task_board[task_id] = (0, task.priority, task)
            logger.info(f"Added task {task_id} of type {task.get_label()} with priority {task.priority}")
            return task_id

    async def remove_task(self, task_id: str) -> bool:
        """Remove a task from the task queue by its unique task id, return True if successful."""
        async with self._task_lock:
            if task_id not in self.task_board:
                return False
                
            del self.task_board[task_id]
            logger.info(f"Removed task {task_id}")
            return True

    async def _next_task(self) -> Optional[Task]:
        """Get the next task from the task board using scheduling strategy."""
        async with self._task_lock:
            if not self.task_board:
                return None
                
            # Remove invalid tasks
            invalid_task_ids = []
            for task_id, (sched_cnt, _, task) in self.task_board.items():
                if not task.has_quota() or sched_cnt >= task.num_repeat:
                    invalid_task_ids.append(task_id)
            for task_id in invalid_task_ids:
                del self.task_board[task_id]
                logger.info(f"Removed exhausted task {task_id}")
            
            valid_tasks = {
                task_id: (sched_cnt, priority, task) 
                for task_id, (sched_cnt, priority, task) in self.task_board.items()
            }
            if not valid_tasks:
                return None
                
            min_sched_cnt = min(sched_cnt for sched_cnt, _, _ in valid_tasks.values())
            least_sched_tasks = {
                task_id: (sched_cnt, priority, task)
                for task_id, (sched_cnt, priority, task) in valid_tasks.items()
                if sched_cnt == min_sched_cnt
            }
            
            max_priority = max(priority for _, priority, _ in least_sched_tasks.values())
            candidates = [
                (task_id, task)
                for task_id, (_, priority, task) in least_sched_tasks.items()
                if priority == max_priority
            ]
            
            selected_id, selected_task = random.choice(candidates)
            sched_cnt, priority, _ = self.task_board[selected_id]
            self.task_board[selected_id] = (sched_cnt + 1, priority, selected_task)

            return selected_task

    async def format_board_status(self) -> str:
        """Format the status of task board for debugging."""
        async with self._task_lock:
            format_str = "Task Board Status:\n"
            format_str += f" - total tasks: {len(self.task_board)}\n"
            
            by_priority = {}
            for task_id, (sched_cnt, priority, task) in self.task_board.items():
                if priority not in by_priority:
                    by_priority[priority] = []
                by_priority[priority].append((task_id, sched_cnt, task))
            
            for priority in sorted(by_priority.keys(), reverse=True):
                tasks = by_priority[priority]
                valid_tasks = sum(1 for _, _, task in tasks if task.has_quota())
                format_str += f" - Priority {priority}: {valid_tasks}/{len(tasks)} valid tasks\n"
                
                for task_id, sched_cnt, task in sorted(tasks, key=lambda x: x[1]):
                    is_valid = task.has_quota()
                    status = "valid" if is_valid else "exhausted"
                    format_str += f"   - Task {task_id}: {task.get_label()}, Scheduled: {sched_cnt}, Status: {status}\n"
            
            return format_str

    async def _task_processor(self, processor_id: str, workdir: Path, submit_script_async_fn, should_continue_fn):
        """Task processor that pulls tasks from the queue and processes them."""
        logger.info(f"Task processor {processor_id} started with workdir: {workdir}")

        while should_continue_fn():
            task = await self._next_task()
            if task is None:
                logger.debug(f"[{processor_id}] No tasks available, waiting...")
                await asyncio.sleep(1)
                continue

            cur_attempts = 0
            while task.has_quota() and cur_attempts < task.dev_attempts and should_continue_fn():
                try:
                    cur_attempts += 1
                    script_content = await task.run()
                    if not script_content:
                        logger.warning(f"[{processor_id}] returned empty script for task {task.get_label()}")
                        continue
                    
                    script = Script.new(
                        content=script_content,
                        task_label=task.get_label(),
                        harness_name=task.harness_name,
                        workdir=workdir,
                        max_exec=task.max_exec,
                    )
                    await submit_script_async_fn(script)
                    logger.info(f"[{processor_id}] Generated and submitted script {script.file_path}")
                    break
                except Exception as e:
                    logger.error(f"[{processor_id}] Error generating script: {e}, {traceback.format_exc()}")

        logger.info(f"Task processor {processor_id} shutting down")

    async def run(self, submit_script_async_fn, should_continue_fn):
        """Run tasks with scheduling."""
        processors = []
        for i in range(self.task_processors):
            processor_id = f"processor-{i}"
            processor_workdir = self.workdir / processor_id
            os.makedirs(processor_workdir, exist_ok=True)
            processors.append(self._task_processor(
                processor_id, 
                processor_workdir,
                submit_script_async_fn, 
                should_continue_fn
            ))

        results = await asyncio.gather(*processors, return_exceptions=True)
        for r in results:
            if isinstance(r, Exception):
                logger.error(f"Task processor raised: {r}, {traceback.format_exc()}")

        logger.info("Task board has completed.")
