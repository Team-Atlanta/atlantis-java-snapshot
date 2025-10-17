import asyncio
import json
import logging
import re
import subprocess
import sys

import aiofiles
from langchain_core.output_parsers.base import BaseOutputParser

from vuli.common.decorators import async_lock
from vuli.common.setting import Setting
from vuli.common.singleton import Singleton
from vuli.struct import LLMParseException
from vuli.util import async_process_run_and_exit

logger = logging.getLogger("vuli")


class JsonParser(BaseOutputParser[list]):
    async def parse(self, text: str) -> str:
        try:
            jsons = [
                json.loads(x) for x in re.findall(r"```json\n(.*?)```", text, re.DOTALL)
            ]
            if len(jsons) == 0:
                raise LLMParseException()
            return jsons[0]
        except Exception as e:
            logger.debug(e)
            error_message = f"""Your response does not contain content in JSON format, so the following error occurred while parsing:
ERROR:
{type(e).__name__}: {e}
PARSE CODE:
jsons = [
    json.loads(x) for x in re.findall(r"```json\n(.*?)```", text, re.DOTALL)
]
Please carefully review your previous response to ensure that no parsing errors occur.
After reviewing, please regenerate your response to address the issues from your previous answer.
"""
            raise LLMParseException(error_message)


class PythonParser(metaclass=Singleton):
    def __init__(self):
        self._lock = asyncio.Lock()
        self._logger = logging.getLogger(self.__class__.__name__)
        self._script_file = Setting().tmp_dir / "tmp-python-script.py"
        self._output_file = Setting().tmp_dir / "tmp-output.bin"

    @async_lock("_lock")
    async def parse(self, text: str, timeout: int = 10) -> list[dict]:
        scripts: list[str] = re.findall(r"```python\n(.*?)```", text, re.DOTALL)
        result: list[tuple[str, bytes]] = [
            (x, await self.__run_python(x, timeout)) for x in scripts
        ]
        result: list[dict] = [
            {"blob": blob, "script": script} for script, blob in result if len(blob) > 0
        ]
        if len(result) == 0:
            raise LLMParseException(
                "You MUST include python script in your answer. Put python script in ```python\n``` format."
            )
        return result

    async def __run_python(self, script: str, timeout: int) -> bytes:
        async with aiofiles.open(self._script_file, "w") as f:
            await f.write(script)
            await f.flush()

        async with aiofiles.open(self._output_file, "wb") as f:
            await f.write(b"")
            await f.flush()

        cmd = [
            "timeout",
            "-s",
            "SIGKILL",
            str(timeout),
            sys.executable,
            self._script_file,
            self._output_file,
        ]
        p = await asyncio.create_subprocess_exec(
            *cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
        )
        try:
            returncode, _, stderr = await async_process_run_and_exit(p, timeout)
        except TimeoutError:
            raise LLMParseException(
                "Timeout happens when run your script. Please do not include any logic that may cause timeout."
            )
        if returncode != 0:
            raise LLMParseException(
                f"""I encountered an error while executing the Python script generated from your response.
Analyze the error using the provided stack trace and fix the issue in the previously generated script before responding again.
The corrected script must follow the Python format used in your previous response, and be enclosed in ```python\n``` format.

<ERROR>
{stderr.decode("utf-8")}"""
            )

        if not self._output_file.exists():
            return b""

        async with aiofiles.open(self._output_file, mode="rb") as f:
            blob: bytes = await f.read()
        return blob
