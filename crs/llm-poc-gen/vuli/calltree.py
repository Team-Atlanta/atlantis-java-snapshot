import asyncio
import json
import logging
import time
from functools import reduce
from pathlib import Path
from queue import Queue
from typing import Any, Optional

import aiofiles
import networkx as nx

from vuli.common.decorators import SEVERITY, async_lock, async_safe, step
from vuli.common.singleton import Singleton
from vuli.cp import CP
from vuli.joern import Joern, joern_query_generator
from vuli.query_loader import QueryLoader


class CallTree(metaclass=Singleton):

    def __init__(self):
        self._logger = logging.getLogger("CallTree")
        self._call_depth: int = 30
        self._updated_time = None
        self._lock = asyncio.Lock()
        self._path = None

    @async_lock("_lock")
    async def build(self, harnesses: list[str]) -> None:
        graph = await self._build(harnesses)
        await self._save(graph)

    @async_safe(nx.DiGraph(), SEVERITY.ERROR, "CallTree")
    async def _build(self, harnesses: list[str]) -> None:
        """
        Build CallTree using harness_names as roots

        Args:
            harnesses: Harness IDs. This will be used to find path of
                harnesses.
        """
        graph: nx.DiGraph = await self._load_graph()
        self._logger.info(
            f"Building from harnesses: {",".join(
                [harness for harness in harnesses])}"
        )
        if len(harnesses) == 0:
            self._logger.info("CallTree Build Done [updated=False, reason=No Harness]")
            return graph

        query: str = QueryLoader().get(
            "fuzzer_entries",
            **{
                "harnesses": ",".join(
                    [
                        f"""("{CP().get_harness_path(x)}", "{CP().target_method(x)}")"""
                        for x in harnesses
                    ]
                )
            },
        )
        targets: list[int] = await Joern().run_query(query)
        if targets is None or len(targets) == 0:
            self._logger.info(
                "CallTree Build Done [updated=False, reason=No Target Node Found]"
            )
            return graph

        query: str = QueryLoader().get(
            "callee_tree",
            **{
                "call_depth": self._call_depth,
                "path": self._path,
                "targets": ",".join([f"{x}L" for x in targets]),
            },
        )
        calltree: list[dict] = await Joern().run_query(query, 1200)
        if calltree is None or len(calltree) == 0:
            self._logger.info(
                "CallTree Build Done [updated=False, reason=No Updateable Nodes]"
            )
            return graph

        if self._update(graph, calltree) is True:
            self._updated_time = time.time()
            self._logger.info(
                f"Build CallTree Done [updated=True, time={self._updated_time}, nodes={len(calltree)}]"
            )
            return graph
        self._logger.info("Build CallTree Done [updated=False]")
        return graph

    @async_lock("_lock")
    async def get_graph(self) -> nx.DiGraph:
        return await self._load_graph()

    @async_lock("_lock")
    async def insert(self, src: int, dsts: set[int]) -> bool:
        graph: nx.DiGraph = await self._load_graph()
        if await self._insert(graph, src, dsts):
            self._updated_time = time.time()
            await self._save(graph)
            self._logger.info(
                f"Insert CallTree Done [updated=True, time={self._updated_time}]"
            )
            return True
        return False

    @async_lock("_lock")
    async def insert_batch(self, srcs: set[int], dsts: set[int]) -> bool:
        graph: nx.DiGraph = await self._load_graph()
        if reduce(lambda y, x: y | self._insert(graph, x, dsts), srcs, False) is True:
            self._updated_time = time.time()
            await self._save(graph)
            return True
        return False

    @async_safe(False, SEVERITY.ERROR, "CallTree")
    async def _insert(self, graph: nx.DiGraph, src: int, dsts: set[int]) -> bool:
        self._logger.info(f"Insert {src}->{",".join([str(x) for x in dsts])}")

        callee_to_add: set[int] = self._update_each(graph, src, dsts)
        if len(callee_to_add) == 0:
            self._logger.info(
                "Insert CallTree Done [updated=False, reason=No New Callees]"
            )
            return

        await self._save(graph)
        query: str = QueryLoader().get(
            "callee_tree",
            **{
                "call_depth": self._call_depth,
                "path": self._path,
                "targets": ",".join([f"{x}L" for x in callee_to_add]),
            },
        )
        calltree: list[dict] = await Joern().run_query(query, timeout=1200)
        if calltree is None or len(calltree) == 0:
            self._logger.info(
                "Insert CallTree Done [updated=False, reason=No New Node]"
            )
            return True
        return self._update(graph, calltree)

    @async_lock("_lock")
    async def update(self, src: list[dict]) -> bool:
        graph: nx.DiGraph = await self._load_graph()
        if self._update(graph, src) is True:
            self._updated_time = time.time()
            await self._save(graph)
            return True
        return False

    @async_lock("_lock")
    async def set_path(self, path: Path) -> None:
        self._path = path

    def _get_all_node_id(self, graph: nx.DiGraph) -> set[int]:
        return set({node for node in graph.nodes})

    async def _load_graph(self) -> nx.DiGraph:
        try:
            async with aiofiles.open(self._path) as f:
                return nx.node_link_graph(json.loads(await f.read()), edges="links")
        except Exception:
            return nx.DiGraph()

    def _update(self, graph: nx.DiGraph, result: list[dict]) -> bool:
        if not result:
            return False

        cnt: int = reduce(
            lambda y, x: y + len(self._update_each(graph, x["id"], set(x["callees"]))),
            result,
            0,
        )
        return cnt > 0

    def _update_each(
        self, graph: nx.DiGraph, caller: int, callees: set[int]
    ) -> set[int]:
        graph.add_node(caller)
        [graph.add_node(callee) for callee in callees]

        callees_to_add: set[int] = set(
            {callee for callee in callees if not graph.has_edge(caller, callee)}
        )
        [graph.add_edge(caller, callee) for callee in callees_to_add]
        if len(callees_to_add) > 0:
            self._logger.info(
                f"Update Link {caller} -> {",".join([str(x) for x in callees_to_add])}"
            )
        return callees_to_add

    async def _save(self, graph: nx.DiGraph) -> None:
        if self._path is None:
            return

        async def update_node(graph: nx.DiGraph) -> None:
            node_to_add: set[int] = set(
                {
                    node_id
                    for node_id, attributes in graph.nodes(data=True)
                    if "data" not in attributes
                }
            )
            if len(node_to_add) == 0:
                return

            def chunk(src: list[Any], chunk_size=5000):
                for i in range(0, len(src), chunk_size):
                    yield src[i : i + chunk_size]

            table: dict = {}
            [
                table.update(
                    await Joern().run_query(
                        f"""
cpg.ids({",".join([str(node) for node in nodes])})
    .collect{{case x: Method => x}}
    .map(x => x.id ->
        Map(
            "func_name" -> x.name,
            "file_name" -> x.filename,
            "class_name" -> x.typeDecl.fullName.headOption.getOrElse(""),
            "func_sig" -> x.signature,
            "method_desc" -> x.genericSignature,
            "start_line" -> x.lineNumber.getOrElse(-1),
            "end_line" -> x.lineNumberEnd.getOrElse(-1)
    )).toMap
"""
                    )
                )
                for nodes in chunk(list(node_to_add), 5000)
            ]
            if len(table) == 0:
                return
            [graph.add_node(int(key), data=value) for key, value in table.items()]

        await update_node(graph)
        async with aiofiles.open(self._path, mode="w") as f:
            await f.write(json.dumps(nx.node_link_data(graph, edges="links"), indent=4))


class UpdateCallTree:
    def __init__(self):
        self._logger = logging.getLogger("UpdateCallTree")

    async def update(self, path: Path) -> bool:
        self._logger.info(f"Update Call Tree[path={path}]")
        meta: Optional[dict] = await self._load(path)
        if meta is None:
            self._logger.info(f"Nothing Loaded [path={path}]")
            return False

        entries: set[int] = meta["entries"]
        if len(entries) == 0:
            self._logger.info(f"Entry Not Found [path={path}]")
            return False

        graph: nx.Graph = meta["graph"]
        node_to_cpg: dict[int, int] = await self._node_to_cpg(graph)
        calltree_src: dict[int, set[int]] = await asyncio.to_thread(
            self._walk, graph, node_to_cpg, entries
        )
        calltree_src: list[dict] = [
            {"id": x, "callees": list(y)} for x, y in calltree_src.items()
        ]
        result: bool = await CallTree().update(calltree_src)
        self._logger.info(f"Call Tree Update [updated={result}, path={path}]")
        return result

    @async_safe(None, SEVERITY.ERROR, "UpdateCallTree")
    async def _load(self, path: Path) -> dict:
        async with aiofiles.open(path, mode="rt") as f:
            try:
                root: dict = json.loads(await f.read())
            except json.decoder.JSONDecodeError:
                self._logger.warning(f"Invalid Json File [path={path}]")
                return None
            try:
                graph: nx.Graph = nx.node_link_graph(root, edges="links")
            except Exception:
                graph: nx.Graph = nx.node_link_graph(root["graph"], edges="links")
            candidate: set[str] = set(
                {CP().target_method(x) for x in CP().get_harnesses()}
            )
            entries: set[int] = set(
                {
                    id
                    for id, data in graph.nodes(data=True)
                    if data["data"]["func_name"] in candidate
                }
            )
        return {"entries": entries, "graph": graph}

    async def _node_to_cpg(self, graph: nx.DiGraph) -> dict:
        @step(None, SEVERITY.NORMAL, "UpdateCallTree")
        def preprocess_for_joern_query(data: dict) -> Optional[dict]:
            return {
                "class_name": data["class_name"],
                "func_name": data["func_name"],
                "mid_line": data["start_line"]
                + int((data["end_line"] - data["start_line"]) / 2),
            }

        nodes: list[tuple[int, Optional[dict]]] = [
            (id, preprocess_for_joern_query(data.get("data", {})))
            for id, data in graph.nodes(data=True)
        ]
        nodes: list[tuple[int, dict]] = [(x, y) for x, y in nodes if y is not None]
        if len(nodes) == 0:
            return {}

        query_elements: list[str] = [
            f'("{x["class_name"]}", "{x["func_name"]}", {x["mid_line"]})'
            for _, x in nodes
        ]
        node_to_cpg: dict[int, int] = {}
        for query_element in joern_query_generator(query_elements):
            query: str = f"""
List({",".join([x for x in query_element])})
  .map(x => cpg.method.where(_.and(
    _.typeDecl.fullNameExact(x._1),
    _.nameExact(x._2),
    _.lineNumberLte(x._3),
    _.lineNumberEndGte(x._3)
  )).id.headOption.getOrElse(-1)).l"""
            result = await Joern().run_query(query)
            node_to_cpg.update(dict(zip([x[0] for x in nodes], result)))
        node_to_cpg: dict[int, int] = {x: y for x, y in node_to_cpg.items() if y != -1}
        return node_to_cpg

    def _walk(self, graph: nx.Graph, node_to_id: dict[int, int], entries: set[int]):
        queue: Queue[tuple[int, int]] = Queue()
        visit: set[int] = entries.copy()
        result: dict[int, set[int]] = {}
        [
            queue.put((successor, entry))
            for entry in entries
            for successor in graph.successors(entry)
        ]
        while queue.qsize() > 0:
            dst, src = queue.get()
            if src not in node_to_id:
                continue
            src_id: int = node_to_id[src]
            dst_id: int = node_to_id.get(dst, -1)
            if dst_id != -1:
                if src_id not in result:
                    result[src_id] = set()
                result[src_id].add(dst_id)
            visit.add(dst)
            for x in graph.successors(dst):
                if x in visit:
                    continue
                queue.put((x, src if dst_id == -1 else dst))
                continue
        return result


class CallTreePathFinder:
    def __init__(self, G):
        self._logger = logging.getLogger("CallTreePathFinder")
        self._G = G

    def find_path(self, src: int, dst: int) -> Optional[list[int]]:
        if src not in self._G or dst not in self._G:
            return None

        if not nx.has_path(self._G, src, dst):
            return None

        return nx.shortest_path(self._G, src, dst)
