import asyncio
import logging
from enum import Enum
from agents.BaseAgent import BaseAgent

from utility.llm import *


class TriggerVerifier(BaseAgent):
    class TokenType(Enum):
        STRING = "String"
        INTEGER = "Integer"
        INVALID = "Invalid"

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
        self.calculate_token_cost = calculate_token_cost
        self.logger = logger
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

    async def apply(self, source_code, vuln_type, token) -> bool:
        message = (
            self.replace_template(
                self.prompt, {"<VULN_TYPE>": vuln_type, "<TOKEN_VALUE>": token}
            )
            + "\n```\n"
            + source_code
            + "\n```\n"
        )
        self.logger.debug(f"Message: {message}")
        response, input_token_cost, output_token_cost = await self.model.infer(message)
        self.total_input_token_cost += input_token_cost
        self.total_output_token_cost += output_token_cost
        self.logger.debug(f"Response: {response}")
        return self.parse_response_yes_no(response)

    def get_vuln_type(self, key) -> str:
        split = key.split(" - ", 1)
        return split[1] if len(split) > 1 else "Unknown"

    async def verify(self, source_code: str, source_file: str, func: str, trigger):
        lined_code = self.annotating_line_numbers(source_code)

        tasks = []
        for key, tokens in list(trigger.items()):
            vuln_type = self.get_vuln_type(key)
            for token in tokens:
                self.logger.debug(
                    f"Verifying {token} can trigger {vuln_type} in {func} of {source_file}"
                )
                task = asyncio.create_task(self.apply(lined_code, vuln_type, token))
                tasks.append((task, key, vuln_type, token))

        results_list = await asyncio.gather(*(task for task, _, _, _ in tasks))
        results = {}
        for (_, key, vuln_type, token), ok in zip(tasks, results_list):
            if ok:
                if key not in results:
                    results[key] = []
                results[key].append(token)
            else:
                self.logger.debug(f"Removing {token} from {vuln_type} in {func}")

        return results
