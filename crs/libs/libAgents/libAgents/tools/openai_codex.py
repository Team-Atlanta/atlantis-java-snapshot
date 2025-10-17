from dataclasses import dataclass
import os
import logging
import json
import asyncio
from typing import List, Optional, Dict, Any
from pathlib import Path
from libAgents.utils import run_cmd, run_command

logger = logging.getLogger(__name__)


@dataclass
class OpenAICodexConfig:
    model_name: str = "gpt-4.1"
    quiet: bool = True
    use_json: bool = True
    verbose: bool = False
    full_auto: bool = True
    skip_permissions: bool = True
    cwd: str = os.getcwd()


class OpenAICodex:
    def __init__(self, config: OpenAICodexConfig = None):
        self.config = config or OpenAICodexConfig()

    def _build_command(
        self, prompt: str
    ) -> List[str]:
        flag_mapping = {
            "quiet": "-q",
            "use_json": "--json",
            "full_auto": "--full-auto",
            "skip_permissions": "--dangerously-auto-approve-everything",
        }

        cmd = ["codex"]
        cmd.extend(["--model", self.config.model_name])
        cmd.extend(["-q"])
        # Add the prompt, potentially wrapped in quotes
        # Ensure the prompt string itself is passed enclosed in double quotes
        cmd.append(f'"{prompt}"')
        print(cmd)

        return cmd

    def _parse_output(self, output: str) -> str:
        for line in reversed(output.splitlines()):
            # quick skip of obviously non‑JSON lines
            if line.lstrip()[:1] not in ("{", "["):
                continue

            try:
                data: Dict[str, Any] = json.loads(line)
            except json.JSONDecodeError:
                continue

            if data.get("type") != "message" or data.get("role") != "assistant":
                continue

            # content is a list of blocks; newest is last ⇒ iterate reversed
            for block in reversed(data.get("content", [])):
                if block.get("type") == "output_text":
                    return block.get("text", "")
        return output  # Return original output if no structured result found

    async def async_query(
        self, prompt: str, args: Optional[List[str]] = None, max_retries: int = 3
    ) -> str:
        cmd = self._build_command(prompt)
        last_stdout = ""
        os.environ["OPENAI_API_KEY"] = os.environ["LITELLM_KEY"]
        os.environ["OPENAI_BASE_URL"] = os.environ["AIXCC_LITELLM_HOSTNAME"]

        for attempt in range(max_retries):
            stdout, stderr = run_command(cmd, cwd=self.config.cwd, env=os.environ)

            print(stdout)
            print("--------------------------------")
            print(stderr)

            result = self._parse_output(stdout)
            if result:
                return result

            if attempt < max_retries - 1:
                logger.warning(
                    f"No result found, retrying... ({attempt + 1}/{max_retries})"
                )

        # If we got here, parsing failed on all attempts, but _parse_output should now
        # return the original output as fallback
        return self._parse_output(last_stdout)

    def query(
        self, prompt: str, args: Optional[List[str]] = None, max_retries: int = 3
    ) -> str:
        return asyncio.run(self.async_query(prompt, args, max_retries))
