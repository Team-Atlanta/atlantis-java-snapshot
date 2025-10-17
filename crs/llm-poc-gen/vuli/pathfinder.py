import logging
from dataclasses import asdict

import asyncstdlib

from vuli.blackboard import Blackboard
from vuli.calltree import CallTree, CallTreePathFinder
from vuli.cp import CP
from vuli.joern import Joern
from vuli.path_manager import PathManager
from vuli.query_loader import QueryLoader
from vuli.sink import Origin, SinkManager, SinkProperty, SinkStatus
from vuli.struct import CodeLocation, CodePoint, VulInfo
from vuli.task import ServiceHandler


class PathFinder:
    def __init__(self):
        self._logger = logging.getLogger("PathFinder")

    async def find(self, harness_name: str, sinks: set[int]) -> list[VulInfo]:
        paths: list[VulInfo] = await self._sta(harness_name, sinks)
        covered_sinks: set[int] = sinks - {path.sink_id for path in paths}
        paths.extend(await self._cg(harness_name, covered_sinks))
        return paths

    async def _sta(self, harness_name: str, sinks: set[int]) -> list[VulInfo]:
        if len(sinks) == 0:
            self._logger.info("Skip STA [reason=No Targets]")
            return []

        params = {
            "harness": str(CP().get_harness_path_by_name(harness_name)),
            "sink_ids": ",".join([str(sink) for sink in sinks]),
        }
        joern_query: str = QueryLoader().get("sta", **params)
        joern_result: dict = await Joern().run_query(joern_query, timeout=1200)
        joern_result: dict = {int(node): paths for node, paths in joern_result.items()}
        result: list[VulInfo] = []
        for sink_node, paths in joern_result.items():
            paths: list[list[CodePoint]] = [
                [
                    CodePoint(
                        point["filename"],
                        point["fullName"],
                        point["linNumber"],
                        point["columnNumber"],
                    )
                    for point in path
                ]
                for path in paths
            ]
            paths: list[list[CodePoint]] = [
                self._erase_duplicates(path) for path in paths
            ]
            paths: list[VulInfo] = [
                VulInfo(
                    harness_name,
                    sink_node,
                    path,
                    CodeLocation(path[-1].path, path[-1].line, path[-1].column),
                )
                for path in paths
                if len(path) > 0
            ]
            result.extend(paths)
        self._logger.info(
            f"STA in PathFinder found {len(result)} Paths [harness={harness_name}]"
        )
        return result

    async def _cg(self, harness_name: str, sinks: set[int]) -> list[VulInfo]:
        if len(sinks) == 0:
            self._logger.info("Skip CG [reason=No Targets]")
            return []
        params = {
            "harness": str(CP().get_harness_path_by_name(harness_name)),
            "sink_ids": ",".join([str(sink) for sink in sinks]),
        }
        joern_query: str = QueryLoader().get("cg", **params)
        joern_result: dict = await Joern().run_query(joern_query)
        srcs: set[int] = set(joern_result.get("srcs", []))
        dst_table: dict[int, list[int]] = {
            int(key): value for key, value in joern_result.get("dst_table", {}).items()
        }
        dsts: set[int] = set(dst_table.keys())

        finder = CallTreePathFinder(await CallTree().get_graph())
        result: list[VulInfo] = []
        covered_sinks: set[int] = set()
        for src in srcs:
            for dst in dsts:
                path: list[int] = finder.find_path(src, dst)
                if path is None or len(path) < 1:
                    continue
                related_sinks: set[int] = set(dst_table.get(path[-1], []))
                if len(related_sinks) == 0:
                    continue
                joern_query: str = f"""
def firstNode(method: Method): CfgNode = {{
    val node: CfgNode = method.cfgFirst.head
    node.lineNumber match {{
        case Some(x) => node
        case _ => method.call.map(x => (x, x.lineNumber)).collect{{case (a, Some(b)) => (a, b)}}.sortBy(_._2).head._1
    }}
}}
cpg.ids({",".join([str(x) for x in path])})
    .collect{{case x: Method => x}}
    .map(firstNode)
    .map(x => (x.method.filename, x.method.fullName, x.lineNumber, x.columnNumber.getOrElse(-1)))
    .collect{{case (a, b, Some(c), d) => (a, b, c, d)}}
    .map(x => Map(
        "path" -> x._1,
        "method" -> x._2,
        "line" -> x._3,
        "column" -> x._4
    )).l"""
                joern_path: list[dict] = await Joern().run_query(joern_query)
                if joern_path is None or len(joern_path) == 0:
                    continue
                covered_sinks |= related_sinks
                joern_query: str = f"""
cpg.ids({",".join([str(sink) for sink in related_sinks])})
    .collect{{case x: CfgNode => x}}
    .map(x => (x.id, x.method.filename, x.lineNumber, x.columnNumber.getOrElse(-1)))
    .collect{{case (a, b, Some(c), d) => (a, b, c, d)}}
    .map(x => (x._1, s"${{x._2}}:${{x._3}}:${{x._4}}"))
    .toMap
"""
                joern_result: list[str] = await Joern().run_query(joern_query)
                for sink in related_sinks:
                    loc: str = joern_result.get(str(sink), "")
                    if len(loc) == 0:
                        continue

                    v_point = CodeLocation.create(loc)
                    v_path = [
                        CodePoint(
                            item["path"],
                            item["method"],
                            item["line"],
                            item["column"],
                        )
                        for item in joern_path
                        + [
                            {
                                **asdict(v_point),
                                "method": joern_path[-1]["method"],
                            }
                        ]
                    ]
                    v_path: list[CodePoint] = self._erase_duplicates(v_path)
                    v_info = VulInfo(harness_name, sink, v_path, v_point)
                    result.append(v_info)
        self._logger.info(
            f"CGA in PathFinder found {len(result)} Paths [harness={harness_name}]"
        )
        return result

    def _erase_duplicates(self, path: list[CodePoint]) -> list[CodePoint]:
        if len(path) == 0:
            return path

        real_path: list[CodePoint] = [path[-1]]
        for point in reversed(path[0:-1]):
            if real_path[-1].path != point.path or real_path[-1].line != point.line:
                real_path.append(point)
        real_path.reverse()
        return real_path


class FindPathService(ServiceHandler):
    def __init__(self, interval: int = 180):
        super().__init__(interval)
        self._logger = logging.getLogger(self.__class__.__name__)
        self._last_calltree_time = None

    async def _run(self) -> None:
        sinks = await SinkManager().get()
        untested_sinks: set[int] = set(
            {
                id
                for id, property in sinks.items()
                if property.status == SinkStatus.UNKNOWN
            }
        )
        unreached_sinks: set[int] = set()
        if CallTree()._updated_time != self._last_calltree_time:
            self._last_calltree_time = CallTree()._updated_time
            unreached_sinks: set[int] = set(
                {
                    id
                    for id, property in sinks.items()
                    if property.status == SinkStatus.MAY_UNREACHABLE
                }
            )
        if len(untested_sinks | unreached_sinks) == 0:
            return

        async def reducer(accumulator: set[int], harness: str):
            return accumulator | await self._find_by_harness(
                harness, untested_sinks, unreached_sinks
            )

        covered_sinks: set[int] = await asyncstdlib.reduce(
            reducer, CP().harnesses, set()
        )
        uncovered_sinks: set[int] = untested_sinks - covered_sinks

        [
            await SinkManager().update_status(sink, SinkStatus.MAY_REACHABLE)
            for sink in covered_sinks
        ]
        [
            await SinkManager().update_status(sink, SinkStatus.MAY_UNREACHABLE)
            for sink in uncovered_sinks
        ]
        await Blackboard().save()

    async def _find_by_harness(
        self, harness: str, untested_sinks: set[int], unreached_sinks: set[int]
    ) -> set[int]:
        self._logger.info(
            f"Start Finding Path [harness={harness}, untested_sinks={len(untested_sinks)}, unreached_sinks={len(unreached_sinks)}]"
        )
        paths: list[VulInfo] = await PathFinder()._sta(harness, untested_sinks)
        uncovered_sinks: set[int] = (
            untested_sinks - set({path.sink_id for path in paths})
        ) | unreached_sinks
        paths.extend(await PathFinder()._cg(harness, uncovered_sinks))
        covered_sinks: set[int] = set({path.sink_id for path in paths})
        await PathManager().add_batch(paths)
        for path in paths:
            methods: set[str] = set({x.method for x in path.v_paths})
            if len(Blackboard()._modified_methods & methods) > 0:
                await SinkManager().add(
                    (path.sink_id, SinkProperty(origins=set({Origin.FROM_DELTA})))
                )
        self._logger.info(
            f"Finish Finding Path [harness={harness}, covered_sinks={len(covered_sinks)}]"
        )
        return covered_sinks
