import os
import logging
from pathlib import Path
from claude_code_sdk import query, ClaudeCodeOptions, Message, AssistantMessage, TextBlock, ResultMessage
from claude_code_sdk._errors import CLIJSONDecodeError
from libAgents.utils import environs, async_run_cmd, cd
from dataclasses import dataclass
from typing import Optional, List
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class ClaudeConfig:
    print_mode: bool = True
    use_json: bool = True
    debug: bool = False
    verbose: bool = False
    skip_permissions: bool = False
    cwd: str = os.getcwd()


class ClaudeCodeCLI:
    """
    npm install -g @anthropic-ai/claude-code
    https://docs.anthropic.com/en/docs/agents-and-tools/claude-code/overview
    """

    def __init__(self, config: Optional[ClaudeConfig] = None):
        self.config = config or ClaudeConfig()

    def _build_command(
        self, prompt: str, args: Optional[List[str]] = None
    ) -> List[str]:
        cmd = ["claude"]
        # dynamic parameter mapping
        flag_mapping = {
            "print_mode": "-p",
            "debug": "-d",
            "verbose": "--verbose",
            "skip_permissions": "--dangerously-skip-permissions",
            "use_json": "--output-format=json",
        }
        for attr, flag in flag_mapping.items():
            if getattr(self.config, attr, False):
                cmd.append(flag)
        return cmd + (args or []) + [prompt]

    async def async_query(self, prompt: str, args: Optional[List[str]] = None):
        cmd = self._build_command(prompt, args)
        res = await async_run_cmd(cmd, env={
            "ANTHROPIC_BASE_URL": os.environ["AIXCC_LITELLM_HOSTNAME"],
            "ANTHROPIC_AUTH_TOKEN": os.environ["LITELLM_KEY"]
        })
        if res.returncode != 0:
            logger.error(
                f"Command failed: {res.stderr.decode(errors='ignore')}"
            )
            return res.stderr.decode(errors="ignore")
        
        output = res.stdout.decode(errors="ignore")
        
        # Validate JSON if using JSON output format
        if self.config.use_json:
            try:
                import json
                # Try to parse to validate JSON
                json.loads(output)
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON output from CLI: {e}")
                # Return raw output if JSON is invalid
                return output
        
        return output


class ClaudeCode:
    """
    npm install -g @anthropic-ai/claude-code
    https://docs.anthropic.com/en/docs/agents-and-tools/claude-code/overview
    https://docs.anthropic.com/en/docs/claude-code/llm-gateway
    """

    def __init__(self, cwd: Path):
        self.cwd = cwd

    def _build_system_prompt(self) -> str:
        return """
        When the user ask you to write codes, you prefer write it in a copy-pasteable self-contained python script and print the result to the console.
        """
    
    def _build_options(self) -> ClaudeCodeOptions:
        options = ClaudeCodeOptions(
            cwd=self.cwd,
            append_system_prompt=self._build_system_prompt(),
            permission_mode="default", # or bypassPermissions
        )
        return options

    async def async_query(self, prompt: str,  max_retries: int = 3):
        with environs({"ANTHROPIC_BASE_URL": os.environ["AIXCC_LITELLM_HOSTNAME"], "ANTHROPIC_AUTH_TOKEN": os.environ["LITELLM_KEY"]}):
            messages: list[Message] = []
            res = None
            options = self._build_options()

            with cd(self.cwd):
                for attempt in range(max_retries):
                    try:
                        # Use asyncio timeout to prevent hanging
                        async with asyncio.timeout(300):  # 5 minute timeout
                            async for message in query(prompt=prompt, options=options):
                                messages.append(message)
                                # print(message)

                                if isinstance(message, AssistantMessage):
                                    for block in message.content:
                                        if isinstance(block, TextBlock):
                                            # print(f"<claude_text>\n {block.text} \n </claude_text>")
                                            res = block.text

                                if isinstance(message, ResultMessage):
                                    if message.result is not None:
                                        # print(f"<claude_result>\n {message.result} \n </claude_result>")
                                        res = message.result
                        
                        return res
                        
                    except (CLIJSONDecodeError, KeyError) as e:
                        # Only catch specific SDK errors, not anyio task group errors
                        if ("cost_usd" in str(e) or "JSONDecodeError" in str(type(e)) or 
                            isinstance(e, CLIJSONDecodeError)):
                            logger.warning(f"SDK error on attempt {attempt + 1}/{max_retries}: {e}")
                            if attempt == max_retries - 1:
                                pass
                            await asyncio.sleep(2 ** attempt)  # Exponential backoff
                            continue
                        else:
                            raise e
                    except Exception as e:
                        logger.error(f"Error: {e}")
                        raise e
                        return res