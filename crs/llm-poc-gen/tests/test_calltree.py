import json
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import patch

import aiofiles
import networkx as nx
import pytest

from tests.test_util import prepare_sample_cp
from vuli.calltree import CallTree, UpdateCallTree
from vuli.common.setting import Setting
from vuli.cp import CP
from vuli.joern import CPG, Joern
from vuli.query_loader import QueryLoader

counter: int = 0


@pytest.fixture(autouse=True)
def setup():
    QueryLoader().load(Path(__file__).parent.parent / "queries" / "java.yaml")


@pytest.mark.asyncio
@patch.object(Joern, "run_query")
async def test_calltree_insert(patch_1):
    def mock_1(*args, **kwargs) -> Any:
        if len(args) > 0 and "cpg.ids(0,1)" in args[0]:
            return {
                0: {
                    "func_name": "fuzzerTestOneInput",
                    "file_name": "Harness.java",
                    "class_name": "Harness",
                    "func_sig": "func_sig",
                    "method_desc": "method_desc",
                    "start_line": 1,
                    "end_line": 10,
                },
                1: {
                    "func_name": "fuzz",
                    "file_name": "Harness.java",
                    "class_name": "Harness",
                    "func_sig": "func_sig",
                    "method_desc": "method_desc",
                    "start_line": 12,
                    "end_line": 24,
                },
            }
        if len(args) > 0 and "getCalleeTree" in args[0]:
            return [
                {"id": 0, "callees": [1, 2]},
                {"id": 1, "callees": [2]},
                {"id": 2, "callees": []},
            ]
        if len(args) > 0 and "cpg.ids(2)" in args[0]:
            return {
                2: {
                    "func_name": "select",
                    "file_name": "Harness.java",
                    "class_name": "Harness",
                    "func_sig": "func_sig",
                    "method_desc": "method_desc",
                    "start_line": 30,
                    "end_line": 40,
                }
            }

    patch_1.side_effect = mock_1
    t_ct = tempfile.NamedTemporaryFile()
    p_ct = Path(t_ct.name)
    await CallTree().set_path(p_ct)
    await CallTree().insert(0, set({1}))
    graph: nx.DiGraph = await CallTree().get_graph()
    assert set(graph.nodes()) == set({0, 1, 2})
    assert set(graph.edges()) == set({(0, 1), (0, 2), (1, 2)})


@pytest.mark.asyncio
@patch.object(CP, "target_method")
@patch.object(CP, "get_harnesses")
async def test_updatecalltree__load_format1(patch_1, patch_2):
    def mock_2(*args, **kwargs) -> str:
        if args[0] == "Harness":
            return "fuzzerTestOneInput"
        else:
            raise RuntimeError

    patch_1.return_value = ["Harness"]
    patch_2.side_effect = mock_2

    t_cg = tempfile.NamedTemporaryFile()
    p_cg = Path(t_cg.name)
    with p_cg.open("w") as f:
        json.dump(
            {
                "entrypoint": 1,
                "graph": {
                    "directed": True,
                    "multigraph": False,
                    "graph": {},
                    "nodes": [
                        {
                            "id": 1,
                            "data": {
                                "class_name": "Harness",
                                "func_name": "fuzzerTestOneInput",
                                "start_line": 1,
                                "end_line": 10,
                            },
                        },
                        {
                            "id": 2,
                            "data": {
                                "class_name": "Harness",
                                "func_name": "fuzz",
                                "start_line": 12,
                                "end_line": 24,
                            },
                        },
                    ],
                    "links": [{"source": 1, "target": 2}],
                },
            },
            f,
        )
    result: dict = await UpdateCallTree()._load(p_cg)
    assert result["entries"] == {1}
    assert result["graph"] is not None


@pytest.mark.asyncio
@patch.object(CP, "target_method")
@patch.object(CP, "get_harnesses")
async def test_updatecalltree__load_format2(patch_1, patch_2):
    def mock_2(*args, **kwargs) -> str:
        if args[0] == "Harness":
            return "fuzzerTestOneInput"
        else:
            raise RuntimeError

    patch_1.return_value = ["Harness"]
    patch_2.side_effect = mock_2

    t_cg = tempfile.NamedTemporaryFile()
    p_cg = Path(t_cg.name)
    with p_cg.open("w") as f:
        json.dump(
            {
                "directed": True,
                "multigraph": False,
                "graph": {},
                "nodes": [
                    {
                        "id": 1,
                        "data": {
                            "class_name": "Harness",
                            "func_name": "fuzzerTestOneInput",
                            "start_line": 1,
                            "end_line": 10,
                        },
                    },
                    {
                        "id": 2,
                        "data": {
                            "class_name": "Harness",
                            "func_name": "fuzz",
                            "start_line": 12,
                            "end_line": 24,
                        },
                    },
                ],
                "links": [{"source": 1, "target": 2}],
            },
            f,
        )
    result: dict = await UpdateCallTree()._load(p_cg)
    assert result["entries"] == {1}
    assert result["graph"] is not None


@pytest.mark.asyncio
async def test_updatecalltree__load_path_not_exist():
    name: int = 0
    while Path(str(name)).exists() is True:
        name += 1
    await UpdateCallTree()._load(Path(str(name)))


@pytest.mark.asyncio
async def test_updatecalltree__load_invalid_file():
    t = tempfile.NamedTemporaryFile()
    p = Path(t.name)
    with p.open("w") as f:
        f.write("hello")
        f.flush()
    await UpdateCallTree()._load(p)


@pytest.mark.asyncio
@patch.object(CP, "target_method")
@patch.object(CP, "get_harnesses")
@patch.object(Joern, "run_query")
async def test_updatecalltree_update_format1(patch_1, patch_2, patch_3):
    global counter
    counter = 0

    def mock_1(*args, **kwargs) -> Any:
        global counter
        if counter == 0:
            counter += 1
            return [0, 1]
        if counter == 1:
            return {
                0: {
                    "func_name": "fuzzerTestOneInput",
                    "file_name": "Harness.java",
                    "class_name": "Harness",
                    "func_sig": "func_sig",
                    "method_desc": "method_desc",
                    "start_line": 1,
                    "end_line": 10,
                },
                1: {
                    "func_name": "fuzz",
                    "file_name": "Harness.java",
                    "class_name": "Harness",
                    "func_sig": "func_sig",
                    "method_desc": "method_desc",
                    "start_line": 12,
                    "end_line": 24,
                },
            }

    def mock_2(*args, **kwargs) -> str:
        if args[0] == "Harness":
            return "fuzzerTestOneInput"
        else:
            raise RuntimeError

    patch_1.side_effect = mock_1
    patch_2.return_value = ["Harness"]
    patch_3.side_effect = mock_2

    t_cg = tempfile.NamedTemporaryFile()
    p_cg = Path(t_cg.name)
    t_ct = tempfile.NamedTemporaryFile()
    p_ct = Path(t_ct.name)
    await CallTree().set_path(p_ct)

    with p_cg.open("w") as f:
        json.dump(
            {
                "entrypoint": 1,
                "graph": {
                    "directed": True,
                    "multigraph": False,
                    "graph": {},
                    "nodes": [
                        {
                            "id": 1,
                            "data": {
                                "class_name": "Harness",
                                "func_name": "fuzzerTestOneInput",
                                "start_line": 1,
                                "end_line": 10,
                            },
                        },
                        {
                            "id": 2,
                            "data": {
                                "class_name": "Harness",
                                "func_name": "fuzz",
                                "start_line": 12,
                                "end_line": 24,
                            },
                        },
                    ],
                    "links": [{"source": 1, "target": 2}],
                },
            },
            f,
        )
    await UpdateCallTree().update(p_cg)
    graph: nx.DiGraph = await CallTree()._load_graph()
    assert set(graph.nodes) & set({0, 1}) == set({0, 1})
    assert (0, 1) in graph.edges


@pytest.mark.asyncio
async def test_calltree_insert_e2e():
    await prepare_sample_cp()
    cpg = CPG(Setting().cpg_path)
    await cpg.build(
        Setting().joern_javasrc_path, CP().source_dir, [], CP().get_dependent_jars()
    )
    try:
        Joern().set_path(Setting().joern_cli_path)
        await Joern().run_server(cpg, Setting().query_path, Setting().semantic_dir)
        await CallTree().set_path(Setting().calltree_db_path)
        await CallTree().build(CP().harnesses)
        result: list[int] = await Joern().run_query(
            """
List("sample.one.SampleOne.fuzzerTestOneInput", "sample.one.SampleOne.fuzz", "sample.BugTwo.run", "sample.BugTwo._run")
    .map(x => cpg.method.fullName("^" + x + ".*").id.head)"""
        )
        graph: nx.DiGraph = await CallTree().get_graph()
        assert nx.has_path(graph, result[0], result[1])
        assert result[2] not in graph
        assert result[3] not in graph
        await CallTree().insert(result[1], set({result[2]}))
        graph: nx.DiGraph = await CallTree().get_graph()
        assert nx.has_path(graph, result[0], result[1])
        assert nx.has_path(graph, result[1], result[2])
        assert nx.has_path(graph, result[2], result[3])
    finally:
        await Joern().close_server()


@pytest.mark.asyncio
async def test_calltree_build_no_harness():
    t = tempfile.NamedTemporaryFile(suffix=".json")
    Path(t.name).unlink()
    await CallTree().set_path(Path(t.name))
    await CallTree().build([])
    assert Path(t.name).exists() is True


@pytest.mark.asyncio
@patch.object(Joern, "run_query")
async def test_calltree_build_no_haress_node(patch_1):
    patch_1.return_value = []
    t = tempfile.NamedTemporaryFile(suffix=".json")
    Path(t.name).unlink()
    await CallTree().set_path(Path(t.name))
    await CallTree().build(["harness"])
    assert Path(t.name).exists() is True


@pytest.mark.asyncio
@patch.object(Joern, "run_query")
async def test_calltree_build_no_updatable_nodes(patch_1):
    def mock_1(*args, **kwargs) -> None:
        if mock_1.counter == 0:
            mock_1.counter += 1
            return [0]
        if mock_1.counter == 1:
            return []

    mock_1.counter = 0
    patch_1.side_effect = mock_1
    t = tempfile.NamedTemporaryFile(suffix=".json")
    await CallTree().set_path(Path(t.name))
    await CallTree().build(["harness"])
    assert Path(t.name).exists() is True


@pytest.mark.asyncio
@patch.object(CallTree, "_update")
@patch.object(Joern, "run_query")
async def test_calltree_build_no_update(patch_1, patch_2):
    def mock_1(*args, **kwargs) -> None:
        if mock_1.counter == 0:
            mock_1.counter += 1
            return [0]
        if mock_1.counter == 1:
            return [{}]

    mock_1.counter = 0
    patch_1.side_effect = mock_1
    patch_2.return_value = False
    t = tempfile.NamedTemporaryFile(suffix=".json")
    await CallTree().set_path(Path(t.name))
    await CallTree().build(["harness"])
    assert Path(t.name).exists() is True


@pytest.mark.asyncio
async def test_updatecalltree_update_invalid_json():
    t = tempfile.NamedTemporaryFile()
    async with aiofiles.open(t.name, "w") as f:
        await f.write("{")
        await f.flush()
    await UpdateCallTree().update(Path(t.name))
