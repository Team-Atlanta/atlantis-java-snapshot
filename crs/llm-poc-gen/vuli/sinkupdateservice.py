import hashlib
import json
import logging
from abc import abstractmethod
from collections import defaultdict
from functools import reduce
from pathlib import Path
from typing import Optional

import aiofiles
import asyncstdlib
from langchain_core.messages import BaseMessage
from langchain_core.messages.human import HumanMessage
from pydantic import BaseModel

from vuli.agents.parser import JsonParser
from vuli.blackboard import Blackboard
from vuli.codereader import BaseReader, create_code_table
from vuli.common.decorators import SEVERITY, async_safe, step
from vuli.cp import CP
from vuli.joern import Joern, joern_query_generator
from vuli.model_manager import ModelManager
from vuli.pathfinder import PathFinder
from vuli.query_loader import QueryLoader
from vuli.sariflog import SarifLog
from vuli.sink import Origin, SinkManager, SinkProperty
from vuli.struct import CodeLocation, SinkCandidate, VulInfo
from vuli.task import ServiceHandler, TaskHandler


class SinkUpdateData(BaseModel):
    class_name: str
    line_num: int
    bug_types: set[str]
    origins: set[Origin]
    id: int


class SinkUpdateTask(TaskHandler):

    def __init__(self):
        self._logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    async def _get_sinks(self) -> list[SinkUpdateData]:
        pass

    async def run(self) -> None:
        sinks: list[SinkUpdateData] = await self._get_sinks()
        if len(sinks) == 0:
            return

        await SinkManager().add_batch(
            {
                sink.id: SinkProperty(bug_types=sink.bug_types, origins=sink.origins)
                for sink in sinks
            }
        )
        await Blackboard().save()
        self._logger.info(f"Sink Updated: [sinks={len(sinks)}]")


class JavaCRS(SinkUpdateTask):

    def __init__(self, path: Path):
        super().__init__()
        self._logger = logging.getLogger(self.__class__.__name__)
        self._path = path
        self._last_hash: str = ""
        self._table: dict[str, int] = {}

    async def _get_sinks(self) -> list[CodeLocation]:
        if await self._initialize() is False:
            return []

        return await self._parse()

    @async_safe(False, SEVERITY.ERROR, "JavaCRS")
    async def _initialize(self) -> bool:
        file_hash: str = await self._get_file_hash()
        if file_hash == "":
            return False
        if self._last_hash == file_hash:
            return False
        self._last_hash = file_hash
        return True

    @async_safe("", SEVERITY.ERROR, "JavaCRS")
    async def _get_file_hash(self) -> str:
        if not isinstance(self._path, Path) or not self._path.is_file():
            return ""

        hasher = hashlib.sha256()
        async with aiofiles.open(self._path, mode="rb") as f:
            hasher.update(await f.read())
        return hasher.hexdigest()

    @async_safe([], SEVERITY.ERROR, "JavaCRS")
    async def _parse(self) -> list[SinkUpdateData]:
        async with aiofiles.open(self._path) as f:
            try:
                result = await f.read()
                sinks: list[dict] = json.loads(result)
            except json.decoder.JSONDecodeError:
                self._logger.warning(f"Invalid Json File [path={self._path}]")
                return []

        self._logger.info(f"Total Sinks From JavaCRS: {len(sinks)}")
        if len(sinks) == 0:
            return []

        sinks: list[Optional[dict]] = [self._preprocess_sink(sink) for sink in sinks]
        sinks: list[dict] = [sink for sink in sinks if sink is not None]
        self._logger.info(f"Valid Sinks From JavaCRS: {len(sinks)}")
        if len(sinks) == 0:
            return []

        sinks_to_query: list[dict] = [
            sink
            for sink in sinks
            if not (sink["class_name"], sink["line_num"]) in self._table
        ]

        @step(None, SEVERITY.ERROR, "SinkUpdateService")
        def update_table(name: str, num: int, id: int) -> None:
            self._table[name, num] = id

        [
            update_table(x["name"], x["num"], x["id"])
            for x in await self._to_joern_id(sinks_to_query)
        ]
        sinks: list[tuple[int, dict]] = [
            (self._table.get((sink["class_name"], sink["line_num"]), -1), sink)
            for sink in sinks
        ]
        sinks: list[tuple[int, dict]] = [
            (sink_id, sink) for sink_id, sink in sinks if sink_id != -1
        ]
        self._logger.info(f"Joern-Compatible Sinks: {len(sinks)}")
        return [self.to_sinkupdatedata(sink_id, sink) for sink_id, sink in sinks]

    @step(None, SEVERITY.ERROR, "JavaCRS")
    def _preprocess_sink(self, sink: dict) -> Optional[dict]:
        if "coord" not in sink:
            return None

        if "type" not in sink:
            return None

        coord: dict = sink["coord"]
        if "class_name" not in coord or "line_num" not in coord:
            return None

        return {
            "class_name": coord["class_name"],
            "line_num": int(coord["line_num"]),
            "bug_types": set(sink["type"]),
            "in_diff": sink.get("in_diff", False),
            "from_sarif": len(sink.get("sarif_reports", [])) > 0,
            "exploited": reduce(
                lambda y, x: y | x.get("solved", False),
                sink.get("sarif_reports", []),
                False,
            ),
        }

    @async_safe([], SEVERITY.ERROR, "SinkUpdateService")
    async def _to_joern_id(self, sinks: list[dict]) -> list[dict]:
        elements: list[str] = [
            f'("{sink["class_name"]}", {sink["line_num"]})' for sink in sinks
        ]
        if len(elements) == 0:
            return []

        async def reducer(accumulator: list[dict], item: dict):
            return accumulator + await self._get_from_joern(item)

        result: list[dict] = await asyncstdlib.reduce(
            reducer, joern_query_generator(elements), []
        )
        return result

    @async_safe([], SEVERITY.ERROR, "SinkUpdateService")
    async def _get_from_joern(self, elements: list[str]) -> list[dict]:
        query: str = f"""
List({",".join([element for element in elements])})
.map{{case (name, num) => (
    name, num, cpg.typeDecl.fullNameExact(name).method.cfgNode.where(_.lineNumber(num)).id.headOption)}}
.collect{{case (name, num, Some(id)) => Map(
    "name" -> name,
    "num" -> num,
    "id" -> id
)}}.l"""
        result: list[dict] = await Joern().run_query(query)
        return result

    def to_sinkupdatedata(self, id: int, sink: dict) -> None:
        origins: set[Origin] = set({Origin.FROM_CRS})
        if sink.get("in_diff", False) is True:
            origins.add(Origin.FROM_DELTA)
        if sink.get("from_sarif", False) is True:
            origins.add(Origin.FROM_SARIF)

        return SinkUpdateData(
            class_name=sink["class_name"],
            line_num=sink["line_num"],
            bug_types=sink["bug_types"],
            origins=origins,
            id=id,
        )


class SarifUpdateTask(SinkUpdateTask):

    def __init__(self, path: Path):
        super().__init__()
        self._logger = logging.getLogger(self.__class__.__name__)
        self._path = path

    async def _get_sinks(self) -> list[SinkUpdateData]:
        if await self._initialize() is False:
            return []

        return await self._parse()

    @async_safe(False, SEVERITY.ERROR, "JavaCRS")
    async def _initialize(self) -> bool:
        return isinstance(self._path, Path) and self._path.is_file()

    @async_safe([], SEVERITY.ERROR, "JavaCRS")
    async def _parse(self) -> list[SinkUpdateData]:
        async with aiofiles.open(self._path) as f:
            try:
                sinks: list[dict] = json.loads(await f.read())
            except json.decoder.JSONDecodeError:
                self._logger.warning(f"Invalid Json File [path={self._path}]")
                return []

        sink_candidates, additional_candidates = await SarifLog(sinks).extract()
        if len(sink_candidates) == 0:
            return []

        async def reducer(
            accumulator: list[SinkUpdateData], candidates: list[SinkCandidate]
        ) -> list[SinkUpdateData]:
            filtered = await self._filter_sink_candidate(
                candidates, additional_candidates, max_response=1
            )
            return accumulator + filtered

        sinks: list[SinkUpdateData] = await asyncstdlib.reduce(
            reducer, sink_candidates, []
        )
        return sinks

    async def _filter_sink_candidate(
        self,
        sink_candidate: list[SinkCandidate],
        additional_candidates,
        max_response: int,
    ) -> list[SinkUpdateData]:
        fuzzer_entry = QueryLoader().get("fuzzer_entry")
        selected_sink: list[SinkCandidate] = []

        if len(sink_candidate) > 1:
            grouped = defaultdict(set)
            method_to_additional = defaultdict(list)

            for add in additional_candidates:
                method_to_additional[add["match"]].extend(add["candidates"])

            for candidate in sink_candidate:
                key = (candidate.method, candidate.v_point.path)
                grouped[key].add((candidate.v_point.line, candidate.id))

                for x in method_to_additional.get(candidate.method, []):
                    new_key = (x.method, x.v_point.path)
                    grouped[new_key].add((x.v_point.line, x.id))

            grouped = {k: sorted(v, key=lambda x: x[0]) for k, v in grouped.items()}

            self._logger.debug(f"Grouped sink candidate by method: {grouped}")

            for (method, filepath), candidates in grouped.items():
                for harness_name in CP().get_harness_names():

                    try:
                        paths: list[VulInfo] = await PathFinder().find(
                            harness_name, {candidates[0][1]}
                        )
                        if not paths:
                            self._logger.info(
                                f"No path found from grouped sink candidate [method={method}, filename={filepath}, sinks={candidates[0][1]}]"
                            )
                            continue

                        candidate_lines = ", ".join(
                            [str(line) for line, _ in candidates]
                        )
                        code_table = await create_code_table(paths[0].v_paths)
                        code = await BaseReader(CP().source_dir).read_by_table(
                            code_table
                        )

                        message: BaseMessage = HumanMessage(
                            content=f"""
You must write a suspicious line number that can trigger vulnerability. The input values are given for the first parameter of the {fuzzer_entry} method.
You will get information about CODE, TYPE, FILEPATH and CANDIDATES.
You MUST analyze CODE to analyze vulnerability correctly.
TYPE is the sanitizer you should focus on.
CANDIDATES is the a set of specific line that might contains vunerable code.
FILEPATH is the path to the file that contains all the CANDIDATES lines.
The line MUST be the one of CANDIDATES.
You MUST provide up to {max_response}, without duplicates.
Your response MUST include the following JSON format:
```json
{{
    "line": [
        XX, YY
    ]
}}
```

<CODE>
{code}

<TYPE>
{sink_candidate[0].v_type}

<FILEPATH>
{filepath}

<CANDIDATES>
{candidate_lines}
"""
                        )

                        results: list[dict] = [
                            await ModelManager().invoke(
                                [message], model_name, JsonParser()
                            )
                            for model_name in ModelManager().get_all_model_names()
                        ]
                        lines = {line for result in results for line in result["line"]}

                        selected_sink += [
                            candidate
                            for candidate in sink_candidate
                            if candidate.v_point.path == filepath
                            and candidate.v_point.line in lines
                        ]

                        selected_sink += [
                            candidate
                            for add_candidate in additional_candidates
                            for candidate in add_candidate["candidates"]
                            if candidate.v_point.path == filepath
                            and candidate.v_point.line in lines
                        ]

                        self._logger.debug(f"Selected sinks: {selected_sink}")

                    except Exception as e:
                        self._logger.warning(f"Skip Exception: {e}")

        else:
            selected_sink = sink_candidate

        def to_sink(candidate: SinkCandidate) -> dict:
            v_point = candidate.v_point
            return SinkUpdateData(
                class_name=v_point.path,
                line_num=v_point.line,
                bug_types=set({candidate.v_type}),
                origins=set({Origin.FROM_SARIF}),
                id=candidate.id,
            )

        self._logger.info(f"Final selected sinks: {selected_sink}")
        return [to_sink(candidate) for candidate in selected_sink]


class SinkUpdateService(ServiceHandler):
    def __init__(self, interval: int = 10):
        super().__init__(interval=interval)
        self._logger = logging.getLogger(self.__class__.__name__)
        self._handlers: list[TaskHandler] = []

    def add_task(self, task: TaskHandler):
        self._handlers.append(task)

    def clear(self):
        self._handlers.clear()

    async def _run(self) -> None:
        [await self._safe_run(handler) for handler in self._handlers]

    @async_safe(None, SEVERITY.ERROR, "SinkUpdateService")
    async def _safe_run(self, handler: TaskHandler) -> None:
        await handler.run()
