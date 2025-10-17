import logging
import os
from typing import Any, Dict, override

from libAgents.base import (
    ActionPlugin,
    BaseKnowledge,
    ENABLE_IN_NEXT_ROUND,
    DISABLE_IN_NEXT_ROUND,
)
from libAgents.session import ResearchSession
from libAgents.utils.cmd import async_run_cmd

logger = logging.getLogger(__name__)


class SedKnowledge(BaseKnowledge):
    """
    A knowledge about sed.
    """

    start_line: int
    end_line: int
    file_path: str

    def knowledge_question(self) -> str:
        return f"What is the content of the file {self.file_path} between line {self.start_line} and {self.end_line}?"

    def knowledge_answer(self) -> str:
        return self.result


class SedPlugin(ActionPlugin):
    """
    A plugin template for manually copying and pasting.
    """

    @property
    @override
    def action_name(self) -> str:
        return "sed"

    @override
    def get_schema_properties(self, session: ResearchSession) -> Dict[str, Any]:
        return {
            "start_line": {
                "type": "integer",
                "description": "The start line of the range to print.",
            },
            "end_line": {
                "type": "integer",
                "description": "The end line of the range to print.",
            },
            "file_path": {
                "type": "string",
                "description": "The path to the file to perform sed operations on.",
            },
        }

    @override
    def get_prompt_section(self, session: ResearchSession) -> str:
        """
        Get the prompt section for the plugin.
        """
        return f"""<action-{self.action_name}>
- This action is used to perform sed (stream editor) operations for reading a file.
- It is used to print the lines between start_line and end_line in the file.
- Usually it can be combined with <ripgrep> plugin to perform generic code search, especially when there is no code-browser support.
- Put the start_line and end_line in the `start_line` and `end_line` fields.
- Put the path to the file to perform sed operations on in the `file_path` field.
- We prefer absolute path.
</action-{self.action_name}>"""

    async def do_sed(self, start_line: int, end_line: int, file_path: str) -> str:
        """
        Invoke the sed command.
        """
        return await async_run_cmd(
            ["sed", "-n", f"{start_line},{end_line}p", file_path]
        )

    @override
    async def handle(self, session: ResearchSession, _current_question: str) -> bool:
        """
        Handle the sed task.
        """
        start_line = session.get_action_param("start_line")
        end_line = session.get_action_param("end_line")
        file_path = session.get_action_param("file_path")

        if not os.path.exists(file_path):
            session.add_diary_entry(
                f"""At step {session.step}, you took **{self.action_name}** action for to print the lines between {start_line} and {end_line} in the file: {file_path}.
But the file does not exist: {file_path}
"""
            )
            logger.error(f"Error in sed: file does not exist: {file_path}")
            return DISABLE_IN_NEXT_ROUND

        result = await self.do_sed(start_line, end_line, file_path)

        if result.returncode != 0:
            session.add_diary_entry(
                f"""At step {session.step}, you took **{self.action_name}** action for to print the lines between {start_line} and {end_line} in the file: {file_path}.
But you failed to sed the file: {file_path}, 
stdout: 
{result.stdout.decode("utf-8", errors="ignore")}
stderr: 
{result.stderr.decode("utf-8", errors="ignore")}
"""
            )
            logger.error(
                f"Error in sed: returncode {result.returncode}, stdout: {result.stdout.decode('utf-8', errors='ignore')}, stderr: {result.stderr.decode('utf-8', errors='ignore')}"
            )
            return DISABLE_IN_NEXT_ROUND
        else:
            session.add_diary_entry(
                f"""At step {session.step}, you took **{self.action_name}** action for to print the lines between {start_line} and {end_line} in the file: {file_path}.
You successfully sed the file: {file_path}, 
result: {result.stdout.decode("utf-8", errors="ignore")}
"""
            )
            return ENABLE_IN_NEXT_ROUND
