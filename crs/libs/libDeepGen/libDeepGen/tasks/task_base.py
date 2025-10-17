from abc import ABC, abstractmethod
import sys


class Task(ABC):
    """
    Abstract base class for libDeepGen fuzzing seed gen tasks.
    """

    def __init__(self,
                 harness_name: str,
                 priority: int,
                 dev_attempts: int,
                 dev_cost: float,
                 num_repeat: int,
                 max_exec: int = sys.maxsize):
        """
        libDeepGen first generates scripts for tasks, then execute them to generate seeds.
        
        Args:
            harness_name: Name of the harness this task aims to gen seed-gen script for
            priority: Priority of the task, higher values indicate higher priority
            dev_attempts: Maximum number of attempts before giving up on a task
            dev_cost: Maximum cost budget for developers
            num_repeat: Number of times to repeat the task
        """
        self.harness_name = harness_name
        self.priority = priority
        self.dev_attempts = dev_attempts
        self.dev_cost = dev_cost
        self.cur_cost = 0
        self.num_repeat = num_repeat
        self.max_exec = max_exec

    @abstractmethod
    async def _run_impl(self) -> (str, int):
        """
        Run the task asynchronously.
        
        Returns:
            str: Result of the task execution, a seed generation script.
            int: Token cost of the task execution.
        """
        pass

    async def run(self) -> str:
        script_content, token_cost = await self._run_impl()
        self.cur_cost += token_cost
        return script_content

    @abstractmethod
    def get_label(self) -> str:
        """
        Get a label for the task, used for tracking purpose.
        
        Returns:
            str: A label string for the task.
        """
        pass

    def has_quota(self) -> bool:
        return self.cur_cost < self.dev_cost
