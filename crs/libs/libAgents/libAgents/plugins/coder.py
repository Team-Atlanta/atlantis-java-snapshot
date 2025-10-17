import logging
import os
import aiofiles
from typing import Any, Dict, List, Optional, override
from pydantic import Field
from pathlib import Path

from libAgents.base import (
    ActionPlugin,
    BaseKnowledge,
    ENABLE_IN_NEXT_ROUND,
)
from libAgents.utils.utils import cd
from libAgents.session import ResearchSession
from libAgents.config import get_model
from libAgents.tools import AiderCoder
from aider.models import Model

logger = logging.getLogger(__name__)


class GeneratedCodeKnowledge(BaseKnowledge):
    """
    Knowledge about the generated code.
    """

    coding_task: str = Field(
        description="The coding task that the generated code is for."
    )
    code_path: str = Field(description="The path to the generated code.")
    code_content: str = Field(description="The content of the generated code.")

    def knowledge_question(self) -> str:
        return f"What is the solution to the coding issue: {self.coding_task}?"

    def knowledge_answer(self) -> str:
        return self.code_content


class CoderPlugin(ActionPlugin):
    """
    A plugin for coding tasks.

    The plugin currently uses tee Aider library to generate code.
    https://aider.chat/

    My assumption and coding senario:
    - We have a large codebase to be analyzed (e.g., OSS repo)
    - We want to write new codes based on the user-query and analysis (e.g., a fuzzing corpus generator)
    - based on the assumtion, I hard-coded parameters for coder plugin
    - If you need a different senario, please create a new plugin
    """

    def __init__(
        self,
        project_name: str,
        main_repo: Path,
        model_name: Optional[str] = None,
        fnames: List[str] = None,
        ro_fnames: List[str] = None,
        working_dir: Optional[Path] = None,
        output_cache: bool = False,
    ):
        self.project_name = project_name
        self.fnames = fnames if fnames is not None else []
        self.ro_fnames = ro_fnames if ro_fnames is not None else []
        self.main_repo = main_repo
        self.output_cache = output_cache

        # model selection priority
        # self.model_name > session.override_model > global_model_name
        self.model_name = model_name

        # if working_dir is not provided, use the main_repo
        if working_dir is not None:
            self.working_dir = working_dir
        else:
            self.working_dir = main_repo

        global_model = get_model("aider_coder", self.model_name)

        # TODO: can we support token tracker
        if global_model.base_url is not None and global_model.base_url != "":
            os.environ["OPENAI_API_BASE"] = global_model.base_url
        # FIXME: is it okay to override the api key?
        os.environ["OPENAI_API_KEY"] = global_model.api_key

    @property
    @override
    def action_name(self) -> str:
        return "AI-coding"

    @override
    def get_schema_properties(self, session: ResearchSession) -> Dict[str, Any]:
        return {
            "coding_task": {
                "type": "string",
                "description": "The coding task to be completed. It should include all necessary details for the coder to complete the task.",
            },
            "script_name": {
                "type": "string",
                "description": "The name of the script to be created.",
            },
            "context_files": {
                "type": "array",
                "description": (
                    "The code files paths you think the coder needs to know for success. "
                    "(e.g., absolute paths ['/src/main.c', '/src/utils.c']) "
                    "Leave it empty if you don't need any context."
                    "Only pass the file paths, not the directory paths."
                ),
                "items": {
                    "type": "string",
                },
            },
        }

    def __get_model_name(self, session: ResearchSession) -> str:
        model_name = (
            self.model_name if self.model_name is not None else session.override_model
        )
        if model_name is None:
            model_name = get_model("aider_coder").model_name
        if "/" not in model_name:
            if "claude" in model_name:
                model_name = f"anthropic/{model_name}"
            elif "gemini" in model_name:
                model_name = f"gemini/{model_name}"
            else:
                model_name = f"openai/{model_name}"
        return model_name

    def handle_coding_task(
        self,
        session: ResearchSession,
        fnames: List[str],
        ro_fnames: List[str],
        coding_task: str,
    ) -> str:
        """
        Handle the coding task.
        """
        context_store = session.context_store
        chat_history_file = os.path.join(context_store, "aider_chat_history.txt")

        model_name = self.__get_model_name(session)

        logger.debug(f"AiderCoder with model: {model_name}")
        coder = AiderCoder(
            main_model=Model(model_name),
            repo_path=self.main_repo,
            chat_history_file=chat_history_file,
            working_dir=self.working_dir,
        )
        coder.add_files(fnames)
        coder.add_ro_files(ro_fnames)

        coder.get_repo_map()

        # run the coder with given instruction
        output = coder.run(coding_task)

        # token tracking
        session.token_tracker.track_usage("aider_coder", coder.message_tokens_sent)
        session.token_tracker.track_usage("aider_coder", coder.message_tokens_received)

        total_cost = coder.total_cost
        return output, total_cost

    @override
    def get_prompt_section(self, session: ResearchSession) -> str:
        """
        Get the prompt section for the plugin.
        """
        return f"""<action-{self.action_name}>
- Using the popular AI coder -- Aider to write a python script to fulfill the coding task.
- You need to provide a comprehensive description to help the underlying coder understand the coding task.
</action-{self.action_name}>"""

    def add_generated_code_knowledge(
        self,
        session: ResearchSession,
        coding_task: str,
        code_path: str | Path,
        code_content: str,
    ) -> None:
        """
        Add the generated code to the session.
        """
        # Convert Path to string if necessary
        code_path_str = (
            str(code_path.resolve()) if isinstance(code_path, Path) else code_path
        )

        generated_code_knowledge = GeneratedCodeKnowledge(
            source=self.action_name,
            knowledge_type="AI-Coder Knowledge",
            metadata={},
            coding_task=coding_task,
            code_path=code_path_str,
            code_content=code_content,
        )
        session.add_knowledge(generated_code_knowledge)

    @override
    async def handle(self, session: ResearchSession, current_question: str) -> bool:
        """
        Handle the coding task.
        """
        action = session.get_action_details()
        # avoid the shallow copy issue
        fnames = []
        ro_fnames = list(action.get("context_files", []))
        ro_fnames = list(filter(lambda x: os.path.isfile(x), ro_fnames))
        coding_task = action.get("coding_task", "")
        script_name = action.get("script_name", "")

        if not coding_task:
            raise ValueError("Coding task is required")
        if not script_name:
            raise ValueError("Script name is required")

        # aider tips mentioned we need to add the file to the repo
        script_path = Path(self.working_dir) / f"{script_name}"

        script_path.touch()
        fnames.append(script_path)

        TASK_PROMPT = f"""
To Solve the main problem,
<main_problem>
{session.question}
</main_problem>

We propose the following coding task to solve the main problem:
<coding_task>
{coding_task}
</coding_task>

OUTPUT INSTRUCTION
please write the code in the file path:
<file_path>
{script_path}
</file_path>
"""

        with cd(self.working_dir):
            output, _ = self.handle_coding_task(session, fnames, ro_fnames, TASK_PROMPT)
        # print(output)

        async with aiofiles.open(script_path, "r") as f:
            content = await f.read()

        session.add_diary_entry(f"""
At step {session.step}, you took **{self.action_name}** action.
To answer the question, you proposed the following coding task:
{coding_task}

You successfully completed the coding task and accumulated the newly generated codes into your knowledge base <{self.action_name.title()} Knowledge>:
""")

        self.add_generated_code_knowledge(session, coding_task, script_path, content)

        return ENABLE_IN_NEXT_ROUND
