import asyncio
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from vuli import path_manager
from vuli.blackboard import Blackboard
from vuli.calltree import CallTree
from vuli.common.setting import Setting
from vuli.cp import CP
from vuli.pathfinder import FindPathService
from vuli.sink import SinkManager, SinkProperty, SinkStatus
from vuli.struct import CodeLocation, VulInfo
from vuli.task import (
    BlobGeneration,
    PathBasedGeneration,
    ServiceHandler,
    SyncCallGraph,
    TaskHandler,
    TaskManager,
)


@pytest.fixture(autouse=True)
def setup():
    asyncio.run(Blackboard().clear())
    asyncio.run(SinkManager().clear())
    TaskManager().clear()


@pytest.mark.asyncio
async def test_run():
    class MockTask(TaskHandler):
        def __init__(self):
            self._called: int = 0

        async def run(self) -> None:
            self._called += 1

    task: MockTask = MockTask()
    TaskManager().add_handlers(
        task,
    )
    await asyncio.wait_for(TaskManager().run(), timeout=1)
    assert task._called == 1


allow: set[int] = set()


@pytest.mark.asyncio
@patch.object(Blackboard, "save")
@patch("vuli.pathfinder.PathFinder._cg")
@patch("vuli.pathfinder.PathFinder._sta")
async def test_findpath_all(patch_1, patch_2, patch_3) -> None:
    patch_1.return_value = []
    await SinkManager().add((0, SinkProperty(bug_types=set(), origins=set())))
    await SinkManager().add((1, SinkProperty(bug_types=set(), origins=set())))
    await SinkManager().add((2, SinkProperty(bug_types=set(), origins=set())))
    CP().harnesses = {"h1": {}}

    async def controller(patch) -> None:
        sinks: list[int] = [0, 1, 2]
        for i in range(0, len(sinks)):
            while True:
                try:
                    sinks: dict[int, SinkProperty] = await SinkManager().get()
                    if sinks[sinks[i]].status == SinkStatus.MAY_REACHABLE:
                        if i < 2:
                            patch.return_value = [
                                VulInfo(
                                    harness_id="harness",
                                    sink_id=sinks[i + 1],
                                    v_paths=[],
                                    v_point=None,
                                )
                            ]
                            CallTree()._updated_time = time.time()
                        break
                except Exception:
                    pass
                await asyncio.sleep(1)

    patch_2.return_value = [
        VulInfo(harness_id="harness", sink_id=0, v_paths=[], v_point=None)
    ]
    tasks = [controller(patch_2), FindPathService(1).run()]
    try:
        await asyncio.wait_for(asyncio.gather(*tasks), timeout=5)
    except asyncio.TimeoutError:
        pass

    sinks: dict[int, SinkProperty] = await SinkManager().get()
    sinks[0].status == SinkStatus.MAY_REACHABLE
    sinks[1].status == SinkStatus.MAY_REACHABLE
    sinks[2].status == SinkStatus.MAY_REACHABLE


class MockBlobGeneration(PathBasedGeneration):

    async def run(self, path: VulInfo) -> path_manager.Status:
        return path_manager.Status.EXPLOITABLE


async def condition(*paths) -> None:
    while True:
        if {await path_manager.PathManager().get_status(path) for path in paths} == set(
            {path_manager.Status.EXPLOITABLE}
        ):
            break
        await asyncio.sleep(0.5)


@pytest.mark.asyncio
async def test_blob_generation():
    Setting().dev = False
    path: VulInfo = VulInfo("harness_1", 1, [], CodeLocation("path_1", 1, 1))
    await path_manager.PathManager().add(path)
    generator: BlobGeneration = BlobGeneration(MockBlobGeneration())
    task: asyncio.Task = asyncio.create_task(generator.run())
    await asyncio.wait_for(condition(path), timeout=2)
    try:
        task.cancel()
        await asyncio.wait_for(task, timeout=2)
    except asyncio.exceptions.CancelledError:
        pass


@pytest.mark.asyncio
async def test_blob_generation_multiple():
    Setting().dev = False
    path_1: VulInfo = VulInfo("harness_1", 1, [], CodeLocation("path_1", 1, 1))
    path_2: VulInfo = VulInfo("harness_1", 2, [], CodeLocation("path_1", 2, 2))
    await path_manager.PathManager().add(path_1)
    await path_manager.PathManager().add(path_2)
    generator: BlobGeneration = BlobGeneration(MockBlobGeneration())
    task: asyncio.Task = asyncio.create_task(generator.run())
    await asyncio.wait_for(condition(path_1, path_2), timeout=2)
    try:
        task.cancel()
        await asyncio.wait_for(task, timeout=2)
    except asyncio.exceptions.CancelledError:
        pass


@pytest.mark.asyncio
async def test_blob_generation_multiple_in_parallel():
    Setting().dev = False
    path_1: VulInfo = VulInfo("harness_1", 1, [], CodeLocation("path_1", 1, 1))
    path_2: VulInfo = VulInfo("harness_1", 2, [], CodeLocation("path_1", 2, 2))
    await path_manager.PathManager().add(path_1)
    await path_manager.PathManager().add(path_2)
    generator: BlobGeneration = BlobGeneration(MockBlobGeneration(), 2)
    task: asyncio.Task = asyncio.create_task(generator.run())
    await asyncio.wait_for(condition(path_1, path_2), timeout=2)
    try:
        task.cancel()
        await asyncio.wait_for(task, timeout=2)
    except asyncio.exceptions.CancelledError:
        pass


@pytest.mark.asyncio
async def test_blob_generation_over_in_parallel():
    Setting().dev = False
    path_1: VulInfo = VulInfo("harness_1", 1, [], CodeLocation("path_1", 1, 1))
    path_2: VulInfo = VulInfo("harness_1", 2, [], CodeLocation("path_1", 2, 2))
    path_3: VulInfo = VulInfo("harness_1", 3, [], CodeLocation("path_1", 3, 2))
    path_4: VulInfo = VulInfo("harness_1", 4, [], CodeLocation("path_1", 4, 2))
    path_5: VulInfo = VulInfo("harness_1", 5, [], CodeLocation("path_1", 5, 2))
    await path_manager.PathManager().add(path_1)
    await path_manager.PathManager().add(path_2)
    await path_manager.PathManager().add(path_3)
    await path_manager.PathManager().add(path_4)
    await path_manager.PathManager().add(path_5)
    generator: BlobGeneration = BlobGeneration(MockBlobGeneration(), 2)
    task: asyncio.Task = asyncio.create_task(generator.run())

    async def condition(*paths) -> None:
        while True:
            if {
                await path_manager.PathManager().get_status(path) for path in paths
            } == set({path_manager.Status.EXPLOITABLE}):
                break
            await asyncio.sleep(0.5)

    await asyncio.wait_for(condition(path_1, path_2, path_3, path_4, path_5), timeout=5)
    try:
        task.cancel()
        await asyncio.wait_for(task, timeout=2)
    except asyncio.exceptions.CancelledError:
        pass


@pytest.mark.asyncio
@patch("vuli.calltree.UpdateCallTree.update", new_callable=AsyncMock)
async def test_synccallgraph__update(patch_1):
    task = SyncCallGraph()

    t = tempfile.NamedTemporaryFile()
    with Path(t.name).open("w") as f:
        f.write("a")
        f.flush()
    await task._update(Path(t.name))
    patch_1.assert_called_once()


@pytest.mark.asyncio
async def test_synccallgraph__update_no_exist():
    t = tempfile.NamedTemporaryFile()
    os.unlink(t.name)
    assert await SyncCallGraph()._update(Path(t.name)) is False


@pytest.mark.asyncio
@patch("vuli.calltree.UpdateCallTree.update")
async def test_synccallgraph__update_no_when_mtime_is_same(patch_1):
    task = SyncCallGraph()

    t = tempfile.NamedTemporaryFile()
    with Path(t.name).open("w") as f:
        f.write("a")
        f.flush()
    await task._update(Path(t.name))
    await task._update(Path(t.name))
    patch_1.assert_called_once()


@pytest.mark.asyncio
@patch("vuli.calltree.UpdateCallTree.update")
async def test_synccallgraph__update_when_mtime_is_changed(patch_1):
    task = SyncCallGraph()

    t = tempfile.NamedTemporaryFile()
    with Path(t.name).open("w") as f:
        f.write("a")
        f.flush()
    await task._update(Path(t.name))

    time.sleep(0.5)

    with Path(t.name).open("w") as f:
        f.write("a")
        f.flush()
    await task._update(Path(t.name))
    assert patch_1._mock_call_count == 2


@pytest.mark.asyncio
@patch.object(Blackboard, "update_cg")
@patch("vuli.task.SyncCallGraph._update")
async def test_synccallgraph__run(patch_1, patch_2):
    CP()._cg_paths = [Path("a"), Path("b")]
    task = SyncCallGraph()
    await task._run()
    assert patch_1._mock_call_count == 2


@pytest.mark.asyncio
async def test_taskmanager_run():
    class Handler1(TaskHandler):
        def __init__(self):
            self._counter: int = 0

        async def run(self) -> None:
            self._counter += 1
            return

    class Handler2(TaskHandler):
        def __init__(self):
            self._counter: int = 0

        async def run(self) -> None:
            self._counter += 1
            return

    handler1 = Handler1()
    handler2 = Handler2()
    TaskManager().add_handlers(handler1, handler2)
    await TaskManager().run()
    assert handler1._counter == 1
    assert handler2._counter == 1


@pytest.mark.asyncio
async def test_taskmanager_run_exception_safe():
    class Handler(TaskHandler):
        async def run(self):
            raise RuntimeError

    TaskManager().add_handlers(Handler())
    await TaskManager().run()


def test_taskmanager_add_handler():
    class Handler1(TaskHandler):
        async def run(self) -> None:
            return

    class Handler2(TaskHandler):
        async def run(self) -> None:
            return

    handler1 = Handler1()
    handler2 = Handler2()
    TaskManager().add_handlers(handler1, handler2)
    assert handler1 in TaskManager()._handlers
    assert handler2 in TaskManager()._handlers


def test_taskmanager_add_handler_no_taskhandler():
    class Handler1:
        async def run(self) -> None:
            return

    handler1 = Handler1()
    TaskManager().add_handlers(handler1)
    assert len(TaskManager()._handlers) == 0


@pytest.mark.asyncio
async def test_servicehandler_run():
    class Handler(ServiceHandler):
        def __init__(self):
            super().__init__(1)
            self._counter: int = 0

        async def _run(self) -> None:
            self._counter += 1

    handler = Handler()
    try:
        await asyncio.wait_for(handler.run(), timeout=2)
    except asyncio.TimeoutError:
        pass
    assert handler._counter != 0


@pytest.mark.asyncio
async def test_servicehandler_run_exception_safe():
    class Handler(ServiceHandler):
        def __init__(self):
            super().__init__(1)
            self._counter: int = 0

        async def _run(self) -> None:
            if self._counter == 0:
                self._counter += 1
                raise RuntimeError

    handler = Handler()
    try:
        await asyncio.wait_for(handler.run(), timeout=2)
    except asyncio.TimeoutError:
        pass
    assert handler._counter != 0
