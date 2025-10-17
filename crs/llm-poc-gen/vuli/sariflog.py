import logging
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Optional

from vuli.common.singleton import Singleton
from vuli.joern import Joern
from vuli.query_loader import QueryLoader
from vuli.struct import CodeLocation, SinkCandidate

logger = logging.getLogger(__name__)


@dataclass
class SarifLocation:
    uri: str
    start_line: int
    end_line: int = -1
    start_column: int = -1
    v_type: str = ""


class SarifLog(metaclass=Singleton):
    def __init__(self, data: dict):
        self.data = data
        self.sink_candidates: list[list[SinkCandidate]] = list()
        self.additional_candidates: list = list()
        self._logger = logging.getLogger("SarifLog")

    async def extract(self) -> dict:
        runs = self.data.get("runs", [])
        if not runs:
            return {}

        for run in runs:
            results = run.get("results", [])
            if not results:
                continue

            for result in results:
                await self._process_result(result)

        return self.sink_candidates, self.additional_candidates

    async def _process_result(self, result):
        v_type = result.get("ruleId")
        if not v_type:
            return

        for loc in result.get("locations", []):
            await self._process_location(loc, v_type)

    async def _process_location(self, loc, v_type):
        phys_loc = loc.get("physicalLocation", {})
        if not phys_loc:
            self._logger.warning(f"Missing physical location: {loc}")
            return

        sarif_loc = self._extract_location_info(phys_loc, v_type)

        if not sarif_loc:
            return

        if await self.get_sink_candidates(sarif_loc):
            return

        self._logger.error(
            f"Failed to locate by physical location: "
            f"[path] {sarif_loc.uri}, "
            f"[startLine] {sarif_loc.start_line}, "
            f"[endLine] {sarif_loc.end_line}, "
            f"[startColumn] {sarif_loc.start_column}"
        )

    async def get_sink_candidates(self, loc: SarifLocation):
        joern_query = self._build_joern_query(loc)
        if joern_query:
            if await self._process_joern_query(joern_query, loc):
                return True
        return False

    def _extract_location_info(
        self, phys_loc: dict, v_type: str
    ) -> Optional[SarifLocation]:
        uri = phys_loc.get("artifactLocation", {}).get("uri", "")
        region = phys_loc.get("region", {})
        start_line = region.get("startLine", -1)
        end_line = region.get("endLine", -1)
        start_column = region.get("startColumn", -1)

        if not uri or start_line == -1:
            self._logger.error(f"Incomplete physical location: {phys_loc}")
            return None

        if end_line > 0:
            start_column = -1
        else:
            end_line = start_line

        return SarifLocation(uri, start_line, end_line, start_column, v_type)

    def _build_joern_query(self, loc: SarifLocation):
        params = {
            "uri": loc.uri,
            "start_line": loc.start_line,
            "end_line": loc.end_line,
            "start_column": loc.start_column,
        }
        joern_query: str = QueryLoader().get("sink_from_sarif", **params)
        return joern_query

    async def _process_joern_query(self, joern_query: str, loc: SarifLocation) -> bool:
        self._logger.info(joern_query)
        joern_result = await Joern().run_query(joern_query)

        if not joern_result:
            return False

        uri = loc.uri
        v_type = loc.v_type
        start_line = loc.start_line
        start_column = loc.start_column

        for group in joern_result["originals"]:
            name = group["method"]
            filtering_unit = [
                SinkCandidate(
                    v_type,
                    (
                        CodeLocation(uri, loc["line"])
                        if loc["line"] == start_line
                        else CodeLocation(uri, loc["line"], start_column)
                    ),
                    name,
                    loc["id"],
                )
                for loc in group["locations"]
            ]
            self.sink_candidates.append(filtering_unit)

        for additional in joern_result["additionals"]:
            orig_method_name = additional["origMethodName"]
            new_uri = additional["newFilename"]
            nodes = additional["nodes"]

            name = nodes.get("method", "<unknown>")
            additional_unit = [
                SinkCandidate(
                    v_type,
                    (
                        CodeLocation(new_uri, loc["line"])
                        if loc["line"] == start_line
                        else CodeLocation(new_uri, loc["line"], start_column)
                    ),
                    name,
                    loc["id"],
                )
                for loc in nodes["locations"]
            ]
            self.additional_candidates.append(
                {"match": orig_method_name, "candidates": additional_unit}
            )

        return True
