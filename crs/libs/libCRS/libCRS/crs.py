from abc import ABC, abstractmethod
import asyncio
import json
import logging
import os
from pathlib import Path
import random
import time

from .challenge import CP, CP_Harness
from .config import Config
from .util import (
    BAR,
    async_cp,
    get_env,
    set_env,
    async_run_cmd,
    AsyncNamedLocks,
)

__all__ = ["CRS", "HarnessRunner"]


async def async_get_llm_spend(interval=10, N=3, timeout=10):
    llm_url = os.environ.get("AIXCC_LITELLM_HOSTNAME")
    llm_key = os.environ.get("LITELLM_KEY")
    if llm_url is None or llm_key is None:
        return 0
    cmd = ["curl", f"{llm_url}/key/info?key={llm_key}", "-X", "GET"]
    cmd += ["-H", f"Authorization: Bearer {llm_key}"]
    for i in range(N):
        ret = await async_run_cmd(cmd, timeout=timeout)
        try:
            ret = json.loads(ret.stdout.decode("utf-8", errors="ignore"))
            return ret["info"]["spend"]
        except Exception:
            await asyncio.sleep(interval)
    logging.info("Fail to get llm spend..")
    return 0


class CRS(ABC):
    def __init__(
        self,
        name: str,
        hrunner_class,
        config: Config,
        cp: CP,
        workdir: Path | None = None,
    ):
        self.name = name
        self.hrunner_class = hrunner_class
        self.config = config
        self.cp = cp
        if workdir is None:
            workdir = Path(os.environ.get("CRS_WORKDIR", "/crs-workdir/"))
        self.workdir = workdir / f"worker-{config.node_idx}"
        set_env("CRS_WORKDIR", str(self.workdir))
        set_env("TARGET_CP", str(self.cp.name))
        set_env("START_TIME", str(int(time.time())))
        set_env("CP_PROJ_PATH", str(cp.proj_path))
        set_env("CP_SRC_PATH", str(cp.cp_src_path))

        self.target_harnesses = []
        for harness in self.cp.harnesses.values():
            if self.config.is_target_harness(harness):
                self.target_harnesses.append(harness)

        self.modules = self._init_modules()
        for m in self.modules:
            setattr(self, m.name, m)
        self.prepared = False
        self.submitted = {}
        self.__check_config()

        for m in self.modules:
            if m.is_on():
                m._init()

        self.commit_hints: Path | None = None
        self.llm_lock: asyncio.Semaphore | None = None
        self.llm_init_spend: int = asyncio.run(async_get_llm_spend())
        self.__async_named_locks = AsyncNamedLocks()
        self.hrunners = []

    def log(self, msg: str):
        logging.info(f"[{self.name}-{self.config.node_idx}] {msg}")

    def error(self, msg: str):
        logging.error(f"[{self.name}-{self.config.node_idx}] {msg}")
        exit(-1)

    def __check_config(self):
        self.log(BAR())
        self.log("Running options:")
        self.log(f"Target CP: {self.cp.name}")
        self.log(f"Test Mode: {self.config.test}")
        self.log(f"# of cores: {self.config.ncpu}")
        self.log(f"# of llm_lock: {self.config.n_llm_lock}")
        self.log(f"llm_limit: {self.config.llm_limit}")
        self.log(f"node_cnt: {self.config.node_cnt}")
        self.log(f"node_idx: {self.config.node_idx}")
        self.log(
            f"Target Harness: {list(map(lambda x: x.name, self.target_harnesses))}"
        )
        self.log(f"Others: {self.config.others}")
        for m in self.modules:
            msg = "ON" if m.is_on() else "OFF"
            self.log(f"{m.name}: {msg}")
        sanitizer = get_env("SANITIZER")
        self.log(f"Sanitizer: {sanitizer}")
        self.log(BAR())
        if sanitizer in [None, ""]:
            self.error("SANITIZER should be set in env")

    async def async_get_lock(self, name: str):
        return await self.__async_named_locks.async_get_lock(name)

    async def async_llm_total_spend(self):
        spend = await async_get_llm_spend()
        return spend - self.llm_init_spend

    async def async_in_llm_limit(self):
        spend = await self.async_llm_total_spend()
        return spend < self.config.llm_limit

    def get_workdir(self, name: str) -> Path:
        workdir = self.workdir / name
        os.makedirs(workdir, exist_ok=True)
        return workdir

    async def async_cp_to_workdir(self, src: Path) -> Path:
        dst = self.workdir / src.name
        await async_cp(src, dst)
        return dst

    def set_commit_hints(self, commit_hints: Path):
        self.commit_hints = commit_hints

    def is_submitted(self, harness: CP_Harness, pov_path: Path):
        if not pov_path.exists():
            return True
        key = (harness.name, pov_path.read_bytes())
        if key in self.submitted:
            return True
        self.submitted[key] = True
        return False

    async def async_submit_pov(
        self,
        harness: CP_Harness,
        pov_path: Path,
        sanitizer_output_hash: str = "",
        finder: str = "",
    ):
        if self.is_submitted(harness, pov_path):
            return
        cmd = ["python3", "-m", "libCRS.submit", "submit_vd"]
        cmd += ["--harness", harness.name]
        cmd += ["--pov", pov_path]
        if sanitizer_output_hash:
            cmd += ["--sanitizer-output", sanitizer_output_hash]
        if finder:
            cmd += ["--finder", finder]
        logging.info(f"[{harness.name}][{finder}] Submit pov at {pov_path}")
        await async_run_cmd(cmd, timeout=60)

    def submit_pov(
        self,
        harness: CP_Harness,
        pov_path: Path,
        sanitizer_output_hash: str = "",
        finder: str = "",
    ):
        return asyncio.run(
            self.async_submit_pov(harness, pov_path, sanitizer_output_hash, finder)
        )

    async def async_precompile(self):
        cmd = ["python3", "-m", "libCRS.submit", "precompile"]
        if self.commit_hints:
            cmd += ["--commit-hints-file", self.commit_hints]
        await async_run_cmd(cmd, timeout=60)

    async def _async_check_vapi_result(self, remove_rejected: bool):
        cmd = ["python3", "-m", "libCRS.submit", "check"]
        if remove_rejected:
            cmd += ["--remove-rejected"]
        while True:
            await asyncio.sleep(60)
            await async_run_cmd(cmd, timeout=60)

    async def async_wait_prepared(self):
        while not self.prepared:
            await asyncio.sleep(1)

    def wait_prepared(self):
        return asyncio.run(self.async_wait_prepared())

    async def async_prepare_modules(self):
        for m in self.modules:
            await m.async_prepare()

    async def __async_prepare(self):
        await self._async_prepare()
        self.prepared = True

    def alloc_cpu(self, hrunners: list["HarnessRunner"]):
        total = self.config.ncpu
        cnt = len(hrunners)
        avg = int(total / cnt)
        mores = random.sample(range(cnt), total % cnt)
        for hrunner in hrunners:
            hrunner.set_ncpu(avg)
        for idx in mores:
            hrunners[idx].set_ncpu(avg + 1)
        core_id = int(os.environ.get("START_CORE_ID", "0"))
        for hrunner in hrunners:
            hrunner.set_core_id(core_id)
            core_id += hrunner.ncpu

    async def async_run(self, remove_rejected: bool = False):
        self.llm_lock = asyncio.Semaphore(self.config.n_llm_lock)
        jobs = [self.__async_prepare()]
        hrunners = []
        for harness in self.cp.harnesses.values():
            if not self.config.is_target_harness(harness):
                continue
            hrunners.append(self.hrunner_class(harness, self))
        self.hrunners = hrunners
        self.alloc_cpu(hrunners)
        for hrunner in hrunners:
            jobs.append(hrunner.async_run())
        watchdogs = [
            self._async_watchdog(),
            self._async_check_vapi_result(remove_rejected),
        ]
        watchdogs = list(map(asyncio.create_task, watchdogs))
        try:
            await asyncio.gather(*jobs)
            for watchdog in watchdogs:
                watchdog.cancel()
        except asyncio.CancelledError:
            pass

    def run(self, remove_rejected: bool = False):
        if os.environ.get("RUN_SHELL") != None:
            os.system("bash")
        else:
            asyncio.run(self.async_run(remove_rejected))

    @abstractmethod
    async def _async_prepare(self):
        pass

    @abstractmethod
    async def _async_watchdog(self):
        pass

    @abstractmethod
    def _init_modules(self) -> list["Module"]:
        pass


class HarnessRunner(ABC):
    def __init__(self, harness: CP_Harness, crs: CRS):
        self.crs = crs
        self.harness = harness
        self.workdir = self.crs.get_workdir(f"HarnessRunner/{self.crs.cp.name}/{self.harness.name}")
        self.ncpu = None
        self.core_ids = None

    def set_ncpu(self, ncpu: int):
        self.ncpu = ncpu

    def set_core_id(self, core_id):
        self.core_ids = list(range(core_id, core_id + self.ncpu))

    def log(self, msg: str):
        logging.info(f"[{self.harness.name}] {msg}")

    def get_workdir(self, name: str) -> Path:
        ret = self.workdir / name
        os.makedirs(ret, exist_ok=True)
        return ret

    async def async_submit_pov(
        self, pov_path: Path, sanitizer_output_hash: str = "", finder: str = ""
    ):
        return await self.crs.async_submit_pov(
            self.harness, pov_path, sanitizer_output_hash, finder
        )

    def submit_pov(
        self, pov_path: Path, sanitizer_output_hash: str = "", finder: str = ""
    ):
        return asyncio.run(
            self.async_submit_pov(pov_path, sanitizer_output_hash, finder)
        )

    async def async_submit_povs(self, pov_dir: Path, finder: str = ""):
        for pov in pov_dir.iterdir():
            await self.crs.async_submit_pov(self.harness, pov, finder=finder)

    async def async_loop_submit_povs(self, pov_dir: Path, finder: str = ""):
        try:
            while True:
                await asyncio.sleep(10)
                await self.async_submit_povs(pov_dir, finder)
        except asyncio.CancelledError:
            await self.async_submit_povs(pov_dir, finder)

    @abstractmethod
    async def async_run(self):
        pass
