import os
import logging
import asyncio
from openai import *
import tiktoken
import time
from typing import Tuple
from decimal import Decimal
from tokencost import calculate_prompt_cost, calculate_completion_cost


class InferenceException(Exception):
    pass


class LLM:
    def __init__(
        self,
        llm_model: str,
        litellm_url: str,
        litellm_key: str,
        timeout: int,
        temperature: float,
        calculate_token_cost: bool,
        system_role="",
    ) -> None:
        self.llm_model = llm_model
        try:
            encoding = tiktoken.encoding_for_model(self.llm_model)
        except KeyError:
            encoding = tiktoken.get_encoding("cl100k_base")
        self.encoding = encoding
        self.litellm_url = litellm_url
        self.litellm_key = litellm_key
        self.timeout = timeout
        self.temperature = temperature
        self.system_role = system_role
        self.calculate_token_cost = calculate_token_cost

    async def infer(self, message: str) -> Tuple[str, Decimal, Decimal]:
        output = await self._do_infer(message)
        try:
            if self.calculate_token_cost:
                input_token_cost = calculate_prompt_cost(message, self.llm_model)
            else:
                input_token_cost = Decimal(0)
        except Exception as e:
            logging.warning(f"Exception occured in calculate_prompt_cost: {e}")
            input_token_cost = Decimal(0)
        try:
            if self.calculate_token_cost:
                output_token_cost = calculate_completion_cost(output, self.llm_model)
            else:
                output_token_cost = Decimal(0)
        except Exception as e:
            logging.warning(f"Exception occured in calculate_completion_cost: {e}")
            output_token_cost = Decimal(0)
        return output, input_token_cost, output_token_cost

    async def _do_infer(self, message: str) -> str:
        model_input = [
            {"role": "system", "content": self.system_role},
            {"role": "user", "content": message},
        ]

        client = AsyncOpenAI(base_url=self.litellm_url, api_key=self.litellm_key)
        max_attempts = 5

        for attempt in range(1, max_attempts + 1):
            try:
                response = await client.chat.completions.create(
                    model=self.llm_model,
                    messages=model_input,
                    temperature=self.temperature,
                    timeout=self.timeout,
                )
                return str(response.choices[0].message.content)
            except Exception as e:
                logging.warning("Attempt %d/%d failed: %s", attempt, max_attempts, e)
            time.sleep(30)

        if os.getenv("RUNNING_TESTS") == "true":
            raise InferenceException(
                "Failed to get a response from the LLM after multiple attempts."
            )
        else:
            return ""

    MODEL_TOKEN_LIMITS = {
        "gpt-4o": 128000,
        # TODO: add more models here as needed
    }

    @staticmethod
    def count_tokens(text: str, model: str = "gpt-4o") -> int:
        """
        Return the number of tokens that `text` will be for the given OpenAI model.
        """
        try:
            enc = tiktoken.encoding_for_model(model)
        except KeyError:
            enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))

    @classmethod
    def get_token_limit(cls, model: str) -> int:
        """
        Lookup the max token limit for a given model.
        Falls back to 8192 if model is unknown.
        """
        return cls.MODEL_TOKEN_LIMITS.get(model, 128000)

    @classmethod
    def exceeds_limit(cls, text: str, model: str = "gpt-4o", coeff=1) -> bool:
        """
        Return True if the token count of `text` exceeds the model's limit.
        """
        count = cls.count_tokens(text, model)
        limit = cls.get_token_limit(model)
        return int(count * coeff) > limit
