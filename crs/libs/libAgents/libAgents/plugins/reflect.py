import logging
from typing import Any, Dict, Optional, override

from libAgents.base import ActionPlugin, ENABLE_IN_NEXT_ROUND, DISABLE_IN_NEXT_ROUND
from libAgents.session import ResearchSession
from libAgents.tools import dedup_queries, choose_k

logger = logging.getLogger(__name__)


class ReflectPlugin(ActionPlugin):
    """Plugin for handling reflect actions."""

    @property
    @override
    def action_name(self) -> str:
        return "reflect"

    @override
    def is_available(self, session: ResearchSession) -> bool:
        """Check if reflect action is available."""
        plugin_state = session.get_plugin_state(self.action_name)
        return plugin_state.enabled and len(session.gaps) <= 1

    @override
    def get_prompt_section(self, session: ResearchSession) -> str:
        """Get the prompt section for the reflect action."""
        return """<action-reflect>
- Think slowly and planning lookahead. Examine <question>, <context>, previous conversation with users to identify knowledge gaps. 
- Reflect the gaps and plan a list key clarifying questions that deeply related to the original question and lead to the answer
</action-reflect>"""

    @override
    def get_schema_properties(
        self, session: ResearchSession
    ) -> Optional[Dict[str, Any]]:
        """Get the schema properties for reflect action."""
        return {
            "questionsToAnswer": {
                "type": "array",
                "items": {
                    "type": "string",
                    "description": (
                        """Ensure each reflection question:
 - Cuts to core emotional truths while staying anchored to <og-question>
 - Transforms surface-level problems into deeper psychological insights, helps answer <og-question>
 - Makes the unconscious conscious
 - NEVER pose general questions like: "How can I verify the accuracy of information before including it in my answer?", "What information was actually contained in the URLs I found?", "How can i tell if a source is reliable?". 
"""
                    ),
                },
                "description": (
                    f"Required when action='reflect'. Reflection and planing, generate a list of most important questions to fill the knowledge gaps to <og-question> {session.get_current_question()} </og-question>. Maximum provide 2 reflect questions."
                ),
                "maxItems": 2,
            }
        }

    @override
    async def handle(self, session: ResearchSession, current_question: str) -> bool:
        """Handle the reflect action."""
        questions_to_answer = session.get_action_param("questionsToAnswer")
        questions_to_answer_copy = questions_to_answer.copy()
        deduped = await dedup_queries(
            new_queries=questions_to_answer,
            existing_queries=session.all_questions,
            tracker=session.token_tracker,
        )
        unique_questions = deduped.get("unique_queries", [])
        new_gap_questions = choose_k(unique_questions, k=2)

        if new_gap_questions:
            session.add_diary_entry(
                f"""
At step {session.step}, you took **reflect** and think about the knowledge gaps. You found some sub-questions are important to the question: "{current_question}"
You realize you need to know the answers to the following sub-questions:
{chr(10).join(f"- {q}" for q in new_gap_questions)}

You will now figure out the answers to these sub-questions and see if they can help you find the answer to the original question.
""",
            )
            session.gaps.extend(new_gap_questions)
            session.all_questions.extend(new_gap_questions)

            return ENABLE_IN_NEXT_ROUND
        else:
            session.add_diary_entry(
                f"""
At step {session.step}, you took **reflect** and think about the knowledge gaps. You tried to break down the question "{current_question}" into gap-questions like this: {", ".join(questions_to_answer_copy)} 
But then you realized you have asked them before. You decided to to think out of the box or cut from a completely different angle. 
"""
            )
            return DISABLE_IN_NEXT_ROUND
