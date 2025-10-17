import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


# Define your custom exception class if not already defined.
class NoObjectGeneratedError(Exception):
    def __init__(self, text: str, usage: Optional[Dict[str, Any]] = None):
        super().__init__(text)
        self.text = text
        self.usage = usage if usage is not None else {}


async def handle_generate_object_error(error: Exception) -> Dict[str, Any]:
    """
    Handles errors from generate_object.

    If the error is an instance of NoObjectGeneratedError, this function will attempt to
    manually parse a partial JSON response from error.text and return it along with the token usage.
    Otherwise, it will re-raise the error.

    Returns:
        A dictionary with keys:
            - "object": The parsed object.
            - "totalTokens": The number of tokens used (or 0 if not available).
    """
    if isinstance(error, NoObjectGeneratedError):
        logger.debug(
            "Object not generated according to the schema, fallback to manual parsing"
        )
        try:
            partial_response = json.loads(error.text)
            total_tokens = error.usage.get("totalTokens", 0) if error.usage else 0
            return {"object": partial_response, "totalTokens": total_tokens}
        except Exception:
            # If parsing fails, re-raise the original error.
            raise error
    raise error
