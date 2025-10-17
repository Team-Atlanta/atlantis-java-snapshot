import asyncio
import logging
from enum import Enum
from typing import Optional

from pydantic import BaseModel

from vuli.common.decorators import async_lock
from vuli.common.singleton import Singleton


class SinkStatus(Enum):
    UNKNOWN = 0
    UNEXPLOITABLE = 1
    MAY_UNREACHABLE = 2
    MAY_REACHABLE = 3
    REACHABLE = 4
    EXPLOITABLE = 5


class Origin(Enum):
    FROM_INSIDE = 0
    FROM_CRS = 1
    FROM_DELTA = 2
    FROM_SARIF = 3


class SinkProperty(BaseModel):
    bug_types: set[str] = set()
    harnesses: set[str] = set()
    origins: set[Origin] = set({Origin.FROM_INSIDE})
    status: SinkStatus = SinkStatus.UNKNOWN

    def __str__(self) -> str:
        return f"(bug_types:{",".join(self.bug_types)}, origins:{",".join([x.name for x in self.origins])}, harnesses:{",".join(self.harnesses)}, status:{self.status.name})"


class SinkManager(metaclass=Singleton):
    def __init__(self):
        self._logger = logging.getLogger("SinkManager")
        self._lock = asyncio.Lock()
        self._table: dict[int, SinkProperty] = {}

    @async_lock("_lock")
    async def add_batch(self, sinks: dict[int, SinkProperty]) -> None:
        for id, property in sinks.items():
            self._add((id, property))

    @async_lock("_lock")
    async def add(self, sink: tuple[int, SinkProperty]) -> None:
        self._add(sink)

    @async_lock("_lock")
    async def clear(self) -> None:
        self._table.clear()

    @async_lock("_lock")
    async def get_bug_types(self, id: int) -> set[str]:
        if id not in self._table:
            self._logger.warning(f"Sink Not Found [id={id}]")
            return {}
        return self._table[id].bug_types

    @async_lock("_lock")
    async def get_origin(self, id: int) -> Optional[Origin]:
        if id not in self._table:
            self._logger.warning(f"Sink Not Found [id={id}]")
            return None
        origins = self._table[id].origins
        if len(origins) == 0:
            self._logger.warning(
                f"Origin Not Found [id={id}, property={self._table[id]}]"
            )
            return None
        return max(origins, key=lambda x: x.value)

    @async_lock("_lock")
    async def get_status(self, id: int) -> SinkStatus:
        if id not in self._table:
            return SinkStatus.UNKNOWN
        return self._table[id].status

    @async_lock("_lock")
    async def get(self) -> dict[int, SinkProperty]:
        return self._table

    @async_lock("_lock")
    async def get_sink(self, id: int) -> Optional[SinkProperty]:
        return self._table.get(id, None)

    @async_lock("_lock")
    async def update_status(self, id: int, status: SinkStatus) -> None:
        if id not in self._table:
            self._logger.warning(f"Sink Not Found [id={id}]")
            return
        if self._table[id].status.value >= status.value:
            return
        self._table[id].status = status
        self._logger.info(f"Sink status changed [sink={id}, status={status}]")

    def _add(self, sink: tuple[int, SinkProperty]) -> None:
        id, property = sink
        if id not in self._table:
            self._table[id] = property
            self._logger.info(f"New Sink [id={id}, property={property}]")
            return

        new_bug_types: set[str] = property.bug_types - self._table[id].bug_types
        new_harnesses: set[str] = property.harnesses - self._table[id].harnesses
        new_origins: set[str] = property.origins - self._table[id].origins
        new_status: Optional[SinkStatus] = (
            property.status
            if property.status.value > self._table[id].status.value
            else None
        )

        messages: list[str] = []
        if len(new_bug_types) > 0:
            messages.append(f"new_bug_types={",".join(new_bug_types)}")
            self._table[id].bug_types |= new_bug_types
        if len(new_harnesses) > 0:
            messages.append(f"new_harnesses={",".join(new_harnesses)}")
            self._table[id].harnesses |= new_harnesses
        if len(new_origins) > 0:
            messages.append(f"new_origins={",".join([x.name for x in new_origins])}")
            self._table[id].origins |= new_origins
        if new_status is not None:
            messages.append(f"new_status={new_status.name}")
            self._table[id].status = new_status

        if len(messages) == 0:
            return
        self._logger.info(f"Updated Sink [id={id}, {", ".join(messages)}]")
