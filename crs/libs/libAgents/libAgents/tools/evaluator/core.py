"""
Core evaluator functionality.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from libAgents.config import get_model
from libAgents.error import handle_generate_object_error
from libAgents.model import generate_object
from libAgents.tracker import TokenTracker

from libAgents.tools.schemas import Schemas
from .prompts import (
    get_definitive_prompt,
    get_freshness_prompt,
    get_plurality_prompt,
    get_completeness_prompt,
    get_reject_all_answers_prompt,
    get_question_evaluation_prompt,
)

logger = logging.getLogger(__name__)

TOOL_NAME = "evaluator"


class EvaluationMetrics:
    """Metrics for evaluation"""

    def __init__(
        self,
        max_attempts: int = 2,
        evaluation_types: Optional[List[str]] = None,
    ):
        self.metrics: Dict[str, int] = {}  # metric_type -> number of attempts left
        self.allowed_metrics: List[str] = []
        self.max_attempts = max_attempts

        if evaluation_types is not None:
            self.add_metrics(evaluation_types)

    @property
    def length(self) -> int:
        return len(self.metrics)

    @property
    def is_empty(self) -> bool:
        return len(self.metrics) == 0

    def get_available_metrics(self) -> List[str]:
        return [
            metric_type
            for metric_type, attempts in self.metrics.items()
            if attempts > 0
        ]

    def add_metric(self, metric_type: str, attempts_left: int):
        if metric_type in self.metrics:
            logger.warning(f"Metric type {metric_type} already exists")
        self.metrics[metric_type] = attempts_left

    def add_metrics(self, metric_types: List[str], attempts: Optional[int] = None):
        if attempts is None:
            attempts = self.max_attempts
        for metric_type in metric_types:
            self.add_metric(metric_type, attempts)

    def get_attempts_left(self, metric_type: str) -> int:
        if metric_type not in self.metrics:
            raise ValueError(f"Metric type {metric_type} not found")
        return self.metrics[metric_type]

    def decrement_attempts(self, metric_type: str):
        if metric_type in self.metrics:
            self.metrics[metric_type] -= 1
            if self.metrics[metric_type] == 0:
                del self.metrics[metric_type]
        else:
            logger.error(f"Metric type {metric_type} not found")


async def perform_evaluation(
    evaluation_type: str,
    prompt: Dict[str, str],
    tracker: Optional[TokenTracker] = None,
    override_model: Optional[str] = None,
    schemas: Optional[Schemas] = None,
) -> Dict[str, Any]:
    """Perform a single evaluation with the given prompt."""
    model = get_model(TOOL_NAME, override_model)

    if schemas is None:
        schemas = Schemas()

    # Get schema for the evaluation type
    schema = schemas.get_evaluator_schema(evaluation_type)

    result = await generate_object(
        model=model,
        schema=schema,
        system=prompt["system"],
        prompt=prompt["user"],
    )

    obj = json.loads(result.object)
    (tracker or TokenTracker()).track_usage(TOOL_NAME, result.usage.total_tokens)

    logger.debug(f"{evaluation_type.title()} Evaluation: {json.dumps(obj, indent=2)}")

    return obj


async def evaluate_answer(
    question: str,
    answer: str,
    evaluation_types: List[str],
    tracker: Optional[TokenTracker] = None,
    all_knowledge: Optional[List[str]] = None,
    override_model: Optional[str] = None,
    schemas: Optional[Schemas] = None,
) -> Dict[str, Any]:
    """
    Evaluates an answer against the given question using multiple evaluation criteria.
    Returns the evaluation result object directly, matching the TypeScript EvaluationResponse type.
    """
    if all_knowledge is None:
        all_knowledge = []

    if schemas is None:
        schemas = Schemas()

    result: Optional[Dict[str, Any]] = None

    for evaluation_type in evaluation_types:
        try:
            prompt = None

            if evaluation_type == "definitive":
                prompt = get_definitive_prompt(question, answer)
            elif evaluation_type == "freshness":
                prompt = get_freshness_prompt(
                    question, answer, datetime.utcnow().isoformat()
                )
            elif evaluation_type == "plurality":
                prompt = get_plurality_prompt(question, answer)
            elif evaluation_type == "completeness":
                prompt = get_completeness_prompt(question, answer)
            elif evaluation_type == "strict":
                prompt = get_reject_all_answers_prompt(question, answer, all_knowledge)
            else:
                logger.error(f"Unknown evaluation type: {evaluation_type}")
                continue

            if prompt:
                result = await perform_evaluation(
                    evaluation_type, prompt, tracker, override_model, schemas
                )

                # If evaluation fails, return immediately
                if not result.get("pass"):
                    return result

        except Exception as error:
            logger.error(f"Error evaluating answer: {error}")
            error_result = await handle_generate_object_error(error)
            (tracker or TokenTracker()).track_usage(
                TOOL_NAME, error_result.usage.total_tokens
            )
            obj = json.loads(error_result.object)
            return obj

    # If all evaluations pass, return the last result
    return result


async def evaluate_question(
    question: str,
    tracker: Optional[TokenTracker] = None,
    override_model: Optional[str] = None,
    schemas: Optional[Schemas] = None,
) -> List[str]:
    """
    Evaluates a question to determine what types of evaluation checks are needed.
    Returns a list of evaluation types that should be performed on answers to this question.
    """
    try:
        if schemas is None:
            schemas = Schemas()

        model = get_model(TOOL_NAME, override_model)
        prompt = get_question_evaluation_prompt(question)

        result = await generate_object(
            model=model,
            schema=schemas.get_question_evaluate_schema(),
            system=prompt["system"],
            prompt=prompt["user"],
        )

        obj = json.loads(result.object)
        (tracker or TokenTracker()).track_usage(TOOL_NAME, result.usage.total_tokens)

        logger.debug(f"Question Evaluation: {json.dumps(obj, indent=2)}")

        # Build list of evaluation types based on the result
        types: List[str] = []
        if obj.get(
            "needsDefinitive", True
        ):  # Default to True since definitive is usually needed
            types.append("definitive")
        if obj.get("needsFreshness", False):
            types.append("freshness")
        if obj.get("needsPlurality", False):
            types.append("plurality")
        if obj.get("needsCompleteness", False):
            types.append("completeness")

        logger.debug(f"Question Metrics: {question} -> {types}")

        return types

    except Exception as error:
        logger.error(f"Error in question evaluation: {error}")
        # Default to no evaluation on error
        return []
