import asyncio
from unittest.mock import patch

import pytest
from pydantic import BaseModel

from vuli.blackboard import Blackboard
from vuli.runner import CRS, Runner
from vuli.sink import SinkManager
from vuli.sinkupdateservice import SinkUpdateService
from vuli.task import TaskManager

counter: int = 0


@pytest.fixture(autouse=True)
def setup():
    asyncio.run(SinkManager().clear())
    asyncio.run(Blackboard().clear())
    TaskManager().clear()
    TaskManager().add_handlers(SinkUpdateService(1))


class FakeResponse(BaseModel):
    status_code: int
    response: dict

    def json(self) -> dict:
        return self.response


async def quit_runner(runner: Runner, delay: int = 0):
    await asyncio.sleep(delay)
    runner._stop_sink_to_path = True
    runner._stop_generation_if_no_path = True
    if hasattr(runner, "_stop"):
        runner._stop = True
    TaskManager()._stop = True


@pytest.mark.asyncio
@patch("vuli.pathfinder.FindPathService._run")
@patch("vuli.delta.DeltaManager.handle")
@patch("vuli.scanner.Scanner.run")
@patch("vuli.reflection.ReflectionSolver.run")
@patch("vuli.task.SyncCallGraph._run")
@patch("vuli.sinkupdateservice.SinkUpdateService._run")
@patch("vuli.task.BlobGeneration.run")
async def test_basic_run(patch_1, patch_2, patch_3, patch_4, patch_5, patch_6, patch_7):
    async def mock(*args, **kwargs):
        return

    patch_1.side_effect = mock
    patch_2.side_effect = mock
    patch_3.side_effect = mock
    patch_4.side_effect = mock
    patch_5.side_effect = mock
    patch_6.side_effect = mock
    patch_7.side_effect = mock

    runner: Runner = CRS()
    tasks = [
        asyncio.create_task(runner._run()),
    ]
    try:
        await asyncio.wait_for(
            asyncio.gather(*tasks),
            timeout=3.0,
        )
    except asyncio.TimeoutError:
        pass

    assert patch_1._mock_call_count > 0
    assert patch_2._mock_call_count > 0
    assert patch_3._mock_call_count > 0
    assert patch_4._mock_call_count > 0
    assert patch_5._mock_call_count > 0
    assert patch_6._mock_call_count > 0
    assert patch_7._mock_call_count > 0
