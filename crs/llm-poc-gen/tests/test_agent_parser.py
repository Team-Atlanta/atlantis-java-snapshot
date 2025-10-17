import pytest

from vuli.agents.parser import PythonParser
from vuli.struct import LLMParseException


@pytest.mark.asyncio
async def test_pythonparser_parse():
    script: str = """import sys
with open(sys.argv[1], "w") as f:
    f.write("Hello World")"""
    result: list[dict] = await PythonParser().parse(
        f"""```python
{script}
```
"""
    )
    assert len(result) == 1
    assert result[0]["blob"] == b"Hello World"
    assert result[0]["script"] == f"{script}\n"


@pytest.mark.asyncio
async def test_pythonparser_parse_no_result():
    with pytest.raises(LLMParseException):
        await PythonParser().parse("""""")


@pytest.mark.asyncio
async def test_pythonparser_parse_wrong_python():
    with pytest.raises(LLMParseException):
        await PythonParser().parse(
            """
```python
a = []
b = a[0]
```"""
        )


@pytest.mark.asyncio
async def test_pythonparser_parse_timeout():
    with pytest.raises(LLMParseException):
        await PythonParser().parse(
            """
```python
import time
time.sleep(2)
```""",
            timeout=1,
        )


@pytest.mark.asyncio
async def test_pythonparser_parse_no_output_file():
    with pytest.raises(LLMParseException):
        await PythonParser().parse(
            """
```python
print("Hello World")
```""",
        )
