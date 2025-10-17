import asyncio
from unittest.mock import patch

import pytest

from vuli import path_manager
from vuli.blackboard import Blackboard
from vuli.cp import CP
from vuli.runner import C_SARIF
from vuli.sink import SinkManager

allow: set[int] = set()


@pytest.fixture(autouse=True)
def setup():
    global allow
    asyncio.run(Blackboard().clear())
    asyncio.run(SinkManager().clear())
    asyncio.run(path_manager.PathManager().clear())
    CP().harnesses = {}
    allow = set()


@patch("vuli.runner.Runner._initialize_joern")
@patch("vuli.runner.Runner._initialize_calltree")
@patch("vuli.sinkupdateservice.SinkUpdateService._run")
@patch("vuli.task.SyncCallGraph._run")
@patch("vuli.pathfinder.FindPathService._run")
@patch("vuli.task.BlobGeneration.run")
@patch("vuli.runner.Runner._save_output")
@pytest.mark.asyncio
async def test_c_sarif_workflow(
    patch_1, patch_2, patch_3, patch_4, patch_5, patch_6, patch_7
):
    def mock(*args, **kwargs):
        return None

    patches = [patch_1, patch_2, patch_3, patch_4, patch_5, patch_6, patch_7]
    for x in patches:
        x.side_effect = mock

    await asyncio.wait_for(C_SARIF().run(), timeout=1)

    [x.assert_called_once for x in patches]
