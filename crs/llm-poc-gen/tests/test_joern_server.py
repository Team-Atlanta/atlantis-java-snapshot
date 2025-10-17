import asyncio
import os
from typing import Callable
from unittest.mock import AsyncMock, patch

import pytest

from vuli.joern import JoernServer


def is_valid_query(res):
    query_response = res[0]
    query_result = res[1]
    return (
        True
        if (
            query_result is True
            and query_response.get("stdout") is not None
            and not query_response["stdout"].endswith("error found\n")
        )
        else False
    )


@pytest.fixture(scope="module")
def joern_server():
    result = JoernServer(
        os.path.join(os.getenv("JOERN_DIR"), "joern"), os.environ.copy(), ["val a = 1"]
    )
    asyncio.run(result.start())
    yield result
    asyncio.run(result.stop())


@pytest.mark.asyncio
async def test_timeout_and_query(joern_server):
    assert (
        is_valid_query(await joern_server.query("Thread.sleep(10000)", timeout=1))
        is False
    )
    assert is_valid_query(await joern_server.query("")) is True


@pytest.mark.asyncio
async def test_query_intime(joern_server):
    with patch("vuli.joern.JoernServer.restart") as p:
        assert (
            is_valid_query(await joern_server.query("Thread.sleep(1000)", timeout=2))
            is True
        )
        assert p.called is False


@pytest.mark.asyncio
async def test_query_timeout(joern_server):
    with patch("vuli.joern.JoernServer._restart") as p:
        assert (
            is_valid_query(await joern_server.query("Thread.sleep(10000)", timeout=1))
            is False
        )
        p.assert_called_once()


@pytest.mark.asyncio
async def test_query_no_restart_on_failure(joern_server):
    with patch("vuli.joern.JoernServer.restart") as p:
        assert (
            is_valid_query(
                await joern_server.query(
                    "Thread.sleep(10000)", timeout=1, restart_on_failure=False
                )
            )
            is False
        )
        assert p.called is False


@pytest.mark.asyncio
async def test_query_invalid(joern_server):
    assert is_valid_query(await joern_server.query("invalid")) is False


@pytest.mark.asyncio
async def test_query_stopped_server(joern_server):
    await joern_server.stop()
    assert is_valid_query(await joern_server.query("")) is False


@pytest.mark.asyncio
async def test_restart(joern_server):
    await joern_server.restart()
    assert is_valid_query(await joern_server.query("")) is True


@pytest.mark.asyncio
async def test_start_twice(joern_server):
    await joern_server.start()
    await joern_server.start()
    assert is_valid_query(await joern_server.query("")) is True


@pytest.mark.asyncio
async def test_restart_twice(joern_server):
    await joern_server.restart()
    await joern_server.restart()
    assert is_valid_query(await joern_server.query(""))


@pytest.mark.asyncio
async def test_stop_twice(joern_server):
    await joern_server.stop()
    await joern_server.stop()


@pytest.mark.asyncio
async def test_init_script_defined(joern_server):
    if not joern_server.is_running():
        await joern_server.start()
    res = await joern_server.query("val b = a")
    assert is_valid_query(res) is True
    res = await joern_server.query("val c = b")
    assert is_valid_query(res) is True


@pytest.mark.asyncio
async def test_init_script_undefined(joern_server):
    res = await joern_server.query("val c = b")
    assert is_valid_query(res) is True


@pytest.mark.asyncio
async def test_timeout(joern_server):
    if not joern_server.is_running():
        await joern_server.start()
    with patch("vuli.joern.JoernServer._restart") as p:
        res = await joern_server.query(
            "val largeArray: Array[Int] = Array.fill(1000000000)(0)", timeout=2
        )
        assert is_valid_query(res) is False
        assert p.called is True


@pytest.mark.asyncio
async def test_recursion_limit(joern_server):
    class MockResponse:
        def __init__(self, orig: Callable):
            self._counter: int = 0
            self._orig: Callable = orig

        async def response(self, *args, **kwargs):
            if self._counter == 0:
                self._counter += 1
                return {"stdout": "Recursion limit exceeded"}
            return await self._orig(joern_server, *args, **kwargs)

    if not joern_server.is_running():
        await joern_server.start()

    orig: Callable = JoernServer._raw_request
    with patch("vuli.joern.JoernServer._raw_request", new_callable=AsyncMock) as p:
        response = MockResponse(orig)
        p.side_effect = response.response
        assert "Recursion limit exceeded" in (
            await joern_server.query_once("""print("Hello")""")
        )

        response._counter = 0
        assert "11" in (await joern_server.safe_query("""1 + 10"""))
