import asyncio
import time
from unittest.mock import patch

import asyncstdlib
import pytest

from tests.test_util import prepare_sample_cp
from vuli.blackboard import Blackboard
from vuli.calltree import CallTree
from vuli.common.setting import Setting
from vuli.cp import CP
from vuli.joern import CPG, Joern
from vuli.path_manager import PathManager
from vuli.pathfinder import FindPathService, PathFinder
from vuli.sink import SinkManager, SinkProperty, SinkStatus
from vuli.struct import CodeLocation, VulInfo


@pytest.fixture(autouse=True)
def setup():
    asyncio.run(PathManager().clear())
    asyncio.run(SinkManager().clear())


@pytest.mark.asyncio
@patch("vuli.pathfinder.PathFinder._cg")
@patch("vuli.pathfinder.PathFinder._sta")
async def test_run_sta_sink_multiple_src(patch_1, patch_2):
    def mock_1(*args, **kwargs) -> list[VulInfo]:
        if 1 not in args[1]:
            return []
        return [VulInfo(args[0], 1, [], None)]

    def mock_2(*args, **kwargs) -> list[VulInfo]:
        if 2 not in args[1]:
            return []
        return [VulInfo(args[0], 2, [], None)]

    patch_1.side_effect = mock_1
    patch_2.side_effect = mock_2

    sinks: set[int] = set({1, 2})
    finder: PathFinder = PathFinder()

    async def reducer(
        accumulator: list[VulInfo],
        harness: str,
    ):
        return accumulator + await finder.find(harness, sinks)

    paths: list[VulInfo] = await asyncstdlib.reduce(
        reducer, ["Harness1", "Harness2"], []
    )

    assert paths == [
        VulInfo("Harness1", 1, [], None),
        VulInfo("Harness1", 2, [], None),
        VulInfo("Harness2", 1, [], None),
        VulInfo("Harness2", 2, [], None),
    ]


@pytest.mark.asyncio
@patch("vuli.pathfinder.FindPathService._find_by_harness")
async def test_findpathservice_no_target(patch_1):
    patch_1.return_value = set()
    await SinkManager().add((0, SinkProperty(status=SinkStatus.UNEXPLOITABLE)))
    await SinkManager().add((1, SinkProperty(status=SinkStatus.MAY_REACHABLE)))
    await FindPathService()._run()
    assert patch_1._mock_call_count == 0


@pytest.mark.asyncio
@patch.object(Blackboard, "save")
@patch("vuli.pathfinder.PathFinder._sta")
async def test_findpathservice_only_by_sta(patch_1, patch_2):
    CP().harnesses = {"harness": {}}
    patch_1.return_value = [VulInfo("harness", 0, [], CodeLocation("", 0))]
    await SinkManager().add((0, SinkProperty(status=SinkStatus.UNKNOWN)))
    await FindPathService()._run()
    assert (await SinkManager().get())[0].status == SinkStatus.MAY_REACHABLE


@pytest.mark.asyncio
@patch.object(Blackboard, "save")
@patch("vuli.pathfinder.PathFinder._cg")
async def test_findpathservice_only_by_cg(patch_1, patch_2):
    CP().harnesses = {"harness": {}}
    patch_1.return_value = [VulInfo("harness", 0, [], CodeLocation("", 0))]
    await SinkManager().add((0, SinkProperty(status=SinkStatus.MAY_UNREACHABLE)))
    CallTree()._updated_time = time.time()
    await FindPathService()._run()
    assert (await SinkManager().get())[0].status == SinkStatus.MAY_REACHABLE


@pytest.mark.asyncio
@patch("vuli.pathfinder.PathFinder._cg")
@patch("vuli.pathfinder.PathFinder._sta")
async def test_findpathservice__find_by_harness(patch_1, patch_2):
    def mock(*args, **kwargs):
        return [VulInfo(args[0], list(args[1])[1], [], None)]

    patch_1.side_effect = mock
    patch_2.side_effect = mock
    covered_sinks: set[int] = await FindPathService()._find_by_harness(
        "harness", {0, 1}, {2, 3}
    )
    assert covered_sinks == set({1, 2})
    assert VulInfo("harness", 1, [], None) in PathManager()._queue
    assert VulInfo("harness", 2, [], None) in PathManager()._queue


@pytest.mark.asyncio
async def test_findpathservice_e2e():
    await prepare_sample_cp()
    cpg = CPG(Setting().cpg_path)
    await cpg.build(
        Setting().joern_javasrc_path, CP().source_dir, [], CP().get_dependent_jars()
    )
    try:
        Joern().set_path(Setting().joern_cli_path)
        await Joern().run_server(cpg, Setting().query_path, Setting().semantic_dir)
        await CallTree().set_path(Setting().calltree_db_path)
        await CallTree().build(list(CP().harnesses.keys()))

        sink_1: int = await Joern().run_query(
            """
cpg.method.nameExact("bug").call
    .where(_.lineNumber(6))
    .where(_.methodFullNameExact("java.lang.ProcessBuilder.start:java.lang.Process()"))
    .id.head"""
        )
        await SinkManager().add((sink_1, SinkProperty()))
        assert await SinkManager().get_status(sink_1) == SinkStatus.UNKNOWN

        service = FindPathService()
        await service._run()
        assert await SinkManager().get_status(sink_1) == SinkStatus.MAY_REACHABLE

        sink_2: int = await Joern().run_query(
            """
cpg.method.nameExact("_run").call
    .where(_.lineNumber(12))
    .where(_.methodFullNameExact("java.lang.ProcessBuilder.start:java.lang.Process()"))
    .id.head"""
        )
        await SinkManager().add((sink_2, SinkProperty()))
        await service._run()
        assert await SinkManager().get_status(sink_2) == SinkStatus.MAY_UNREACHABLE

        methods: list[int] = await Joern().run_query(
            """
List("sample.one.SampleOne.fuzz", "sample.BugTwo.run")
    .map(x => cpg.method.fullName("^" + x + ".*").id.head)"""
        )
        await CallTree().insert(methods[0], set({methods[1]}))
        await service._run()
        assert await SinkManager().get_status(sink_2) == SinkStatus.MAY_REACHABLE
    finally:
        await Joern().close_server()
