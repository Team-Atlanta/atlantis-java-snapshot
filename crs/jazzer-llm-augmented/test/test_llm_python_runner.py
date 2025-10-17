import subprocess
import textwrap

from jazzer_llm import llm_python_runner

import pytest


# Skip tests if we don't have docker present.
try:
    subprocess.call(["docker", "--help"])
except FileNotFoundError:
    pytest.skip("skipping tests that need docker", allow_module_level=True)


def test_can_run_a_python_script_and_get_output():
    result = llm_python_runner.run_code_and_get_output(r"print(1)")
    assert result.strip() == "1"


def test_run_generate_example_successfully_returns_bytes():
    example = (r"""\
from io import BytesIO

def generate_example(input_bytes):
    # Create a BytesIO buffer to simulate a valid .class file
    output = BytesIO()

    # Write a minimal .class file header
    # Magic number (0xCAFEBABE)
    output.write(b'\xCA\xFE\xBA\xBE')

    # Return the mutated input
    return output.getvalue()
"""
    )
    result = llm_python_runner.run_generate_example_function(example, b'')
    assert result == b"\xCA\xFE\xBA\xBE"


def test_run_generate_example_correctly_passes_existing_input():
    example = textwrap.dedent("""\
    def generate_example(corpus):
        return b"\\x00" + corpus + b"\\x03"
    """)
    result = llm_python_runner.run_generate_example_function(example, b'\x01\x02')
    assert result == b"\x00\x01\x02\x03"


def test_fails_if_code_does_not_have_generate_example_function():
    example = textwrap.dedent("""\
    def hello_world():
        return 2
    """)

    with pytest.raises(ValueError) as e:
        result = llm_python_runner.run_generate_example_function(example, b'')
    assert "generate_example function not present" in str(e)


def test_fails_if_generate_example_has_wrong_params():
    example = textwrap.dedent("""\
    def generate_example():
        return 2
    """)

    with pytest.raises(ValueError) as e:
        result = llm_python_runner.run_generate_example_function(example, b'')
    assert "generate_example does not take exactly 1 argument" in str(e)


def test_fails_if_generate_example_does_not_return_bytes():
    example = textwrap.dedent("""\
    def generate_example(x):
        return 2
    """)

    with pytest.raises(ValueError) as e:
        result = llm_python_runner.run_generate_example_function(example, b'')
    assert "generate_example returned <class 'int'>, not bytes" in str(e)
