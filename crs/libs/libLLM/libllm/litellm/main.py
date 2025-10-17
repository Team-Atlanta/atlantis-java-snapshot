from litellm import completion as completion_unwrapped
from ..resources.logging import logger
from ..resources.error_handling import handle_openai_errors, async_handle_openai_errors

@handle_openai_errors
def completion(*args, **kwargs):
    logger.debug("We are wrapped, litellm completions")
    return completion_unwrapped(*args, **kwargs)
