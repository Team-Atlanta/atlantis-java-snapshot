import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from vuli.blackboard import Blackboard
from vuli.joern import Joern
from vuli.scanner import Scanner
from vuli.sink import Origin, SinkManager, SinkProperty, SinkStatus
from vuli.struct import Sanitizer


@pytest.fixture(autouse=True)
def setup():
    asyncio.run(SinkManager().clear())


@pytest.mark.asyncio
@patch.object(Joern, "run_query")
async def test__run_per_sanitizer(patch_1):
    patch_1.return_value = [{"id": 0, "unexploitable": False}]
    scanner: Scanner = Scanner()
    await scanner._run_per_sanitizer("sink-OsCommandInjection")
    sinks: dict[int, SinkProperty] = await SinkManager().get()
    assert "sink-OsCommandInjection" in sinks[0].bug_types
    assert Origin.FROM_INSIDE in sinks[0].origins
    assert SinkStatus.UNKNOWN == sinks[0].status


@pytest.mark.asyncio
@patch.object(Joern, "run_query")
async def test__run_per_sanitizer_unexploitable(patch_1):
    patch_1.return_value = [{"id": 0, "unexploitable": True}]
    scanner: Scanner = Scanner()
    await scanner._run_per_sanitizer("sink-OsCommandInjection")
    sinks: dict[int, SinkProperty] = await SinkManager().get()
    assert "sink-OsCommandInjection" in sinks[0].bug_types
    assert Origin.FROM_INSIDE in sinks[0].origins
    assert SinkStatus.UNEXPLOITABLE == sinks[0].status


@pytest.mark.asyncio
@patch.object(Joern, "run_query")
async def test__run_per_sanitizer_no_result(patch_1):
    patch_1.return_value = []
    scanner: Scanner = Scanner()
    await scanner._run_per_sanitizer("sink-OsCommandInjection")
    assert len(await SinkManager().get()) == 0


@pytest.mark.asyncio
@patch.object(Joern, "run_query")
async def test__run_per_sanitizer_joern_invalid_output(patch_1):
    patch_1.return_value = [{"error": "error"}]
    scanner: Scanner = Scanner()
    await scanner._run_per_sanitizer("sink-OsCommandInjection")
    assert len(await SinkManager().get()) == 0


@pytest.mark.asyncio
@patch.object(Blackboard, "save", new_callable=AsyncMock)
@patch.object(Joern, "run_query", new_callable=AsyncMock)
async def test__run(patch_1, patch_2):
    async def mock_1(*args, **kwargs) -> list[dict]:
        id: int = 0
        while id in await SinkManager().get():
            id += 1
        return [{"id": id, "unexploitable": False}]

    patch_1.side_effect = mock_1
    scanner: Scanner = Scanner()
    sanitizers: list[Sanitizer] = [
        Sanitizer(name="sink-OsCommandInjection", sentinel=["jazze"]),
        Sanitizer(
            name="sink-ServerSideRequestForgery", sentinel=["jazzer.example.com"]
        ),
    ]
    await asyncio.wait_for(scanner.run(sanitizers), timeout=5)
    sinks: dict[int, SinkProperty] = await SinkManager().get()
    assert "sink-OsCommandInjection" in sinks[0].bug_types
    assert Origin.FROM_INSIDE in sinks[0].origins
    assert SinkStatus.UNKNOWN == sinks[0].status
    assert "sink-ServerSideRequestForgery" in sinks[1].bug_types
    assert Origin.FROM_INSIDE in sinks[1].origins
    assert SinkStatus.UNKNOWN == sinks[1].status
    patch_2.assert_called_once()
