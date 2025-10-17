from typing import Any, Dict, List
import re

from libAgents.base import BaseKnowledge


class KnowledgeManager:
    def __init__(self):
        self._knowledge: Dict[str, List[BaseKnowledge]] = {}  # source -> knowledge list
        self._knowledge_by_type: Dict[str, List[BaseKnowledge]] = {}

    def add_knowledge(self, knowledge: BaseKnowledge):
        """Add knowledge to the manager"""
        # Store by source
        if knowledge.source not in self._knowledge:
            self._knowledge[knowledge.source] = []
        self._knowledge[knowledge.source].append(knowledge)

        # Store by type
        if knowledge.knowledge_type not in self._knowledge_by_type:
            self._knowledge_by_type[knowledge.knowledge_type] = []
        self._knowledge_by_type[knowledge.knowledge_type].append(knowledge)

    def get_knowledge_by_source(self, source: str) -> List[BaseKnowledge]:
        """Get all knowledge from a specific source"""
        return self._knowledge.get(source, [])

    def get_knowledge_by_type(self, knowledge_type: str) -> List[BaseKnowledge]:
        """Get all knowledge of a specific type"""
        return self._knowledge_by_type.get(knowledge_type, [])

    def get_all_knowledge(self) -> List[BaseKnowledge]:
        """Get all knowledge"""
        return [k for k_list in self._knowledge.values() for k in k_list]

    def get_all_knowledge_dict(self) -> List[Dict[str, Any]]:
        return [k.model_dump() for k_list in self._knowledge.values() for k in k_list]

    def compose_messages(self) -> List[Dict[str, Any]]:
        """Compose messages from all knowledge"""
        messages = []
        for knowledge in self.get_all_knowledge():
            messages.append({"role": "user", "content": knowledge.knowledge_question()})
            messages.append(
                {"role": "assistant", "content": knowledge.knowledge_answer()}
            )
        return messages

    def get_knowledge_str(self) -> List[str]:
        """
        Format all knowledge items similar to the JavaScript getKnowledgeStr function.
        Returns a list of formatted knowledge strings with just question and answer.
        """
        all_knowledge = self.get_all_knowledge()
        formatted_knowledge = []

        for idx, knowledge in enumerate(all_knowledge):
            # Get the basic question and answer
            question = knowledge.knowledge_question()
            answer = knowledge.knowledge_answer()

            # Simple format with just question and answer
            formatted_msg = f"""<knowledge-{idx + 1}>
{question}

{answer}
</knowledge-{idx + 1}>"""

            # Remove extra line breaks
            formatted_msg = self._remove_extra_line_breaks(formatted_msg)
            formatted_knowledge.append(formatted_msg)

        return formatted_knowledge

    def _remove_extra_line_breaks(self, text: str) -> str:
        """Remove extra line breaks similar to the JavaScript removeExtraLineBreaks function"""
        # Replace multiple consecutive newlines with at most 2 newlines
        return re.sub(r"\n{3,}", "\n\n", text.strip())
