import asyncio
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from libAgents.agents import AgentBase
from libAgents.tools import ClaudeCode
from libAgents.utils import Project, extract_script_from_response, get_model_by_weights
from libDeepGen.tasks import Task
from libDeepGen.tasks.harness_seedgen import AnyHarnessSeedGen


def _worker(repo_path: str, prompt: str, model: str):
    async def _main():
        claude = ClaudeCode(Path(repo_path))
        response = await claude.async_query(prompt)
        script = await extract_script_from_response(response, model)
        return script

    return asyncio.run(_main())


class ClaudeExpAgent(AgentBase):
    def __init__(
        self,
        model: str,
        project_bundle: Project,
    ):
        super().__init__(project_bundle)
        self.project_bundle = project_bundle
        self.model = model

    async def run(self, prompt):
        loop = asyncio.get_event_loop()
        with ProcessPoolExecutor(max_workers=1) as pool:
            script = await loop.run_in_executor(
                pool,
                _worker,
                self.project_bundle.repo_path,
                prompt,
                self.model,
            )
        return script


class ClaudeExploitScriptTask(Task):
    """Task for exploiting a vulnerability using the provided script content."""

    def __init__(
        self,
        project_bundle: Project,
        harness_name: str,
        harness_entrypoint_func: str,
        weighted_models: dict,
        task_id: str,
        prompt_content: str,
        priority: int = 10,
        dev_attempts: int = 5,
        dev_cost: float = 20.0,
        num_repeat: int = 1,
        max_exec: int = sys.maxsize,
    ):
        super().__init__(
            harness_name=harness_name,
            priority=priority,
            dev_attempts=dev_attempts,
            dev_cost=dev_cost,
            num_repeat=num_repeat,
            max_exec=max_exec,
        )
        self.project_bundle = project_bundle
        self.harness_name = harness_name
        self.harness_entrypoint_func = harness_entrypoint_func
        self.weighted_models = weighted_models
        self.token_cost = 0

        self.task_id = task_id
        self.prompt_content = prompt_content
        model = get_model_by_weights(weighted_models)
        print(f"Initializing ClaudeExploitScriptTask with model: {model}")
        self.coder = ClaudeExpAgent(
            model=model,
            project_bundle=project_bundle,
        )

    def _get_prompt(self) -> str:
        """Override the prompt generation to use the provided content."""
        return self.prompt_content

    def get_label(self) -> str:
        """Return a label for the task."""
        return f"Exploit:{self.task_id}"

    async def _run_impl(self) -> (str, int):
        final_result = await self.coder.run(self.prompt_content)
        # TODO: add cost calculation when supported
        token_cost = 0
        return final_result, token_cost


class DeepGenExploitScriptTask(AnyHarnessSeedGen):
    """Task for exploiting a vulnerability using the provided script content."""

    def __init__(
        self,
        project_bundle: Project,
        harness_name: str,
        harness_entrypoint_func: str,
        weighted_models: dict,
        task_id: str,
        prompt_content: str,
        priority: int = 10,
        dev_attempts: int = 5,
        dev_cost: float = 20.0,
        num_repeat: int = 1,
        max_exec: int = sys.maxsize,
    ):
        super().__init__(
            project_bundle=project_bundle,
            harness_name=harness_name,
            harness_entrypoint_func=harness_entrypoint_func,
            is_jvm=True,
            weighted_models=weighted_models,
            priority=priority,
            dev_attempts=dev_attempts,
            dev_cost=dev_cost,
            num_repeat=num_repeat,
            max_exec=max_exec,
        )
        self.task_id = task_id
        self.prompt_content = prompt_content

    def _get_prompt(self) -> str:
        """Override the prompt generation to use the provided content."""
        return self.prompt_content

    def get_label(self) -> str:
        """Return a label for the task."""
        return f"Exploit:{self.task_id}"
