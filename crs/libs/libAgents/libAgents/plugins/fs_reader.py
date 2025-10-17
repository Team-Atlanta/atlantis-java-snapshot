import logging
import aiofiles
from typing import Any, Dict, override

from pydantic import Field

from libAgents.base import (
    DISABLE_IN_NEXT_ROUND,
    ENABLE_IN_NEXT_ROUND,
    ActionPlugin,
    BaseKnowledge,
)
from libAgents.session import ResearchSession
from pathlib import Path

logger = logging.getLogger(__name__)


class FileKnowledge(BaseKnowledge):
    """
    A knowledge base for files.
    """

    file_path: str = Field(description="The path to the file to read.")
    mode: str = Field(description="The mode to read the file in.")
    content: str = Field(description="The content of the file.")

    def knowledge_question(self) -> str:
        return f"What is the content of the file {self.file_path}?"

    def knowledge_answer(self) -> str:
        return self.content


class FsReaderPlugin(ActionPlugin):
    """
    A plugin for reading files from the file system.
    """

    def __init__(self):
        self.checked_files = set()

    @property
    @override
    def action_name(self) -> str:
        return "file-reader"

    @override
    def get_schema_properties(self, session: ResearchSession) -> Dict[str, Any]:
        return {
            "file_path": {
                "type": "string",
                "description": "The path to the file to read.",
            },
            "mode": {
                "type": "string",
                "description": "The mode to read the file in.",
                "enum": ["text", "binary"],
            },
        }

    @override
    def get_prompt_section(self, session: ResearchSession) -> str:
        """
        Get the prompt section for the plugin.
        We need to decrible the action in a way that is easy for the LLM to understand.
        """
        return f"""<action-{self.action_name}>
- This action is used to read files from the local file system.
- You need to specify a valid file path and a mode to read.
- The file path must be a valid path to a file in the local file system, and don't guess the file path.
- The mode should be either "text" or "binary".
- Use this action carefully, it is expensive and can overload the token budget.
- If you have already checked the file, you can skip this action.
</action-{self.action_name}>"""

    async def read_file(self, file_path: str, mode: str) -> str:
        """
        Read the file at the given path.
        """
        if mode == "text":
            flag = "r"
        elif mode == "binary":
            flag = "rb"
        else:
            raise ValueError(f"Invalid mode: {mode}")

        async with aiofiles.open(file_path, flag) as file:
            return await file.read()

    @override
    async def handle(self, session: ResearchSession, current_question: str) -> bool:
        """
        Handle the template task.
        """
        file_path = session.get_action_param("file_path")
        mode = session.get_action_param("mode")

        if not file_path or not Path(file_path).exists():
            logger.debug(
                f"❗[{self.action_name}] No file path provided or file does not exist: {file_path}"
            )
            session.add_diary_entry(
                f"""At step {session.step}, you took **{self.action_name}** action.
But you did not specify any file path to read.
"""
            )
            return DISABLE_IN_NEXT_ROUND

        if file_path in self.checked_files:
            logger.debug(
                f"[warning][{self.action_name}] File already checked: {file_path}"
            )
            session.add_diary_entry(
                f"""At step {session.step}, you took **{self.action_name}** action.
But you already checked the file at path: {file_path}
"""
            )
            return DISABLE_IN_NEXT_ROUND

        try:
            content = await self.read_file(file_path, mode)
            # logger.debug(f"[debug][{self.action_name}] Content: {content}")
            self.add_file_knowledge(session, file_path, mode, content)

            session.add_diary_entry(
                f"""At step {session.step}, you took **{self.action_name}** action.
As a result, you successfully read the file at path: {file_path} and store the file content into your knowledge base <{self.action_name.title()} Knowledge>:
"""
            )
            self.checked_files.add(file_path)

            return ENABLE_IN_NEXT_ROUND
        except Exception as e:
            logger.error(f"[error][{self.action_name}] Failed to read file: {e}")
            session.add_diary_entry(
                f"""At step {session.step}, you took **{self.action_name}** action.
But you failed to read the file at path: {file_path}, error: {e}
"""
            )
            return DISABLE_IN_NEXT_ROUND

    def add_file_knowledge(
        self, session: ResearchSession, file_path: str, mode: str, content: str
    ) -> None:
        file_knowledge = FileKnowledge(
            source=self.action_name,
            knowledge_type="file",
            metadata={},
            file_path=file_path,
            mode=mode,
            content=content,
        )
        session.add_knowledge(file_knowledge)
