"""
Module that runs Python code provided by LLM using a docker sandbox.
"""
import ast
import time
import logging
import traceback
import subprocess


logger = logging.getLogger(__name__)


DOCKER_IMAGE_NAME = "python:3.13.1-bullseye"

# Gets set to false if `--no-use-docker` passed in through __main__
USE_DOCKER = True


def run_code_and_get_output(code: str) -> str:
    if USE_DOCKER:
        from llm_sandbox.docker import SandboxDockerSession
        with SandboxDockerSession(image=DOCKER_IMAGE_NAME, keep_template=True, lang="python", commit_container=False, stream=False) as session:
            result = session.run(code)
            if result.exit_code != 0:
                raise ValueError(f"Code: {result.exit_code} Output: {result.text.strip()}")
            return result.text
    else:
        logger.info("Running with native python3 command")
        return subprocess.check_output(["python3"], input=code, text=True, timeout=20)


RUNNER_CODE = """\

import inspect
import sys

try:
    function_sig = inspect.signature(generate_example)
except NameError:
    print("generate_example function not present")
    sys.exit(1)

if len(function_sig.parameters) != 1:
    print("generate_example does not take exactly 1 argument")
    sys.exit(1)

return_val = generate_example(input_bytes)
if isinstance(return_val, bytearray):
    return_val = bytes(return_val)

if not isinstance(return_val, bytes):
    print("generate_example returned " + str(type(return_val)) + ", not bytes")
    sys.exit(1)

print(repr(bytes(return_val)))
sys.exit(0)
"""

def run_generate_example_function(code: str, input_bytes: bytes) -> bytes:
    """Runs a python function called `generate_example` with the parameter
    `input_bytes` that should return a bytes instance.
    
    Returns the bytes if the function was called successfully, otherwise throws
    a ValueError with the cause."""
    input_bytes = repr(input_bytes)
    script_preamble = f"input_bytes = {input_bytes}"

    # If the LLM generated code expecting a bytearray, just convert to it...
    if 'isinstance(input, bytearray)' in code:
        script_preamble += "\ninput_bytes = bytearray(input_bytes)"

    full_script = f"""\
{script_preamble}

{code}

{RUNNER_CODE}
"""
    output = run_code_and_get_output(full_script)

    # Get the last line of output, it should be a bytes repr like:
    #   b'\x00A'
    # Turn it back into a bytes object safely with ast.literal_eval
    last_line = output.splitlines()[-1]
    parsed_bytes = ast.literal_eval(last_line)
    if not isinstance(parsed_bytes, bytes):
        raise ValueError("Output did not parse to bytes: " + last_line)

    # Impose a 2mb limit on output corpora.
    if len(parsed_bytes) > 2 * 1024 * 1024:
        raise ValueError("Output too long")

    return parsed_bytes

def run_generate_example_function_with_retry(code: str, input_bytes: bytes, n: int = 5) -> bytes | None:
    """Retries up to n times with 1 second wait between retries. Catches all 
    exceptions, returns None if all attempts fail."""
    for attempt in range(n):
        try:
            return run_generate_example_function(code, input_bytes)
        except Exception as e:
            logger.info(f"Meet exception {e} when executing LLM-generated code, retry {attempt + 1}/{n}")
            logger.debug(f"Exception details: \n{traceback.format_exc()}")
            if attempt < n - 1:
                time.sleep(1)
            else:
                logger.error(f"Failed all {n} attempts")
                return None
