import logging
from typing import Any, Dict, override

from libAgents.base import (
    ActionPlugin,
    BaseKnowledge,
    ENABLE_IN_NEXT_ROUND,
)
from libAgents.session import ResearchSession
from libAgents.utils.cmd import async_run_cmd
from pydantic import Field

logger = logging.getLogger(__name__)


class DirectoryKnowledge(BaseKnowledge):
    """
    Knowledge about the directory.
    """

    directory_path: str = Field(description="The path to the directory.")
    contents: str = Field(description="The contents of the directory.")

    def knowledge_question(self) -> str:
        return f"What is the content of the directory {self.directory_path}?"

    def knowledge_answer(self) -> str:
        return self.contents


class ListDirPlugin(ActionPlugin):
    """
    A plugin for listing the files in a directory.
    """

    @property
    @override
    def action_name(self) -> str:
        return "list_dir"

    @override
    def get_schema_properties(self, session: ResearchSession) -> Dict[str, Any]:
        return {
            "dir_path": {
                "type": "string",
                "description": "The path to the directory to list the files in. (i.e., the `ls` command in the shell) We prefer absolute path.",
            },
            "option": {
                "type": "string",
                "description": "The options to pass to the `ls` command. (i.e., the `ls` command in the shell), default is `none` (no options)",
                "enum": ["none", "-l", "-a", "-h", "-R", "-r", "-t", "-S", "-X"],
            },
        }

    @override
    def get_prompt_section(self, session: ResearchSession) -> str:
        """
        Get the prompt section for the plugin.
        """
        return f"""<action-{self.action_name}>
- This action is used to list the files in a directory (i.e., the `ls` command in the shell).
- Put the path to the directory in the `dir_path` field.
- We prefer absolute path.
- Put the option to pass to the `ls` command in the `option` field.
</action-{self.action_name}>"""

    def add_directory_knowledge(
        self, session: ResearchSession, directory_path: str, contents: str
    ) -> None:
        """
        Add the directory knowledge to the session.
        """
        directory_knowledge = DirectoryKnowledge(
            source=self.action_name,
            knowledge_type=self.action_name,
            directory_path=directory_path,
            contents=contents,
        )
        session.add_knowledge(directory_knowledge)

    @override
    async def handle(self, session: ResearchSession, current_question: str) -> bool:
        """
        Handle the list directory task.
        """
        action = session.get_action_details()
        dir_path = action.get("dir_path", "")
        option = action.get("option", "")

        if not dir_path:
            logger.warning("ListDirPlugin: dir_path is required")
            return ENABLE_IN_NEXT_ROUND

        if option not in ["-l", "-a", "-h", "-R", "-r", "-t", "-S", "-X", "none"]:
            logger.warning(f"ListDirPlugin: Invalid option {option}")
            return ENABLE_IN_NEXT_ROUND

        cmd = ["ls"]
        if option != "none":
            cmd.append(option)
        cmd.append(dir_path)
        contents = await async_run_cmd(cmd)

        if contents.returncode != 0:
            logger.error(
                f"Error listing directory {dir_path}: {contents.stderr.decode('utf-8', errors='ignore')}"
            )
            session.add_diary_entry(f"""
At step {session.step}, you took **{self.action_name}** action.
You tried to list the files in the directory 
{dir_path}:

However, you encountered an error:
{contents.stderr.decode("utf-8", errors="ignore")}

You should avoid using this directory in the future.
""")
            return ENABLE_IN_NEXT_ROUND

        session.add_diary_entry(f"""
At step {session.step}, you took **{self.action_name}** action".

You successfully listed the files in the directory 
{dir_path}:

You added the directory listing results to your knowledge base <{self.action_name.title()} Knowledge>.
""")

        self.add_directory_knowledge(
            session, dir_path, contents.stdout.decode("utf-8", errors="ignore")
        )
        return ENABLE_IN_NEXT_ROUND  # or DISABLE_IN_NEXT_ROUND
