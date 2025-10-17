from .task_base import Task
import sys


class ScriptLoaderTask(Task):
    """Task for loading seed generation scripts provided by users."""
    
    def __init__(self,
                 script_content: str,
                 harness_name: str,
                 label: str = None,
                 priority: int = 1,
                 dev_attempts: int = 1,
                 dev_cost: float = 0.0,
                 num_repeat: int = 1,
                 max_exec: int = sys.maxsize):
        """
        Initialize the script loader task with a user-provided script.
        
        Args:
            script_content: Content of the seed generation script
            harness_name: Name of the harness this script is for
            label: Optional label to identify the script
            priority: Priority of the task
            dev_attempts: Maximum number of attempts
            dev_cost: Maximum cost budget (usually 0 as no generation needed)
            num_repeat: Number of times to repeat the task
        """
        super().__init__(
            harness_name=harness_name,
            priority=priority,
            dev_attempts=dev_attempts,
            dev_cost=dev_cost,
            num_repeat=num_repeat,
            max_exec=max_exec,
        )
        self.script_content = script_content
        self.user_label = label or "user_script"

    def get_label(self) -> str:
        return f"ScriptLoader:{self.harness_name}:{self.user_label}"

    def has_quota(self) -> bool:
        return True

    async def _run_impl(self) -> (str, int):
        # No generation needed, just return the provided script content
        # Token cost is 0 since we're not generating anything
        return self.script_content, 0