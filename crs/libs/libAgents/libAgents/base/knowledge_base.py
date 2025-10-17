from typing import Any, Dict

from pydantic import BaseModel, Field


class BaseKnowledge(BaseModel):
    """Base class for all knowledge types"""

    source: str = Field(description="Source of the knowledge")
    knowledge_type: str = Field(description="Type of knowledge")

    def to_dict(self) -> Dict[str, Any]:
        """Convert the instance to a dictionary for storage"""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseKnowledge":
        """Create an instance from a dictionary"""
        return cls.model_validate(data)

    def knowledge_question(self) -> str:
        raise NotImplementedError("Subclasses didn't implement knowledge_question")

    def knowledge_answer(self) -> str:
        raise NotImplementedError("Subclasses didn't implement knowledge_answer")

    def format_for_prompt(self) -> str:
        """Format the knowledge for inclusion in LLM prompt"""
        raise NotImplementedError("Subclasses didn't implement format_for_prompt")
