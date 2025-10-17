"""
JSON schemas for evaluator functionality.
"""

from datetime import datetime
from typing import Any, Dict, Optional


# Language ISO 639-1 mapping
LANGUAGE_ISO6391_MAP = {
    "en": "English",
    "zh": "Chinese",
    "zh-CN": "Simplified Chinese",
    "zh-TW": "Traditional Chinese",
    "de": "German",
    "fr": "French",
    "es": "Spanish",
    "it": "Italian",
    "ja": "Japanese",
    "ko": "Korean",
    "pt": "Portuguese",
    "ru": "Russian",
    "ar": "Arabic",
    "hi": "Hindi",
    "bn": "Bengali",
    "tr": "Turkish",
    "nl": "Dutch",
    "pl": "Polish",
    "sv": "Swedish",
    "no": "Norwegian",
    "da": "Danish",
    "fi": "Finnish",
    "el": "Greek",
    "he": "Hebrew",
    "hu": "Hungarian",
    "id": "Indonesian",
    "ms": "Malay",
    "th": "Thai",
    "vi": "Vietnamese",
    "ro": "Romanian",
    "bg": "Bulgarian",
}

# Constants
MAX_URLS_PER_STEP = 5
MAX_QUERIES_PER_STEP = 5
MAX_REFLECT_PER_STEP = 2


class Schemas:
    """Schema generator with language support."""

    def __init__(self):
        self.language_style: str = "formal English"
        self.language_code: str = "en"

    def set_language(self, lang_code: str, lang_style: Optional[str] = None):
        """Set language code and style."""
        if lang_code in LANGUAGE_ISO6391_MAP:
            self.language_code = lang_code
            self.language_style = (
                lang_style or f"formal {LANGUAGE_ISO6391_MAP[lang_code]}"
            )
        else:
            self.language_code = "en"
            self.language_style = "formal English"

    def get_language_prompt(self) -> str:
        """Get language prompt for schema descriptions."""
        return f'Must in the first-person in "lang:{self.language_code}"; in the style of "{self.language_style}".'

    def get_language_schema(self) -> Dict[str, Any]:
        """Schema for language detection."""
        return {
            "type": "object",
            "properties": {
                "langCode": {
                    "type": "string",
                    "description": "ISO 639-1 language code",
                    "maxLength": 10,
                },
                "langStyle": {
                    "type": "string",
                    "description": "[vibe & tone] in [what language], such as formal english, informal chinese, technical german, humor english, slang, genZ, emojis etc.",
                    "maxLength": 100,
                },
            },
            "required": ["langCode", "langStyle"],
        }

    def get_question_evaluate_schema(self) -> Dict[str, Any]:
        """Schema for question evaluation."""
        return {
            "type": "object",
            "properties": {
                "think": {
                    "type": "string",
                    "description": f"A very concise explain of why those checks are needed. {self.get_language_prompt()}",
                    "maxLength": 500,
                },
                "needsDefinitive": {
                    "type": "boolean",
                    "description": "Whether the question requires definitive evaluation",
                },
                "needsFreshness": {
                    "type": "boolean",
                    "description": "Whether the question requires freshness evaluation",
                },
                "needsPlurality": {
                    "type": "boolean",
                    "description": "Whether the question requires plurality evaluation",
                },
                "needsCompleteness": {
                    "type": "boolean",
                    "description": "Whether the question requires completeness evaluation",
                },
            },
            "required": [
                "think",
                "needsDefinitive",
                "needsFreshness",
                "needsPlurality",
                "needsCompleteness",
            ],
        }

    def get_evaluator_schema(self, eval_type: str) -> Dict[str, Any]:
        """Get schema for specific evaluation type."""
        base_schema_before = {
            "think": {
                "type": "string",
                "description": f"Explanation the thought process why the answer does not pass the evaluation, {self.get_language_prompt()}",
                "maxLength": 500,
            }
        }

        base_schema_after = {
            "pass": {
                "type": "boolean",
                "description": "If the answer passes the test defined by the evaluator",
            }
        }

        if eval_type == "definitive":
            return {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": ["definitive"]},
                    **base_schema_before,
                    **base_schema_after,
                },
                "required": ["type", "think", "pass"],
            }

        elif eval_type == "freshness":
            return {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": ["freshness"]},
                    **base_schema_before,
                    "freshness_analysis": {
                        "type": "object",
                        "properties": {
                            "days_ago": {
                                "type": "number",
                                "description": f"datetime of the **answer** and relative to {datetime.now().strftime('%Y-%m-%d')}.",
                                "minimum": 0,
                            },
                            "max_age_days": {
                                "type": "number",
                                "description": "Maximum allowed age in days for this kind of question-answer type before it is considered outdated",
                            },
                        },
                        "required": ["days_ago", "max_age_days"],
                    },
                    "pass": {
                        "type": "boolean",
                        "description": 'If "days_ago" <= "max_age_days" then pass!',
                    },
                },
                "required": ["type", "think", "freshness_analysis", "pass"],
            }

        elif eval_type == "plurality":
            return {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": ["plurality"]},
                    **base_schema_before,
                    "plurality_analysis": {
                        "type": "object",
                        "properties": {
                            "minimum_count_required": {
                                "type": "number",
                                "description": "Minimum required number of items from the **question**",
                            },
                            "actual_count_provided": {
                                "type": "number",
                                "description": "Number of items provided in **answer**",
                            },
                        },
                        "required": ["minimum_count_required", "actual_count_provided"],
                    },
                    "pass": {
                        "type": "boolean",
                        "description": "If count_provided >= count_expected then pass!",
                    },
                },
                "required": ["type", "think", "plurality_analysis", "pass"],
            }

        elif eval_type == "completeness":
            return {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": ["completeness"]},
                    **base_schema_before,
                    "completeness_analysis": {
                        "type": "object",
                        "properties": {
                            "aspects_expected": {
                                "type": "string",
                                "description": "Comma-separated list of all aspects or dimensions that the question explicitly asks for.",
                                "maxLength": 100,
                            },
                            "aspects_provided": {
                                "type": "string",
                                "description": "Comma-separated list of all aspects or dimensions that were actually addressed in the answer",
                                "maxLength": 100,
                            },
                        },
                        "required": ["aspects_expected", "aspects_provided"],
                    },
                    **base_schema_after,
                },
                "required": ["type", "think", "completeness_analysis", "pass"],
            }

        elif eval_type == "strict":
            return {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": ["strict"]},
                    **base_schema_before,
                    "improvement_plan": {
                        "type": "string",
                        "description": 'Explain how a perfect answer should look like and what are needed to improve the current answer. Starts with "For the best answer, you must..."',
                        "maxLength": 1000,
                    },
                    **base_schema_after,
                },
                "required": ["type", "think", "improvement_plan", "pass"],
            }

        else:
            raise ValueError(f"Unknown evaluation type: {eval_type}")

    def get_code_generator_schema(self) -> Dict[str, Any]:
        """Schema for code generation."""
        return {
            "type": "object",
            "properties": {
                "think": {
                    "type": "string",
                    "description": f"Short explain or comments on the thought process behind the code. {self.get_language_prompt()}",
                    "maxLength": 200,
                },
                "code": {
                    "type": "string",
                    "description": "The JavaScript code that solves the problem and always use 'return' statement to return the result. Focus on solving the core problem; No need for error handling or try-catch blocks or code comments. No need to declare variables that are already available, especially big long strings or arrays.",
                },
            },
            "required": ["think", "code"],
        }

    def get_error_analysis_schema(self) -> Dict[str, Any]:
        """Schema for error analysis."""
        return {
            "type": "object",
            "properties": {
                "recap": {
                    "type": "string",
                    "description": "Recap of the actions taken and the steps conducted in first person narrative.",
                    "maxLength": 500,
                },
                "blame": {
                    "type": "string",
                    "description": f"Which action or the step was the root cause of the answer rejection. {self.get_language_prompt()}",
                    "maxLength": 500,
                },
                "improvement": {
                    "type": "string",
                    "description": f"Suggested key improvement for the next iteration, do not use bullet points, be concise and hot-take vibe. {self.get_language_prompt()}",
                    "maxLength": 500,
                },
            },
            "required": ["recap", "blame", "improvement"],
        }

    def get_query_rewriter_schema(self) -> Dict[str, Any]:
        """Schema for query rewriting."""
        return {
            "type": "object",
            "properties": {
                "think": {
                    "type": "string",
                    "description": f"Explain why you choose those search queries. {self.get_language_prompt()}",
                    "maxLength": 500,
                },
                "queries": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "description": "Search query, must be less than 30 characters",
                        "maxLength": 30,
                    },
                    "maxItems": MAX_QUERIES_PER_STEP,
                    "description": f"Array of search queries, orthogonal to each other. Maximum {MAX_QUERIES_PER_STEP} queries allowed.",
                },
            },
            "required": ["think", "queries"],
        }


# Create a default instance for backward compatibility
default_schemas = Schemas()

# Legacy schema exports for backward compatibility
definitive_schema = default_schemas.get_evaluator_schema("definitive")
freshness_schema = default_schemas.get_evaluator_schema("freshness")
plurality_schema = default_schemas.get_evaluator_schema("plurality")
completeness_schema = default_schemas.get_evaluator_schema("completeness")
strict_schema = default_schemas.get_evaluator_schema("strict")
question_evaluate_schema = default_schemas.get_question_evaluate_schema()
language_schema = default_schemas.get_language_schema()
code_generator_schema = default_schemas.get_code_generator_schema()
error_analysis_schema = default_schemas.get_error_analysis_schema()
query_rewriter_schema = default_schemas.get_query_rewriter_schema()
