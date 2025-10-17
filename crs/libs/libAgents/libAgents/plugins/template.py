import logging
from typing import Any, Dict, override

from libAgents.base import ActionPlugin, ENABLE_IN_NEXT_ROUND
from libAgents.session import ResearchSession

logger = logging.getLogger(__name__)


class TemplatePlugin(ActionPlugin):
    """
    A plugin template for manually copying and pasting.
    """

    def __init__(self):
        pass

    @property
    @override
    def action_name(self) -> str:
        return "template"

    @override
    def get_schema_properties(self, session: ResearchSession) -> Dict[str, Any]:
        return {}

    @override
    def get_prompt_section(self, session: ResearchSession) -> str:
        """
        Get the prompt section for the plugin.
        """
        return f"""<action-{self.action_name}>
- This action is used to demonstrate the plugin.
- It is not used in the actual workflow.
</action-{self.action_name}>"""

    @override
    async def handle(self, session: ResearchSession, current_question: str) -> bool:
        """
        Handle the template task.
        """
        return ENABLE_IN_NEXT_ROUND  # or DISABLE_IN_NEXT_ROUND
