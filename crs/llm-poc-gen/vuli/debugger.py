import asyncio
import logging
import os
import signal
import subprocess
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path

import aiofiles

from vuli.common.decorators import async_lock
from vuli.common.setting import Setting
from vuli.common.singleton import Singleton
from vuli.cp import CP
from vuli.util import terminate_process


class Debugger(ABC):

    @abstractmethod
    async def run(self, harness_name: str, blob: bytes, cmd: list[str]) -> str:
        pass

    @abstractmethod
    async def stop(self):
        pass


class JDB(metaclass=Singleton):

    def __init__(self, timeout: float = 30.0):
        self._logger = logging.getLogger("JDB")
        self._file = Setting().tmp_dir / "tmp-jdb-blob"
        self._output = Setting().tmp_dir / "tmp-jdb-output"
        self._timeout = timeout
        self._lock = asyncio.Lock()

    @async_lock("_lock")
    async def run(self, harness_name: str, blob: bytes, cmd: list[str]) -> str:
        harness_path: str = CP().get_harness_path(harness_name)
        class_name: str = CP().harnesses.get(harness_name, {}).get("target_class", "")
        async with aiofiles.open(self._file, mode="wb") as f:
            await f.write(blob)
            await f.flush()

        async with aiofiles.open(self._output, mode="wb") as f:
            command: list[str] = [
                "timeout",
                "-s",
                "SIGKILL",
                str(self._timeout + 1),
                "jdb",
                f"-Dllmpocgen={Setting().root_dir}",
                "-classpath",
                f"{":".join([x for x in CP().get_jars(harness_path)])}:{Setting().agent_path}",
                "sr.AgentMain",
                class_name,
                self._file,
            ]
            p = await asyncio.create_subprocess_exec(
                *command,
                stdin=subprocess.PIPE,
                stdout=f,
                stderr=f,
            )
            p.stdin.write(f"{"\n".join(cmd + ["run"])}\n".encode())
            await p.stdin.drain()
            try:
                await asyncio.wait_for(p.wait(), timeout=self._timeout)
            except TimeoutError:
                await terminate_process(p)

        async with aiofiles.open(self._output, mode="rb") as f:
            result: str = (await f.read()).decode("utf-8")
        return result

    async def stop(self) -> None:
        pass


class GDB(Debugger):

    def __init__(self, timeout: float = 30.0):
        self._logger = logging.getLogger("GDB")
        self._file = tempfile.NamedTemporaryFile(dir=Setting().tmp_dir)
        self._lock = asyncio.Lock()
        self._timeout = timeout

    @async_lock("_lock")
    async def run(self, harness_name: str, blob: bytes, cmd: list[str]) -> str:
        binary = f"{harness_name}"
        blob_path = f"{Path(self._file.name)}"
        gdb_cmd_path = f"{Path(Setting().tmp_dir / Path(self._file.name).name)}_cmd"
        breakpoints = cmd
        dir = f"{CP().source_dir}"

        async with aiofiles.open(self._file.name, mode="wb") as f:
            await f.write(blob)
            await f.flush()

        current_dir = Path(os.path.dirname(os.path.abspath(__file__)))
        run_gdb_path = f"{current_dir.parent}/run_gdb.sh"
        self._logger.debug(f"run_gdb.sh located at {run_gdb_path}")

        cmd = (
            [
                "bash",
                run_gdb_path,
                binary,
                blob_path,
                gdb_cmd_path,
            ]
            + breakpoints
            + ["--dir", dir]
        )

        self._logger.debug(f"Run GDB: {" ".join(cmd)}")

        env = os.environ.copy()
        env["ASAN_OPTIONS"] = "detect_leaks=0"
        env["LSAN_OPTIONS"] = "detect_leaks=0"

        p = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
            cwd=CP().built_path,
            start_new_session=True,
        )
        try:
            stdout, _ = await asyncio.wait_for(p.communicate(), timeout=self._timeout)
            return stdout.decode()
        except asyncio.TimeoutError:
            os.killpg(p.pid, signal.SIGKILL)
            stdout, stderr = await p.communicate()
            output = ""
            # if stdout:
            #    output += stdout.decode()
            # if stderr:
            #    output += stderr.decode()
            return output

    def stop(self):
        pass
