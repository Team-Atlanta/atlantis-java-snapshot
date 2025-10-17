import asyncio

import pytest

from vuli.path_manager import PathManager
from vuli.sink import Origin, SinkManager, SinkProperty, SinkStatus
from vuli.struct import CodeLocation, VulInfo


@pytest.fixture(autouse=True)
def setup():
    asyncio.run(SinkManager().clear())
    asyncio.run(PathManager().clear())


@pytest.mark.asyncio
async def test_add_ignore():
    path_1 = VulInfo("harness", 0, [], CodeLocation("path", 0))
    path_2 = VulInfo("harness", 0, [], CodeLocation("path", 0))
    await PathManager().add(path_1)
    assert len(PathManager()._table) == 1
    assert len(PathManager()._queue) == 1
    await PathManager().add(path_1)
    assert len(PathManager()._table) == 1
    assert len(PathManager()._queue) == 1
    await PathManager().add(path_2)
    assert len(PathManager()._table) == 1
    assert len(PathManager()._queue) == 1
    await PathManager().get()
    assert len(PathManager()._table) == 1
    assert len(PathManager()._queue) == 0
    await PathManager().add(path_1)
    assert len(PathManager()._table) == 1
    assert len(PathManager()._queue) == 0


@pytest.mark.asyncio
async def test_empty_get():
    assert await PathManager().get() is None


@pytest.mark.asyncio
async def test_get():
    path = VulInfo("harness", 0, [], CodeLocation("path", 0))
    await PathManager().add(path)
    (await PathManager().get()) == path
    (await PathManager().get()) is None


@pytest.mark.asyncio
async def test_get_multiple():
    path_1 = VulInfo("harness", 0, [], CodeLocation("path_1", 0))
    path_2 = VulInfo("harness", 0, [], CodeLocation("path_2", 0))
    await PathManager().add(path_1)
    await PathManager().add(path_2)
    assert (await PathManager().get()) == path_1
    assert (await PathManager().get()) == path_2
    assert (await PathManager().get()) is None


@pytest.mark.asyncio
async def test_get_priority():
    path_1 = VulInfo("harness", 0, [], CodeLocation("path_1", 0))
    path_2 = VulInfo("harness", 1, [], CodeLocation("path_2", 0))
    await PathManager().add(path_1)
    await PathManager().add(path_2)
    await SinkManager().add(
        (
            0,
            SinkProperty(
                bug_types=set(), origins={Origin.FROM_INSIDE}, status=SinkStatus.UNKNOWN
            ),
        )
    )
    await SinkManager().add(
        (
            1,
            SinkProperty(
                bug_types=set(), origins={Origin.FROM_SARIF}, status=SinkStatus.UNKNOWN
            ),
        )
    )
    assert (await PathManager().get()) == path_2
    assert (await PathManager().get()) == path_1
    assert (await PathManager().get()) is None


@pytest.mark.asyncio
async def test_get_harness_balance():
    path_1 = VulInfo("harness_1", 0, [], CodeLocation("path_1", 0))
    path_2 = VulInfo("harness_1", 1, [], CodeLocation("path_2", 0))
    path_3 = VulInfo("harness_2", 2, [], CodeLocation("path_3", 0))
    await PathManager().add(path_1)
    await PathManager().add(path_2)
    await PathManager().add(path_3)
    assert (await PathManager().get()) == path_1
    assert (await PathManager().get()) == path_3
    assert (await PathManager().get()) == path_2
    assert (await PathManager().get()) is None


@pytest.mark.asyncio
async def test_get_harness_balance_and_priority():
    path_1 = VulInfo("harness_1", 0, [], CodeLocation("path_1", 0))
    path_2 = VulInfo("harness_1", 1, [], CodeLocation("path_2", 0))
    path_3 = VulInfo("harness_2", 2, [], CodeLocation("path_3", 0))
    await PathManager().add(path_1)
    await PathManager().add(path_2)
    await PathManager().add(path_3)
    await SinkManager().add(
        (
            0,
            SinkProperty(
                bug_types=set(), origins={Origin.FROM_SARIF}, status=SinkStatus.UNKNOWN
            ),
        )
    )
    await SinkManager().add(
        (
            1,
            SinkProperty(
                bug_types=set(), origins={Origin.FROM_SARIF}, status=SinkStatus.UNKNOWN
            ),
        )
    )
    await SinkManager().add(
        (
            2,
            SinkProperty(
                bug_types=set(), origins={Origin.FROM_INSIDE}, status=SinkStatus.UNKNOWN
            ),
        )
    )
    assert (await PathManager().get()) == path_1
    assert (await PathManager().get()) == path_2
    assert (await PathManager().get()) == path_3
    assert (await PathManager().get()) is None
