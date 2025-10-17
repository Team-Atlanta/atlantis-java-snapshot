"""
Evaluator module for answer and question evaluation.
"""

from .core import (
    EvaluationMetrics,
    evaluate_answer,
    evaluate_question,
    perform_evaluation,
)
from libAgents.tools.schemas import (
    Schemas,
    definitive_schema,
    freshness_schema,
    plurality_schema,
    completeness_schema,
    strict_schema,
    question_evaluate_schema,
    language_schema,
    code_generator_schema,
    error_analysis_schema,
    query_rewriter_schema,
    LANGUAGE_ISO6391_MAP,
    MAX_URLS_PER_STEP,
    MAX_QUERIES_PER_STEP,
    MAX_REFLECT_PER_STEP,
)
from .prompts import (
    get_definitive_prompt,
    get_freshness_prompt,
    get_plurality_prompt,
    get_completeness_prompt,
    get_reject_all_answers_prompt,
    get_question_evaluation_prompt,
)

__all__ = [
    # Core functions and classes
    "EvaluationMetrics",
    "evaluate_answer",
    "evaluate_question",
    "perform_evaluation",
    "Schemas",
    # Legacy schemas for backward compatibility
    "definitive_schema",
    "freshness_schema",
    "plurality_schema",
    "completeness_schema",
    "strict_schema",
    "question_evaluate_schema",
    # New schemas
    "language_schema",
    "code_generator_schema",
    "error_analysis_schema",
    "query_rewriter_schema",
    # Constants
    "LANGUAGE_ISO6391_MAP",
    "MAX_URLS_PER_STEP",
    "MAX_QUERIES_PER_STEP",
    "MAX_REFLECT_PER_STEP",
    # Prompts
    "get_definitive_prompt",
    "get_freshness_prompt",
    "get_plurality_prompt",
    "get_completeness_prompt",
    "get_reject_all_answers_prompt",
    "get_question_evaluation_prompt",
]
