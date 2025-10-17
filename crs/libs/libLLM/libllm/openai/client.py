from ..resources.logging import logger

from openai import OpenAI as OpenAIUnwrapped
from openai import AsyncOpenAI as AsyncOpenAIUnwrapped

from .completions import Completions, AsyncCompletions
from .chat import Chat, AsyncChat

__all__ = [
    "OpenAI",
    "AsyncOpenAI",
    "Client",
    "AsyncClient",
]

class OpenAI(OpenAIUnwrapped):
    completions: Completions
    chat: Chat
    
    def __init__(self, *args, **kwargs):
        logger.debug("OpenAI we are wrapped!")
        super().__init__(*args, **kwargs)
        self.completions = Completions(self)
        self.chat = Chat(self)

    # NOTE we could override _make_status_error, however it's hard to implement retries here

class AsyncOpenAI(AsyncOpenAIUnwrapped):
    completions: AsyncCompletions
    chat: AsyncChat
    
    def __init__(self, *args, **kwargs):
        logger.debug("AsyncOpenAI we are wrapped!")
        super().__init__(*args, **kwargs)
        self.completions = AsyncCompletions(self)
        self.chat = AsyncChat(self)


Client = OpenAI
AsyncClient = AsyncOpenAI
