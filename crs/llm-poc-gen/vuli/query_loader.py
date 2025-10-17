import logging
from pathlib import Path

import yaml

from vuli.common.singleton import Singleton


class QueryLoader(metaclass=Singleton):

    def __init__(self):
        self._logger = logging.getLogger("QueryLoader")
        self._queries = None

    def load(self, path: Path) -> None:
        with path.open() as f:
            self._queries = yaml.safe_load(f)

    def get(self, key, **kwargs) -> str:
        if self._queries is None:
            self._logger.warning("Not Loaded")
            return ""

        val = self._queries.get(key)
        if val is None:
            self._logger.warning(f"Query '{key}' not found.")
            return ""
        return val.format(**kwargs) if kwargs else val
