import logging
from .task_base import Task
from .script_checker import ScriptChecker
from libAgents.agents import SeedsGenForDiff
from libAgents.utils import Project
from typing import Optional

logger = logging.getLogger(__name__)

class DiffAnalysisTask(Task):
    def __init__(self, 
                 project_bundle: Project,
                 harness_id: str,
                 model: str,
                 priority: int = 1,
                 dev_attempts: int = 1,
                 dev_cost: float = 100.0,
                 num_repeat: int = 1,
                 cache_type: Optional[str] = "disk",
                 cache_expire_time: int = 300,
                 ):
        super().__init__(
            harness_name=harness_id,
            priority=priority,
            dev_attempts=dev_attempts,
            dev_cost=dev_cost,
            num_repeat=num_repeat
        )
        self.project_bundle = project_bundle
        self.harness_id = harness_id
        self.model = model
        self.token_cost = 0
        self.cache_type = cache_type
        self.cache_expire_time = cache_expire_time

    def get_label(self) -> str:
        return f"DiffAnalysisTask-{self.harness_id}"

    async def _run_impl(self) -> tuple[str, int]:
        agent = SeedsGenForDiff(
            model=self.model,
            project_bundle=self.project_bundle,
            harness_id=self.harness_id,
            cache_type=self.cache_type,
            cache_expire_time=self.cache_expire_time,
        )
        final_result = await agent.run()
        checker = ScriptChecker(model=self.model, script_content=final_result)
        fixed_script = await checker.check()
        return fixed_script, self.token_cost