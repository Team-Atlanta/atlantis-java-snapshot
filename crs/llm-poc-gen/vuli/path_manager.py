import asyncio
import json
import logging
import pickle
from enum import Enum
from pathlib import Path
from typing import Optional

import aiofiles

from vuli.common.decorators import SEVERITY, async_lock, step
from vuli.common.singleton import Singleton
from vuli.sink import Origin, SinkManager
from vuli.struct import CodePoint, VulInfo


class Status(Enum):
    UNKNOWN = 0
    ANALYZING = 1
    MAY_UNREACHABLE = 2
    REACHABLE = 3
    EXPLOITABLE = 4


class PathManager(metaclass=Singleton):
    def __init__(self):
        self._logger = logging.getLogger("PathManager")
        self._lock = asyncio.Lock()
        self._key_counter: dict[str, int] = {}  # (Harness Name, # of scheduled)
        self._table: dict[bytes, Status] = {}  # (Serialized VulInfo, Path Status)
        self._queue: list[VulInfo] = []
        self._failures: list[list[CodePoint]] = []

    @async_lock("_lock")
    async def add_failure(self, path: list[CodePoint]) -> None:
        if path in self._failures:
            return
        self._logger.info(f"Added Failed Path: {path}")
        self._failures.append(path)

    @async_lock("_lock")
    async def add(self, path: VulInfo) -> None:
        self._add(path)

    @async_lock("_lock")
    async def add_batch(self, paths: list[VulInfo]) -> None:
        for path in paths:
            self._add(path)

    @async_lock("_lock")
    async def get_status(self, path: VulInfo) -> Status:
        serialized: bytes = pickle.dumps(path)
        return self._table.get(serialized, Status.UNKNOWN)

    @async_lock("_lock")
    async def clear(self) -> None:
        self._key_counter = {}
        self._table = {}
        self._queue = []

    @async_lock("_lock")
    async def get(self) -> Optional[VulInfo]:
        @step(False, SEVERITY.ERROR, "PathManager")
        def is_failed_path(path: VulInfo) -> bool:
            for failure in self._failures:
                if len(path.v_paths) < len(failure):
                    continue
                if path.v_paths[: len(failure)] == failure:
                    return True
            return False

        async def to_comparable(
            path: VulInfo, key_priority: list[int]
        ) -> tuple[int, int, bool]:
            origin: Optional[Origin] = await SinkManager().get_origin(path.sink_id)
            if origin is None:
                origin = Origin.FROM_INSIDE
            try:
                harness_idx: int = key_priority.index(path.harness_id)
            except ValueError:
                harness_idx: int = 0

            return (origin.value, harness_idx, is_failed_path(path))

        if len(self._queue) == 0:
            return None

        key_priority: list[int] = list(
            reversed(
                sorted(
                    list(self._key_counter.keys()),
                    key=lambda x: self._key_counter.get(x, 0),
                )
            )
        )
        pick: tuple[int, int, bool, int] = await to_comparable(
            self._queue[0], key_priority
        ) + (0,)
        if (
            pick[0] != Origin.FROM_SARIF
            or pick[1] != len(key_priority) - 1
            or pick[2] is True
        ):
            for i in range(1, len(self._queue)):
                compare: tuple[int, int, bool] = await to_comparable(
                    self._queue[i], key_priority
                )

                # If current is failed path and other is not, then schedule other first.
                if pick[2] is True and compare[2] is False:
                    self._logger.info(f"Failed Path is deprioritized [path={pick}]")
                    pick = compare + (i,)
                    continue

                # If it's a SARIF, and its harness is the least scheduled
                # then it is selected immediately.
                if (
                    compare[0] == Origin.FROM_SARIF
                    and compare[1] == len(key_priority) - 1
                ):
                    pick = compare + (i,)
                    break

                # Consider origin
                if compare[0] > pick[0]:
                    pick = compare + (i,)
                    continue

                # Consider schedule time of it's harness.
                if compare[0] == pick[0]:
                    if compare[1] > pick[1]:
                        pick = compare + (i,)
                        continue
        result: VulInfo = self._queue[pick[3]]
        del self._queue[pick[3]]
        self._key_counter[result.harness_id] += 1
        self._logger.info(f"Remaining Paths: {len(self._queue)}")
        return result

    @async_lock("_lock")
    async def update(self, path: VulInfo, status: Status) -> None:
        serialized: bytes = pickle.dumps(path)
        if serialized not in self._table:
            self._logger.warning(f"Path Not Found to Update [path={path}]")
            return
        self._table[serialized] = status
        self._logger.info(f"Path status is updated to [{status.name}]")

    def _add(self, path: VulInfo) -> None:
        serialized: bytes = pickle.dumps(path)
        if serialized in self._table:
            self._logger.warning(f"Path ignored [path={path}]")
            return
        self._table[serialized] = Status.UNKNOWN
        self._queue.append(path)
        if path.harness_id not in self._key_counter:
            self._key_counter[path.harness_id] = 0
        self._logger.info(f"Path updated[path={path}]")

    async def summary(self, path: Path) -> None:
        async def to_obj(task: VulInfo) -> dict:
            return {
                "sink": f"{task.v_point.path}:{task.v_point.line}",
                "path": [f"{x.path}:{x.line}" for x in task.v_paths[:-1]],
                "origin": [
                    x.name for x in (await SinkManager().get())[task.sink_id].origins
                ],
                "status": (await SinkManager().get_status(task.sink_id)).name,
            }

        result: list[dict] = [await to_obj(pickle.loads(x)) for x in self._table.keys()]
        async with aiofiles.open(path, mode="w") as f:
            await f.write(json.dumps(result, indent=4))
            await f.flush()
