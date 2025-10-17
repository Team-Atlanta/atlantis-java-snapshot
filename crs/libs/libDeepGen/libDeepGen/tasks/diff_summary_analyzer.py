import logging
from .task_base import Task
from libAgents.agents import DiffAnalyzer
from libAgents.utils import Project, get_model_by_weights
from .script_checker import ScriptChecker
from typing import Optional

logger = logging.getLogger(__name__)

class DiffSummaryAnalyzer(Task):
    def __init__(self,
                 project_bundle: Project,
                 harness_id: str,
                 model: str,
                 priority: int = 1,
                 dev_attempts: int = 1,
                 dev_cost: float = 100.0,
                 num_repeat: int = 1,
                 cache_type: Optional[str] = "disk",
                 cache_expire_time: int = 1800,
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
        return f"DiffSummaryAnalyzer-{self.harness_id}"
    async def _run_impl(self) -> tuple[str, int]:
        agent = DiffAnalyzer(
            model=self.model,
            project_bundle=self.project_bundle,
            harness_id=self.harness_id,
            cache_type=self.cache_type,
            cache_expire_time=self.cache_expire_time,
        )
        final_result = await agent.run()
        checker = ScriptChecker(model=self.model, script_content=final_result)
        fixed_script = await checker.check()
        logger.info(f"final_result for DiffSummaryAnalyzer : {final_result}")
        return final_result, self.token_cost