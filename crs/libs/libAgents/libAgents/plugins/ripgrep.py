import logging
import os
from typing import Any, Dict, Optional, override

from libAgents.base import (
    ENABLE_IN_NEXT_ROUND,
    DISABLE_IN_NEXT_ROUND,
    ActionPlugin,
    BaseKnowledge,
)
from libAgents.session import ResearchSession
from libAgents.utils.cmd import async_run_cmd, CmdExecutionResult

logger = logging.getLogger(__name__)


class RipGrepKnowledge(BaseKnowledge):
    """
    A knowledge about ripgrep.
    """

    pattern: str
    search_path: str
    result: str

    def knowledge_question(self) -> str:
        return f"What is the content when I grep for the pattern {self.pattern} in the search path {self.search_path}?"

    def knowledge_answer(self) -> str:
        return self.result


class RipGrepPlugin(ActionPlugin):
    """
    A plugin for ripgrep tasks.
    """

    @property
    @override
    def action_name(self) -> str:
        return "ripgrep"

    @override
    def get_schema_properties(
        self, session: ResearchSession
    ) -> Optional[Dict[str, Any]]:
        return {
            "pattern": {
                "type": "string",
                "description": "The regular expression used by ripgrep to search for.",
            },
            "path": {
                "type": "string",
                "description": "the path to search for the pattern",
            },
        }

    @override
    def get_prompt_section(self, session: ResearchSession) -> str:
        """
        Get the prompt section for the plugin.
        """
        return f"""<action-{self.action_name}>
- This action allows you to perform grep searches using ripgrep.
- We will do `rg -i -n pattern path` for you.
</action-{self.action_name}>"""

    async def do_ripgrep(self, pattern: str, search_path: str) -> CmdExecutionResult:
        """
        Invoke the ripgrep.
        """
        cmd = [
            "rg",
            "-i",
            "-n",
            pattern,
            search_path,
            "-A",
            5,
            "-B",
            2,
        ]
        return await async_run_cmd(cmd)

    @override
    async def handle(self, session: ResearchSession, current_question: str) -> bool:
        """
        Handle the ripgrep task.
        """
        pattern = session.get_action_param("pattern")
        search_path = session.get_action_param("path")

        if not os.path.exists(search_path):
            session.add_diary_entry(
                f"""At step {session.step}, you took **{self.action_name}** action.
But you provided a non-existing path: {search_path} to ripgrep.
"""
            )
            return ENABLE_IN_NEXT_ROUND

        result = await self.do_ripgrep(pattern, search_path)

        if result.returncode != 0:
            session.add_diary_entry(
                f"""At step {session.step}, you took **{self.action_name}** action".
But you failed to ripgrep the pattern: {pattern} in the path: {search_path}, error: {result.stderr.decode("utf-8", errors="ignore")}
And you should avoid using this pattern+path combination in the future.
"""
            )
            logger.error(
                f"Error in ripgrep: returncode {result.returncode}, stdout: {result.stdout.decode('utf-8', errors='ignore')}, stderr: {result.stderr.decode('utf-8', errors='ignore')}"
            )
            return DISABLE_IN_NEXT_ROUND
        else:
            output = result.stdout.decode("utf-8", errors="ignore")
            session.add_diary_entry(
                f"""At step {session.step}, you took **{self.action_name}** action.
You successfully ripgreped the pattern: {pattern} in the path: {search_path}, result: {output}
"""
            )

        return ENABLE_IN_NEXT_ROUND

    def add_ripgrep_knowledge(
        self, session: ResearchSession, pattern: str, search_path: str, result: str
    ):
        """
        Add the ripgrep knowledge to the session.
        """
        ripgrep_knowledge = RipGrepKnowledge(
            source=self.action_name,
            knowledge_type="ripgrep",
            pattern=pattern,
            search_path=search_path,
            result=result,
        )
        session.add_knowledge(ripgrep_knowledge)
