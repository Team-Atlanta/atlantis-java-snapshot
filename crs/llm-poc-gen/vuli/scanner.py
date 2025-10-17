import logging

from vuli.blackboard import Blackboard
from vuli.common.decorators import SEVERITY, async_safe
from vuli.joern import Joern
from vuli.sink import Origin, SinkManager, SinkProperty, SinkStatus
from vuli.struct import Sanitizer
from vuli.task import TaskHandler


class Scanner(TaskHandler):
    def __init__(self):
        self._logger = logging.getLogger("Scanner")

    async def run(self, sanitizers: list[Sanitizer]) -> None:
        [await self._run_per_sanitizer(sanitizer.name) for sanitizer in sanitizers]
        await Blackboard().save()

    @async_safe([], SEVERITY.ERROR, "Scanner")
    async def _run_per_sanitizer(self, name: str) -> None:
        self._logger.info(f"Scan Start[name={name}]")
        sink_name: str = Joern().get_sink_name(name)
        query: str = f"""
{sink_name}
    .whereNot(_.method.filename(".*/src/test/.*"))
    .whereNot(_.method.filenameExact("<empty>"))
    .map(x => Map("id" -> x.id, "unexploitable" -> check_constant(x)))
    .l
"""
        result: list[dict] = await Joern().run_query(query, 600)
        unexploitable: int = [
            src for src in result if bool(src["unexploitable"]) is True
        ]
        self._logger.info(
            f"Scan Finished [result={len(result)}, unexploitable={len(unexploitable)}, name={name}]"
        )
        if len(result) == 0:
            return

        @async_safe(None, SEVERITY.ERROR, "Scanner")
        async def add_as_property(src: dict) -> None:
            id: int = int(src["id"])
            unexploitable: bool = bool(src["unexploitable"])
            property = SinkProperty(
                bug_types=set({name}),
                origins=set({Origin.FROM_INSIDE}),
                status=(
                    SinkStatus.UNEXPLOITABLE
                    if unexploitable is True
                    else SinkStatus.UNKNOWN
                ),
            )
            await SinkManager().add((id, property))

        [await add_as_property(data) for data in result]
