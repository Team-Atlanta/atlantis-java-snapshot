import asyncio
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import aiofiles
import aiofiles.os
import pytest

from tests.test_util import prepare_sample_cp
from vuli.blackboard import Blackboard
from vuli.common.setting import Setting
from vuli.cp import CP
from vuli.joern import CPG, Joern
from vuli.sink import Origin, SinkManager, SinkProperty
from vuli.sinkupdateservice import JavaCRS, SinkUpdateService


@pytest.fixture(autouse=True)
def setup():
    asyncio.run(Blackboard().clear())
    asyncio.run(SinkManager().clear())


@pytest.mark.asyncio
@patch.object(Blackboard, "save")
@patch("vuli.sinkupdateservice.JavaCRS._get_from_joern")
async def test_sinkupdateservice_javacrs__update(patch_1, patch_2):
    patch_1.return_value = [
        {"name": "cls", "num": 1, "id": 0},
        {"name": "cls", "num": 2, "id": 1},
    ]
    t = await aiofiles.tempfile.NamedTemporaryFile()
    p = Path(t.name)
    src: dict = [
        {
            "coord": {"class_name": "cls", "line_num": 1},
            "type": ["sink-RegexInjection"],
            "in_diff": False,
            "sarif_reports": [],
        },
        {
            "coord": {"line": 3},
        },
        {
            "coord": {"class_name": "cls", "line_num": 2},
            "type": ["sink-deserialization"],
            "in_diff": True,
            "sarif_reports": [{"solved": True}, {"solved": False}],
        },
        {
            "coord": {"class_name": "cls", "line_num": 3},
            "type": ["sink-timeout"],
            "in_diff": False,
            "sarif_reports": [],
        },
    ]
    async with aiofiles.open(p, mode="w") as f:
        await f.write(json.dumps(src))
        await f.flush()

    task = JavaCRS(p)
    await task.run()
    sinks = await SinkManager().get()
    assert sinks[0] == SinkProperty(
        bug_types=set({"sink-RegexInjection"}), origins=set({Origin.FROM_CRS})
    )
    assert sinks[1] == SinkProperty(
        bug_types=set({"sink-deserialization"}),
        origins=set({Origin.FROM_CRS, Origin.FROM_DELTA, Origin.FROM_SARIF}),
    )


@pytest.mark.asyncio
@patch.object(Blackboard, "save")
@patch("vuli.sinkupdateservice.JavaCRS._get_from_joern")
async def test_sinkupdateservice_javacrs_run(patch_1, patch_2):
    async def writer(path: Path):
        await aiofiles.os.unlink(path)
        async with aiofiles.open(path, "w") as f:
            await f.write(
                json.dumps(
                    [
                        {
                            "coord": {"class_name": "cls", "line_num": 1},
                            "type": ["sink-RegexInjection"],
                            "in_diff": False,
                            "sarif_reports": [],
                        },
                    ]
                )
            )
            await f.flush()
            os.fsync(f.fileno())
        patch_1.return_value = [{"name": "cls", "num": 1, "id": 0}]
        while 0 not in await SinkManager().get():
            await asyncio.sleep(1)
            pass

        await aiofiles.os.unlink(path)
        async with aiofiles.open(path, "w") as f:
            await f.write(
                json.dumps(
                    [
                        {
                            "coord": {"class_name": "cls", "line_num": 2},
                            "type": ["sink-RegexInjection"],
                            "in_diff": False,
                            "sarif_reports": [],
                        },
                    ]
                )
            )
            await f.flush()
            os.fsync(f.fileno())
        patch_1.return_value = [{"name": "cls", "num": 2, "id": 1}]

    t = tempfile.NamedTemporaryFile()
    p = Path(t.name)
    service = SinkUpdateService(1)
    service.add_task(JavaCRS(p))
    tasks = [asyncio.create_task(service.run()), asyncio.create_task(writer(p))]
    try:
        await asyncio.wait_for(asyncio.gather(*tasks), timeout=5)
    except asyncio.TimeoutError:
        pass
    sinks = await SinkManager().get()
    assert sinks[0] == SinkProperty(
        bug_types=set({"sink-RegexInjection"}), origins=set({Origin.FROM_CRS})
    )
    assert sinks[1] == SinkProperty(
        bug_types=set({"sink-RegexInjection"}), origins=set({Origin.FROM_CRS})
    )
    assert patch_2._mock_call_count == 2


@pytest.mark.asyncio
async def test_sinkupdateservice_javacrs_path_not_exist():
    await JavaCRS(None).run()


@pytest.mark.asyncio
@patch("vuli.sinkupdateservice.JavaCRS._parse")
async def test_sinkupdateservice_javacrs_same_mtime(patch_1):
    patch_1.return_value = []
    t = tempfile.NamedTemporaryFile()
    handler = JavaCRS(Path(t.name))
    await handler.run()
    await handler.run()
    patch_1.assert_called_once()


@pytest.mark.asyncio
async def test_sinkupdateservice_javacrs_invalid_file():
    t = tempfile.NamedTemporaryFile()
    await JavaCRS(Path(t.name)).run()


@pytest.mark.asyncio
@patch.object(Blackboard, "save")
async def test_sinkupdateservice_javacrs_e2e(patch_1):
    await prepare_sample_cp()
    t = tempfile.NamedTemporaryFile()
    p = Path(t.name)
    with p.open("w") as f:
        json.dump(
            [
                {
                    "coord": {"class_name": "sample.BugOne", "line_num": 6},
                    "type": ["sink-OsCommandInjection"],
                    "in_diff": False,
                    "sarif_reports": [],
                },
            ],
            f,
        )
    cpg = CPG(Setting().cpg_path)
    await cpg.build(
        Setting().joern_javasrc_path, CP().source_dir, [], CP().get_dependent_jars()
    )
    try:
        Joern().set_path(Setting().joern_cli_path)
        await Joern().run_server(cpg, Setting().query_path, Setting().semantic_dir)
        await JavaCRS(p).run()
    finally:
        await Joern().close_server()

    sinks = await SinkManager().get()
    id: int = list(sinks.keys())[0]
    assert sinks[id] == SinkProperty(
        bug_types=set({"sink-OsCommandInjection"}), origins=set({Origin.FROM_CRS})
    )
