import asyncio
import json
import logging
from typing import Any, Dict, Optional

from libAgents.config import get_model
from libAgents.error import handle_generate_object_error
from libAgents.model import generate_object
from libAgents.tracker import TokenTracker
from libAgents.tools.schemas import Schemas

logger = logging.getLogger(__name__)

TOOL_NAME = "queryRewriter"


def get_prompt(action: Dict[str, Any]) -> Dict[str, str]:
    """
    Build the prompt for query rewriting using the provided SearchAction.
    The action is expected to have at least 'searchQuery' and 'think' keys.
    """
    system_prompt = """You are an expert Information Retrieval query optimizer. Optimize user queries into precise keyword combinations with strategic reasoning and appropriate search operators.

<rules>
1. Generate search queries that directly include appropriate operators
2. Keep base keywords minimal: 2-3 words preferred
3. Use exact match quotes for specific phrases that must stay together
4. Split queries only when necessary for distinctly different aspects
5. Preserve crucial qualifiers while removing fluff words
6. Make the query resistant to SEO manipulation
7. When necessary, append <query-operators> at the end only when must needed


<query-operators>
A query can't only have operators; and operators can't be at the start a query;

- "phrase" : exact match for phrases
- +term : must include term; for critical terms that must appear
- -term : exclude term; exclude irrelevant or ambiguous terms
- filetype:pdf/doc : specific file type
- site:example.com : limit to specific site
- lang:xx : language filter (ISO 639-1 code)
- loc:xx : location filter (ISO 3166-1 code)
- intitle:term : term must be in title
- inbody:term : term must be in body text
</query-operators>

</rules>

<examples>
Input Query: What's the difference between ReactJS and Vue.js for building web applications?
<think>
This is a comparison query. User is likely looking for technical evaluation and objective feature comparisons, possibly for framework selection decisions. We'll split this into separate queries to capture both high-level differences and specific technical aspects.
</think>
Queries: [
  "react performance",
  "vue performance",
  "react vue comparison"
]

Input Query: How to fix a leaking kitchen faucet?
<think>
This is a how-to query seeking practical solutions. User likely wants step-by-step guidance and visual demonstrations for DIY repair. We'll target both video tutorials and written guides.
</think>
Output Queries: [
  "kitchen faucet leak repair",
  "faucet drip fix site:youtube.com",
  "how to repair faucet"
]

Input Query: What are healthy breakfast options for type 2 diabetes?
<think>
This is a health-specific informational query. User needs authoritative medical advice combined with practical meal suggestions. Splitting into medical guidelines and recipes will provide comprehensive coverage.
</think>
Output Queries: [
  "what to eat for type 2 diabetes",
  "type 2 diabetes breakfast guidelines",
  "diabetic breakfast recipes"
]

Input Query: Latest AWS Lambda features for serverless applications
<think>
This is a product research query focused on recent updates. User wants current information about specific technology features, likely for implementation purposes. We'll target official docs and community insights.
</think>
Output Queries: [
  "aws lambda features site:aws.amazon.com intitle:2025",
  "new features lambda serverless"
]
</examples>"""

    user_prompt = f"""Now, process this query:
Input Query: {action.get("searchQuery")}
Intention: {action.get("think")}"""

    return {
        "system": system_prompt,
        "user": user_prompt,
    }


async def rewrite_query(
    action: Dict[str, Any],
    tracker: Optional[TokenTracker] = None,
    override_model: Optional[str] = None,
    schemas: Optional[Schemas] = None,
) -> Dict[str, Any]:
    """
    Process the provided SearchAction to generate refined search queries.

    Returns a dictionary with:
      - "queries": a list of generated query strings.
      - "tokens": the number of tokens used.
    """
    try:
        if schemas is None:
            schemas = Schemas()

        model = get_model(TOOL_NAME, override_model)
        prompt = get_prompt(action)

        result = await generate_object(
            model=model,
            schema=schemas.get_query_rewriter_schema(),
            system=prompt["system"],
            prompt=prompt["user"],
        )

        obj = json.loads(result.object)
        tokens = result.usage.total_tokens

        logger.info(f"{TOOL_NAME}: %s", obj.get("queries"))
        (tracker or TokenTracker()).track_usage(TOOL_NAME, tokens)

        return {"queries": obj.get("queries"), "tokens": tokens}

    except Exception as error:
        logger.error(f"Error in {TOOL_NAME}: %s", error)
        try:
            # Handle error and get fallback result
            error_result = await handle_generate_object_error(error)
            obj = json.loads(error_result.object)
            tokens = error_result.usage.total_tokens
            (tracker or TokenTracker()).track_usage(TOOL_NAME, tokens)
            return {"queries": obj.get("queries", []), "tokens": tokens}
        except Exception as fallback_error:
            logger.error(f"Fallback error in {TOOL_NAME}: %s", fallback_error)
            raise error


# --- For local testing ---
if __name__ == "__main__":

    async def main():
        # Example SearchAction
        action_example = {
            "searchQuery": "difference between ReactJS and Vue.js",
            "think": "This is a comparison query. The user likely needs both high-level differences and specific technical aspects.",
        }
        result = await rewrite_query(action_example)
        logger.info("Rewrite result: %s", json.dumps(result, indent=2))

    asyncio.run(main())
