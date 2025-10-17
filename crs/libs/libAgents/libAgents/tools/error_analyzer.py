import json
import logging
from typing import Any, Dict, List, Optional

from libAgents.config import get_model
from libAgents.error import handle_generate_object_error
from libAgents.model import generate_object
from libAgents.tracker import TokenTracker
from libAgents.tools.schemas import Schemas

TOOL_NAME = "errorAnalyzer"


logger = logging.getLogger(__name__)


def get_prompt(diary_context: List[str]) -> Dict[str, str]:
    """
    Build the prompt for error analysis using the provided diary context.
    """
    system_prompt = """You are an expert at analyzing search and reasoning processes. Your task is to analyze the given sequence of steps and identify what went wrong in the search process.

<rules>
1. The sequence of actions taken
2. The effectiveness of each step
3. The logic between consecutive steps
4. Alternative approaches that could have been taken
5. Signs of getting stuck in repetitive patterns
6. Whether the final answer matches the accumulated information

Analyze the steps and provide detailed feedback following these guidelines:
- In the recap: Summarize key actions chronologically, highlight patterns, and identify where the process started to go wrong
- In the blame: Point to specific steps or patterns that led to the inadequate answer
- In the improvement: Provide actionable suggestions that could have led to a better outcome
</rules>

<example>
<input>
<steps>

At step 1, you took the **search** action and look for external information for the question: "how old is jina ai ceo?".
In particular, you tried to search for the following keywords: "jina ai ceo age".
You found quite some information and add them to your URL list and **visit** them later when needed. 


At step 2, you took the **visit** action and deep dive into the following URLs:
https://www.linkedin.com/in/hxiao87
https://www.crunchbase.com/person/han-xiao
You found some useful information on the web and add them to your knowledge for future reference.


At step 3, you took the **search** action and look for external information for the question: "how old is jina ai ceo?".
In particular, you tried to search for the following keywords: "Han Xiao birthdate, Jina AI founder birthdate".
You found quite some information and add them to your URL list and **visit** them later when needed. 


At step 4, you took the **search** action and look for external information for the question: "how old is jina ai ceo?".
In particular, you tried to search for the following keywords: han xiao birthday. 
But then you realized you have already searched for these keywords before.
You decided to think out of the box or cut from a completely different angle.


At step 5, you took the **search** action and look for external information for the question: "how old is jina ai ceo?".
In particular, you tried to search for the following keywords: han xiao birthday. 
But then you realized you have already searched for these keywords before.
You decided to think out of the box or cut from a completely different angle.


At step 6, you took the **visit** action and deep dive into the following URLs:
https://kpopwall.com/han-xiao/
https://www.idolbirthdays.net/han-xiao
You found some useful information on the web and add them to your knowledge for future reference.


At step 7, you took **answer** action but evaluator thinks it is not a good answer:

</steps>

Original question: 
how old is jina ai ceo?

Your answer: 
The age of the Jina AI CEO cannot be definitively determined from the provided information.

The evaluator thinks your answer is bad because: 
The answer is not definitive and fails to provide the requested information.  Lack of information is unacceptable, more search and deep reasoning is needed.
</input>


<output>
{
  "recap": "The search process consisted of 7 steps with multiple search and visit actions. The initial searches focused on basic biographical information through LinkedIn and Crunchbase (steps 1-2). When this didn't yield the specific age information, additional searches were conducted for birthdate information (steps 3-5). The process showed signs of repetition in steps 4-5 with identical searches. Final visits to entertainment websites (step 6) suggested a loss of focus on reliable business sources.",
  
  "blame": "The root cause of failure was getting stuck in a repetitive search pattern without adapting the strategy. Steps 4-5 repeated the same search, and step 6 deviated to less reliable entertainment sources instead of exploring business journals, news articles, or professional databases. Additionally, the process didn't attempt to triangulate age through indirect information like education history or career milestones.",
  
  "improvement": "1. Avoid repeating identical searches and implement a strategy to track previously searched terms. 2. When direct age/birthdate searches fail, try indirect approaches like: searching for earliest career mentions, finding university graduation years, or identifying first company founding dates. 3. Focus on high-quality business sources and avoid entertainment websites for professional information. 4. Consider using industry event appearances or conference presentations where age-related context might be mentioned. 5. If exact age cannot be determined, provide an estimated range based on career timeline and professional achievements.",
 
}
</output>
</example>"""

    user_prompt = "\n".join(diary_context)

    return {
        "system": system_prompt,
        "user": user_prompt,
    }


async def analyze_steps(
    diary_context: List[str],
    tracker: Optional[TokenTracker] = None,
    override_model: Optional[str] = None,
    schemas: Optional[Schemas] = None,
) -> Dict[str, Any]:
    """
    Analyze the provided diary context and return an error analysis response.
    """
    try:
        if schemas is None:
            schemas = Schemas()

        prompt = get_prompt(diary_context)
        model = get_model(TOOL_NAME, override_model)

        result = await generate_object(
            model=model,
            schema=schemas.get_error_analysis_schema(),
            system=prompt["system"],
            prompt=prompt["user"],
        )

        obj = json.loads(result.object)
        tokens = result.usage.total_tokens

        # Track token usage
        (tracker or TokenTracker()).track_usage(TOOL_NAME, tokens)

        return obj

    except Exception as error:
        logger.error(f"Error in {TOOL_NAME}:", error)
        try:
            # Handle error and get fallback result
            error_result = await handle_generate_object_error(error)
            obj = json.loads(error_result.object)
            tokens = error_result.usage.total_tokens
            (tracker or TokenTracker()).track_usage(TOOL_NAME, tokens)
            return obj
        except Exception as fallback_error:
            logger.error(f"Fallback error in {TOOL_NAME}:", fallback_error)
            raise error
