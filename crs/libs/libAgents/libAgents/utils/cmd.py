import asyncio
import logging
import os
import pty
import subprocess
import time
import psutil
import re
import signal
from pathlib import Path
from dataclasses import dataclass
from typing import (
    Dict,
    List,
    Optional,
    Tuple,
    Union,
)

logger = logging.getLogger(__name__)


@dataclass
class CmdExecutionResult:
    args: list
    returncode: int
    stdout: bytes
    stderr: bytes


class CommandInteractionError(Exception):
    def __init__(self, stdout, stderr, return_code):
        self.stdout = stdout
        self.stderr = stderr
        self.return_code = return_code
        super().__init__(f"Command failed with return code {return_code}")


class TimeoutExpired(Exception):
    def __init__(self, stdout, stderr):
        self.stdout = stdout
        self.stderr = stderr
        super().__init__("Command timed out")


def remove_ansi_escape_codes(text):
    """Remove ANSI escape codes from text."""
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", text) if isinstance(text, str) else text


def _kill_process_tree(pid: int):
    """Kill a process and all its children."""
    if psutil is None:
        # Fallback if psutil is not available
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass
        return

    try:
        psutil_process = psutil.Process(pid)
    except psutil.NoSuchProcess:
        return

    children = psutil_process.children(recursive=True)
    for child in children[::-1]:
        try:
            child.kill()
        except psutil.NoSuchProcess:
            pass

    try:
        psutil_process.kill()
    except psutil.NoSuchProcess:
        pass


def run_command(
    command: Union[List[str], Tuple[str, Path], str],
    cwd: Optional[Path] = None,
    timeout: Optional[int] = None,
    env: Optional[Dict[str, str]] = None,
    input: Optional[bytes] = None,
    isatty: bool = False,
    no_color: bool = False,
) -> Tuple[str, str]:
    """Run a command and return stdout and stderr.

    Args:
        command: The command to run. Can be a list of arguments, a tuple of (command_string, cwd),
                or a command string.
        cwd: The working directory to run the command in. Only used if command is not a tuple.
        timeout: Timeout in seconds.
        env: Environment variables.
        input: Input to pass to the command.
        isatty: Whether to use a pseudo-terminal.
        no_color: Whether to remove ANSI escape codes from output.

    Returns:
        A tuple of (stdout, stderr).

    Raises:
        CommandInteractionError: If the command returns a non-zero exit code.
        TimeoutExpired: If the command times out.
    """
    # Handle different command formats
    if isinstance(command, tuple) and len(command) == 2:
        cmd_str, cmd_cwd = command
    elif isinstance(command, list):
        cmd_str = " ".join(str(arg) for arg in command)
        cmd_cwd = cwd
    else:
        cmd_str = str(command)
        cmd_cwd = cwd

    # Prepare environment
    full_env = os.environ.copy()
    if env:
        full_env.update(env)

    # Use pty if requested and available
    if isatty and pty is not None:
        return _run_command_with_pty((cmd_str, cmd_cwd), timeout, full_env, input)

    # Regular subprocess execution
    process = subprocess.Popen(
        cmd_str,
        cwd=cmd_cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
        env=full_env,
    )

    try:
        stdout, stderr = process.communicate(input=input, timeout=timeout)

        if no_color:
            stdout = remove_ansi_escape_codes(stdout.decode(errors="ignore"))
            stderr = remove_ansi_escape_codes(stderr.decode(errors="ignore"))
        else:
            stdout = stdout.decode(errors="ignore")
            stderr = stderr.decode(errors="ignore")

        if process.returncode != 0:
            raise CommandInteractionError(stdout, stderr, process.returncode)

        return stdout, stderr

    except subprocess.TimeoutExpired:
        # Try to terminate gracefully first
        process.terminate()
        time.sleep(1)

        # If still running, kill forcefully
        if process.poll() is None:
            _kill_process_tree(process.pid)

        # Collect any output that was produced
        try:
            stdout, stderr = process.communicate(timeout=1)
            stdout = stdout.decode(errors="ignore")
            stderr = stderr.decode(errors="ignore")
        except Exception:
            stdout = ""
            stderr = ""

        raise TimeoutExpired(stdout, stderr)


def _run_command_with_pty(
    command: Tuple[str, Path],
    timeout: Optional[int] = None,
    env: Optional[Dict[str, str]] = None,
    input: Optional[bytes] = None,
) -> Tuple[str, str]:
    """Run a command with a pseudo-terminal."""
    if pty is None:
        raise ImportError(
            "The pty module is required for isatty=True but is not available"
        )

    line, cwd = command

    main, sub = pty.openpty()
    process = subprocess.Popen(
        line,
        cwd=cwd,
        stdin=sub,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
        env=env,
    )
    os.close(sub)

    try:
        if input:
            os.write(main, input + b"\n")
        stdout, stderr = process.communicate(timeout=timeout)

        if process.returncode != 0:
            raise CommandInteractionError(
                stdout.decode(errors="ignore"),
                stderr.decode(errors="ignore"),
                process.returncode,
            )

        return stdout.decode(errors="ignore"), stderr.decode(errors="ignore")

    except subprocess.TimeoutExpired:
        process.terminate()
        time.sleep(1)

        if process.poll() is None:
            _kill_process_tree(process.pid)

        try:
            stdout, stderr = process.communicate(timeout=1)
            stdout = stdout.decode(errors="ignore")
            stderr = stderr.decode(errors="ignore")
        except Exception:
            stdout = ""
            stderr = ""

        raise TimeoutExpired(stdout, stderr)


def _run_command_with_pty(
    command: Tuple[str, Path],
    timeout: Optional[int] = None,
    env: Optional[Dict[str, str]] = None,
    input: Optional[bytes] = None,
) -> Tuple[str, str]:
    """Run a command with a pseudo-terminal."""
    if pty is None:
        raise ImportError(
            "The pty module is required for isatty=True but is not available"
        )

    line, cwd = command

    main, sub = pty.openpty()
    process = subprocess.Popen(
        line,
        cwd=cwd,
        stdin=sub,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
        env=env,
    )
    os.close(sub)

    try:
        if input:
            os.write(main, input + b"\n")
        stdout, stderr = process.communicate(timeout=timeout)

        if process.returncode != 0:
            raise CommandInteractionError(
                stdout.decode(errors="ignore"),
                stderr.decode(errors="ignore"),
                process.returncode,
            )

        return stdout.decode(errors="ignore"), stderr.decode(errors="ignore")

    except subprocess.TimeoutExpired:
        process.terminate()
        time.sleep(1)

        if process.poll() is None:
            _kill_process_tree(process.pid)

        try:
            stdout, stderr = process.communicate(timeout=1)
            stdout = stdout.decode(errors="ignore")
            stderr = stderr.decode(errors="ignore")
        except Exception:
            stdout = ""
            stderr = ""

        raise TimeoutExpired(stdout, stderr)


def run_cmd(cmd, cwd=None, env=None, timeout=None, debug=False):
    """Run a command and return stdout.

    Args:
        cmd: The command to run. Can be a list of arguments or a string.
        cwd: The working directory to run the command in.
        env: Environment variables as a dict or list of "KEY=VALUE" strings.
        timeout: Timeout in seconds.
        debug: Whether to print debug information.

    Returns:
        The stdout of the command.

    Raises:
        Exception: If the command fails.
    """
    # Convert environment from list to dict if needed
    env_dict = None
    if env:
        if isinstance(env, list):
            env_dict = {}
            for item in env:
                if "=" in item:
                    key, value = item.split("=", 1)
                    env_dict[key] = value
        else:
            env_dict = env

    # Convert command list to string for debug printing
    cmd_str = cmd
    if isinstance(cmd, list):
        cmd_str = " ".join(str(arg) for arg in cmd)

    if debug:
        logger.debug(f"Running command: {cmd_str}")
        logger.debug(f"Working directory: {cwd}")
        logger.debug(f"Environment: {env_dict}")

    try:
        stdout, stderr = run_command(cmd, cwd=cwd, timeout=timeout, env=env_dict)
        return stdout
    except CommandInteractionError as e:
        logger.error(f"Command failed: {cmd_str}")
        logger.error(f"Working directory: {cwd}")
        logger.error(f"Stdout: {e.stdout}")
        logger.error(f"Stderr: {e.stderr}")
        raise Exception(f"Command failed with return code {e.return_code}: {e.stderr}")
    except TimeoutExpired as e:
        logger.error(f"Command timed out: {cmd_str}")
        logger.error(f"Stdout: {e.stdout}")
        logger.error(f"Stderr: {e.stderr}")
        raise Exception(f"Command timed out: {cmd_str}")


async def async_run_cmd(cmd, cwd=None, env=None, disable_info=True):
    try:
        cmd = list(map(str, cmd))
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=cwd,
            env=env,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        out, err = await proc.communicate()
        if not disable_info:
            logger.info("Result of running " + " ".join(cmd))
            logger.info((out + err).decode("utf-8", errors="ignore"))
        return CmdExecutionResult(
            args=cmd, returncode=proc.returncode, stdout=out, stderr=err
        )
    except Exception:
        logging.error("Fail to run: " + " ".join(cmd))
        return CmdExecutionResult(args=cmd, returncode=1, stdout=b"", stderr=b"")


def copy_dir(src, dst):
    """Copy a directory from src to dst."""
    return run_cmd(["rsync", "-a", str(src) + "/.", str(dst)])


def async_copy_dir(src, dst):
    """Copy a directory from src to dst."""
    return async_run_cmd(["rsync", "-a", str(src) + "/.", str(dst)])


def copy_files_in_dir(
    src_dir: Path,
    dst_dir: Path,
    exclude_patterns: list[str] = None,
):
    cmd = ["rsync", "-a"]

    # Add default exclude patterns
    # default execlude fuzzer lock files
    # cmd.extend(["--exclude", "*.lafl_lock", "--exclude", "*.tmp", "--exclude", "*.metadata", "--exclude", "*-[0-9]*"])

    # Add custom exclude patterns if provided
    if exclude_patterns:
        for pattern in exclude_patterns:
            cmd.extend(["--exclude", pattern])

    # Add source and destination paths
    cmd.extend([str(src_dir) + "/", str(dst_dir)])

    return run_cmd(cmd, disable_info=True)


async def async_copy_files_in_dir(
    src_dir: Path,
    dst_dir: Path,
    exclude_patterns: list[str] = None,
):
    cmd = ["rsync", "-a"]

    # Add default exclude patterns
    # default execlude fuzzer lock files
    # cmd.extend(["--exclude", "*.lafl_lock", "--exclude", "*.tmp", "--exclude", "*.metadata", "--exclude", "*-[0-9]*"])

    # Add custom exclude patterns if provided
    if exclude_patterns:
        for pattern in exclude_patterns:
            cmd.extend(["--exclude", pattern])

    # Add source and destination paths
    cmd.extend([str(src_dir) + "/", str(dst_dir)])

    return async_run_cmd(cmd, disable_info=True)
