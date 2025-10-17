import random
from typing import Any, Dict, List, Optional

from libAgents.tracker import TokenTracker
from libAgents.tools.embedding import get_embeddings, cosine_similarity

SIMILARITY_THRESHOLD = 0.86  # Adjustable threshold for cosine similarity


def choose_k(items: List[str], k: int) -> List[str]:
    """
    Randomly sample k items from the list without repetition.

    Args:
        items: List of items to sample from
        k: Number of items to sample

    Returns:
        List of k randomly selected items (or all items if k >= len(items))
    """
    if k >= len(items):
        return items.copy()

    # Create a copy and shuffle it
    shuffled = items.copy()
    random.shuffle(shuffled)

    # Return first k items
    return shuffled[:k]


async def dedup_queries(
    new_queries: List[str],
    existing_queries: List[str],
    tracker: Optional[TokenTracker] = None,
) -> Dict[str, Any]:
    """
    Deduplicate queries by removing duplicates based on semantic similarity using embeddings.

    Args:
        new_queries (List[str]): List of new queries to deduplicate.
        existing_queries (List[str]): List of existing queries to compare against.
        tracker (Optional[TokenTracker]): Token tracker for usage tracking.
        override_model (Optional[str]): Not used in embedding-based approach, kept for compatibility.

    Returns:
        Dict containing unique_queries list and token count.
    """
    try:
        # Quick return for single new query with no existing queries
        if len(new_queries) == 1 and len(existing_queries) == 0:
            return {"unique_queries": new_queries, "tokens": 0}

        # Get embeddings for all queries in one batch
        all_queries = new_queries + existing_queries
        embedding_result = await get_embeddings(all_queries, tracker)
        all_embeddings = embedding_result["embeddings"]
        tokens = embedding_result["tokens"]

        # If embeddings is empty (due to error), return all new queries
        if not all_embeddings:
            return {"unique_queries": new_queries, "tokens": 0}

        # Split embeddings back into new and existing
        new_embeddings = all_embeddings[: len(new_queries)]
        existing_embeddings = all_embeddings[len(new_queries) :]

        unique_queries: List[str] = []
        used_indices = set()

        # Compare each new query against existing queries and already accepted queries
        for i in range(len(new_queries)):
            is_unique = True

            # Check against existing queries
            for j in range(len(existing_queries)):
                similarity = cosine_similarity(
                    new_embeddings[i], existing_embeddings[j]
                )
                if similarity >= SIMILARITY_THRESHOLD:
                    is_unique = False
                    break

            # Check against already accepted queries
            if is_unique:
                for used_index in used_indices:
                    similarity = cosine_similarity(
                        new_embeddings[i], new_embeddings[used_index]
                    )
                    if similarity >= SIMILARITY_THRESHOLD:
                        is_unique = False
                        break

            # Add to unique queries if passed all checks
            if is_unique:
                unique_queries.append(new_queries[i])
                used_indices.add(i)

        print("Dedup:", unique_queries)
        return {"unique_queries": unique_queries, "tokens": tokens}

    except Exception as error:
        print("Error in deduplication analysis:", error)
        # Return all new queries if there is an error
        return {"unique_queries": new_queries, "tokens": 0}
