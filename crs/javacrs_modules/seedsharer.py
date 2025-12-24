#!/usr/bin/env python3
import asyncio
import heapq
import os
import random
import shlex
import time
import traceback
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple

import aiofiles
from libCRS import CRS, HarnessRunner, Module, util
from pydantic import BaseModel, Field, field_validator

from .jazzer import is_fuzzing_module
from .utils import (
    CRS_ERR_LOG,
    CRS_WARN_LOG,
    atomic_write_file_frm_path,
    get_env_exports,
    is_jazzer_gen_seed,
    run_process_and_capture_output,
)
from .utils_nfs import get_oss_crs_artifact_corpus_dir

CRS_ERR = CRS_ERR_LOG("seedsharer-mod")
CRS_WARN = CRS_WARN_LOG("seedsharer-mod")


class SeedSharerParams(BaseModel):
    enabled: bool = Field(
        ..., description="**Mandatory**, true/false to enable/disable this module."
    )
    sync_period: int = Field(
        ...,
        description="**Mandatory**, seed sync period in seconds among all Jazzer modules.",
    )
    N_latest_seed: int = Field(
        5,
        description="**Optional**, latest N seed sync among all Jazzer modules. Default is 5.",
    )

    @field_validator("enabled")
    def enabled_should_be_boolean(cls, v):
        if not isinstance(v, bool):
            raise ValueError("enabled must be a boolean")
        return v

    @field_validator("sync_period")
    def period_should_be_positive(cls, v):
        if v <= 0:
            raise ValueError("sync_period must be a positive integer")
        return v

    @field_validator("N_latest_seed")
    def N_latest_seed_should_be_positive(cls, v):
        if v <= 0:
            raise ValueError("N_latest_seed must be a positive integer")
        return v


class DirectoryScanner:
    """Scanner for corpus directories that periodically checks for new files."""

    def __init__(self, module_name, harness_name, parent, corpus_dir):
        self.module_name = module_name
        self.harness_name = harness_name
        self.parent = parent
        self.corpus_dir = corpus_dir
        # Map of filename -> last seen mtime to detect changes
        self.seen_files: Set[str] = set()

    def get_stats(self):
        """Get statistics about tracked files by module name."""
        return len(self.seen_files)

    async def scan(self):
        """Scan the directory for new files and add them to the queue."""
        if not self.corpus_dir.exists():
            return

        try:
            loop = asyncio.get_running_loop()
            entries = await loop.run_in_executor(
                None, lambda: list(os.scandir(self.corpus_dir))
            )
            for entry in entries:
                if not entry.is_file():
                    continue

                try:
                    seed_path = Path(entry.path)

                    if entry.name in self.seen_files:
                        continue

                    self.seen_files.add(entry.name)

                    if self.module_name == "crs-multilang":
                        await self.parent.queue.put(
                            (self.harness_name, self.module_name, seed_path)
                        )
                    else:
                        if is_jazzer_gen_seed(seed_path.name):
                            await self.parent.queue.put(
                                (self.harness_name, self.module_name, seed_path)
                            )
                except Exception as e:
                    self.parent.logH(
                        None,
                        f"{CRS_ERR} error processing file {entry.path}: {str(e)} {traceback.format_exc()}",
                    )
        except Exception as e:
            self.parent.logH(
                None,
                f"{CRS_ERR} error scanning directory {self.corpus_dir}: {str(e)} {traceback.format_exc()}",
            )


class DirectoryScannerManager:
    """Management of directory scanners for all corpus dirs."""

    def __init__(self, seedsharer):
        self.seedsharer = seedsharer
        # Structure: {harness_name: {module_name: {corpus_dir_str: DirectoryScanner}}}
        self.scanners: Dict[str, Dict[str, Dict[str, DirectoryScanner]]] = {}
        self.dirs_to_scan: List[Tuple[str, str, Path]] = []

    def get_scanner(self, harness_name, module_name, corpus_dir):
        corpus_dir_str = str(corpus_dir)

        if harness_name not in self.scanners:
            self.scanners[harness_name] = {}
        if module_name not in self.scanners[harness_name]:
            self.scanners[harness_name][module_name] = {}

        if corpus_dir_str not in self.scanners[harness_name][module_name]:
            scanner = DirectoryScanner(
                module_name, harness_name, self.seedsharer, corpus_dir
            )
            self.scanners[harness_name][module_name][corpus_dir_str] = scanner

        return self.scanners[harness_name][module_name][corpus_dir_str]

    def add_directory(self, harness_name, module_name, corpus_dir):
        if not corpus_dir.exists():
            # Ensure dir exists before monitoring
            corpus_dir.mkdir(parents=True, exist_ok=True)

        self.get_scanner(harness_name, module_name, corpus_dir)
        self.dirs_to_scan.append((harness_name, module_name, corpus_dir))
        self.seedsharer.logH(
            None,
            f"Added dir to scan: {corpus_dir} of '{module_name}', '{harness_name}'",
        )

    async def scan_all(self):
        """Scan all directories for new files."""
        scan_tasks = []
        for harness_name, module_name, corpus_dir in self.dirs_to_scan:
            scanner = self.get_scanner(harness_name, module_name, corpus_dir)
            scan_tasks.append(scanner.scan())

        await asyncio.gather(*scan_tasks)

    async def setup_all(self):
        self.seedsharer.logH(None, "Setting up corpus directory scanners")

        for hrunner in self.seedsharer.crs.hrunners:
            seedmerger = self.seedsharer.crs.seedmerger
            artifact_corpus_dir = get_oss_crs_artifact_corpus_dir()

            # Monitor if either seedmerger is enabled OR artifact corpus is configured
            if seedmerger.enabled or artifact_corpus_dir:
                # Monitor all harness corpus dirs
                for jazzer_mod in self.seedsharer._get_enabled_fuzzing_modules():
                    corpus_dirs = await jazzer_mod.get_expected_corpus_dirs(hrunner)
                    for corpus_dir in corpus_dirs:
                        self.add_directory(
                            hrunner.harness.name, jazzer_mod.name, corpus_dir
                        )

            # Monitor seedmerger output dir for all harnesses (only if seedmerger is enabled)
            if seedmerger.enabled:
                corpus_dir = seedmerger.get_expected_full_cov_dir(hrunner)
                self.add_directory(hrunner.harness.name, seedmerger.name, corpus_dir)

            # Monitor seeds shared from crs-multilang
            multilang_seed_dir = self.seedsharer.multilang_local_seed_dir
            corpus_dir = multilang_seed_dir / hrunner.harness.name
            self.add_directory(hrunner.harness.name, "crs-multilang", corpus_dir)

    def get_aggregated_stats(self):
        """Aggregate statistics from all scanners by harness and module name."""
        aggregated_stats = {}
        for harness_name, module_dict in self.scanners.items():
            aggregated_stats[harness_name] = {}
            for module_name, dir_dict in module_dict.items():
                total_count = 0
                for scanner in dir_dict.values():
                    total_count += scanner.get_stats()
                aggregated_stats[harness_name][module_name] = total_count
        return aggregated_stats

    def clear(self):
        self.seedsharer.logH(None, "Clearing all directory scanners")
        self.scanners.clear()
        self.dirs_to_scan.clear()


class SeedSharer(Module):
    def __init__(
        self,
        name: str,
        crs: CRS,
        params: SeedSharerParams,
        run_per_harness: bool,
    ):
        super().__init__(name, crs, run_per_harness)
        self.envs: dict[str, str] = {}
        self.workdir = self.get_workdir("") / self.crs.cp.name
        self.workdir.mkdir(parents=True, exist_ok=True)

        self.ttl_fuzz_time: int = self.crs.ttl_fuzz_time
        self.params = params
        self.enabled = self.params.enabled
        self.sync_period = self.params.sync_period
        self.N_latest_seed = self.params.N_latest_seed
        self.LATEST_SEED_POOL_SIZE = max(self.N_latest_seed, 100000)
        self.sync_history: Dict[str, Dict[str, Set[str]]] = {}

        self._scanner_manager = DirectoryScannerManager(self)
        self.multilang_local_seed_dir = self.workdir / "crs-multilang"
        self.multilang_local_seed_dir.mkdir(parents=True, exist_ok=True)

        # Stores latest seeds as heaps
        # Structure: {harness_name: {module_name: [(creation_time, seed_path), ...]}}
        # Using min-heap, so oldest (smallest creation_time) is at index 0
        self._latest_seeds: Dict[str, Dict[str, List[Tuple[float, Path]]]] = {}
        self._latest_seeds_lock = asyncio.Lock()

        # Asyncio queue for coroutine communication
        # Each item: (harness_name, module_name, seed_path)
        self.queue = asyncio.Queue()

    def _init(self):
        pass

    async def _async_prepare(self):
        pass

    async def _async_test(self, hrunner: HarnessRunner):
        util.TODO("Add test")

    async def _async_get_mock_result(self, hrunner: HarnessRunner | None):
        util.TODO("Add mock result")

    def get_multilang_seed_local_dir(self, harness_id: str) -> Path:
        """NOTE: Safe to call at any time."""
        dir = self.multilang_local_seed_dir / harness_id
        if not dir.exists():
            dir.mkdir(parents=True, exist_ok=True)
        return dir

    def _get_enabled_fuzzing_modules(self):
        """Retrieve all enabled Jazzer modules."""
        return [
            mod for mod in self.crs.modules if is_fuzzing_module(mod) and mod.enabled
        ]

    async def _record_seedmerger_new_seeds(self, frm_seedmerger):
        async with self._latest_seeds_lock:
            module_name = self.crs.seedmerger.name
            for harness_name, seed_paths in frm_seedmerger.items():
                for seed_path in seed_paths:
                    creation_time = seed_path.stat().st_ctime
                    if harness_name not in self._latest_seeds:
                        self._latest_seeds[harness_name] = {}
                    if module_name not in self._latest_seeds[harness_name]:
                        self._latest_seeds[harness_name][module_name] = []

                    heap = self._latest_seeds[harness_name][module_name]
                    if len(heap) < self.LATEST_SEED_POOL_SIZE:
                        # < N, add seed anyway
                        heapq.heappush(heap, (creation_time, seed_path))
                    elif creation_time > heap[0][0]:
                        # >= N, replace the oldest
                        heapq.heappushpop(heap, (creation_time, seed_path))
                    self._latest_seeds[harness_name][module_name] = heap

    async def _create_command_sh(
        self,
        cmd: List[str],
        script_name: str,
        working_dir: str = None,
    ) -> Path:
        cmd_str = " ".join(shlex.quote(str(arg)) for arg in cmd)
        command_sh_content = f"""#!/bin/bash
# Env
{get_env_exports(os.environ)}
# Cmd
{f'cd "{working_dir}"' if working_dir else ''}
{cmd_str}
"""
        command_sh = self.workdir / script_name
        async with aiofiles.open(command_sh, "w") as f_sh:
            await f_sh.write(command_sh_content)
        command_sh.chmod(0o755)
        return command_sh

    async def _copy_seeds_to_dir(
        self, harness_name, seed_path_pairs, tgt_dir, purpose_name
    ):
        """
        Copy seeds to a target directory.

        Args:
            harness_name: Name of the harness
            seed_path_pairs: List of (seed_path, del_after_cp) tuples
            tgt_dir: Target directory to copy seeds to
            purpose_name: Name of the purpose (for logging, e.g., "seedmerger", "artifact corpus")

        Returns:
            Number of seeds successfully copied
        """
        if not tgt_dir.exists():
            tgt_dir.mkdir(parents=True, exist_ok=True)

        if len(seed_path_pairs) <= 10:
            # Small number of seeds - use direct file copy
            ttl_num, ttl_del = 0, 0
            for seed_path, del_after_cp in seed_path_pairs:
                try:
                    if del_after_cp:
                        os.replace(seed_path, tgt_dir / seed_path.name)
                        ttl_del += 1
                    else:
                        await atomic_write_file_frm_path(
                            tgt_dir / seed_path.name, seed_path
                        )
                    ttl_num += 1
                except FileNotFoundError:
                    self.logH(
                        None,
                        f"Eat the FileNotFoundError in {purpose_name} seed transfer: {seed_path}",
                    )
            self.logH(
                None,
                f"Sent {ttl_num} seeds to {purpose_name} for {harness_name}, deleted {ttl_del} after copy",
            )
            return ttl_num

        # For larger numbers, use rsync with files-from
        timestamp = int(time.time())
        list_file_path = self.workdir / f"{harness_name}_{timestamp}_{purpose_name.replace(' ', '_')}_rsync_list.txt"

        async with aiofiles.open(list_file_path, "w") as list_file:
            contents = "\n".join(
                [str(seed_path.absolute()) for seed_path, _ in seed_path_pairs]
            )
            await list_file.write(contents + "\n")

        cmd = [
            "rsync",
            "-av",
            "--files-from",
            str(list_file_path),
            "--ignore-missing-args",
            "--no-relative",
            "-q",
            "/",  # Source directory (paths in files-from are absolute)
            f"{str(tgt_dir)}/",
        ]

        script_name = f"{harness_name}_{timestamp}_{purpose_name.replace(' ', '_')}_rsync.sh"
        log_file = self.workdir / f"{harness_name}_{timestamp}_{purpose_name.replace(' ', '_')}_rsync.log"

        try:
            command_sh = await self._create_command_sh(cmd, script_name)
            ret = await run_process_and_capture_output(command_sh, log_file)

            if ret not in [0, 23, 24]:
                self.logH(
                    None,
                    f"{CRS_ERR} Failed to send new seeds to {purpose_name} for {harness_name} {list_file_path}: ret {ret}",
                )
            else:
                if self.crs.verbose:
                    self.logH(
                        None,
                        f"Successfully sent {len(seed_path_pairs)} seeds to {purpose_name} for {harness_name} {list_file_path}: ret {ret}",
                    )

            # Clean up the seed_path whose del_after_cp is True
            ttl_del = 0
            for seed_path, del_after_cp in seed_path_pairs:
                if del_after_cp and seed_path.exists():
                    try:
                        seed_path.unlink()
                        ttl_del += 1
                    except Exception as e:
                        self.logH(
                            None,
                            f"{CRS_ERR} Failed to delete seed file {seed_path}: {str(e)} {traceback.format_exc()}",
                        )
            self.logH(
                None,
                f"Deleted {ttl_del} seeds after sending to {purpose_name} for {harness_name}",
            )

            return len(seed_path_pairs)

        except Exception as e:
            self.logH(
                None,
                f"{CRS_ERR} Error sending new seeds to {purpose_name} for {harness_name} {list_file_path}: {str(e)} {traceback.format_exc()}",
            )
            return 0

    async def _copy_seeds_to_artifact_corpus(self, harness_name, seed_path_pairs):
        """Copy seeds to OSS_CRS_ARTIFACT_CORPUS directory."""
        artifact_corpus_dir = get_oss_crs_artifact_corpus_dir()
        if not artifact_corpus_dir:
            return

        # NOTE: Use del_after_cp=False for artifact copy to preserve original files
        artifact_seed_pairs = [(path, False) for path, _ in seed_path_pairs]

        try:
            await self._copy_seeds_to_dir(
                harness_name, artifact_seed_pairs, artifact_corpus_dir, "osscrs"
            )
        except Exception as e:
            self.logH(
                None,
                f"{CRS_ERR} Error copying seeds to artifact corpus for {harness_name}: {str(e)} {traceback.format_exc()}",
            )

    async def _send_new_seeds_to_seedmerger(self, harness_name, seed_path_pairs):
        seedmerger = self.crs.seedmerger
        if not seedmerger.enabled:
            self.logH(
                None,
                f"Seed merger is not enabled, skipping sending {len(seed_path_pairs)} new seeds for {harness_name}",
            )
            return

        tgt_dir = seedmerger.try_get_expected_merge_from_dir(harness_name)
        if not tgt_dir:
            self.logH(
                None,
                f"{CRS_WARN} Could not get target directory for harness {harness_name}",
            )
            return

        # Copy seeds to seedmerger
        await self._copy_seeds_to_dir(
            harness_name, seed_path_pairs, tgt_dir, "seedmerger"
        )

    async def _process_seed_queue(self):
        """Process seeds from the async queue."""
        start_time = time.time()
        last_stats_time = start_time

        total_processed = 0
        harness_module_counters = defaultdict(
            lambda: defaultdict(int)
        )  # {harness: {module: count}}

        while self.crs.should_continue():
            frm_seedmerger = defaultdict(set)
            to_seedmerger = defaultdict(set)

            # batch seed collection
            cur_collected = 0
            while not self.queue.empty():
                if cur_collected >= 3333:
                    self.logH(
                        None,
                        f"Break out the collection loop, processing seed queue: {self.queue.qsize()} items, total processed: {total_processed}",
                    )
                    break

                try:
                    harness_name, module_name, seed_path = await self.queue.get()
                    if module_name == self.crs.seedmerger.name:
                        frm_seedmerger[harness_name].add(seed_path)
                    elif module_name == self.crs.concolic.name:
                        to_seedmerger[harness_name].add((seed_path, True))
                    else:
                        to_seedmerger[harness_name].add((seed_path, False))
                    cur_collected += 1
                    total_processed += 1
                    harness_module_counters[harness_name][module_name] += 1

                except Exception as e:
                    self.logH(
                        None,
                        f"{CRS_ERR} batch seed collection: {str(e)} {traceback.format_exc()}",
                    )
                finally:
                    self.queue.task_done()

            # batch seed processing
            try:
                tasks = []
                if len(frm_seedmerger) > 0:
                    tasks.append(self._record_seedmerger_new_seeds(frm_seedmerger))
                if len(to_seedmerger) > 0:
                    for harness_name, seed_path_pairs in to_seedmerger.items():
                        tasks.append(
                            self._copy_seeds_to_artifact_corpus(
                                harness_name, seed_path_pairs
                            )
                        )
                        tasks.append(
                            self._send_new_seeds_to_seedmerger(
                                harness_name, seed_path_pairs
                            )
                        )
                if len(tasks) > 0:
                    await asyncio.gather(*tasks)
            except Exception as e:
                self.logH(
                    None,
                    f"{CRS_ERR} batch seed processing: {str(e)} {traceback.format_exc()}",
                )

            # Log stats periodically
            current_time = time.time()
            if current_time - last_stats_time >= 180:
                for harness, module_stats in sorted(harness_module_counters.items()):
                    if module_stats:  # Only print if there are stats
                        stats_line = f"PROC Harness {harness}: " + ", ".join(
                            [
                                f"{module}: {count}"
                                for module, count in sorted(module_stats.items())
                            ]
                        )
                        self.logH(None, stats_line)
                last_stats_time = current_time

            if self.queue.empty():
                await asyncio.sleep(1)

        self.logH(None, "Seed queue processor reached ttl_fuzz_time, exiting.")

    async def _sync_seeds(
        self,
        hrunner: HarnessRunner,
        harness_id: str,
        file_hash_to_info: dict[str, tuple[str, Path]],
    ):
        """Sync seeds among Jazzer modules for a specific harness."""
        all_file_hashes = set(file_hash_to_info.keys())
        for file_hash in all_file_hashes:
            if file_hash not in self.sync_history[harness_id]:
                self.sync_history[harness_id][file_hash] = set()

            frm_mod_name, seed_file = file_hash_to_info[file_hash]
            for to_mod in self._get_enabled_fuzzing_modules():
                to_mod_name = to_mod.name

                if await to_mod.corpus_file_exists(hrunner, file_hash):
                    # Already exists in target module
                    continue
                if to_mod_name in self.sync_history[harness_id][file_hash]:
                    # Already synced
                    continue

                if self.crs.verbose:
                    self.logH(
                        None,
                        f"Sync seed {seed_file.name} from module '{frm_mod_name}' to '{to_mod_name}', '{harness_id}'",
                    )

                try:
                    # Add seed
                    await to_mod.add_corpus_file(hrunner, seed_file)

                    # Update sync_history
                    self.sync_history[harness_id][file_hash].add(to_mod_name)
                except Exception as e:
                    err_str = str(e)
                    if self.crs.verbose or "No such file or directory" not in err_str:
                        # NOTE: Skip 'No such file or directory' error since Jazzer will delete some seeds during fuzzing
                        self.logH(
                            None,
                            f"{CRS_ERR} Failed to add seed {seed_file.name} to '{to_mod_name}', '{harness_id}': {err_str} {traceback.format_exc()}",
                        )

    async def _sync_seeds_for_harness(self, hrunner: HarnessRunner):
        """Sync seeds for a single harness using collected seed info."""
        harness_id = hrunner.harness.name
        if harness_id not in self.sync_history:
            self.sync_history[harness_id] = {}
        self.logH(None, f"Sync seeds for harness {harness_id}")

        local_seeds_copy = {}
        async with self._latest_seeds_lock:
            if harness_id not in self._latest_seeds:
                self.logH(None, f"No seed data collected yet for harness {harness_id}")
                return

            for mod_name, seed_tuples in self._latest_seeds[harness_id].items():
                start_idx = max(0, len(seed_tuples) - self.N_latest_seed)
                local_seeds_copy[mod_name] = [
                    path for _, path in seed_tuples[start_idx:]
                ]

        file_hash_to_info = {}
        for mod_name, seed_paths in local_seeds_copy.items():
            for seed_path in seed_paths:
                file_hash = seed_path.name
                if file_hash not in file_hash_to_info:
                    file_hash_to_info[file_hash] = (mod_name, seed_path)

        await self._sync_seeds(hrunner, harness_id, file_hash_to_info)

    async def _sync_seed_among_jazzers(self):
        """Sync seeds among all Jazzer modules."""
        self.logH(None, "Starting seed sync among Jazzer modules")

        for hrunner in self.crs.hrunners:
            try:
                await self._sync_seeds_for_harness(hrunner)
            except Exception as e:
                self.logH(
                    None,
                    f"{CRS_ERR} Failed to sync seeds for harness '{hrunner.harness.name}': {str(e)} {traceback.format_exc()}",
                )

    async def get_N_latest_seeds(
        self, hrunner: HarnessRunner, n: int, retrieved_seeds: set = None
    ) -> list[Path]:
        """Get at most N latest seeds for a specific harness."""
        if not self.enabled:
            if self.crs.verbose:
                self.logH(None, f"Calling get_N_latest_seeds of disabled {self.name}")
            return []

        if retrieved_seeds is None:
            retrieved_seeds = set()

        harness_name = hrunner.harness.name
        all_seeds = []

        async with self._latest_seeds_lock:
            if harness_name not in self._latest_seeds:
                return []

            for mod_name, heap in self._latest_seeds[harness_name].items():
                all_seeds.extend(
                    [
                        path
                        for _, path in heap
                        if path.exists() and path not in retrieved_seeds
                    ]
                )

        if len(all_seeds) <= n:
            return all_seeds

        # NOTE: random sample here, can use sort if needed
        return random.sample(all_seeds, n)

    async def add_seed_to_queue(
        self, hrunner: HarnessRunner, mod_name: str, seed_path: Path
    ):
        """Add a new seed to the seed queue."""
        one_new_seed = (hrunner.harness.name, mod_name, seed_path)
        await self.queue.put(one_new_seed)
        if self.crs.verbose:
            self.logH(None, f"Added {one_new_seed} to seed queue")

    async def _corpus_scan_loop(self):
        """Periodically scan corpus directories for new seeds."""
        self.logH(None, "Starting corpus directory scanner")
        try:
            self.logH(None, "Setting up directory scanning")
            await self._scanner_manager.setup_all()

            counter = 0
            stats_interval = 180  # Print stats every 3 minutes (180 seconds)
            scan_interval = 30  # Scan every 30 seconds

            while self.crs.should_continue():
                await asyncio.sleep(1)
                counter += 1

                if counter % stats_interval == 0:
                    stats = self._scanner_manager.get_aggregated_stats()
                    for harness, module_stats in stats.items():
                        stats_line = f"SCAN Harness {harness}: " + ", ".join(
                            [
                                f"{module}: {count}"
                                for module, count in sorted(module_stats.items())
                            ]
                        )
                        self.logH(None, stats_line)

                if counter % scan_interval == 0:
                    try:
                        await self._scanner_manager.scan_all()
                    except Exception as e:
                        self.logH(
                            None,
                            f"{CRS_ERR} in corpus scan loop: {str(e)}, {traceback.format_exc()}",
                        )

            self.logH(None, "Corpus directory scanner reached ttl_fuzz_time, exiting.")
        finally:
            self.logH(None, "Clearing all directory scanners")
            self._scanner_manager.clear()

    def _get_sync_stats(self):
        """Get stats about synced seeds per module for each harness."""
        stats = {}
        for harness_id, file_hashes in self.sync_history.items():
            # Initialize counters for all modules
            module_counts = defaultdict(int)

            # Count syncs per module
            for file_hash, synced_modules in file_hashes.items():
                for module_name in synced_modules:
                    module_counts[module_name] += 1

            stats[harness_id] = dict(module_counts)

        return stats

    async def _sync_loop(self):
        """Periodically sync seeds among Jazzer modules."""
        self.logH(None, "Starting seed sync loop")
        start_time = time.time()
        last_sync_time = start_time

        counter = 0
        stats_interval = 180  # Print stats every 3 minutes (180 seconds)

        while self.crs.should_continue():
            # Sleep for 1s
            await asyncio.sleep(1)
            counter += 1

            # Print stats every 3 minutes
            if counter % stats_interval == 0:
                sync_stats = self._get_sync_stats()
                for harness, module_stats in sync_stats.items():
                    if module_stats:  # Only print if there are stats
                        stats_line = f"SYNC Harness {harness}: " + ", ".join(
                            [
                                f"{module}: {count}"
                                for module, count in sorted(module_stats.items())
                            ]
                        )
                        self.logH(None, stats_line)

            # Check if it's time to sync
            cur_time = time.time()
            if cur_time - last_sync_time >= self.sync_period:
                try:
                    await self._sync_seed_among_jazzers()
                    last_sync_time = cur_time
                except Exception as e:
                    self.logH(
                        None,
                        f"{CRS_ERR} in sync loop: {str(e)}, {traceback.format_exc()}",
                    )

        self.logH(None, "Seed sync loop reached ttl_fuzz_time, exiting.")

    async def _async_run(self, _):
        """Run the seed sharer module with separate collection and sync tasks."""
        if not self.enabled:
            self.logH(None, f"Module {self.name} is disabled")
            return

        self.logH(None, f"Module {self.name} starts")

        # Just inherit main CRS process CPU affinity for seed sharer
        #   but still wait the completion of cpuallocator.
        _ = await self.crs.cpuallocator.poll_allocation(None, self.name)

        try:
            corpus_scan_task = asyncio.create_task(self._corpus_scan_loop())
            seed_processor_task = asyncio.create_task(self._process_seed_queue())
            sync_task = asyncio.create_task(self._sync_loop())

            await asyncio.gather(corpus_scan_task, seed_processor_task, sync_task)

            self.logH(
                None,
                f"Module {self.name} reached ttl_fuzz_time ({self.ttl_fuzz_time}s), exiting.",
            )

        except Exception as e:
            self.logH(
                None, f"{CRS_ERR} in seedsharer: {str(e)}, {traceback.format_exc()}"
            )
