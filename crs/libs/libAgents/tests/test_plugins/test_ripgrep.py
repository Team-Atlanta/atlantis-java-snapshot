import os
import tempfile
from typing import Generator

import pytest

from libAgents.plugins.ripgrep import RipGrepPlugin


@pytest.fixture
def temp_test_dir() -> Generator[str, None, None]:
    """Create a temporary directory with test files.

    Returns:
        Generator[str, None, None]: Path to the temporary directory
    """
    with tempfile.TemporaryDirectory() as tmpdirname:
        # Create some test files with content
        test_files = {
            "test1.txt": "Hello world\nThis is a test\nAnother line",
            "test2.py": 'def test_function():\n    print("Hello")\n    return True',
            "test3.json": '{"message": "Hello JSON", "value": 42}',
            "subdir/test4.txt": "Nested test\nHello from subdir\nTest content",
            "subdir/test5.py": 'class TestClass:\n    def __init__(self):\n        self.hello = "Hello"',
        }

        for file_path, content in test_files.items():
            full_path = os.path.join(tmpdirname, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w") as f:
                f.write(content)

        yield tmpdirname


@pytest.mark.asyncio
async def test_ripgrep_success(temp_test_dir: str) -> None:
    """Test successful ripgrep search."""
    plugin = RipGrepPlugin()

    # Test searching for "Hello" in all file types
    result = await plugin.do_ripgrep("Hello", temp_test_dir)
    print(result)
    assert result.returncode == 0
    output = result.stdout.decode()
    assert "Hello" in output
    # Check specific files are found
    assert any("test1.txt" in line for line in output.splitlines())
    assert any("test2.py" in line for line in output.splitlines())
    assert any("test3.json" in line for line in output.splitlines())
    assert any("subdir/test4.txt" in line for line in output.splitlines())


@pytest.mark.asyncio
async def test_ripgrep_no_matches(temp_test_dir: str) -> None:
    """Test ripgrep when no matches are found."""
    plugin = RipGrepPlugin()

    # Test searching for non-existent pattern
    result = await plugin.do_ripgrep("NonExistentPattern", temp_test_dir)
    assert result.returncode == 1  # ripgrep returns 1 when no matches found
    assert result.stdout.decode().strip() == ""


@pytest.mark.asyncio
async def test_ripgrep_case_insensitive(temp_test_dir: str) -> None:
    """Test ripgrep case insensitivity (implementation uses -i flag)."""
    plugin = RipGrepPlugin()

    # Test case-insensitive search (should find both HELLO and Hello)
    result = await plugin.do_ripgrep("HELLO", temp_test_dir)
    print(result)
    assert result.returncode == 0
    output = result.stdout.decode()
    # Check that we find matches regardless of case
    # Note: ripgrep returns the original text, so we check for lowercase
    assert any("Hello" in line for line in output.splitlines())


@pytest.mark.asyncio
async def test_ripgrep_invalid_directory() -> None:
    """Test ripgrep with invalid directory path."""
    plugin = RipGrepPlugin()

    result = await plugin.do_ripgrep("test", "/nonexistent/directory")
    assert result.returncode == 2  # ripgrep returns 2 for file system errors
    assert b"No such file" in result.stderr or b"no such file" in result.stderr


@pytest.mark.asyncio
async def test_ripgrep_nginx_src() -> None:
    """Test ripgrep with nginx source code."""
    oss_repo = pytest.get_oss_repo("aixcc/c/asc-nginx")
    plugin = RipGrepPlugin()
    result = await plugin.do_ripgrep("ngx_decode_base64", oss_repo)
    print(result)
    assert result.returncode == 0
    output = result.stdout.decode()
    assert "ngx_decode_base64" in output
