#!/usr/bin/env python3
import asyncio
import base64
import hashlib
import json
import os
import queue
import random
import shlex
import traceback
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncGenerator, Dict, List, Optional, Set

import aiofiles
import atomics
from libCRS import CRS, HarnessRunner, Module, util
from pydantic import BaseModel, Field, field_validator
from watchdog.events import FileClosedEvent, FileMovedEvent, FileSystemEventHandler
from watchdog.observers import Observer

from .base_objs import BeepSeed, InsnCoordinate
from .jazzer import is_beep_mode_on
from .sinkmanager import SinkUpdateEvent
from .utils import (
    CRS_ERR_LOG,
    CRS_WARN_LOG,
    atomic_write_file,
    get_env_exports,
    run_process_and_capture_output,
)

CRS_ERR = CRS_ERR_LOG("concolic-mod")
CRS_WARN = CRS_WARN_LOG("concolic-mod")


class ConcolicExecutorParams(BaseModel):
    enabled: bool = Field(
        ..., description="**Mandatory**, true/false to enable/disable this module."
    )
    num_instance: int = Field(
        1, description="Number of instances concolic server maintains per harness."
    )
    max_xms: int = Field(
        8192,
        description="Maximum heap size for the concolic server (in MB).",
    )
    max_mem: int = Field(
        16384,
        description="Maximum memory for the concolic server (in MB).",
    )
    generators: List[str] = Field(
        ...,
        description="**Mandatory**, list of concolic request generators to use. Valid values: 'dummy-seed', 'local_dir', 'new-cov-seed', 'beepseed'.",
    )
    debug: bool = Field(
        False,
        description="Enable debugging mode. When enabled, writes requests to debug_dir.",
    )
    exec_timeout: int = Field(
        1200,
        description="Timeout for one round execution of the target harness in concolic engine (in seconds).",
    )

    @field_validator("enabled")
    def enabled_should_be_boolean(cls, v):
        if not isinstance(v, bool):
            raise ValueError("enabled must be a boolean")
        return v

    @field_validator("num_instance")
    def num_instance_should_be_positive(cls, v):
        if v <= 0:
            raise ValueError("num_instance must be a positive integer")
        return v

    @field_validator("max_xms", "max_mem")
    def max_xms_n_mem_should_be_positive(cls, v, field):
        if v <= 0:
            raise ValueError("max_xms and max_mem must be a positive integer")
        return v

    @field_validator("generators")
    def generators_should_be_valid(cls, v):
        # Define valid generators directly to avoid circular imports
        valid_generators = ["dummy-seed", "local_dir", "new-cov-seed", "beepseed"]

        if not isinstance(v, list) or not v:
            raise ValueError("generators must be a non-empty list of strings")

        if len(v) != len(set(v)):
            raise ValueError("generators must not contain duplicates")

        for gen in v:
            if gen not in valid_generators:
                raise ValueError(
                    f"Invalid generator: {gen}. Valid generators are: {valid_generators}"
                )

        return v


class RespDirWatcher(FileSystemEventHandler):
    """Watcher for concolic response directory."""

    def __init__(self, module, hrunner, resp_dir, resp_queue):
        super().__init__()
        self.module = module
        self.hrunner = hrunner
        self.resp_dir = resp_dir
        self.resp_queue = resp_queue
        self.observer = None

    def start(self):
        self.observer = Observer()
        self.observer.schedule(self, str(self.resp_dir), recursive=False)
        self.observer.start()
        self.module.logH(
            self.hrunner,
            f"Started watching response dir {self.resp_dir} for '{self.hrunner.harness.name}'",
        )

    def stop(self):
        if not self.observer:
            return

        try:
            self.observer.stop()
            self.observer.join(timeout=1.0)
            self.module.logH(
                self.hrunner,
                f"Stopped watching response dir {self.resp_dir} for '{self.hrunner.harness.name}'",
            )
        except Exception as e:
            self.module.logH(
                self.hrunner,
                f"{CRS_ERR} stopping watcher for {self.resp_dir}: {str(e)} {traceback.format_exc()}",
            )
        finally:
            self.observer = None

    def on_closed(self, event):
        resp_path = Path(event.src_path)
        if not resp_path.is_file():
            return

        self.resp_queue.put(resp_path)


@dataclass
class ConcolicReq:
    class_name: str
    method_name: str
    method_desc: str
    base64_blob: str
    bytes_blob: bytes
    gen_label: str

    @classmethod
    async def frm_json(cls, file_path: Path, label: str) -> "ConcolicReq":
        """Load a ConcolicReq from a JSON file."""
        async with aiofiles.open(file_path, "r") as f:
            data = await f.read()
            json_data = json.loads(data)
            base64_blob = json_data["blob"]
            bytes_blob = base64.b64decode(base64_blob)
            return cls(
                class_name=json_data["class_name"],
                method_name=json_data["method_name"],
                method_desc=json_data["method_desc"],
                base64_blob=base64_blob,
                bytes_blob=bytes_blob,
                gen_label=label,
            )

    @classmethod
    async def frm_blob(cls, file_path: Path, label: str) -> "ConcolicReq":
        """Load a ConcolicReq from a blob file."""
        async with aiofiles.open(file_path, "rb") as f:
            bytes_blob = await f.read()
            base64_blob = base64.b64encode(bytes_blob).decode("utf-8", errors="ignore")
            return cls(
                class_name="",
                method_name="",
                method_desc="",
                base64_blob=base64_blob,
                bytes_blob=bytes_blob,
                gen_label=label,
            )

    @classmethod
    def frm_bytes(cls, data: bytes, label: str) -> "ConcolicReq":
        """Load a ConcolicReq from bytes."""
        return cls(
            class_name="",
            method_name="",
            method_desc="",
            base64_blob=base64.b64encode(data).decode("utf-8", errors="ignore"),
            bytes_blob=data,
            gen_label=label,
        )

    @classmethod
    async def frm_beepseed(
        cls, crs: CRS, beepseed: BeepSeed, label: str
    ) -> List["ConcolicReq"]:
        """Load a ConcolicReq from a beepseed."""
        reqs, coords, the_bytes = [], [], None

        for frame in beepseed.stack_trace:
            coord = crs.query_code_coord(frame["class_name"], frame["line_num"])
            if coord:
                coords.append(coord)

        the_bytes = beepseed.get_bytes()

        for coord in coords:
            base64_blob = base64.b64encode(the_bytes).decode("utf-8", errors="ignore")
            reqs.append(
                cls(
                    class_name=coord.class_name,
                    method_name=coord.method_name,
                    method_desc=coord.method_desc,
                    base64_blob=base64_blob,
                    bytes_blob=the_bytes,
                    gen_label=label,
                )
            )

        return reqs

    async def to_file(self, dir_path: Path):
        """Write the request to a file in JSON format."""
        file_name = hashlib.sha1(self.bytes_blob).hexdigest()
        file_path = dir_path / f"{self.gen_label}-{file_name}.json"
        await atomic_write_file(
            file_path,
            json.dumps(
                {
                    "class_name": self.class_name,
                    "method_name": self.method_name,
                    "method_desc": self.method_desc,
                    "blob": self.base64_blob,
                },
                indent=2,
            ),
        )


class ReqGenBase(ABC):
    """Base class for concolic request generators."""

    @abstractmethod
    async def __aenter__(self):
        """Initialize the request generator."""
        raise NotImplementedError("Subclasses must implement this method")

    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up the request generator."""
        raise NotImplementedError("Subclasses must implement this method")

    @abstractmethod
    async def try_get_next(self) -> AsyncGenerator[ConcolicReq, None]:
        """Try to get the next concolic request, return None if not available."""
        raise NotImplementedError("Subclasses must implement this method")

    @abstractmethod
    def stat(self) -> str:
        """Return the status of the request generator."""
        raise NotImplementedError("Subclasses must implement this method")


class DirMonitorReqGen(ReqGenBase):

    GEN_LABEL = "local_dir"
    CONCOLIC_TEST_INPUT_DIR = Path("/eva/concolic")

    class FileMonitor(FileSystemEventHandler):

        def __init__(self, queue: queue.Queue, watch_dir: Path):
            super().__init__()
            self.queue = queue
            self.watch_dir = watch_dir

        def on_closed(self, event: FileClosedEvent):
            if not event.is_directory:
                self.queue.put(Path(event.src_path))

        def on_moved(self, event: FileMovedEvent):
            if not event.is_directory:
                dest_path = Path(event.dest_path)
                if dest_path.parent == self.watch_dir:
                    self.queue.put(dest_path)

    def __init__(
        self, logger, crs: CRS, hrunner: HarnessRunner, req_src_dirs: List[Path] = None
    ):
        self.logger = logger
        self.crs = crs
        self.hrunner = hrunner
        self.queue = queue.Queue()
        self.processed_files = set()
        self.req_src_dirs = (
            req_src_dirs
            if req_src_dirs
            else [self.CONCOLIC_TEST_INPUT_DIR / hrunner.harness.name]
        )
        self._running = atomics.atomic(width=4, atype=atomics.INT)
        self._running.store(0)

    async def __aenter__(self):
        for req_src_dir in self.req_src_dirs:
            req_src_dir.mkdir(parents=True, exist_ok=True)

        self.observer = Observer()
        self.event_handlers = []
        for req_src_dir in self.req_src_dirs:
            handler = self.FileMonitor(self.queue, req_src_dir)
            self.observer.schedule(handler, str(req_src_dir), recursive=False)
            self.event_handlers.append(handler)

        self.observer.start()
        for req_src_dir in self.req_src_dirs:
            for existing_file in req_src_dir.glob("*"):
                if existing_file.is_file():
                    self.queue.put(existing_file)

        self._running.store(1)
        monitored_dirs_str = ", ".join(str(d) for d in self.req_src_dirs)
        self.logger(f"Started monitoring directories: {monitored_dirs_str}")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._running.store(0)
        self.observer.stop()
        self.observer.join()

    async def _handle_next_file(
        self, next_file: Path
    ) -> AsyncGenerator[ConcolicReq, None]:
        try:
            if next_file.suffix == ".json":
                req = await ConcolicReq.frm_json(next_file, self.GEN_LABEL)
                yield req
            else:
                req = await ConcolicReq.frm_blob(next_file, self.GEN_LABEL)
                yield req
        except Exception as e:
            self.logger(
                f"Error in _handle_next_file {next_file}: {e}\n {traceback.format_exc()}"
            )

    async def try_get_next(self) -> AsyncGenerator[ConcolicReq, None]:
        while self._running.load() == 1:
            try:
                next_file = self.queue.get_nowait()
                self.queue.task_done()

                if next_file in self.processed_files:
                    # Skip already processed files
                    continue
                self.processed_files.add(next_file)

                async for req in self._handle_next_file(next_file):
                    yield req

            except queue.Empty:
                # No any new file can be handled in the queue
                yield None

            except Exception as e:
                self.logger(
                    f"Error reading file {next_file}: {e}\n {traceback.format_exc()}"
                )
                continue

    def stat(self) -> str:
        status = "DirMonitorReqGen Status:\n"
        status += "  - Watching directories:\n"
        for src_dir in self.req_src_dirs:
            status += f"      - {src_dir}\n"
        status += f"  - Processed files: {len(self.processed_files)}\n"
        return status


class BeepSeedReqGen(DirMonitorReqGen):

    GEN_LABEL = "beepseed"

    def __init__(
        self, logger, crs: CRS, hrunner: HarnessRunner, beepseed_dirs: List[Path] = None
    ):
        self.beepseed_dirs = beepseed_dirs if beepseed_dirs else []
        self.crs = crs
        self.hrunner = hrunner
        super().__init__(logger, crs, hrunner, beepseed_dirs)

    @classmethod
    async def _get_all_beepseed_dirs(
        cls, logger, crs: CRS, hrunner: HarnessRunner
    ) -> List[Path]:
        beep_jazzer_mods = [mod for mod in crs.modules if is_beep_mode_on(mod)]

        if not beep_jazzer_mods:
            logger("Jazzer modules with beep mode enabled not found")
            return []

        logger(f"Found {len(beep_jazzer_mods)} beep jazzer mods: {beep_jazzer_mods}")

        all_beepseed_dirs = []
        for mod in beep_jazzer_mods:
            beepseed_dirs = await mod.get_expected_beepseed_dir(hrunner)
            for beepseed_dir in beepseed_dirs:
                # N.B. Fuzzer may not be ready now, guarantee dir existence
                beepseed_dir.parent.mkdir(parents=True, exist_ok=True)
                all_beepseed_dirs.append(beepseed_dir)

        logger(f"Found {len(all_beepseed_dirs)} beepseed dirs: {all_beepseed_dirs}")
        return all_beepseed_dirs

    @classmethod
    async def create(cls, logger, crs: CRS, hrunner: HarnessRunner):
        """Create an instance of BeepSeedReqGen."""
        beepseed_dirs = await cls._get_all_beepseed_dirs(logger, crs, hrunner)
        return cls(logger, crs, hrunner, beepseed_dirs)

    async def try_get_next(self) -> AsyncGenerator[ConcolicReq, None]:
        beepseeds = defaultdict(lambda: defaultdict(set))
        processed_bs = set()
        while self._running.load() == 1:
            # 1.1 load all files in current queue
            while True:
                try:
                    next_file = self.queue.get_nowait()
                    self.queue.task_done()
                    if (
                        next_file.name == "xcode.json"
                        or next_file.name.startswith(".")
                        or next_file in self.processed_files
                    ):
                        # Skip already processed files
                        continue
                    self.processed_files.add(next_file)

                    bs = await BeepSeed.frm_beep_file(next_file)
                    if bs not in processed_bs:
                        beepseeds[bs.coord][bs.stack_hash].add(bs)
                except queue.Empty:
                    break
                except Exception as e:
                    self.logger(
                        f"Error reading file {next_file}: {e}\n {traceback.format_exc()}"
                    )
                    continue
            # 1.2 load beepseeds from outside
            for bs in await self.crs.concolic.get_beepseeds(self.hrunner.harness.name):
                if bs not in processed_bs:
                    beepseeds[bs.coord][bs.stack_hash].add(bs)

            # 2. check updates
            for coord in await self.crs.concolic.get_exploited_coords():
                if coord in beepseeds:
                    del beepseeds[coord]

            if len(beepseeds) == 0:
                # No any new file can be handled in the queue
                yield None
            else:
                picked_coord = None
                for coord in await self.crs.concolic.get_in_prio_coords():
                    if coord in beepseeds and beepseeds[coord]:
                        picked_coord = coord
                        break
                if picked_coord is None and beepseeds:
                    picked_coord = random.choice(list(beepseeds.keys()))

                stack_hash = next(iter(beepseeds[picked_coord]))
                picked_beepseed = next(iter(beepseeds[picked_coord][stack_hash]))

                beepseeds[picked_coord][stack_hash].remove(picked_beepseed)
                if not beepseeds[picked_coord][stack_hash]:
                    del beepseeds[picked_coord][stack_hash]
                if not beepseeds[picked_coord]:
                    del beepseeds[picked_coord]
                processed_bs.add(picked_beepseed)

                reqs = await ConcolicReq.frm_beepseed(
                    self.crs, picked_beepseed, self.GEN_LABEL
                )
                for req in reqs:
                    yield req

    def stat(self) -> str:
        status = "BeepSeedReqGen Status:\n"
        status += "  - Watching directories:\n"
        for src_dir in self.req_src_dirs:
            status += f"      - {src_dir}\n"
        status += f"  - Processed files: {len(self.processed_files)}\n"
        return status


class DummySeedReqGen(ReqGenBase):
    """Generator that produces dummy seed data for initial concolic execution."""

    GEN_LABEL = "dummy-seed"

    def __init__(self, logger, num_seeds: int = 10):
        self.logger = logger
        self.num_seeds = num_seeds
        self._running = atomics.atomic(width=4, atype=atomics.INT)
        self._running.store(0)

    async def __aenter__(self):
        self._running.store(1)
        self.logger(f"Started DummySeedReqGen with {self.num_seeds} seeds")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._running.store(0)
        self.logger("Stopped DummySeedReqGen")
        return False

    async def try_get_next(self) -> AsyncGenerator[ConcolicReq, None]:
        """Generate and yield dummy seeds directly."""
        if self._running.load() == 1:
            for _ in range(self.num_seeds):
                # 128 bytes of random data
                content = os.urandom(128)
                yield ConcolicReq.frm_bytes(content, self.GEN_LABEL)

    def stat(self) -> str:
        """Return the status of the request generator."""
        status = "DummySeedReqGen Status:\n"
        status += f"  - Num seeds configured: {self.num_seeds}\n"
        status += f"  - Running: {self._running.load() == 1}\n"
        return status


class NewCovSeedReqGen(ReqGenBase):
    """Generator that retrieves new coverage seeds from seedsharer."""

    GEN_LABEL = "new-cov-seed"

    def __init__(self, logger, crs: CRS, hrunner: HarnessRunner, batch_size: int = 10):
        self.logger = logger
        self.crs = crs
        self.hrunner = hrunner
        self.batch_size = batch_size
        self.req_seed_cache = set()
        self._running = atomics.atomic(width=4, atype=atomics.INT)
        self._running.store(0)

    async def __aenter__(self):
        self._running.store(1)
        self.logger(
            f"Started NewCovSeedReqGen for harness '{self.hrunner.harness.name}'"
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._running.store(0)
        self.logger(
            f"Stopped NewCovSeedReqGen for harness '{self.hrunner.harness.name}'"
        )
        return False

    async def try_get_next(self) -> AsyncGenerator[ConcolicReq, None]:
        """Async generator that yields concolic requests from seedsharer directly."""
        while self._running.load() == 1:
            try:
                latest_seeds = await self.crs.seedsharer.get_N_latest_seeds(
                    self.hrunner, self.batch_size, self.req_seed_cache
                )

                if len(latest_seeds) == 0:
                    yield None

                for seed_path in latest_seeds:
                    if seed_path.exists() and seed_path not in self.req_seed_cache:
                        try:
                            req = await ConcolicReq.frm_blob(seed_path, self.GEN_LABEL)
                            self.req_seed_cache.add(seed_path)
                            yield req
                        except Exception as e:
                            self.logger(
                                f"Error reading seed file {seed_path}: {e} {traceback.format_exc()}"
                            )

            except Exception as e:
                self.logger(f"Error retrieving seeds: {e}\n{traceback.format_exc()}")

    def stat(self) -> str:
        """Return the status of the request generator."""
        status = "NewCovSeedReqGen Status:\n"
        status += f"  - Harness: {self.hrunner.harness.name}\n"
        status += f"  - Cached seeds: {len(self.req_seed_cache)}\n"
        status += f"  - Running: {self._running.load() == 1}\n"
        return status


class ReqScheduler:
    """Concolic request scheduler."""

    def __init__(
        self, logger, crs: CRS, hrunner: HarnessRunner, req_gens: List[ReqGenBase]
    ):
        self.logger = logger
        self.crs = crs
        self.hrunner = hrunner
        self.req_gens: List[ReqGenBase] = req_gens

    @classmethod
    async def create(
        cls, logger, crs: CRS, hrunner: HarnessRunner, generators: List[str]
    ):
        """Create an instance of ReqScheduler."""
        req_gens = []
        for gen in generators:
            if gen == DirMonitorReqGen.GEN_LABEL:
                req_gens.append(DirMonitorReqGen(logger, crs, hrunner))
                logger(f"Creating DirMonitorReqGen for {hrunner.harness.name}")
            elif gen == NewCovSeedReqGen.GEN_LABEL:
                req_gens.append(NewCovSeedReqGen(logger, crs, hrunner))
                logger(f"Creating NewCovSeedReqGen for {hrunner.harness.name}")
            elif gen == DummySeedReqGen.GEN_LABEL:
                req_gens.append(DummySeedReqGen(logger))
                logger(f"Creating DummySeedReqGen for {hrunner.harness.name}")
            elif gen == BeepSeedReqGen.GEN_LABEL:
                req_gens.append(await BeepSeedReqGen.create(logger, crs, hrunner))
                logger(f"Creating BeepSeedReqGen for {hrunner.harness.name}")
            else:
                logger(f"Unknown concolic request generator: {gen}")
        return cls(logger, crs, hrunner, req_gens)

    async def __aenter__(self):
        for req_gen in self.req_gens:
            await req_gen.__aenter__()
        self.req_gen_iters = [gen.try_get_next() for gen in self.req_gens]
        self.alive_gen_iters = list(self.req_gen_iters)

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        for gen_iter in self.req_gen_iters:
            await gen_iter.aclose()
        for req_gen in self.req_gens:
            await req_gen.__aexit__(exc_type, exc_val, exc_tb)

    async def try_get_next(self) -> Optional[ConcolicReq]:
        still_alive_iters = []
        for gen_iter in self.alive_gen_iters:
            try:
                req = await gen_iter.__anext__()
                still_alive_iters.append(gen_iter)
                if req is None:
                    continue
                else:
                    return req
            except StopAsyncIteration:
                continue
        self.alive_gen_iters = still_alive_iters
        return None

    async def format_scheduler_status(self) -> str:
        status = "Concolic Request Scheduler Status:\n"
        for req_gen in self.req_gens:
            status += req_gen.stat()
        return status


class ConcolicExecutor(Module):
    def __init__(
        self,
        name: str,
        crs: CRS,
        params: ConcolicExecutorParams,
        run_per_harness: bool,
    ):
        super().__init__(name, crs, run_per_harness)
        self.envs: Dict[str, str] = {}
        self.ttl_fuzz_time: int = self.crs.ttl_fuzz_time
        self.params = params
        self.enabled = self.params.enabled
        self.num_instance = self.params.num_instance
        self.max_xms = self.params.max_xms
        self.max_mem = self.params.max_mem
        self.generators = self.params.generators
        self.debug = self.params.debug
        self.exec_timeout = self.params.exec_timeout

        self.base_workdir = self.get_workdir("") / self.crs.cp.name
        self.base_workdir.mkdir(parents=True, exist_ok=True)

        self.RELOAD_N_CORPUS = self.num_instance * 2
        self.SERVER_PORT_BASE = 10000

        self.workdir = self.get_workdir("") / self.crs.cp.name
        self.workdir.mkdir(parents=True, exist_ok=True)

        self._coord_lock = asyncio.Lock()
        self._in_prio_coords = set()
        self._exploited_coords = set()
        self._beepseeds = defaultdict(set)
        self.target_harnesses = {hrunner.harness.name for hrunner in self.crs.hrunners}

    def _init(self):
        pass

    async def _async_prepare(self):
        pass

    async def _async_test(self, hrunner: HarnessRunner):
        util.TODO("Add test")

    async def _async_get_mock_result(self, hrunner: HarnessRunner | None):
        util.TODO("Add mock result")

    def get_num_cores(self) -> int:
        # Here returns exclusive cores
        return self.num_instance + 1

    async def get_exploited_coords(self) -> Set[InsnCoordinate]:
        """Get the set of exploited coordinates."""
        if not self.enabled:
            return
        async with self._coord_lock:
            return self._exploited_coords.copy()

    async def get_beepseeds(self, harness_name: str) -> Set[BeepSeed]:
        """Get the set of beepseeds for a given harness."""
        async with self._coord_lock:
            beepseeds = self._beepseeds[harness_name]
            del self._beepseeds[harness_name]
            return beepseeds

    async def add_beepseeds(self, beepseeds: List[BeepSeed]):
        """Add beepseeds to the executor."""
        async with self._coord_lock:
            for bs in beepseeds:
                if bs.target_harness in self.target_harnesses:
                    self._beepseeds[bs.target_harness].add(bs)

    async def get_in_prio_coords(self) -> Set[InsnCoordinate]:
        """Get the set of coordinates in priority."""
        async with self._coord_lock:
            return self._in_prio_coords.copy()

    async def _set_coord_prio(self, coord: InsnCoordinate, new_prio: bool) -> bool:
        """Set the priority of a coordinate."""
        async with self._coord_lock:
            old_prio = coord in self._in_prio_coords
            if new_prio:
                self._in_prio_coords.add(coord)
            else:
                self._in_prio_coords.discard(coord)
            return old_prio != new_prio

    async def _set_coord_exploited(self, coord: InsnCoordinate) -> bool:
        """Set the coordinate as exploited."""
        async with self._coord_lock:
            self._exploited_coords.add(coord)

    async def on_event_update_coord_info(self, events: List[SinkUpdateEvent]):
        """NOTE: Called by sinkmanager to update the status of a coordinate."""
        if not self.enabled:
            return

        for event in events:
            prio_changed = await self._set_coord_prio(event.coord, event.in_prio)
            if prio_changed:
                self.logH(
                    None,
                    f"ConcolicExecutor: {event.coord} priority changed to {event.in_prio}",
                )
            if event.exploited is True:
                await self._set_coord_exploited(event.coord)
                self.logH(None, f"ConcolicExecutor: {event.coord} exploited")
            # Currently this module does not care event.reached
            await self.add_beepseeds(event.beepseeds)

    def get_harness_workdir(self, harness_name: str) -> Path:
        workdir = self.base_workdir / harness_name
        workdir.mkdir(parents=True, exist_ok=True)
        return workdir

    def get_req_debug_dir(self, harness_name: str) -> Path:
        debug_dir = self.get_harness_workdir(harness_name) / "debug"
        debug_dir.mkdir(parents=True, exist_ok=True)
        return debug_dir

    def get_req_dir(self, harness_name: str) -> Path:
        req_dir = self.get_harness_workdir(harness_name) / "req"
        req_dir.mkdir(parents=True, exist_ok=True)
        return req_dir

    def get_resp_dir(self, harness_name: str) -> Path:
        resp_dir = self.get_harness_workdir(harness_name) / "resp"
        resp_dir.mkdir(parents=True, exist_ok=True)
        return resp_dir

    async def _create_restart_stub(self, name, base_cmd):
        """Restart stub script that keeps restarting the concolic server if it crashes."""
        workdir = self.get_harness_workdir(name)
        stub_path = workdir / "concolic_restart_stub.sh"

        stub_content = """#!/bin/bash
# Restart loop for concolic server
while true
do
  echo "Starting concolic server..."
  stdbuf -e 0 -o 0 \\
    {} || echo @@@@@ exit code of concolic server is $? @@@@@ >&2

  sleep 1
done
""".format(
            base_cmd
        )

        async with aiofiles.open(stub_path, "w") as f:
            await f.write(stub_content)

        stub_path.chmod(0o755)
        return stub_path

    async def _create_command_sh(
        self,
        cmd: List[str],
        harness_name: str,
        script_name: str,
        timeout: int,
        working_dir: str = None,
        cpu_list: List[int] = None,
        buffer_output: bool = True,
        log_file: Path = None,
    ) -> Path:
        if cpu_list:
            cpu_str = ",".join(map(str, cpu_list))
            cmd = ["taskset", "-c", cpu_str] + cmd
        if buffer_output:
            cmd = ["stdbuf", "-e", "0", "-o", "0"] + cmd

        cmd_str = " ".join(shlex.quote(str(arg)) for arg in cmd)

        command_sh_content = f"""#!/bin/bash
# Env
{get_env_exports(os.environ)}
# Cmd
{f'cd "{working_dir}"' if working_dir else ''}
setsid \
  {cmd_str} \
  {f' > {shlex.quote(str(log_file))} 2>&1' if log_file else ''} \
  &
pid=$!
echo "Process started with PID: $pid"

timeout_seconds={timeout}
elapsed=0
while kill -0 $pid 2>/dev/null; do
  if [ $elapsed -ge $timeout_seconds ]; then
    break
  fi
  sleep 1s
  elapsed=$((elapsed + 1))
done
if kill -0 $pid 2>/dev/null; then
  echo "Timeout reached, terminating processes..."
  pkill -P $pid
  kill $pid
  sleep 5
  pkill -KILL -P $pid 2>/dev/null
  kill -KILL $pid 2>/dev/null
fi
"""
        harness_workdir = self.get_harness_workdir(harness_name)
        command_sh = harness_workdir / script_name
        async with aiofiles.open(command_sh, "w") as f_sh:
            await f_sh.write(command_sh_content)
        command_sh.chmod(0o755)
        return command_sh

    async def _run_concolic_server_instance(
        self, hrunner, cpu_list, name, req_dir, resp_dir
    ):
        harness_workdir = self.get_harness_workdir(name)
        port = self.SERVER_PORT_BASE + int(cpu_list[0])
        self.logH(
            hrunner, f"Starting concolic server on port {port} for harness '{name}'"
        )

        base_cmd = [
            "python3.12",
            "-u",
            "/graal-jdk/concolic/graal-concolic/executor/scripts/server.py",
            "--work-dir",
            str(harness_workdir),
            "--input-corpus-dir",
            str(req_dir),
            "--output-corpus-dir",
            str(resp_dir),
            "--cp-metadata",
            str(self.crs.meta.meta_path),
            "--harness",
            name,
            "--cpu-list",
            f'{",".join(map(str, cpu_list))}',
            "--port",
            str(port),
            "--max-concurrency",
            str(self.num_instance),
            "--max-xms",
            str(self.max_xms),
            "--max-mem",
            str(self.max_mem),
            "--timeout",
            str(self.exec_timeout),
        ]
        seedmerger = self.crs.seedmerger
        if seedmerger.enabled:
            base_cmd += [
                "--coverage-seed-dir",
                str(seedmerger.get_expected_full_cov_only_dir(hrunner)),
            ]

        server_cmd_str = " ".join(shlex.quote(str(arg)) for arg in base_cmd)
        restart_stub = await self._create_restart_stub(name, server_cmd_str)

        script_name = "concolic-server-command.sh"
        log_file = harness_workdir / "concolic-server.log"
        run_log = harness_workdir / "run.log"
        command_sh = await self._create_command_sh(
            [str(restart_stub)],
            name,
            script_name,
            self.ttl_fuzz_time,
            cpu_list=cpu_list,
            buffer_output=True,
            log_file=log_file,
        )

        ret = await run_process_and_capture_output(command_sh, run_log)
        self.logH(None, f"Concolic server for harness '{name}' exit with {ret})")

    async def _run_concolic_server(self, hrunner: HarnessRunner, cpu_list: List[int]):
        name = hrunner.harness.name
        req_dir = self.get_req_dir(name)
        resp_dir = self.get_resp_dir(name)

        self.logH(
            hrunner,
            f"Starting concolic server instance for {name} {req_dir} {resp_dir}",
        )
        try:
            await self._run_concolic_server_instance(
                hrunner, cpu_list, name, req_dir, resp_dir
            )
        except Exception as e:
            self.logH(
                hrunner,
                f"{CRS_ERR} Exception in concolic server instance: {e}\n"
                f"Traceback: \n{traceback.format_exc()}",
            )

        self.logH(hrunner, "Concolic server instance completed")

    async def _reload_concolic_reqs(
        self, hrunner: HarnessRunner, req_scheduler: ReqScheduler
    ):
        """Reload N latest seed to req_dir for a specific harness if remaining reqs are <= 1."""
        try:
            harness_name = hrunner.harness.name
            req_dir = self.get_req_dir(harness_name)
            debug_dir = self.get_req_debug_dir(harness_name)
            req_files = [f for f in req_dir.glob("*") if f.is_file()]
            if len(req_files) <= 1:
                # Reload when only zero or one request is left
                reloaded = 0
                for i in range(self.RELOAD_N_CORPUS):
                    try:
                        req = await req_scheduler.try_get_next()
                        if req:
                            await req.to_file(req_dir)
                            if self.debug:
                                await req.to_file(debug_dir)
                            reloaded += 1
                    except Exception as e:
                        self.logH(
                            hrunner,
                            f"{CRS_ERR} reloading request {i}: {e} {traceback.format_exc()}",
                        )

                self.logH(
                    hrunner,
                    f"Reloaded {reloaded}/{self.RELOAD_N_CORPUS} seeds to req_dir for harness '{harness_name}'",
                )
        except Exception as e:
            self.logH(
                hrunner,
                f"{CRS_ERR} getting latest seeds for harness '{harness_name}': {e} {traceback.format_exc()}",
            )

    async def _dispatch_concolic_resps(self, hrunner: HarnessRunner, resp_queue):
        """Dispatch concolic responses for a specific harness using watchdog-based queue."""
        try:
            harness_name = hrunner.harness.name
            processed_count = 0

            while not resp_queue.empty():
                try:
                    resp_path = resp_queue.get_nowait()
                    if resp_path.exists():
                        await self.crs.seedsharer.add_seed_to_queue(
                            hrunner, self.name, resp_path
                        )
                        processed_count += 1
                    resp_queue.task_done()
                except queue.Empty:
                    break
                except Exception as e:
                    self.logH(
                        hrunner,
                        f"{CRS_ERR} dispatching result '{resp_path.name if 'resp_path' in locals() else 'unknown'}': {e} {traceback.format_exc()}",
                    )

            if processed_count > 0:
                self.logH(
                    hrunner,
                    f"Dispatched {processed_count} result(s) for harness '{harness_name}'",
                )

        except Exception as e:
            self.logH(
                hrunner,
                f"{CRS_ERR} processing results for harness '{harness_name}': {e} {traceback.format_exc()}",
            )

    async def _run_concolic_client(self, hrunner: HarnessRunner, resp_queue):
        self.logH(hrunner, "Starting concolic client")

        req_scheduler = await ReqScheduler.create(
            lambda m: self.logH(hrunner, m),
            self.crs,
            hrunner,
            generators=self.generators,
        )

        async with req_scheduler:
            while self.crs.should_continue():
                await self._reload_concolic_reqs(hrunner, req_scheduler)
                await self._dispatch_concolic_resps(hrunner, resp_queue)
                await asyncio.sleep(1)

        self.logH(hrunner, "Concolic client completed successfully")
        self.logH(hrunner, f"{await req_scheduler.format_scheduler_status()}")

    async def _async_run(self, hrunner: HarnessRunner):
        if not self.enabled:
            self.logH(None, f"Module {self.name} is disabled")
            return

        cpu_list = await self.crs.cpuallocator.poll_allocation(hrunner, self.name)
        cp_name = self.crs.cp.name
        harness_name = hrunner.harness.name
        if len(cpu_list) == 0:
            self.logH(
                hrunner,
                f"{CRS_WARN} No CPU cores available for concolic for harness '{harness_name}' in CP '{cp_name}'",
            )
            return
        else:
            self.logH(
                hrunner,
                f"Starting module {self.name} for harness '{harness_name}' in CP '{cp_name}' using CPU cores: {cpu_list}",
            )

        try:
            resp_queue = queue.Queue()

            watcher = RespDirWatcher(
                self, hrunner, self.get_resp_dir(harness_name), resp_queue
            )
            watcher.start()
            self.logH(hrunner, f"Started response watcher for harness '{harness_name}'")

            server_task = asyncio.create_task(
                self._run_concolic_server(hrunner, cpu_list)
            )
            client_task = asyncio.create_task(
                self._run_concolic_client(hrunner, resp_queue)
            )

            results = await asyncio.gather(
                server_task,
                client_task,
                return_exceptions=True,
            )

            for result in results:
                if isinstance(result, Exception):
                    raise result

        except Exception as e:
            self.logH(
                hrunner,
                f"{CRS_ERR} Module {self.name} encountered an exception: {e} for harness '{harness_name}', traceback: \n{traceback.format_exc()}",
            )
        finally:
            watcher.stop()
            self.logH(hrunner, f"Stopped response watcher for harness '{harness_name}'")
