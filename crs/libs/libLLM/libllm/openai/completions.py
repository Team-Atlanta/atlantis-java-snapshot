from openai.resources.chat import Completions as CompletionsUnwrapped
from openai.resources.chat import AsyncCompletions as AsyncCompletionsUnwrapped
from ..resources.error_handling import handle_openai_errors, async_handle_openai_errors
from ..resources.logging import logger

__all__ = [
    "Completions",
    "AsyncCompletions",
]


# TODO with raw response, with streaming

class Completions(CompletionsUnwrapped):
    @handle_openai_errors
    def create(self, *args, **kwargs):
        logger.debug("Completions wrapped!")
        return super().create(*args, **kwargs)

class AsyncCompletions(AsyncCompletionsUnwrapped):
    @async_handle_openai_errors
    async def create(self, *args, **kwargs):
        logger.debug("AsyncCompletions wrapped!")
        return await super().create(*args, **kwargs)
