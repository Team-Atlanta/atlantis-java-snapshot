import os
import tempfile
import pytest

from libAgents.plugins.sed import SedPlugin


@pytest.fixture
def temp_test_dir():
    """Create a temporary directory with test files."""
    with tempfile.TemporaryDirectory() as tmpdirname:
        test_files = {
            "test1.txt": "Line 1\nLine 2\nLine 3\nLine 4\nLine 5",
            "test2.txt": "Alpha\nBeta\nGamma\nDelta",
            "subdir/test3.txt": "A\nB\nC\nD\nE\nF",
        }
        for file_path, content in test_files.items():
            full_path = os.path.join(tmpdirname, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w") as f:
                f.write(content)
        yield tmpdirname


@pytest.mark.asyncio
async def test_sed_extract_single_line(temp_test_dir):
    plugin = SedPlugin()
    file_path = os.path.join(temp_test_dir, "test1.txt")
    result = await plugin.do_sed(3, 3, file_path)
    assert result.returncode == 0
    assert result.stdout.decode().strip() == "Line 3"


@pytest.mark.asyncio
async def test_sed_extract_range(temp_test_dir):
    plugin = SedPlugin()
    file_path = os.path.join(temp_test_dir, "test2.txt")
    result = await plugin.do_sed(2, 4, file_path)
    assert result.returncode == 0
    lines = result.stdout.decode().splitlines()
    assert lines == ["Beta", "Gamma", "Delta"]


@pytest.mark.asyncio
async def test_sed_out_of_bounds(temp_test_dir):
    plugin = SedPlugin()
    file_path = os.path.join(temp_test_dir, "test1.txt")
    result = await plugin.do_sed(10, 15, file_path)
    assert result.returncode == 0
    assert result.stdout.decode().strip() == ""


@pytest.mark.asyncio
async def test_sed_file_not_exist(temp_test_dir):
    plugin = SedPlugin()
    file_path = os.path.join(temp_test_dir, "no_such_file.txt")
    result = await plugin.do_sed(1, 2, file_path)
    assert result.returncode != 0
    assert b"No such file" in result.stderr or b"no such file" in result.stderr


@pytest.mark.asyncio
async def test_sed_start_greater_than_end(temp_test_dir):
    plugin = SedPlugin()
    file_path = os.path.join(temp_test_dir, "test2.txt")
    result = await plugin.do_sed(4, 2, file_path)
    assert result.returncode == 0
    assert result.stdout.decode().strip() == "Delta"


@pytest.mark.asyncio
async def test_sed_negative_lines(temp_test_dir):
    plugin = SedPlugin()
    file_path = os.path.join(temp_test_dir, "test1.txt")
    result = await plugin.do_sed(-2, 2, file_path)
    # sed may treat negative as invalid, so expect error
    assert result.returncode != 0 or result.stdout.decode().strip() == ""
