import asyncio
import base64
import datetime
import hashlib
import json
import tempfile
import time
from pathlib import Path
from unittest.mock import AsyncMock, patch

import aiofiles
import pytest

from tests.test_util import prepare_sample_cp
from vuli.blackboard import Blackboard, BlackboardDataStatus, BlackboardSink
from vuli.common.setting import Setting
from vuli.cp import CP
from vuli.joern import Joern
from vuli.path_manager import PathManager
from vuli.runner import Runner
from vuli.scanner import Scanner
from vuli.sink import Origin, SinkManager, SinkProperty, SinkStatus
from vuli.struct import CodePoint


@pytest.fixture(autouse=True)
def setup():
    asyncio.run(Blackboard().clear())
    asyncio.run(SinkManager().clear())
    asyncio.run(PathManager().clear())


@pytest.mark.asyncio
async def test_path():
    t = tempfile.NamedTemporaryFile()
    await Blackboard().set_path(Path(t.name))
    await Blackboard().add_path(
        "id_1",
        [CodePoint("path", "method", 0, 0)],
        ["cmdi"],
        BlackboardDataStatus.EXPLOITED,
    )
    await Blackboard().save()
    async with aiofiles.open(t.name) as f:
        root = json.loads(await f.read())
        assert root.get("paths", {}) == [
            {
                "harness_id": "id_1",
                "route": [{"path": "path", "line": 0, "column": 0}],
                "bug_types": ["cmdi"],
                "status": "EXPLOITED",
            }
        ]


@pytest.mark.asyncio
async def test_path_multiple():
    t = tempfile.NamedTemporaryFile()
    await Blackboard().set_path(Path(t.name))
    await Blackboard().add_path(
        "id_1",
        [CodePoint("path_1", "method_1", 0, 5)],
        ["cmdi"],
        BlackboardDataStatus.EXPLOITED,
    )
    await Blackboard().add_path(
        "id_2",
        [
            CodePoint("path_2", "method_2", 10, 15),
            CodePoint("path_3", "method_3", 20, 25),
        ],
        ["ssrf"],
        BlackboardDataStatus.NOT_REACHED,
    )
    await Blackboard().save()
    async with aiofiles.open(t.name) as f:
        root = json.loads(await f.read())
        assert root.get("paths", {}) == [
            {
                "harness_id": "id_1",
                "route": [{"path": "path_1", "line": 0, "column": 5}],
                "bug_types": ["cmdi"],
                "status": "EXPLOITED",
            },
            {
                "harness_id": "id_2",
                "route": [
                    {"path": "path_2", "line": 10, "column": 15},
                    {"path": "path_3", "line": 20, "column": 25},
                ],
                "bug_types": ["ssrf"],
                "status": "NOT_REACHED",
            },
        ]


@pytest.mark.asyncio
@patch.object(Joern, "run_query", new_callable=AsyncMock)
async def test_sink(patch_1):
    def mock_1(*args, **kwargs) -> dict:
        return {0: {"class_name": "cls1", "file_path": "path1.java", "line_num": 1}}

    patch_1.side_effect = mock_1

    t = tempfile.NamedTemporaryFile()
    await SinkManager().add(
        (0, SinkProperty(bug_types=set({"OS Command Injection"}), origins=set()))
    )
    await Blackboard().set_path(Path(t.name))
    await Blackboard().save()
    async with aiofiles.open(t.name) as f:
        assert json.loads(await f.read()).get("sinks", {}) == [
            {
                "class_name": "cls1",
                "file_path": "path1.java",
                "line_num": 1,
                "type": ["sink-OsCommandInjection"],
                "in_diff": False,
                "status": "UNKNOWN",
                "ana_reachability": {},
                "ana_exploitability": {},
            }
        ]


@pytest.mark.asyncio
@patch.object(Joern, "run_query", new_callable=AsyncMock)
async def test_sink_multiple(patch_1):
    def mock(*args, **kwargs) -> dict:
        return {
            0: {"class_name": "cls1", "file_path": "path1.java", "line_num": 1},
            1: {"class_name": "cls2", "file_path": "path2.java", "line_num": 2},
        }

    patch_1.side_effect = mock

    t = tempfile.NamedTemporaryFile()
    await Blackboard().set_path(Path(t.name))
    await SinkManager().add_batch(
        {
            0: SinkProperty(bug_types=set(), origins=set()),
            1: SinkProperty(bug_types=set(), origins=set({Origin.FROM_DELTA})),
        }
    )
    await Blackboard().save()
    async with aiofiles.open(t.name) as f:
        assert json.loads(await f.read()).get("sinks", {}) == [
            {
                "class_name": "cls1",
                "file_path": "path1.java",
                "line_num": 1,
                "type": [],
                "in_diff": False,
                "status": "UNKNOWN",
                "ana_reachability": {},
                "ana_exploitability": {},
            },
            {
                "class_name": "cls2",
                "file_path": "path2.java",
                "line_num": 2,
                "type": [],
                "in_diff": True,
                "status": "UNKNOWN",
                "ana_reachability": {},
                "ana_exploitability": {},
            },
        ]


@pytest.mark.asyncio
async def test_seed():
    t = tempfile.NamedTemporaryFile()
    await Blackboard().set_path(Path(t.name))
    await Blackboard().add_seed("harness", b"blob")
    async with aiofiles.open(t.name) as f:
        result: list[dict] = json.loads(await f.read()).get("result", [])
        assert result == [
            {
                "harness_id": "harness",
                "blob": [base64.b64encode(b"blob").decode("utf-8")],
            }
        ]


@pytest.mark.asyncio
async def test_seed_multiple():
    t = tempfile.NamedTemporaryFile()
    await Blackboard().set_path(Path(t.name))
    await Blackboard().add_seed("harness_1", b"blob1")
    await Blackboard().add_seed("harness_1", b"blob2")
    await Blackboard().add_seed("harness_2", b"blob3")
    async with aiofiles.open(t.name) as f:
        result: list[dict] = json.loads(await f.read()).get("result", [])
        assert result == [
            {
                "harness_id": "harness_1",
                "blob": [
                    base64.b64encode(b"blob1").decode("utf-8"),
                    base64.b64encode(b"blob2").decode("utf-8"),
                ],
            },
            {
                "harness_id": "harness_2",
                "blob": [base64.b64encode(b"blob3").decode("utf-8")],
            },
        ]


@pytest.mark.asyncio
@patch.object(Joern, "run_query", new_callable=AsyncMock)
async def test_all(patch_1):
    async def mock(*args, **kwargs) -> dict:
        return {
            0: {"class_name": "cls1", "file_path": "path1.java", "line_num": 1},
            1: {"class_name": "cls2", "file_path": "path2.java", "line_num": 2},
            2: {"class_name": "cls3", "file_path": "path3.java", "line_num": 3},
        }

    patch_1.side_effect = mock
    t = tempfile.NamedTemporaryFile()
    await Blackboard().set_path(Path(t.name))
    await Blackboard().add_diff_harnesses(set({"Harness1", "Harness2"}))
    await SinkManager().add_batch(
        {
            0: SinkProperty(bug_types=set(), origins=set()),
            1: SinkProperty(bug_types=set(), origins=set({Origin.FROM_DELTA})),
            2: SinkProperty(bug_types=set(), origins=set()),
        }
    )
    await Blackboard().add_path(
        "harness_1",
        [CodePoint("path_1", "method_1", 0, 1)],
        ["cmdi"],
        BlackboardDataStatus.EXPLOITED,
    )
    await Blackboard().add_path(
        "harness_2",
        [CodePoint("path_2", "method_2", 2, 3)],
        ["ssrf"],
        BlackboardDataStatus.NOT_REACHED,
    )
    await Blackboard().add_path(
        "harness_3",
        [CodePoint("path_3", "method_3", 4, 5)],
        ["pt"],
        BlackboardDataStatus.REACHED,
    )
    await Blackboard().add_seed("harness_1", b"blob1")
    await Blackboard().add_seed("harness_1", b"blob2")
    await Blackboard().add_seed("harness_2", b"blob3")
    await Blackboard().add_seed("harness_3", b"blob4")
    await Blackboard().save()
    async with aiofiles.open(t.name) as f:
        blackboard: dict = json.loads(await f.read())
        diff_harnesses: set[str] = set(blackboard["diff"]["harnesses"])
        assert diff_harnesses == set({"Harness1", "Harness2"})
        del blackboard["diff"]
        assert blackboard == {
            "sinks": [
                {
                    "class_name": "cls1",
                    "file_path": "path1.java",
                    "line_num": 1,
                    "type": [],
                    "in_diff": False,
                    "status": "UNKNOWN",
                    "ana_reachability": {},
                    "ana_exploitability": {},
                },
                {
                    "class_name": "cls2",
                    "file_path": "path2.java",
                    "line_num": 2,
                    "type": [],
                    "in_diff": True,
                    "status": "UNKNOWN",
                    "ana_reachability": {},
                    "ana_exploitability": {},
                },
                {
                    "class_name": "cls3",
                    "file_path": "path3.java",
                    "line_num": 3,
                    "type": [],
                    "in_diff": False,
                    "status": "UNKNOWN",
                    "ana_reachability": {},
                    "ana_exploitability": {},
                },
            ],
            "paths": [
                {
                    "harness_id": "harness_1",
                    "route": [{"path": "path_1", "line": 0, "column": 1}],
                    "bug_types": ["cmdi"],
                    "status": "EXPLOITED",
                },
                {
                    "harness_id": "harness_2",
                    "route": [{"path": "path_2", "line": 2, "column": 3}],
                    "bug_types": ["ssrf"],
                    "status": "NOT_REACHED",
                },
                {
                    "harness_id": "harness_3",
                    "route": [{"path": "path_3", "line": 4, "column": 5}],
                    "bug_types": ["pt"],
                    "status": "REACHED",
                },
            ],
            "merged_joern_cg": "",
            "merged_sarif_cg": "",
            "merged_soot_cg": "",
            "result": [
                {
                    "harness_id": "harness_1",
                    "blob": [
                        base64.b64encode(b"blob1").decode("utf-8"),
                        base64.b64encode(b"blob2").decode("utf-8"),
                    ],
                },
                {
                    "harness_id": "harness_2",
                    "blob": [base64.b64encode(b"blob3").decode("utf-8")],
                },
                {
                    "harness_id": "harness_3",
                    "blob": [base64.b64encode(b"blob4").decode("utf-8")],
                },
            ],
        }


class MockRunner(Runner):
    async def _run(self) -> None:
        pass

    async def run(self) -> None:
        try:
            start_time: time.time = time.time()
            if await self._initialize_joern() is False:
                raise RuntimeError
            await Scanner().run([CP().get_sanitizer("sink-LoadArbitraryLibrary")])
            await self._save_output(start_time)
        finally:
            await Joern().close_server()


@pytest.mark.asyncio
async def test_save_output():
    await prepare_sample_cp()
    runner: Runner = MockRunner()
    await asyncio.wait_for(runner.run(), timeout=30)
    async with aiofiles.open(Setting().blackboard_path) as f:
        root = json.loads(await f.read())
    assert "sinks" in root

    assert (
        len(
            [
                x
                for x in root["sinks"]
                if x["file_path"] == "sample/src/main/java/sample/BugOne.java"
                and x["line_num"] == 20
            ]
        )
        == 1
    )
    assert (
        len(
            [
                x
                for x in root["sinks"]
                if x["file_path"] == "sample/src/main/java/sample/BugOne.java"
                and x["line_num"] == 26
            ]
        )
        == 1
    )


@pytest.mark.asyncio
@patch("vuli.blackboard.Blackboard._update_sinks_location", new_callable=AsyncMock)
async def test_blackboard_sinks_to_dump(patch_1):
    patch_1.return_value = None
    assert len(await Blackboard()._sinks_to_dump()) == 0
    await SinkManager().add_batch(
        {
            0: SinkProperty(
                bug_types=set({"OS Command Injection"}),
                harnesses=set({"Harness1"}),
                origins=set({Origin.FROM_INSIDE}),
                status=SinkStatus.MAY_REACHABLE,
            ),
            1: SinkProperty(
                bug_types=set({"Deserialization"}),
                harnesses=set({"Harness2"}),
                origins=set({Origin.FROM_SARIF}),
                status=SinkStatus.MAY_REACHABLE,
            ),
            2: SinkProperty(
                bug_types=set({"Reflective Call"}),
                origins=set({Origin.FROM_SARIF}),
                status=SinkStatus.UNEXPLOITABLE,
            ),
            3: SinkProperty(
                bug_types=set({"Express Language Injection"}),
                harnesses=set({"Harness3"}),
                origins=set({Origin.FROM_DELTA}),
                status=SinkStatus.MAY_REACHABLE,
            ),
            4: SinkProperty(
                bug_types=set({"Regular Expression Injection"}),
                origins=set({Origin.FROM_SARIF}),
                status=SinkStatus.UNEXPLOITABLE,
            ),
        }
    )
    Blackboard()._sinks = {
        0: {"class_name": "Cls1", "file_path": "path1.java", "line_num": 1},
        1: {"class_name": "Cls1", "file_path": "path1.java", "line_num": 2},
        2: {"class_name": "Cls1", "file_path": "path1.java", "line_num": 3},
        3: {"class_name": "Cls1", "file_path": "path1.java", "line_num": 1},
        4: {"class_name": "Cls1", "file_path": "path1.java", "line_num": 1},
    }

    assert await Blackboard()._sinks_to_dump() == [
        BlackboardSink(
            class_name="Cls1",
            file_path="path1.java",
            line_num=1,
            type=[
                "sink-ExpressionLanguageInjection",
                "sink-OsCommandInjection",
                "sink-RegexInjection",
            ],
            in_diff=True,
            status="MAY_REACHABLE",
            ana_reachability=["Harness1", "Harness3"],
            ana_exploitability=True,
        ),
        BlackboardSink(
            class_name="Cls1",
            file_path="path1.java",
            line_num=2,
            type=["sink-UnsafeDeserialization"],
            in_diff=False,
            status="MAY_REACHABLE",
            ana_reachability=["Harness2"],
            ana_exploitability=True,
        ),
        BlackboardSink(
            class_name="Cls1",
            file_path="path1.java",
            line_num=3,
            type=["sink-UnsafeReflectiveCall"],
            in_diff=False,
            status="UNEXPLOITABLE",
            ana_reachability=[],
            ana_exploitability=False,
        ),
    ]


@pytest.mark.asyncio
@patch.object(CP, "get_harnesses")
@patch("vuli.blackboard.Blackboard._update_sinks_location", new_callable=AsyncMock)
async def test_save(patch_1, patch_2):
    patch_1.return_value = None
    patch_2.return_value = ["Harness1", "Harness2", "Harness3"]
    assert len(await Blackboard()._sinks_to_dump()) == 0
    await SinkManager().add_batch(
        {
            0: SinkProperty(
                bug_types=set({"OS Command Injection"}),
                harnesses=set({"Harness1"}),
                origins=set({Origin.FROM_INSIDE}),
                status=SinkStatus.MAY_REACHABLE,
            ),
            1: SinkProperty(
                bug_types=set({"Deserialization"}),
                harnesses=set({"Harness2"}),
                origins=set({Origin.FROM_SARIF}),
                status=SinkStatus.MAY_REACHABLE,
            ),
            2: SinkProperty(
                bug_types=set({"Reflective Call"}),
                origins=set({Origin.FROM_SARIF}),
                status=SinkStatus.UNEXPLOITABLE,
            ),
            3: SinkProperty(
                bug_types=set({"Express Language Injection"}),
                harnesses=set({"Harness3"}),
                origins=set({Origin.FROM_DELTA}),
                status=SinkStatus.MAY_REACHABLE,
            ),
            4: SinkProperty(
                bug_types=set({"Regular Expression Injection"}),
                origins=set({Origin.FROM_SARIF}),
                status=SinkStatus.UNEXPLOITABLE,
            ),
        }
    )
    Blackboard()._sinks = {
        0: {"class_name": "Cls1", "file_path": "path1.java", "line_num": 1},
        1: {"class_name": "Cls1", "file_path": "path1.java", "line_num": 2},
        2: {"class_name": "Cls1", "file_path": "path1.java", "line_num": 3},
        3: {"class_name": "Cls1", "file_path": "path1.java", "line_num": 1},
        4: {"class_name": "Cls1", "file_path": "path1.java", "line_num": 1},
    }
    t = tempfile.NamedTemporaryFile()
    await Blackboard().set_path(Path(t.name))
    await Blackboard().save()
    async with aiofiles.open(t.name) as f:
        blackboard = json.loads(await f.read())
    assert blackboard == {
        "sinks": [
            {
                "class_name": "Cls1",
                "file_path": "path1.java",
                "line_num": 1,
                "type": [
                    "sink-ExpressionLanguageInjection",
                    "sink-OsCommandInjection",
                    "sink-RegexInjection",
                ],
                "in_diff": True,
                "status": "MAY_REACHABLE",
                "ana_reachability": {"Harness1": True, "Harness3": True},
                "ana_exploitability": {},
            },
            {
                "class_name": "Cls1",
                "file_path": "path1.java",
                "line_num": 2,
                "type": ["sink-UnsafeDeserialization"],
                "in_diff": False,
                "status": "MAY_REACHABLE",
                "ana_reachability": {"Harness2": True},
                "ana_exploitability": {},
            },
            {
                "class_name": "Cls1",
                "file_path": "path1.java",
                "line_num": 3,
                "type": ["sink-UnsafeReflectiveCall"],
                "in_diff": False,
                "status": "UNEXPLOITABLE",
                "ana_reachability": {},
                "ana_exploitability": {
                    "Harness1": False,
                    "Harness2": False,
                    "Harness3": False,
                },
            },
        ],
        "paths": [],
        "diff": {"harnesses": []},
        "merged_joern_cg": "",
        "merged_sarif_cg": "",
        "merged_soot_cg": "",
        "result": [],
    }


@pytest.mark.asyncio
async def test_diff_harnesses_exist_when_empty():
    t = tempfile.NamedTemporaryFile()
    await Blackboard().set_path(Path(t.name))
    await Blackboard().save()
    async with aiofiles.open(t.name) as f:
        assert json.loads(await f.read())["diff"]["harnesses"] == []


@pytest.mark.asyncio
async def test_diff_harnesses_save_immediately():
    t = tempfile.NamedTemporaryFile()
    await Blackboard().set_path(Path(t.name))
    await Blackboard().add_diff_harnesses(set({"Harness1"}))
    async with aiofiles.open(t.name) as f:
        assert json.loads(await f.read())["diff"]["harnesses"] == ["Harness1"]


@pytest.mark.asyncio
async def test_diff_harnesses_no_save_if_no_change():
    t = tempfile.NamedTemporaryFile()
    await Blackboard().set_path(Path(t.name))
    await Blackboard().add_diff_harnesses(set({"Harness1"}))
    mtime = datetime.datetime.fromtimestamp(Path(t.name).stat().st_mtime)
    async with aiofiles.open(t.name) as f:
        harnesses: list[str] = json.loads(await f.read())["diff"]["harnesses"]
    await Blackboard().add_diff_harnesses(set({"Harness1"}))
    assert mtime == datetime.datetime.fromtimestamp(Path(t.name).stat().st_mtime)
    async with aiofiles.open(t.name) as f:
        json.loads(await f.read())["diff"]["harnesses"] == harnesses


def get_hash_string(source: bytes) -> str:
    hasher = hashlib.sha256()
    hasher.update(source)
    return hasher.hexdigest()


@pytest.mark.asyncio
async def test_blackboard_update_cg():
    t = tempfile.TemporaryDirectory()
    t1 = Path(t.name, "sarif-cg.json")
    t2 = Path(t.name, "soot-cg.json")
    t3 = Path(t.name, "joern-cg.json")
    t4 = Path(t.name, "invalid-cg.json")
    t5 = tempfile.NamedTemporaryFile()
    async with aiofiles.open(t1, mode="w") as f:
        await f.write("a")
        await f.flush()
    async with aiofiles.open(t2, mode="w") as f:
        await f.write("b")
        await f.flush()
    async with aiofiles.open(t3, mode="w") as f:
        await f.write("c")
        await f.flush()
    async with aiofiles.open(t4, mode="w") as f:
        await f.write("d")
        await f.flush()
    Setting().calltree_db_path = t3
    await Blackboard().set_path(Path(t5.name))
    await Blackboard().update_cg(set({t1, t2, None, t4}))
    async with aiofiles.open(t5.name) as f:
        blackboard = json.loads(await f.read())
    assert blackboard["merged_sarif_cg"] == get_hash_string(b"a")
    assert blackboard["merged_soot_cg"] == get_hash_string(b"b")
    assert blackboard["merged_joern_cg"] == get_hash_string(b"c")


@pytest.mark.asyncio
async def test_update_cg_empty_path():
    Blackboard()._merged_joern_cg = ""
    await Blackboard().update_cg(set())
    assert Blackboard()._merged_joern_cg == ""
