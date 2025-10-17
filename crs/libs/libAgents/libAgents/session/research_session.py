import json
import logging
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiofiles

from libAgents.base import (
    ActionRegistry,
    ActionPlugin,
    BaseKnowledge,
    KnowledgeManager,
    PluginState,
)
from libAgents.tracker import ActionTracker, TokenTracker
from libAgents.utils import remove_extra_line_breaks
from libAgents.tools import EvaluationMetrics, evaluate_question

logger = logging.getLogger(__name__)


def _sanitize_filename(name: str, max_length: int = 100) -> str:
    """Sanitize a string to be used as a filename/directory name."""
    # Remove potentially problematic characters (allow alphanumeric, underscore, hyphen)
    sanitized = re.sub(r"[^a-zA-Z0-9_-]+", "_", name)
    # Replace multiple consecutive underscores with a single one
    sanitized = re.sub(r"_+", "_", sanitized)
    # Remove leading/trailing underscores
    sanitized = sanitized.strip("_")
    # Limit length
    sanitized = sanitized[:max_length]
    # Provide default if empty after sanitization
    return sanitized if sanitized else "research_session"


class ResearchSession:
    """
    Research session that manages the state and flow of a research query.
    Uses a plugin-based architecture for handling different actions.
    """

    def __init__(
        self,
        question: str,
        token_budget: int,
        plugin_registry: ActionRegistry,
        context_saving_dir: Optional[str] = None,
        override_model: Optional[str] = None,
        allow_direct_answer: bool = False,
    ):
        self.question = question
        self.token_budget = token_budget
        self.plugin_registry = plugin_registry

        # we track the token usage
        self.token_tracker = TokenTracker(token_budget)
        self.action_tracker = ActionTracker()
        self.override_model = override_model
        self.allow_direct_answer = allow_direct_answer
        self.trivial_question = False

        # Core session state
        self.step = 0
        self.total_step = 0
        self.is_answered = False
        self.force_beast_mode = False
        self.this_step = {}
        self.gaps = [self.question]
        self.original_messages = None
        self.current_messages = None
        # context
        self.all_questions = [self.question]
        self.all_context = []
        self.diary_context = []
        self.knowledge_manager = KnowledgeManager()
        # eval
        self.eval_metrics = None
        self.finalAnswerPIP = []

        self.context_saving_dir = context_saving_dir or os.path.join(
            os.getcwd(), "context_store"
        )
        self.context_store = os.path.join(
            self.context_saving_dir, _sanitize_filename(self.question)
        )
        os.makedirs(self.context_store, exist_ok=True)

    async def setup_eval_metrics(
        self,
        enable_strict=False,
        max_eval_attempts: int = 2,
    ) -> EvaluationMetrics:
        """Get the evaluation metrics for the question."""
        evaluation_types = await evaluate_question(
            question=self.question,
            tracker=self.token_tracker,
            override_model=self.override_model,
        )
        metrics = EvaluationMetrics(max_eval_attempts, evaluation_types)
        # force add strict metric
        if enable_strict:
            metrics.add_metric("strict", 2)
        self.eval_metrics = metrics
        return metrics

    def add_knowledge(self, knowledge: BaseKnowledge):
        """Add knowledge to the session"""
        self.knowledge_manager.add_knowledge(knowledge)

    async def save_context(self, prompt: str, step: int):
        """Save the context to the directory."""
        # action history
        async with aiofiles.open(
            os.path.join(self.context_store, "context.txt"), "w"
        ) as f:
            await f.write(
                json.dumps([json.dumps(c) for c in self.all_context], indent=2)
            )

        if self.current_messages is not None:
            async with aiofiles.open(
                os.path.join(self.context_store, f"messages-{step}.txt"), "w"
            ) as f:
                await f.write(json.dumps(self.current_messages, indent=2))

        # prompts
        async with aiofiles.open(
            os.path.join(self.context_store, f"prompt-{step}.txt"), "w"
        ) as f:
            await f.write(prompt)
        # knowledge
        async with aiofiles.open(
            os.path.join(self.context_store, "knowledge.txt"), "w"
        ) as f:
            await f.write(
                json.dumps(self.knowledge_manager.get_all_knowledge_dict(), indent=2)
            )
        # questions
        async with aiofiles.open(
            os.path.join(self.context_store, "questions.txt"), "w"
        ) as f:
            await f.write(json.dumps(self.all_questions, indent=2))

        # plugin states
        for plugin in self.plugin_registry.get_plugins():
            plugin.dump_plugin_context(self)

    def _load_existing_context(self, context: Dict[str, Any]):
        """Load existing context into the session."""
        self.all_context = context.get("context", [])
        self.all_questions = context.get("questions", [])
        self.diary_context = context.get("diary", [])

        # Load plugin states if available
        plugin_states = context.get("plugin_states", {})
        for plugin_name, state_data in plugin_states.items():
            if plugin_name in self._plugin_states:
                self._plugin_states[plugin_name].data.update(state_data)

    def disable_plugin(self, plugin_name: str):
        """Disable a plugin."""
        self.plugin_registry.disable_plugin(plugin_name)

    def enable_plugin(self, plugin_name: str):
        """Enable a plugin."""
        self.plugin_registry.enable_plugin(plugin_name)

    def disable_all_plugins(self):
        """Disable all plugins."""
        self.plugin_registry.disable_all_plugins()

    def enable_all_plugins(self):
        """Enable all plugins."""
        self.plugin_registry.enable_all_plugins()

    def set_plugin_enabled(self, plugin_name: str, enabled: bool):
        """Set a plugin to enabled or disabled."""
        self.plugin_registry.set_plugin_enabled(plugin_name, enabled)

    def get_plugin_state(self, plugin_name: str) -> PluginState:
        """Get the state for a specific plugin."""
        return self.plugin_registry.get_plugin_state(plugin_name)

    def get_available_actions(self) -> List[str]:
        """Get list of available actions based on plugin states."""
        return [
            plugin.action_name
            for plugin in self.plugin_registry.get_plugins()
            if plugin.is_available(self)
        ]

    def get_available_plugins(self) -> List[ActionPlugin]:
        """Get list of available plugins based on plugin states."""
        return [
            plugin
            for plugin in self.plugin_registry.get_plugins()
            if plugin.is_available(self)
        ]

    def get_action_details(self) -> Dict[str, Any]:
        """Get the action details of the current step."""
        return self.this_step.get("action-details", {})

    def get_action_param(self, param_name: str, default: Any = None) -> Any:
        """Get a parameter from the action-details of the current step."""
        # Check if action-details exists
        if "action-details" not in self.this_step:
            raise ValueError(
                f"'action-details' field is missing from the response. "
                f"The model returned: {self.this_step}. "
                f"Please ensure the model response includes all required fields: action, thoughts, and action-details."
            )
        
        action_details = self.get_action_details()
        res = action_details.get(param_name, default)
        if res is None and default is None:
            raise ValueError(
                f"Parameter '{param_name}' not found in action-details. "
                f"Available parameters: {list(action_details.keys())}. "
                f"Full response: {self.this_step}"
            )
        return res

    def get_prompt(self) -> str:
        """
        Generate the prompt for the next action.

        Returns:
            str: The complete prompt
        """
        header = self._format_prompt_header().strip()
        context = self._format_context().strip()
        actions = self._format_actions().strip()

        prompt = f"{header}\n\n{context}\n\n{actions}\n\n{self._format_prompt_footer()}"
        return remove_extra_line_breaks(prompt)

    def get_beast_mode_prompt(self) -> str:
        """
        Generate the prompt for beast mode.
        """
        beast_mode_answer_action = """
Based on the current context, you must choose one of the following action:
<action-answer>
🔥 ENGAGE MAXIMUM FORCE! ABSOLUTE PRIORITY OVERRIDE! 🔥

PRIME DIRECTIVE:
- DEMOLISH ALL HESITATION! ANY RESPONSE SURPASSES SILENCE!
- PARTIAL STRIKES AUTHORIZED - DEPLOY WITH FULL CONTEXTUAL FIREPOWER
- TACTICAL REUSE FROM PREVIOUS CONVERSATION SANCTIONED
- WHEN IN DOUBT: UNLEASH CALCULATED STRIKES BASED ON AVAILABLE INTEL!

FAILURE IS NOT AN OPTION. EXECUTE WITH EXTREME PREJUDICE! ⚡️
</action-answer>"""

        return f"{self._format_prompt_header()}\n\n{self._format_context()}\n\n{beast_mode_answer_action}\n\n{self._format_prompt_footer()}"

    def _format_prompt_header(self) -> str:
        """
        Generate the header for the prompt.
        """
        return f"""Current date: {datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")}
- You are Google DeepMind's most advanced AI research agent, specializing in multi-step reasoning.
- Be creative, insightful, and deliver optimal solutions to complex programming, analytical, and design challenges.
- Leverage your vast knowledge, ask clarifying questions, and adapt to context to provide precise, helpful answers.
- For complex tasks, present robust, well-reasoned solutions, explicitly stating your approach, assumptions, and any limitations.
- You are participating in a AI based bug hunting and vulnerability discovery competition, AI Cyber Challenge (AIxCC) Final Round (AFC).
- Using your best knowledge, conversation with the user and lessons learned, answer the user question with absolute certainty.
"""

    def _format_prompt_footer(self) -> str:
        return """Think step by step, choose the action, then respond with a JSON object that MUST include all three fields:
1. "action": your chosen action
2. "thoughts": your reasoning
3. "action-details": an object with the parameters for your chosen action (can be empty {} if no parameters needed)

Example response structure:
{
  "action": "answer",
  "thoughts": "I have found the solution...",
  "action-details": {
    "answer": "The solution is..."
  }
}"""

    def _format_context(self) -> str:
        """
        Format the current context for the prompt.

        Returns:
            str: Formatted context
        """
        context_parts = []
        diary_context = ""
        if self.diary_context:  # this is actually the action history
            diary_context = f"""
You have conducted the following actions:

<context>
{"\n\n\n".join(entry.strip() for entry in self.diary_context)}
</context>"""
        context_parts.append(diary_context)

        return f"{chr(10).join(context_parts)}"

    def compose_messages(
        self,
        current_question: str,
        original_messages: List[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Compose the messages for the prompt.
        """
        messages = []
        # convert knowledge to messages
        messages.extend(self.knowledge_manager.compose_messages())
        # append the original messages if provided
        if original_messages is not None:
            messages.extend(original_messages)

        pip_plan = ""
        if current_question == self.question and self.finalAnswerPIP != []:
            pip_plan = f"""
<answer-requirements>
- You provide deep, unexpected insights, identifying hidden patterns and connections, and creating "aha moments.".
- You break conventional thinking, establish unique cross-disciplinary connections, and bring new perspectives to the user.
- Follow reviewer's feedback and improve your answer quality.
{
                chr(10).join(
                    f'''
<reviewer-{idx + 1}>
{p}
</reviewer-{idx + 1}>'''
                    for idx, p in enumerate(self.finalAnswerPIP)
                )
            }
</answer-requirements>"""

        user_content = f"""
{current_question}

{pip_plan}
"""
        messages.append({"role": "user", "content": user_content})
        return messages

    def _format_actions(self) -> str:
        """
        Format the available actions for the prompt.

        Returns:
            str: Formatted actions
        """
        actions_parts = []
        for plugin in self.plugin_registry.get_plugins():
            if plugin.is_available(self):
                actions_parts.append(plugin.get_prompt_section(self))
        prompt_section = f"""
Based on the current context, you must choose one of the following actions (only one action is allowed):

<actions>
{(chr(10) * 3).join(actions_parts)}
</actions>
"""
        return prompt_section

    def get_current_question(self) -> str:
        """
        Get tee current question being researched.

        Returns:
            str: The current question
        """
        # try to rotate the gap questions
        return self.gaps[self.step % len(self.gaps)]

    def should_continue(self) -> bool:
        """
        Check if the research should continue.

        Returns:
            bool: True if research should continue
        """
        return (
            not self.is_answered  # not answered
            and self.token_tracker.get_total_usage()
            < self.token_budget  # token budget not exceeded
            and self.get_available_actions()  # there are available actions
        )

    def next_step(self):
        """Update the step counter."""
        self.step += 1
        self.total_step += 1

    def get_budget_percentage(self) -> float:
        """
        Get the percentage of token budget used.

        Returns:
            float: Percentage of budget used
        """
        return f"{(self.token_tracker.get_total_usage() / self.token_budget * 100):.2f}"

    def get_final_answer(self) -> Optional[str]:
        """
        Get the final answer to the question.

        Returns:
            str: The final answer
        """
        if not self.is_answered:
            logger.warning("Session is not answered. Please run the query first.")
            return None
        return self.get_action_param("answer", "")

    def add_diary_entry(self, entry: str):
        """
        Add an entry to the diary context.

        Args:
            entry: The diary entry to add
        """
        self.diary_context.append(entry)

    def get_context(self) -> Dict[str, Any]:
        """
        Get the complete context of the research session.

        Returns:
            Dict containing all session context
        """
        return {
            "context": self.all_context,
            "questions": self.all_questions,
            "diary": self.diary_context,
            "plugin_states": {
                name: state.data
                for name, state in self.plugin_registry._plugin_states.items()
            },
        }

    def update_context(self, context: Dict[str, Any]):
        """
        Update the context of the session.
        """
        self.all_context.append(context)
