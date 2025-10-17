import asyncio
import logging
from agents.BaseAgent import BaseAgent

from utility.llm import *


class ParsingFunctionDetector(BaseAgent):
    def __init__(
        self,
        prompt_config_file_path,
        online_model_name: str,
        openai_url: str,
        openai_key: str,
        timeout: int,
        temp: float,
        logger: logging.Logger,
        calculate_token_cost: bool,
        replacement: dict,
    ) -> None:
        super().__init__()
        self.logger = logger
        self.calculate_token_cost = calculate_token_cost
        self.prompt_config_file_path = prompt_config_file_path
        self.openai_url = openai_url
        self.openai_key = openai_key
        system_role, prompt = self.construct_general_prompt(
            self.prompt_config_file_path,
            replacement,
        )
        self.model = LLM(
            online_model_name,
            self.openai_url,
            self.openai_key,
            timeout,
            temp,
            self.calculate_token_cost,
            system_role,
        )
        self.prompt = prompt
        pass

    async def detect_parsing_function(self, source_code) -> bool:
        message = (
            self.prompt
            + "\n```\n"
            + self.annotating_line_numbers(source_code)
            + "\n```\n"
        )
        self.logger.debug(f"Message: {message}")
        response, input_token_cost, output_token_cost = await self.model.infer(message)
        self.total_input_token_cost += input_token_cost
        self.total_output_token_cost += output_token_cost
        self.logger.debug(f"Response: {response}")
        return self.parse_response_yes_no(response)
