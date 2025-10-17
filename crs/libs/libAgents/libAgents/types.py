from enum import Enum
from typing import Dict, List, Literal, Optional, Union

from pydantic import BaseModel

from libAgents.tracker import ActionTracker, TokenTracker


class SchemaType(str, Enum):
    STRING = "string"
    ARRAY = "array"
    OBJECT = "object"
    BOOLEAN = "boolean"

    def __str__(self):
        return f"'{self.value}'"

    def __repr__(self):
        return f"'{self.value}'"

    def json(self):
        return f"'{self.value}'"

    def __json__(self):  # Adding this for completeness
        return f"'{self.value}'"


# ----------------------------------
# Action Types
# ----------------------------------


class BaseAction(BaseModel):
    action: Literal[
        "search", "answer", "reflect", "visit"
    ]  # TODO: two extra actions: code_search (visit?) and debugger_run? (or simply run?)
    thoughts: str


class SearchAction(BaseAction):
    action: Literal["search"]
    searchQuery: str


class Reference(BaseModel):
    exactQuote: str
    url: str


class AnswerAction(BaseAction):
    action: Literal["answer"]
    answer: str
    references: List[Reference]


class ReflectAction(BaseAction):
    action: Literal["reflect"]
    questionsToAnswer: List[str]


class VisitAction(BaseAction):
    action: Literal["visit"]
    URLTargets: List[str]


class CodeSearchAction(BaseAction):
    action: Literal["codesearch"]
    CodeSearchTargets: List[str]


class XRefAction(BaseAction):
    action: Literal["xref"]
    XRefTargets: List[str]


# StepAction can be any of the four action types.
StepAction = Union[SearchAction, AnswerAction, ReflectAction, VisitAction]


# ----------------------------------
# Response Types
# ----------------------------------


class TokenUsage(BaseModel):
    tool: str
    tokens: int


class Usage(BaseModel):
    tokens: int


class SearchResponseDataItem(BaseModel):
    title: str
    description: str
    url: str
    content: str
    usage: Usage


class SearchResponse(BaseModel):
    code: int
    status: int
    data: Optional[List[SearchResponseDataItem]]
    name: Optional[str] = None
    message: Optional[str] = None
    readableMessage: Optional[str] = None


class BraveSearchResult(BaseModel):
    title: str
    description: str
    url: str


class BraveSearchWeb(BaseModel):
    results: List[BraveSearchResult]


class BraveSearchResponse(BaseModel):
    web: BraveSearchWeb


class DedupResponse(BaseModel):
    thought: str
    unique_queries: List[str]


class ReadResponse(BaseModel):
    code: int
    status: int
    data: Optional[SearchResponseDataItem] = None
    name: Optional[str] = None
    message: Optional[str] = None
    readableMessage: Optional[str] = None


class EvaluationResponse(BaseModel):
    is_definitive: bool
    reasoning: str


class ErrorAnalysisResponse(BaseModel):
    recap: str
    blame: str
    improvement: str


class SearchResult(BaseModel):
    title: str
    url: str
    description: str


class QueryResult(BaseModel):
    query: str
    results: List[SearchResult]


class StepData(BaseModel):
    step: int
    question: str
    action: str
    reasoning: str
    searchQuery: Optional[str] = None
    result: Optional[List[QueryResult]] = None


class KeywordsResponse(BaseModel):
    thought: str
    queries: List[str]


# ----------------------------------
# Schema Types
# ----------------------------------

# Note: There is a circular reference between SchemaProperty and SchemaPropertyItems.
# We can work around that by using forward references.


class SchemaPropertyItems(BaseModel):
    type: SchemaType
    description: Optional[str] = None
    properties: Optional[Dict[str, "SchemaProperty"]] = None  # Forward reference
    required: Optional[List[str]] = None


class SchemaProperty(BaseModel):
    type: SchemaType
    description: str
    enum: Optional[List[str]] = None
    items: Optional[SchemaPropertyItems] = None
    properties: Optional[Dict[str, "SchemaProperty"]] = None  # Forward reference
    required: Optional[List[str]] = None
    maxItems: Optional[int] = None


# Resolve forward references
# SchemaPropertyItems.update_forward_refs()
# SchemaProperty.update_forward_refs()
SchemaPropertyItems.model_rebuild()
SchemaProperty.model_rebuild()


class ResponseSchema(BaseModel):
    type: SchemaType
    properties: Dict[str, SchemaProperty]
    required: List[str]


# ----------------------------------
# Stream Message Types
# ----------------------------------


class Budget(BaseModel):
    used: int
    total: int
    percentage: str


class StreamMessage(BaseModel):
    type: Literal["progress", "answer", "error"]
    data: Union[str, StepAction]
    step: Optional[int] = None
    budget: Optional[Budget] = None


class TrackerContext(BaseModel):
    tokenTracker: TokenTracker
    actionTracker: ActionTracker

    class Config:
        # Allow arbitrary types (i.e. non-Pydantic objects) as fields.
        arbitrary_types_allowed = True


# ----------------------------------
# Example usage:
# ----------------------------------
if __name__ == "__main__":
    token_tracker = TokenTracker(budget=1000)
    action_tracker = ActionTracker()

    context = TrackerContext(tokenTracker=token_tracker, actionTracker=action_tracker)

    print("Total token usage:", context.tokenTracker.get_total_usage())
    print("Current action state:", context.actionTracker.get_state())
