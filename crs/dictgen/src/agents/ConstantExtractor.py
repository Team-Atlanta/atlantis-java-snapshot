import json
import logging

from agents.BaseAgent import BaseAgent

from utility.llm import *


class ConstantExtractor(BaseAgent):
    def __init__(
        self,
        prompt_config_file_path,
        online_model_name: str,
        openai_url: str,
        openai_key: str,
        timeout: int,
        temp: float,
    ) -> None:
        super().__init__()
        self.prompt_config_file_path = prompt_config_file_path
        self.openai_url = openai_url
        self.openai_key = openai_key
        system_role, prompt = self.construct_general_prompt(
            self.prompt_config_file_path, {}
        )
        self.model = LLM(
            online_model_name,
            self.openai_url,
            self.openai_key,
            timeout,
            temp,
            system_role,
        )
        self.prompt = prompt
        pass

    def parse_response(self, response):
        # Remove any leading or trailing ```json and ```
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]  # Remove the leading ```json
        if response.endswith("```"):
            response = response[:-3]  # Remove the trailing ```

        # Strip again to remove any extra whitespace
        response = response.strip()
        # XXX: Is this safe?
        response = response.replace("\\", "\\\\")

        try:
            # Parse the JSON data
            data = json.loads(response)
            return data
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON: {e}")
            return None

    def apply(self, source_content) -> None:
        message = self.prompt + "\n```\n" + source_content + "\n```\n"
        logging.debug(f"Message: {message}")
        response, input_token_cost, output_token_cost = self.model.infer(message)
        _ = input_token_cost
        _ = output_token_cost
        logging.debug(f"Response: {response}")
        return self.parse_response(response)

    def extract_constants(self, source_file):
        logging.debug(f"Extracting constants from {source_file}")
        with open(source_file, "r") as file:
            source_content = file.read()
        constants = self.apply(source_content)
        logging.debug(f"Constants: {constants}")
        return constants
