from functools import cached_property as cached_property
from openai.resources.chat import Chat as ChatUnwrapped
from openai.resources.chat import AsyncChat as AsyncChatUnwrapped
from .completions import Completions, AsyncCompletions

__all__ = [
    "Chat",
    "AsyncChat",
]

class Chat(ChatUnwrapped):
    @cached_property
    def completions(self) -> Completions:
        return Completions(self._client)

class AsyncChat(AsyncChatUnwrapped):
    @cached_property
    def completions(self) -> AsyncCompletions:
        return AsyncCompletions(self._client)
