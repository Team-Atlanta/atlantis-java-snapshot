import asyncio
import base64
import hashlib
import json
import logging
import os
from enum import Enum
from pathlib import Path
from typing import Optional

import aiofiles
import aiofiles.os
from pydantic import BaseModel

from vuli.common.decorators import async_lock
from vuli.common.setting import Setting
from vuli.common.singleton import Singleton
from vuli.cp import CP
from vuli.joern import Joern
from vuli.sink import Origin, SinkManager, SinkProperty, SinkStatus
from vuli.struct import CodeLocation, CodePoint


class BlackboardDataStatus(Enum):
    NOT_REACHED = 0
    REACHED = 1
    EXPLOITED = 2


class BlackboardPath(BaseModel):
    harness_id: str
    route: list[CodeLocation]
    bug_types: list[str]
    status: BlackboardDataStatus


class BlackboardSink(BaseModel):
    class_name: str
    file_path: str
    line_num: int
    type: list[str]
    in_diff: bool
    ana_reachability: list[str]
    ana_exploitability: bool
    status: str


class Blackboard(metaclass=Singleton):
    def __init__(self):
        self._logger = logging.getLogger("Blackboard")
        self._lock = asyncio.Lock()
        self._path: Path = None
        self._seed: dict[str, set[bytes]] = {}
        self._sinks: dict[int, dict] = {}
        self._paths: list[BlackboardPath] = []
        self._time = -1
        self._diff_harnesses: set[str] = set()
        self._merged_sarif_cg: str = ""
        self._merged_soot_cg: str = ""
        self._merged_joern_cg: str = ""
        self._modified_methods: set[str] = set()

    @async_lock("_lock")
    async def add_seed(self, harness_id: str, blob: bytes, score: float = 0.0) -> None:
        if score == 1.0 and Setting().shared_dir:
            shared_dir = Setting().shared_dir / harness_id
            await aiofiles.os.makedirs(shared_dir, exist_ok=True)
            t = await aiofiles.tempfile.NamedTemporaryFile(
                dir=shared_dir, suffix=".bin", delete=False
            )
            async with aiofiles.open(t.name, mode="wb") as f:
                await f.write(blob)
                await f.flush()

        if self._add_seed(harness_id, {base64.b64encode(blob).decode("utf-8")}) is True:
            await self._save()

    @async_lock("_lock")
    async def add_path(
        self,
        harness_id: str,
        path: list[CodePoint],
        bug_types: list[str],
        status: BlackboardDataStatus,
    ) -> None:
        self._paths.append(
            BlackboardPath(
                harness_id=harness_id,
                route=[CodeLocation(x.path, x.line, x.column) for x in path],
                bug_types=bug_types,
                status=status,
            )
        )

    @async_lock("_lock")
    async def add_diff_harnesses(self, harnesses: set[str]) -> None:
        new_harnesses: set[str] = harnesses - self._diff_harnesses
        if len(new_harnesses) > 0:
            self._diff_harnesses |= new_harnesses
            await self._save()
        self._logger.info(
            f"Diff Harnesses Updated [request={",".join(harnesses)}, updated={",".join(new_harnesses)}]"
        )

    @property
    def diff_harnesses(self) -> set[str]:
        return self._diff_harnesses

    @async_lock("_lock")
    async def update_cg(self, paths: set[Path]) -> None:
        paths.add(None)
        [await self._update_cg(path) for path in paths]

    async def _update_cg(self, path: Path) -> None:
        attribute: Optional[str] = self._get_cg_attribute(path)
        if attribute is None:
            return
        if path is None:
            path = Setting().calltree_db_path
        if path is None:
            return
        if not path.exists():
            return
        async with aiofiles.open(path, mode="rb") as f:
            hasher = hashlib.sha256()
            hasher.update(await f.read())
            setattr(self, attribute, hasher.hexdigest())
        self._logger.info(f"CG Updated [attribute={attribute}, path=[{path}]")
        await self._save()

    def _get_cg_attribute(self, path: Path) -> Optional[str]:
        if path is None:
            return "_merged_joern_cg"
        if path.name.startswith("sarif-"):
            return "_merged_sarif_cg"
        if path.name.startswith("soot-"):
            return "_merged_soot_cg"
        return None

    @async_lock("_lock")
    async def clear(self) -> None:
        self._seed = {}
        self._sinks = {}
        self._paths = []
        self._time = -1
        self._diff_harnesses = set()

    @async_lock("_lock")
    async def save(self) -> None:
        await self._save()

    @async_lock("_lock")
    async def set_path(self, path) -> None:
        self._path = path

    @async_lock("_lock")
    async def set_time(self, time: int) -> None:
        self._time = time

    def _add_seed(self, harness_id: str, blobs: set[str]) -> None:
        seeds: set[bytes] = self._seed.setdefault(harness_id, set())
        new_seeds: set[bytes] = blobs - seeds
        if len(new_seeds) == 0:
            return False
        seeds |= new_seeds
        self._logger.info(f"{len(new_seeds)} seeds are generated for {harness_id}")
        return True

    async def _save(self) -> None:
        try:

            def convert_enum(obj):
                if isinstance(obj, Enum):
                    return obj.name

            sinks: list[dict] = [
                sink.model_dump() for sink in await self._sinks_to_dump()
            ]
            harnesses: set[str] = CP().get_harnesses()
            for sink in sinks:
                sink["ana_reachability"] = {
                    x: True for x in sink.get("ana_reachability", [])
                }
                sink["ana_exploitability"] = (
                    {x: False for x in harnesses}
                    if sink.get("ana_exploitability") is False
                    else {}
                )

            root: dict = {
                "sinks": sinks,
                "paths": [path.model_dump() for path in self._paths],
                "diff": {"harnesses": list(self._diff_harnesses)},
                "merged_sarif_cg": self._merged_sarif_cg,
                "merged_soot_cg": self._merged_soot_cg,
                "merged_joern_cg": self._merged_joern_cg,
            }

            if self._time >= 0:
                root["time"] = self._time
            root.update(self._seed_to_dump())
            await self._atomic_dump(json.dumps(root, indent=4, default=convert_enum))
        except Exception:
            await self._atomic_dump(
                json.dumps(self._seed_to_dump(), indent=4, default=convert_enum)
            )

    def _seed_to_dump(self) -> dict:
        keys: list[str] = sorted(list(self._seed.keys()))
        return {
            "result": [
                {"harness_id": key, "blob": sorted(list(self._seed[key]))}
                for key in keys
            ]
        }

    async def _atomic_dump(self, content: str) -> None:
        """Write content to a temporary file and then atomically move it to the target path."""
        temp_path = self._path.parent / f".hidden.{self._path.name}"

        try:
            async with aiofiles.open(temp_path, "w") as f:
                await f.write(content)
                # Ensure all data is written to disk
                await f.flush()
                os.fsync(f.fileno())

            # Atomically rename temp file to target file
            os.replace(temp_path, self._path)
        except Exception:
            try:
                os.unlink(temp_path)
            except Exception:
                pass

    async def _sinks_to_dump(self) -> list[BlackboardSink]:
        sinks: dict[int, SinkProperty] = await SinkManager().get()
        if len(sinks) == 0:
            return []
        await self._update_sinks_location(set(sinks.keys()))
        sinks_to_dump: list[BlackboardSink] = [
            x
            for x in [
                self._sink_to_dump(sink_id, sink_property)
                for sink_id, sink_property in sinks.items()
            ]
            if x is not None
        ]
        merge: dict[tuple[str, int], BlackboardSink] = {}
        for x in sinks_to_dump:
            file_path: str = x.file_path
            line_num: int = x.line_num
            if (file_path, line_num) in merge:
                merge[(file_path, line_num)].type = sorted(
                    list(set(merge[(file_path, line_num)].type) | set(x.type))
                )
                merge[(file_path, line_num)].in_diff |= x.in_diff
                merge[(file_path, line_num)].ana_reachability = sorted(
                    list(
                        set(merge[(file_path, line_num)].ana_reachability)
                        | set(x.ana_reachability)
                    )
                )
                merge[(file_path, line_num)].ana_exploitability |= x.ana_exploitability
            else:
                merge[(file_path, line_num)] = x
        return list(merge.values())

    def _sink_to_dump(
        self, sink_id: int, sink_property: SinkProperty
    ) -> Optional[BlackboardSink]:
        class_name: str = self._sinks.get(sink_id, {}).get("class_name", "")
        file_path: str = self._sinks.get(sink_id, {}).get("file_path", "")
        line_num: int = self._sinks.get(sink_id, {}).get("line_num", -1)
        if file_path == "" or line_num == -1:
            self._logger.warning(f"Failed to get location for sink(id={sink_id})")
            return None
        from_delta: bool = Origin.FROM_DELTA in sink_property.origins
        return BlackboardSink(
            class_name=class_name,
            file_path=file_path,
            line_num=line_num,
            type=[self._to_crs_type(x) for x in sink_property.bug_types],
            in_diff=from_delta,
            ana_reachability=list(sink_property.harnesses),
            ana_exploitability=sink_property.status != SinkStatus.UNEXPLOITABLE,
            status=sink_property.status.name,
        )

    def _to_crs_type(self, bug_type: str) -> str:
        if bug_type == "OS Command Injection":
            return "sink-OsCommandInjection"
        elif bug_type == "Server Side Request Forgery":
            return "sink-ServerSideRequestForgery"
        elif bug_type == "Deserialization":
            return "sink-UnsafeDeserialization"
        elif bug_type == "SQL Injection":
            return "sink-SqlInjection"
        elif bug_type == "JNDI Lookup":
            return "sink-RemoteJNDILookup"
        elif bug_type == "LDAP Injection":
            return "sink-LdapInjection"
        elif bug_type == "XPath Injection":
            return "sink-XPathInjection"
        elif bug_type == "Load Arbitrary Library":
            return "sink-LoadArbitraryLibrary"
        elif bug_type == "Regular Expression Injection":
            return "sink-RegexInjection"
        elif bug_type == "Script Engine Injection":
            return "sink-ScriptEngineInjection"
        elif bug_type == "File Path Traversal":
            return "sink-FilePathTraversal"
        elif bug_type == "Reflective Call":
            return "sink-UnsafeReflectiveCall"
        elif bug_type == "Express Language Injection":
            return "sink-ExpressionLanguageInjection"
        else:
            return bug_type

    async def _update_sinks_location(self, sinks: set[int]) -> None:
        sinks_to_update: set[int] = sinks - set(self._sinks.keys())
        if len(sinks_to_update) == 0:
            return

        query: str = f"""
cpg.ids({",".join([str(x) for x in sinks_to_update])})
    .collect{{case x: CfgNode => x}}
    .collect{{
        case x if x.astParent.isInstanceOf[Call] => (x.id, x.astParent.asInstanceOf[Call])
        case x => (x.id, x)
    }}
    .map(x => (x._1, x._2, x._2.method.typeDecl.headOption))
    .collect{{case (x, y, Some(z)) => (x, y, z)}}
    .map{{case (x, y, z) => x -> Map(
        "class_name" -> z.fullName,
        "file_path" -> y.method.filename,
        "line_num" -> y.lineNumber.getOrElse(-1)
    )}}.toMap"""
        joern_result: dict = await Joern().run_query(query)
        joern_result: dict = {int(x): y for x, y in joern_result.items()}
        self._sinks.update(joern_result)
        self._logger.info(f"{len(joern_result)} sinks location updated")
