import logging
from dataclasses import dataclass
from pathlib import Path

import toml

from vuli.common.singleton import Singleton


@dataclass(frozen=True)
class Target:
    harness_name: str | list[str]
    path: str
    line: int


class Dev(metaclass=Singleton):
    def __init__(self):
        self._logger = logging.getLogger("Dev")
        self._targets: set[Target] = set()

    def load(self, path: Path):
        if not path.exists():
            self._logger.warning("Configuration for Dev not found: Skip")
            return

        with path.open("r") as f:
            root: dict = toml.load(f)

        self._targets = []
        for cpv in root.values():
            for location in cpv.values():
                if isinstance(location["harness"], list):
                    for harness in location["harness"]:
                        self._targets.append(
                            Target(harness, location["path"], location["line"])
                        )
                else:
                    self._targets.append(
                        Target(location["harness"], location["path"], location["line"])
                    )

    def is_target(self, harness_name: str, path: str, line: int) -> bool:
        return Target(harness_name, path, line) in self._targets
