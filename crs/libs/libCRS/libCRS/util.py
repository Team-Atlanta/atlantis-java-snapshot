import asyncio
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
import time

import coloredlogs

__all__ = ["SharedFile", "TODO", "cp"]

coloredlogs.install(fmt="%(asctime)s %(levelname)s %(message)s")


class SharedFile:
    def __init__(self, path: Path):
        self.path = path

    def __metadata_path(self):
        path = self.path
        return path.parent / f".meta_{path.name}"

    def finalize(self):
        with open(self.__metadata_path(), "wb") as f:
            f.write(b"")
        return self

    def write(self, data: bytes):
        with open(self.path, "wb") as f:
            f.write(data)
        self.finalize()

    def is_finalized(self):
        return self.__metadata_path().exists()

    def wait(self):
        logging.info(f"Wait SharedFile: {self.path}")
        while not self.is_finalized():
            time.sleep(1)

    async def async_wait(self):
        logging.info(f"Wait SharedFile: {self.path}")
        while not self.is_finalized():
            await asyncio.sleep(1)

    def __str__(self):
        return self.path.__str__()


class TestResult:
    def __init__(self, is_passed, msg):
        self.is_passed = is_passed
        self.msg = msg

    def __str__(self):
        if self.is_passed:
            return f"Pass: {self.msg}"
        return f"Fail: {self.msg}"


class CmdResult:
    def __init__(self, cmd, out: bytes, err: bytes, returncode: int):
        self.cmd = cmd
        self.stdout = out
        self.stderr = err
        self.returncode = returncode

    def __str__(self):
        ret = "\n" + BAR() + "\n"
        ret += " ".join(self.cmd).strip() + "\n"
        ret += f">> RETCODE: {self.returncode}\n"
        ret += ">> STDOUT:\n" + self.stdout.decode("utf-8", errors="ignore")
        ret = ret.rstrip() + "\n"
        ret += ">> STDERR:\n" + self.stderr.decode("utf-8", errors="ignore")
        ret = ret.rstrip() + "\n" + BAR()
        return ret

    def to_test_result(self, msg, include_output=False):
        cmd = " ".join(self.cmd).strip()
        msg += f" ({cmd})"
        if self.returncode == 0:
            if include_output:
                msg += "\n" + str(self)
            return TestResult(True, msg)
        else:
            msg += "\n" + str(self)
            return TestResult(False, msg)


class AsyncNamedLocks:
    def __init__(self):
        self.__named_locks = {}
        self.__lock = asyncio.Lock()

    async def async_get_lock(self, name):
        async with self.__lock:
            if name not in self.__named_locks:
                self.__named_locks[name] = asyncio.Lock()
            return self.__named_locks[name]


def TODO(msg=""):
    raise Exception(f"TODO: {msg}")


def BAR():
    return "=" * 50


def get_env(key, must_have=False, default=None):
    value = os.environ.get(key, default)
    if value is None and must_have:
        logging.error(f"env[{key}] is None")
        sys.exit(-1)
    return value


def set_env(key: str, value: str):
    os.environ[key] = value


def run_cmd(
    cmd: list, cwd: str | Path | None = None, env=os.environ, timeout: int | None = None
):
    cmd = list(map(str, cmd))
    if isinstance(cwd, Path):
        cwd = str(cwd)
    if timeout:
        cmd = ["timeout", str(timeout)] + cmd
    return subprocess.run(cmd, cwd=cwd, env=env, capture_output=True)


async def async_run_cmd(
    cmd: list, cwd: str | Path | None = None, env=os.environ, timeout: int | None = None
):
    cmd = list(map(str, cmd))
    if isinstance(cwd, Path):
        cwd = str(cwd)
    if timeout:
        cmd = ["timeout", str(timeout)] + cmd
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=cwd,
        env=env,
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()
    return CmdResult(cmd, out, err, proc.returncode)


def __cp_cmd(src, dst):
    if src.is_dir():
        src = f"{src}/."
    return ["rsync", "-a", src, dst]


def cp(src: Path, dst: Path):
    os.makedirs(dst.parent, exist_ok=True)
    run_cmd(__cp_cmd(src, dst))


async def async_cp(src: Path, dst: Path):
    os.makedirs(dst.parent, exist_ok=True)
    await async_run_cmd(__cp_cmd(src, dst))


def __rm_cmd(path):
    return ["rm", "-rf", path]


def rm(path: Path):
    run_cmd(__rm_cmd(path))


async def async_rm(path: Path):
    await async_run_cmd(__rm_cmd(path))


def replace_base(target: Path, base: Path, dst: Path) -> Path:
    idx = len(str(base))
    name = str(target)[idx:]
    if name.startswith("/"):
        name = name[1:]
    return dst / name


async def async_wait_file(file: Path):
    while not file.exists():
        await asyncio.sleep(1)
