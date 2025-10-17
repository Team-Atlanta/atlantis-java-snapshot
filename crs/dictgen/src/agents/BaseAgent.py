import json
from pathlib import Path

from typing import Dict, Tuple


class BaseAgent:
    def __init__(self) -> None:
        self.total_input_token_cost = 0
        self.total_output_token_cost = 0
        self.prompt_dir_path = (
            Path(__file__).resolve().parent.parent.absolute() / "prompt"
        )

    def construct_general_prompt(
        self, config_file_path: str, replacements: Dict[str, str]
    ) -> Tuple[str, str]:
        with open(self.prompt_dir_path / config_file_path, "r") as f:
            config_data = json.load(f)
        system_role = config_data.get("system_role", "")
        task_description = config_data.get("task", "")
        analysis_rules = config_data.get("analysis_rules", [])
        analysis_examples = config_data.get("analysis_examples", [])
        # meta_prompts = config_data.get("meta_prompts", [])
        output_constraints = config_data.get("output_constraints", [])
        output_examples = config_data.get("output_examples", [])
        prompt_parts = [
            task_description,
            "\n".join(analysis_rules),
            "\n".join(analysis_examples),
            # "".join(meta_prompts),
            "".join(output_constraints),
            "\n".join(output_examples),
            "Here is the program:",
        ]
        prompt = "\n".join(prompt_parts)
        for placeholder, replacement_value in replacements.items():
            prompt = prompt.replace(placeholder, replacement_value)

        return system_role, prompt

    def replace_template(self, template: str, replacements: Dict[str, str]) -> str:
        for key, value in replacements.items():
            template = template.replace(key, value)
        return template

    def annotating_line_numbers(self, source_content: str) -> str:
        return "\n".join(f"{i + 1}. {line}" for i, line in enumerate(source_content))

    def parse_response_yes_no(self, response: str) -> bool:
        lines = response.splitlines()
        found_answer = None
        for line in lines:
            line = line.strip()
            if line.startswith("- Answer: "):
                answer = line[len("- Answer: ") :].strip()
                answer = answer.lower()
                if answer in {"yes", "no"}:
                    if found_answer is not None:
                        return False
                    found_answer = answer == "yes"
        return found_answer if found_answer is not None else False
