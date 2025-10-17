#!/usr/bin/env python3

import asyncio
import os
import shlex
import shutil
import subprocess
import sys
import traceback
from pathlib import Path
from typing import Optional, Tuple

import aiofiles
import ijson

CHUNK_SIZE = 8192

SENSITIVE_ENV_VARS = [
    "AZURE_OPENAI_API_KEY",
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_DEPLOYMENT",
    "LITELLM_KEY",
    "GITHUB_TOKEN",
    "GITHUB_USER",
]


def CRS_ERR_LOG(mod: str) -> str:
    return f"CRS-JAVA-ERR-{mod}"


def CRS_WARN_LOG(mod: str) -> str:
    return f"CRS-JAVA-WARN-{mod}"


def get_env_or_abort(env_name: str) -> str:
    env_value = os.getenv(env_name)
    if env_value is None:
        print(f"Environment variable {env_name} is not set.", file=sys.stderr)
        sys.exit(1)
    return env_value


def get_env_or_empty(env_name: str) -> str:
    return os.getenv(env_name, "")


def is_jazzer_gen_seed(name: str) -> bool:
    # libafl -> 16 bytes, libfuzzer -> 40 bytes
    return len(name) in [16, 40] and all(c in "0123456789abcdefABCDEF" for c in name)


def sanitize_env(env: dict) -> dict:
    """Remove sensitive environment variables from the environment."""
    global SENSITIVE_ENV_VARS

    new_env = env.copy()
    for var in SENSITIVE_ENV_VARS:
        new_env.pop(var, None)

    return new_env


def get_env_exports(env: dict) -> str:
    """Return a string that can be used to export the environment variables."""
    return "\n".join(
        f"export {k}={shlex.quote(v)}" for k, v in sanitize_env(env).items()
    )


async def run_process_and_capture_output(command_sh: Path, output_log: Path) -> int:
    process = await asyncio.create_subprocess_exec(
        "bash",
        str(command_sh.resolve()),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )

    async with aiofiles.open(output_log, "wb") as f:
        while True:
            chunk = await process.stdout.read(CHUNK_SIZE)
            if not chunk:
                break
            await f.write(chunk)

    ret = await process.wait()
    return ret


async def stream_load_json(file_path: Path, field_path: str, logger=None):
    if not file_path.exists():
        if logger:
            logger(f"JSON file not found: {file_path}")
        return

    try:
        async with aiofiles.open(file_path, "rb") as f:
            async for item in ijson.items(f, field_path):
                yield item

    except Exception as e:
        if logger:
            logger(f"Error streaming JSON from {file_path}: {str(e)}")
            logger(f"Traceback: {traceback.format_exc()}")


async def atomic_write_file(target_path: Path, content: str):
    """Write content to a temporary file and then atomically move it to the target path."""
    temp_path = target_path.parent / f".hidden.{target_path.name}"

    try:
        async with aiofiles.open(temp_path, "w") as f:
            await f.write(content)
            # Ensure all data is written to disk
            await f.flush()
            os.fsync(f.fileno())

        # Atomically rename temp file to target file
        os.replace(temp_path, target_path)
    except Exception as e:
        try:
            os.unlink(temp_path)
        except Exception:
            pass
        raise e


async def atomic_write_file_frm_path(target_path: Path, source_path: Path):
    """Write content from source file to a temporary file and then atomically move it to the target path."""
    temp_path = target_path.parent / f".hidden.{target_path.name}"

    try:
        async with aiofiles.open(source_path, "rb") as s, aiofiles.open(
            temp_path, "wb"
        ) as d:
            while data := await s.read(CHUNK_SIZE):
                await d.write(data)

        os.replace(temp_path, target_path)
    except Exception as e:
        try:
            temp_path.unlink()
        except Exception:
            pass
        raise e


def atomic_write_file_sync(target_path: Path, content: str):
    """Write content to a temporary file and then atomically move it to the target path."""
    temp_path = target_path.parent / f".hidden.{target_path.name}"

    try:
        with open(temp_path, "w") as f:
            f.write(content)
            # Ensure all data is written to disk
            f.flush()
            os.fsync(f.fileno())

        # Atomically rename temp file to target file
        os.replace(temp_path, target_path)
    except Exception as e:
        try:
            os.unlink(temp_path)
        except Exception:
            pass
        raise e


def unzip_sync(zip_path: Path, target_dir: Path, err_tag: str):
    """Unzip a file synchronously with error handling."""
    try:
        subprocess.run(
            ["unzip", "-o", str(zip_path), "-d", str(target_dir)],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception as e:
        raise Exception(f"{err_tag}: {str(e)} {traceback.format_exc()}")


def flatten_dir_copy_sync(src_path: Path, dst_path: Path, logger):
    """Recursively copy all files from src_path to dst_path with flat structure.
    Rename files with numeric suffix if name conflicts occur."""
    if not src_path.exists() or not src_path.is_dir():
        logger(f"Error: Source directory not found: {src_path}")
        return 0, 0

    dst_path.mkdir(parents=True, exist_ok=True)
    succ_count = fail_count = 0

    for src_file in src_path.rglob("*"):
        if src_file.is_file():
            dst_file = dst_path / src_file.name
            counter = 1

            while dst_file.exists():
                dst_file = dst_path / f"{src_file.stem}_{counter}{src_file.suffix}"
                counter += 1

            try:
                shutil.copy2(src_file, dst_file)
                succ_count += 1
            except Exception:
                fail_count += 1

    return succ_count, fail_count


async def download_file_async(
    src_path: Path,
    dst_dir: Path,
    logger,
    err_tag: str,
) -> Tuple[Optional[Path], bool]:
    """Download file asynchronously with chunked streaming for NFS efficiency."""
    if not src_path.exists():
        if logger:
            logger(f"{err_tag}: Source file {src_path} does not exist")
        return None, False

    dst_path = dst_dir / src_path.name
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    chunk_size = 64 * 1024  # 64KB chunks

    try:
        async with aiofiles.open(src_path, "rb") as src_f:
            async with aiofiles.open(dst_path, "wb") as dst_f:
                while chunk := await src_f.read(chunk_size):
                    await dst_f.write(chunk)
                await dst_f.flush()
                os.fsync(dst_f.fileno())

        if logger:
            logger(f"Downloaded {src_path.name} to {dst_path}")
        return dst_path, True
    except Exception as e:
        if logger:
            logger(f"{err_tag}: Download error: {str(e)} {traceback.format_exc()}")
        return None, False
