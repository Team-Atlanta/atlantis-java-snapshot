import json
import logging
import os
from pathlib import Path
import sys

from .challenge import CP, CP_Harness
from .util import SharedFile, get_env

__all__ = ["Config"]

NODE_IDX = "NODE_IDX"
NODE_CNT = "NODE_CNT"
MAIN_IDX = 0


def get_env_int(key: str) -> int:
    value = get_env(key, must_have=True)
    try:
        return int(value)
    except ValueError:
        logging.error(f"Invalid {key}: {value}")
        sys.exit(-1)


def get_conf_path(shared_dir: Path, node_idx: int):
    return shared_dir / f"{node_idx}.config"


def distribute(L: list, n: int) -> list[list]:
    """
    Distribute items from one list across N new lists, as evenly as
    possible.
    Raises ValueError if n is 0.
    https://stackoverflow.com/a/54802737

    >>> items = list('abcdefg')
    >>> for i in range(8): print(distribute(items[:i], 3))
    [[], [], []]
    [['a'], [], []]
    [['a'], ['b'], []]
    [['a'], ['b'], ['c']]
    [['a', 'b'], ['c'], ['d']]
    [['a', 'b'], ['c', 'd'], ['e']]
    [['a', 'b'], ['c', 'd'], ['e', 'f']]
    [['a', 'b', 'c'], ['d', 'e'], ['f', 'g']]
    """
    if n == 0:
        raise ValueError
    out = []
    d, r = divmod(len(L), n)
    for i in range(n):
        si = (d + 1) * (i if i < r else r) + d * (0 if i < r else i - r)
        out.append(L[si : si + (d + 1 if i < r else d)])
    return out


def distribute_min_1(L: list, n: int) -> list[list]:
    """
    A version of distribute() that ensures that each list receives at
    least one element, even if that means duplicating some of them.
    Raises ValueError if L is empty or n is 0.

    >>> items = list('abcdefg')
    >>> for i in range(1, 8): print(distribute_min_1(items[:i], 3))
    [['a'], ['a'], ['a']]
    [['a'], ['b'], ['a']]
    [['a'], ['b'], ['c']]
    [['a', 'b'], ['c'], ['d']]
    [['a', 'b'], ['c', 'd'], ['e']]
    [['a', 'b'], ['c', 'd'], ['e', 'f']]
    [['a', 'b', 'c'], ['d', 'e'], ['f', 'g']]
    >>> print(distribute_min_1(['a', 'b', 'c'], 8))
    [['a'], ['b'], ['c'], ['a'], ['b'], ['c'], ['a'], ['b']]
    """
    if not L:
        raise ValueError

    lists = distribute(L, n)

    # If we find an empty list, add a duplicate of the first element of
    # L the first time, the second element of L the second time, and so
    # on -- looping back to the start of L if we reach the end of it
    next_idx_to_copy = 0
    for sublist in lists:
        if not sublist:
            sublist.append(L[next_idx_to_copy])
            next_idx_to_copy = (next_idx_to_copy + 1) % len(L)

    return lists


class Config:
    def log(self, msg: str):
        logging.info(f"[Config] {msg}")

    def __init__(self, node_idx: int | None = None, node_cnt: int | None = None):
        self.modules: list[str] | None = None
        self.target_cps: list[str] | None = None
        self.target_harnesses: list[str] | None = None
        self.debug: bool = False
        self.test: bool = bool(os.environ.get("CRS_TEST"))
        self.test_wo_harness: bool = (
            os.environ.get("CRS_TEST_WO_HARNESS", "True") == "True"
        )
        self.ncpu: int = os.cpu_count()
        if os.environ.get("N_CPU"):
            self.ncpu = int(os.environ.get("N_CPU"))
        self.n_llm_lock: int = 3
        self.llm_limit: int = 70
        self.llm_on = True
        self.node_idx: int = node_idx if node_idx is not None else get_env_int(NODE_IDX)
        self.node_cnt: int = node_cnt if node_cnt is not None else get_env_int(NODE_CNT)
        self.others = {}

    def load(self, conf_path: Path | str):
        if isinstance(conf_path, str):
            conf_path = Path(conf_path)
        if not conf_path.exists():
            return self
        with open(conf_path) as f:
            config = json.load(f)
        for key in vars(self):
            if key in config:
                setattr(self, key, config[key])
        self.ncpu = int(self.ncpu)
        env_ncpu = os.cpu_count()
        if env_ncpu < self.ncpu:
            self.ncpu = env_ncpu
        self.n_llm_lock = int(self.n_llm_lock)
        self.llm_limit = int(self.llm_limit)
        return self

    def is_module_on(self, module_name: str) -> bool:
        return self.modules is None or module_name in self.modules

    def is_main(self):
        return self.node_idx == MAIN_IDX

    def is_worker(self):
        return not self.is_main()

    def distribute(self, cp: CP, shared_dir: Path):
        if self.is_main():
            self.__distribute_job(cp, shared_dir)
        else:
            self.__load_job(shared_dir)

    def __distribute_job(self, cp: CP, shared_dir: Path):
        self.log(f"Distribute jobs into {self.node_cnt} nodes")
        if self.node_cnt == 1:
            return
        harness_names = [
            x.name for x in cp.harnesses.values() if self.is_target_harness(x)
        ]
        self.log(f"Total jobs: {len(harness_names)}")
        jobs = distribute_min_1(harness_names, self.node_cnt)
        self.target_harnesses = jobs[0]
        self.log(f"idx: 0, jobs: {jobs[0]}")
        for idx in range(1, self.node_cnt):
            data = {"target_harnesses": jobs[idx]}
            self.log(f"idx: {idx}, jobs: {jobs[idx]}")
            self.__save_job(shared_dir, idx, data)

    def __save_job(self, shared_dir: Path, idx: int, data: dict[str, list[str]]):
        conf = get_conf_path(shared_dir, idx)
        SharedFile(conf).write(bytes(json.dumps(data), "utf-8"))

    def __load_job(self, shared_dir: Path):
        conf = get_conf_path(shared_dir, self.node_idx)
        self.log(f"Load job conf at {conf}")
        SharedFile(conf).wait()
        self.load(conf)

    def is_target_harness(self, harness: CP_Harness):
        if self.target_harnesses is None:
            return True
        return harness.name in self.target_harnesses
