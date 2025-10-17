import json
import logging
import contextlib
import asyncio
import litellm
from dataclasses import dataclass
from typing import Any, Dict, Optional, List, Iterator
from contextlib import contextmanager
from libAgents.config import LLM_PROVIDER, RESONING_EFFORTS

from google import genai
from openai import AsyncOpenAI
import openai
import time
import os
import random

from libAgents.config import default_model_override

litellm.drop_params = True
# litellm.num_retries = 3
litellm.set_verbose = False

logger = logging.getLogger(__name__)

LITELLEM_KEY = os.environ["LITELLM_KEY"]
LITELLEM_BASE_URL = os.environ["AIXCC_LITELLM_HOSTNAME"]

def get_max_tokens(model: str) -> int:
    max_tokens_map = {
       "claude-opus-4-20250514": 32000,
       "claude-sonnet-4-20250514": 64000,
       "o3": 100000,
       "o4-mini": 100000,
       "gemini-2.5-pro": 65535,
       "gpt-4.1": 32768,
    }
    return max_tokens_map.get(model, 32000)

@contextmanager
def environs(env_vars: Dict[str, Optional[str]]) -> Iterator[None]:
    """Context manager to temporarily set multiple environment variables."""
    original_values = {}

    def _set_env(k: str, v: Optional[str]) -> None:
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v

    try:
        # Store original values and set new ones
        for key, value in env_vars.items():
            original_values[key] = os.environ.get(key, None)
            _set_env(key, value)

        yield
    finally:
        # Restore original values
        for key, original_value in original_values.items():
            _set_env(key, original_value)

@dataclass
class ResponseWrapper:
    object: Dict[str, Any]
    usage: Dict[str, Any]


def retry_with_exponential_backoff(
    func,
    initial_delay: float = 1,
    exponential_base: float = 2,
    jitter: bool = True,
    max_retries: int = 20,
    errors: tuple = (openai.RateLimitError,),
):
    """Retry a function with exponential backoff."""

    def wrapper(*args, **kwargs):
        # Initialize variables
        num_retries = 0
        delay = initial_delay

        # Loop until a successful response or max_retries is hit or an exception is raised
        while True:
            try:
                return func(*args, **kwargs)

            # Retry on specified errors
            except errors as e:
                # Increment retries
                num_retries += 1

                # Check if max retries has been reached
                if num_retries > max_retries:
                    raise Exception(
                        f"Maximum number of retries ({max_retries}) exceeded."
                    )

                # Increment the delay
                delay *= exponential_base * (1 + jitter * random.random())

                # Enhanced logging with progress indication
                logger.warning(
                    f"🔄 Retry {num_retries}/{max_retries} - {type(e).__name__}: {str(e)}"
                )
                logger.info(
                    f"⏳ Waiting {delay:.2f}s before retry... "
                    f"[{'█' * num_retries}{'░' * (max_retries - num_retries)}] "
                    f"{num_retries}/{max_retries}"
                )

                # Sleep for the delay
                time.sleep(delay)
                logger.debug(f"🚀 Attempting retry {num_retries}/{max_retries}...")

            # Raise exceptions for any errors not specified
            except Exception as e:
                raise e

    return wrapper


def async_retry_with_exponential_backoff(
    func=None,
    *,
    initial_delay: float = 1,
    exponential_base: float = 2,
    jitter: bool = True,
    max_retries: int = 10,
    errors: tuple = (openai.RateLimitError,),
):
    """Retry an async function with exponential backoff."""

    # This is the actual decorator that will be applied to the function
    def decorator(async_func):
        # This is the wrapper function that adds retry functionality
        async def wrapper(*args, **kwargs):
            # Initialize variables
            num_retries = 0
            delay = initial_delay

            # Loop until a successful response or max_retries is hit or an exception is raised
            while True:
                try:
                    return await async_func(*args, **kwargs)

                # Retry on specified errors
                except errors as e:
                    # Increment retries
                    num_retries += 1

                    # Check if max retries has been reached
                    if num_retries > max_retries:
                        raise Exception(
                            f"Maximum number of retries ({max_retries}) exceeded."
                        )

                    # Increment the delay
                    delay *= exponential_base * (1 + jitter * random.random())

                    # Enhanced logging with progress indication
                    logger.error(
                        f"🔄 Retry {num_retries}/{max_retries} - {type(e).__name__}: {str(e)}"
                    )
                    logger.debug(
                        f"⏳ Waiting {delay:.2f}s before retry... "
                        f"[{'█' * num_retries}{'░' * (max_retries - num_retries)}] "
                        f"{num_retries}/{max_retries}"
                    )

                    await asyncio.sleep(delay)

                    logger.debug(f"🚀 Attempting retry {num_retries}/{max_retries}...")

                # Raise exceptions for any errors not specified
                except Exception as e:
                    raise e

        return wrapper

    # Handle both @async_retry_with_exponential_backoff and
    # @async_retry_with_exponential_backoff() cases
    if func is None:
        # Called with parameters or no parameters in parentheses
        return decorator
    # Called without parentheses
    return decorator(func)


@contextlib.contextmanager
def model_override(model_name: str | None):
    token = default_model_override.set(model_name)
    try:
        yield
    finally:
        default_model_override.reset(token)


async def generate_text(
    model: Any,
    prompt: str,
    temperature: float = 1,
    system: Optional[str] = None,
    messages: Optional[List[Dict[str, Any]]] = None,
) -> ResponseWrapper:
    """
    Generate text response from language models without structured output.

    This function supports three usage patterns:
    1. Simple prompt: generate_text(model, prompt="Hello")
    2. Prompt with system: generate_text(model, prompt="Hello", system="You are helpful")
    3. Full messages: generate_text(model, messages=[...], system="You are helpful")

    Args:
        model: The model instance (client wrapper) returned by get_model.
        prompt: Simple user prompt string (mutually exclusive with messages).
        temperature: Sampling temperature.
        system: Optional system message to prepend.
        messages: List of message dictionaries in OpenAI format (mutually exclusive with prompt).

    Returns:
        ResponseWrapper containing the generated text and usage metrics.

    Raises:
        ValueError: If neither prompt nor messages is provided, or if both are provided.
    """
    # Validate input parameters
    if prompt is None and messages is None:
        raise ValueError("Either 'prompt' or 'messages' must be provided")
    if prompt is not None and messages is not None:
        raise ValueError(
            "Cannot provide both 'prompt' and 'messages' - they are mutually exclusive"
        )

    # Handle the case where system is provided in messages
    if messages is not None and system is not None:
        for msg in messages:
            if msg.get("role") == "system":
                logger.warning(
                    "Found system prompt in messages, but system is also provided, ignoring system in messages"
                )
                messages = [msg for msg in messages if msg.get("role") != "system"]
                break

    # Convert prompt to messages format if needed
    if prompt is not None:
        messages = [{"role": "user", "content": prompt}]

    # Build the final messages list
    final_messages = []
    if system:
        final_messages.append({"role": "system", "content": system})
    final_messages.extend(messages)

    # Call the model without response_format for plain text generation
    content, usage = await model.chat.completions.create(
        messages=final_messages,
        temperature=temperature,
    )

    # print(f"Content ❤️: {content}")
    # print(f"Usage ❤️: {usage}")
    return ResponseWrapper(object=content, usage=usage)


async def generate_object(
    model: Any,
    schema: Dict[str, Any],
    prompt: Optional[str] = None,
    messages: Optional[List[Dict[str, Any]]] = None,
    system: Optional[str] = None,
    temperature: float = 1,
) -> Dict[str, Any]:
    """
    Unified function for generating structured responses from language models.

    This function supports three usage patterns:
    1. Simple prompt: generate_object(model, schema, prompt="Hello")
    2. Prompt with system: generate_object(model, schema, prompt="Hello", system="You are helpful")
    3. Full messages: generate_object(model, schema, messages=[...], system="You are helpful")

    Args:
        model: The model instance (client wrapper) returned by get_model.
        schema: A JSON-schema–like dictionary describing the expected response.
        prompt: Simple user prompt string (mutually exclusive with messages).
        messages: List of message dictionaries in OpenAI format (mutually exclusive with prompt).
        system: Optional system message to prepend.
        max_completion_tokens: Maximum tokens to generate.
        temperature: Sampling temperature.

    Returns:
        ResponseWrapper containing the generated output and usage metrics.

    Raises:
        ValueError: If neither prompt nor messages is provided, or if both are provided.
    """

    # Validate input parameters
    if prompt is None and messages is None:
        raise ValueError("Either 'prompt' or 'messages' must be provided")
    if prompt is not None and messages is not None:
        raise ValueError(
            "Cannot provide both 'prompt' and 'messages' - they are mutually exclusive"
        )

    # handle the case where system is provided in messages
    if messages is not None and system is not None:
        for msg in messages:
            if msg.get("role") == "system":
                logger.warning(
                    "Find system prompt in messages, but system is also provided, ignoring system in messages"
                )
                messages = [msg for msg in messages if msg.get("role") != "system"]

    # Convert prompt to messages format if needed
    if prompt is not None:
        messages = [{"role": "user", "content": prompt}]

    def modify_properties(schema_obj: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively adds additionalProperties: False to all objects in strict mode."""
        if not isinstance(schema_obj, dict):
            return schema_obj

        result = schema_obj.copy()

        from libAgents.config import LLM_PROVIDER

        _openai_models = [
            "o1-mini",
            "o3-mini",
            "o4-mini",
            "o1",
            "o3",
            "o4",
            "o1-pro",
            "gpt-4.5-preview",
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4.1",
            "gpt-4.1-mini",
            "gpt-4.1-nano",
        ]

        _gemini_models = [
            "gemini-2.5-pro",
            "gemini-2.5-flash-preview-05-20",
        ]

        if LLM_PROVIDER == "openai" or LLM_PROVIDER == "litellm":
            # Remove maxItems if present
            # FIXME: now openai actually supports maxItems and minItems
            # So we need to confirm if claude or grok supports it
            result.pop("maxItems", None)
            result.pop("minItems", None)
            result.pop("maxLength", None)
            result.pop("minLength", None)

            # Add additionalProperties: False to objects
            if result.get("type") == "object":
                result["additionalProperties"] = False

        # Recursively process nested properties
        if "properties" in result:
            result["properties"] = {
                k: modify_properties(v) for k, v in result["properties"].items()
            }

        # Handle array items
        if "items" in result:
            result["items"] = modify_properties(result["items"])

        # Handle schema composition keywords
        for key in ["anyOf", "allOf", "oneOf"]:
            if key in result and isinstance(result[key], list):
                result[key] = [modify_properties(item) for item in result[key]]

        return result

    is_strict = model.compatibility == "strict"
    modified_schema = modify_properties(schema) if is_strict else schema
    final_schema = {
        "type": "json_schema",
        "json_schema": {
            "strict": is_strict,
            "name": "response",
            "schema": modified_schema,
        },
    }

    # Build the final messages list
    final_messages = []
    if system:
        final_messages.append({"role": "system", "content": system})
    final_messages.extend(messages)

    # logger.debug(f"Final schema: {final_schema}")
    content, usage = await model.chat.completions.create(
        messages=final_messages,
        temperature=temperature,
        response_format=final_schema,
    )

    # print(f"Content: {content}")
    # print(f"Usage 💙: {usage}")

    return ResponseWrapper(object=content, usage=usage)


def create_openai(opt: dict):
    """
    Create an OpenAI client using the provided options.

    Expected keys in opt:
      - "apiKey": Your OpenAI API key.
      - "compatibility": A string (e.g., "strict" or "compatible") — not used here but preserved for compatibility.
      - "baseURL": (optional) The base URL for API requests.

    This function sets the global OpenAI API key (and base URL, if provided) and returns a callable.
    That callable accepts a model name and returns a client instance with chainable attributes
    so that you can call, for example, `client.chat.completions.create(...)`.
    """
    # Configure the global OpenAI API settings.

    if opt.get("compatibility"):
        if opt["compatibility"] not in ["strict", "compatible"]:
            raise ValueError("compatibility must be either 'strict' or 'compatible'")

    class OpenAIClientWrapper:
        def __init__(self, model_name: str):
            self.model_name = model_name
            self.compatibility = opt.get("compatibility", "strict")
            self.base_url = opt.get("baseURL", None)
            self.api_key = opt["apiKey"]
            self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)

        @property
        def chat(self):
            # Return self to allow chaining: client.chat.completions.create(...)
            return self

        @property
        def completions(self):
            return self

        @async_retry_with_exponential_backoff
        async def completion_impl(self, **kwargs):
            if LLM_PROVIDER == "litellm" or LLM_PROVIDER == "openai":
                try:
                    if "claude" in kwargs.get("model"):
                        kwargs["max_tokens"] = get_max_tokens(kwargs.get("model"))
                        if '/' not in kwargs.get("model"):
                            kwargs["model"] = f"anthropic/{kwargs.get('model')}"
                        if "opus" in kwargs.get("model"):
                            kwargs["thinking"] = {"type": "enabled", "budget_tokens": 20000}
                        else:
                            kwargs["thinking"] = {"type": "enabled", "budget_tokens": 20000}
                        with environs({"ANTHROPIC_API_KEY": LITELLEM_KEY, "ANTHROPIC_API_BASE": LITELLEM_BASE_URL}):
                            res = await litellm.acompletion(**kwargs)
                    else:
                        kwargs["max_tokens"] = get_max_tokens(kwargs.get("model"))
                        res = await self.client.chat.completions.create(**kwargs)
                except Exception as e:
                    logger.error(f"Error creating OpenAI chat completion: {e}")
                    raise e
            return res

        async def create(self, **kwargs):
            try:
                # logger.debug(f"[+] Using OpenAI with apiKey: {opt['apiKey']}")
                # logger.debug(f"[+] Using OpenAI with baseURL: {opt['baseURL']}")
                kwargs["model"] = self.model_name

                if kwargs["model"] in RESONING_EFFORTS:
                    kwargs["reasoning_effort"] = RESONING_EFFORTS[kwargs["model"]]

                res = await self.completion_impl(**kwargs)

                return res.choices[0].message.content, res.usage
            except Exception as e:
                logger.error(f"Error creating OpenAI chat completion: {e}")
                raise e

        def __repr__(self):
            return f"OpenAIClientWrapper(model_name={self.model_name})"

    def client_creator(model_name: str):
        return OpenAIClientWrapper(model_name)

    return client_creator


def create_google_generative_ai(opt: dict):
    """
    Create a Gemini client using the provided options.
    Expected opt contains at least:
      - "apiKey": Your Gemini API key.
      - "compatibility": A string (e.g., "strict" or "compatible") — used for consistency with other clients
    Returns a callable that accepts a model name and returns a client instance.
    """
    if opt.get("compatibility"):
        if opt["compatibility"] not in ["strict", "compatible"]:
            raise ValueError("compatibility must be either 'strict' or 'compatible'")

    class GeminiClientWrapper:
        def __init__(self, model_name: str):
            self.model_name = model_name
            self.compatibility = opt.get("compatibility", "strict")
            self._client = genai.Client(api_key=opt["apiKey"])

        @property
        def chat(self):
            return self

        @property
        def completions(self):
            return self

        @async_retry_with_exponential_backoff
        async def completion_impl(self, **kwargs):
            messages = kwargs.get("messages", [])
            response_format = kwargs.get("response_format", {})
            temperature = kwargs.get("temperature", 1)
            max_tokens = kwargs.get("max_tokens")

            # logger.debug(
            #     f"[{self.__class__.__name__}] Entering completion_impl for model {self.model_name}"
            # )

            # Convert OpenAI-style messages to Gemini format
            prompt = "\n".join(msg["content"] for msg in messages)

            # Configure generation config
            generation_config = {
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            }

            if "json_schema" in response_format:
                schema = response_format["json_schema"]["schema"]
                # Remove additionalProperties as Gemini doesn't support it
                if isinstance(schema, dict):
                    schema.pop("additionalProperties", None)

                generation_config.update(
                    {
                        "response_mime_type": "application/json",
                        "response_schema": schema,
                    }
                )

            # Generate content
            logger.debug(
                f"[{self.__class__.__name__}] Attempting Gemini generate_content call"
            )
            response = self._client.models.generate_content(
                model=self.model_name, contents=prompt, config=generation_config
            )
            logger.debug(
                f"[{self.__class__.__name__}] Gemini generate_content call completed"
            )

            # Parse the response text as JSON since we requested JSON output
            try:
                content = response
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Gemini response as JSON: {e}")
                raise

            @dataclass
            class UsageMetrics:
                total_tokens: int
                prompt_tokens: int
                completion_tokens: int

            usage = UsageMetrics(
                total_tokens=response.usage_metadata.total_token_count,
                prompt_tokens=response.usage_metadata.prompt_token_count,
                completion_tokens=response.usage_metadata.candidates_token_count,
            )

            return content.text, usage

        async def create(self, **kwargs):
            try:
                return await self.completion_impl(**kwargs)
            except Exception as e:
                logger.error(f"Error creating Gemini chat completion: {e}")
                raise e

        def __repr__(self):
            return f"GeminiClientWrapper(model_name={self.model_name})"

    def client_creator(model_name: str):
        return GeminiClientWrapper(model_name)

    return client_creator
