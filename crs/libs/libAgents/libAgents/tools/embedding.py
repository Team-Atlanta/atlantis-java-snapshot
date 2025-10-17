import logging
from typing import List, Optional, Dict, Any
from openai import AsyncOpenAI

from libAgents.config import (
    OPENAI_API_KEY,
    LLM_PROVIDER,
    LITELLEM_KEY,
    LITELLEM_BASE_URL,
)
from libAgents.tracker import TokenTracker

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "text-embedding-3-large"  # OpenAI's embedding model


async def get_embeddings(
    texts: List[str], tracker: Optional[TokenTracker] = None
) -> Dict[str, Any]:
    """
    Get embeddings for a list of texts using OpenAI's embedding model.

    Args:
        texts: List of text strings to get embeddings for
        tracker: Optional token tracker for usage tracking

    Returns:
        Dictionary containing embeddings list and token usage
    """
    try:
        # Determine which API key and base URL to use
        if LLM_PROVIDER == "openai":
            api_key = OPENAI_API_KEY
        elif LLM_PROVIDER == "litellm":
            api_key = LITELLEM_KEY
            base_url = LITELLEM_BASE_URL
        else:
            # Fallback to OpenAI
            api_key = OPENAI_API_KEY

        if not api_key:
            logger.warning(
                "No API key available for embeddings, returning empty embeddings"
            )
            return {"embeddings": [], "tokens": 0}

        # Create OpenAI client
        if LLM_PROVIDER == "openai":
            client = AsyncOpenAI(
                api_key=api_key,
            )
        elif LLM_PROVIDER == "litellm":
            client = AsyncOpenAI(api_key=api_key, base_url=base_url)

        # Get embeddings
        response = await client.embeddings.create(model=EMBEDDING_MODEL, input=texts)

        # Extract embeddings
        embeddings = [data.embedding for data in response.data]
        tokens = response.usage.total_tokens

        # Track token usage
        if tracker:
            tracker.track_usage("embeddings", tokens)

        return {"embeddings": embeddings, "tokens": tokens}

    except Exception as error:
        logger.error(f"Error getting embeddings: {error}")
        # Return empty embeddings on error to allow graceful fallback
        return {"embeddings": [], "tokens": 0}


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Calculate cosine similarity between two vectors.

    Args:
        vec1: First vector
        vec2: Second vector

    Returns:
        Cosine similarity score between 0 and 1
    """
    try:
        # Calculate dot product
        dot_product = sum(a * b for a, b in zip(vec1, vec2))

        # Calculate magnitudes
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5

        # Avoid division by zero
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        # Calculate cosine similarity
        similarity = dot_product / (magnitude1 * magnitude2)

        # Ensure result is between 0 and 1
        return max(0.0, min(1.0, similarity))

    except Exception as error:
        logger.error(f"Error calculating cosine similarity: {error}")
        return 0.0
