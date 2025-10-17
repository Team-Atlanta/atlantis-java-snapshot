import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, override

from pydantic import Field

from libAgents.base import (
    ActionPlugin,
    ENABLE_IN_NEXT_ROUND,
    DISABLE_IN_NEXT_ROUND,
    BaseKnowledge,
)
from libAgents.session import ResearchSession
from libAgents.tools import OpenAICodex, OpenAICodexConfig
from libAgents.config import get_model
from libAgents.utils import cd

logger = logging.getLogger(__name__)


class CodebaseKnowledge(BaseKnowledge):
    """
    Knowledge about codebase questions and answers from OpenAI Codex.
    """

    question: str = Field(description="The question asked about the codebase")
    answer: str = Field(description="The answer provided by OpenAI Codex")

    def knowledge_question(self) -> str:
        return self.question

    def knowledge_answer(self) -> str:
        return self.answer


class AskCodebasePlugin(ActionPlugin):
    """
    A plugin that uses OpenAI Codex to answer questions about the current codebase.
    """

    def __init__(
        self, project_name: str, src_path: Path, model_name: Optional[str] = None
    ):
        # Model selection priority: self.model_name > session.override_model > global_model_name
        self.model_name = model_name
        self.project_name = project_name
        self.src_path = src_path
        self.codex = None  # Will be initialized in _get_codex()

    def _get_model_name(self, session: ResearchSession) -> str:
        """Get the model name with proper priority handling."""
        model_name = (
            self.model_name if self.model_name is not None else session.override_model
        )
        if model_name is None:
            # Use the global model configuration for codex tool
            global_model = get_model("codex")
            model_name = global_model.model_name
        return model_name

    def _setup_api_credentials(self, session: ResearchSession):
        """Setup API credentials similar to coder.py."""
        global_model = get_model("codex", self.model_name)

        # Set up API base URL if provided
        if global_model.base_url is not None and global_model.base_url != "":
            os.environ["OPENAI_BASE_URL"] = global_model.base_url

        # Set up API key
        os.environ["OPENAI_API_KEY"] = global_model.api_key

    def _get_codex(self, session: ResearchSession) -> OpenAICodex:
        """Get or create the OpenAI Codex instance with proper configuration."""
        if self.codex is None:
            # Setup API credentials
            self._setup_api_credentials(session)

            # Get the model name
            model_name = self._get_model_name(session)

            # Create codex configuration
            config = OpenAICodexConfig(
                model_name=model_name,
                quiet=True,
                use_json=True,
                verbose=False,
                full_auto=True,
                skip_permissions=False,
                cwd=os.getcwd(),
            )

            self.codex = OpenAICodex(config)
            logger.debug(
                f"[{self.action_name}] Initialized OpenAI Codex with model: {model_name}"
            )

        return self.codex

    @property
    @override
    def action_name(self) -> str:
        return "ask-codebase"

    @override
    def get_schema_properties(self, session: ResearchSession) -> Dict[str, Any]:
        return {
            "question": {
                "type": "string",
                "description": "The question to ask the oracle. The question should be about the current codebase.",
            },
        }

    @override
    def get_prompt_section(self, session: ResearchSession) -> str:
        """
        Get the prompt section for the plugin.
        """
        return f"""<action-{self.action_name}>
- Ask the codebase oracle specific questions about the current codebase structure, implementation details, or functionality.
- Use this when you need to understand:
  * How specific functions or classes work
  * Code architecture and design patterns
  * Implementation details of particular features
  * Dependencies and relationships between components
  * Best practices followed in the codebase
  * Debugging assistance for specific code sections
- Frame questions clearly and specifically (e.g., "How does the authentication system work?" rather than "Tell me about auth")
- The oracle has deep knowledge of the entire codebase and can provide detailed technical explanations
- Answers will be automatically added to your knowledge base for future reference
</action-{self.action_name}>"""

    def add_codebase_knowledge(
        self, session: ResearchSession, question: str, answer: str
    ) -> None:
        """
        Add the codebase knowledge to the session.
        """
        codebase_knowledge = CodebaseKnowledge(
            source=self.action_name,
            knowledge_type="codebase_oracle",
            question=question,
            answer=answer,
        )
        session.add_knowledge(codebase_knowledge)

    @override
    async def handle(self, session: ResearchSession, current_question: str) -> bool:
        """
        Handle the ask-codebase task by using OpenAI Codex to answer questions about the codebase.
        """
        try:
            # Extract the question from action details
            question = session.get_action_param("question")

            if not question:
                logger.warning(f"[{self.action_name}] No question provided")
                session.add_diary_entry(
                    f"""At step {session.step}, you took **{self.action_name}** action.
However, no question was provided to ask the oracle.
"""
                )
                return ENABLE_IN_NEXT_ROUND

            logger.debug(f"[{self.action_name}] Asking codex: {question}")

            # Get the properly configured codex instance
            codex = self._get_codex(session)

            # Use OpenAI Codex to answer the question about the codebase
            with cd(self.src_path):
                answer = await codex.async_query(question)

            if not answer:
                logger.warning(f"[{self.action_name}] No answer received from codex")
                session.add_diary_entry(
                    f"""At step {session.step}, you took **{self.action_name}** action.
You asked the oracle: "{question}"
However, the oracle did not provide any answer.
"""
                )
                return ENABLE_IN_NEXT_ROUND

            # Add structured knowledge to the session
            self.add_codebase_knowledge(session, question, answer)

            # Add the result to the session diary
            session.add_diary_entry(
                f"""At step {session.step}, you took **{self.action_name}** action.
You asked the oracle: "{question}"

The oracle responded:
{answer}

This information has been added to your knowledge base <Codebase Oracle Knowledge>.
"""
            )

            logger.debug(
                f"[{self.action_name}] Successfully got answer from codex and added to knowledge base"
            )
            return ENABLE_IN_NEXT_ROUND

        except Exception as e:
            logger.error(f"[{self.action_name}] Error: {e}")
            session.add_diary_entry(
                f"""At step {session.step}, you took **{self.action_name}** action.
But encountered an error: {str(e)}
"""
            )
            return DISABLE_IN_NEXT_ROUND
