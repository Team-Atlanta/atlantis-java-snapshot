#!/usr/bin/env python3
import asyncio
import hashlib
import json
import os
import time
import traceback
from itertools import cycle
from pathlib import Path

import aiofiles
from libCRS import CRS, Module
from pydantic import BaseModel, Field, field_validator

from .base_objs import DiffReachabilityReport
from .utils import CRS_ERR_LOG, CRS_WARN_LOG, atomic_write_file
from .utils_leader import CRS_JAVA_POD_NAME
from .utils_nfs import (
    get_all_crs_java_cfg_paths,
    get_all_crs_java_diff_ana_paths,
    get_crs_java_cfg_path,
    get_crs_java_diff_ana_path,
    get_crs_java_sched_flag_path,
    get_crs_java_share_diff_schedule_dir,
    get_planned_crs_java_cfg_path,
)

CRS_ERR = CRS_ERR_LOG("diff-scheduler-mod")
CRS_WARN = CRS_WARN_LOG("diff-scheduler-mod")


class DiffSchedulerParams(BaseModel):
    enabled: bool = Field(
        ..., description="**Mandatory**, true/false to enable/disable this module."
    )
    min_sched_time: int = Field(
        3600,
        description="**Optional**, minimum time in seconds to wait before scheduling. Default is 3600 seconds (1h).",
    )
    max_sched_time: int = Field(
        10800,
        description="**Optional**, maximum time in seconds to wait before forcing scheduling. Default is 10800 seconds (3h).",
    )

    @field_validator("enabled")
    def enabled_should_be_boolean(cls, v):
        if not isinstance(v, bool):
            raise ValueError("enabled must be a boolean")
        return v

    @field_validator("min_sched_time", "max_sched_time")
    def schedule_time_should_be_positive(cls, v):
        if v <= 0:
            raise ValueError("min/max_sched_time must be a positive integer")
        return v


class DiffScheduler(Module):
    def __init__(
        self,
        name: str,
        crs: CRS,
        params: DiffSchedulerParams,
        run_per_harness: bool,
    ):
        super().__init__(name, crs, run_per_harness)
        self.params = params
        self.enabled = self.params.enabled
        self.check_interval = 60
        self.workdir = self.get_workdir("") / self.crs.cp.name
        self.diff_schedule_dir = get_crs_java_share_diff_schedule_dir()
        self.pod_id = CRS_JAVA_POD_NAME

        self.min_sched_time = self.crs.start_time + self.params.min_sched_time
        self.max_sched_time = self.crs.start_time + self.params.max_sched_time
        if self.max_sched_time < self.min_sched_time:
            raise ValueError(
                f"max_sched_time {self.max_sched_time} must be greater than min_sched_time {self.min_sched_time}"
            )

    def _init(self):
        pass

    async def _async_prepare(self):
        pass

    async def _async_test(self, hrunner):
        self.logH(hrunner, "Test DiffScheduler")

    async def _async_get_mock_result(self, hrunner):
        self.logH(hrunner, "Mock result for DiffScheduler")

    async def _upload_file(self, path: Path, content: str):
        checksum = hashlib.sha256(content.encode()).hexdigest()
        await atomic_write_file(path, content)
        checksum_path = path.with_suffix(".sha256")
        await atomic_write_file(checksum_path, checksum)

    async def _download_file(self, path: Path) -> str | None:
        if not path.exists():
            self.logH(None, f"File {path} does not exist")
            return None

        checksum_path = path.with_suffix(".sha256")
        if not checksum_path.exists():
            self.logH(None, f"Checksum file {checksum_path} does not exist")
            return None

        async with aiofiles.open(path, "r") as f:
            content = await f.read()
        async with aiofiles.open(checksum_path, "r") as f:
            checksum = await f.read()
        calculated_checksum = hashlib.sha256(content.encode()).hexdigest()
        if calculated_checksum != checksum:
            self.logH(None, f"Checksum mismatch for {path}, ")
            return None
        return content

    async def _upload_this_node_crs_cfg(self):
        cfg = {
            "target_harnesses": [h.name for h in self.crs.target_harnesses],
        }
        cfg_path = get_crs_java_cfg_path(self.pod_id)

        self.logH(None, f"Uploading crs config {cfg} to {cfg_path}")
        await self._upload_file(cfg_path, json.dumps(cfg))
        self.logH(None, f"Uploaded crs config {cfg_path}")

    async def _upload_this_node_diff_ana_results(self):
        diff_ana = await self.crs.llmpocgen.get_diff_ana_results()
        if diff_ana is None:
            self.logH(None, "No diff analysis result found")
            return
        diff_ana_path = get_crs_java_diff_ana_path(self.pod_id)

        self.logH(None, f"Uploading diff analysis result {diff_ana} to {diff_ana_path}")
        await self._upload_file(diff_ana_path, diff_ana.to_json())
        self.logH(None, f"Uploaded diff analysis result {diff_ana_path}")

    async def _exit_procedure(self):
        self.logH(None, "Ending this crs container")
        # NOTE: this will NOT cause resource leak as the container will be restarted
        os._exit(0)

    async def _get_crs_cfg(self, cfg_path: Path | None) -> dict | None:
        if cfg_path is None or not cfg_path.exists():
            return None

        cfg_content = await self._download_file(cfg_path)
        if cfg_content is None:
            return None

        try:
            cfg_json = json.loads(cfg_content)
            return cfg_json
        except Exception:
            return None

    async def _check_this_node_crs_cfg(self):
        plan_cfg = await self._get_crs_cfg(get_planned_crs_java_cfg_path(self.pod_id))
        cur_cfg = await self._get_crs_cfg(get_crs_java_cfg_path(self.pod_id))

        if cur_cfg is None:
            # This should not happen
            self.logH(None, f"{CRS_ERR} No current crs config found")
            return
        if plan_cfg is None:
            # NOTE: not scheduled yet
            return
        planned_harnesses = set(plan_cfg.get("target_harnesses", []))
        cur_harnesses = set(cur_cfg.get("target_harnesses", []))
        if len(planned_harnesses) == 0:
            self.logH(None, "No planned crs config found")
            return
        if planned_harnesses == cur_harnesses:
            self.logH(
                None,
                f"Planned crs config matches current config: {planned_harnesses}",
            )
            return
        self.logH(
            None,
            f"Planned CRS config harnesses {planned_harnesses} differs from current config {cur_harnesses}. Exiting to trigger restart.",
        )
        await self._exit_procedure()

    async def _is_ready_to_sched(
        self, diff_analysis_files: list[tuple[str, Path]]
    ) -> tuple[bool, dict[str, DiffReachabilityReport]]:
        """Check if ready to schedule based on diff analysis files."""
        diff_results = {}
        force_schedule = time.time() >= self.max_sched_time
        ready_to_schedule = True

        if force_schedule:
            self.logH(
                None, "Max schedule time reached, scheduling diff-based tasks anyway"
            )

        for pod_id, file_path in diff_analysis_files:
            content = await self._download_file(file_path)
            if content is None:
                self.logH(
                    None, f"Failed to download diff analysis result from {file_path}"
                )
                ready_to_schedule = False
                continue

            try:
                diff_report = DiffReachabilityReport.frm_dict(json.loads(content))
                diff_results[pod_id] = diff_report

                if not diff_report.from_all_cg_sources():
                    ready_to_schedule = False
            except Exception as e:
                self.logH(
                    None,
                    f"Error parsing diff analysis result from {file_path}: {str(e)}",
                )
                ready_to_schedule = False

        return force_schedule or ready_to_schedule, diff_results

    async def _do_schedule(self, diff_results: dict[str, DiffReachabilityReport]):
        reachable_harnesses = set()
        for pod_id, diff_report in diff_results.items():
            reachable_harnesses.update(diff_report.get_reachable_harnesses())
        self.logH(None, f"Diff mode reachable harnesses: {reachable_harnesses}")
        if len(reachable_harnesses) == 0:
            self.logH(
                None, f"{CRS_ERR} No reachable harnesses found, skipping scheduling"
            )
            return

        h_cycle = cycle(list(reachable_harnesses))
        for pod_id, cfg_path in get_all_crs_java_cfg_paths():
            try:
                pod_cfg = await self._get_crs_cfg(cfg_path)
                if pod_cfg is None:
                    self.logH(
                        None, f"{CRS_ERR} Failed to get crs config from {cfg_path}"
                    )
                    continue
                target_harnesses = set(pod_cfg["target_harnesses"])
                if len(target_harnesses.intersection(reachable_harnesses)) == 0:
                    picked_harness = next(h_cycle)
                    self.logH(
                        None,
                        f"Updating crs config for {pod_id} to add reachable harness {picked_harness}",
                    )
                    plan_cfg = {
                        "target_harnesses": list(
                            target_harnesses.union({picked_harness})
                        ),
                    }
                    plan_cfg_path = get_planned_crs_java_cfg_path(pod_id)
                    await self._upload_file(plan_cfg_path, json.dumps(plan_cfg))
                    self.logH(
                        None,
                        f"Uploaded planned crs config {plan_cfg} to {plan_cfg_path}",
                    )
            except Exception as e:
                self.logH(
                    None,
                    f"{CRS_ERR} Error in scheduling: {str(e)} {traceback.format_exc()}",
                )
                continue

        # Mark the scheduled.flag
        sched_flag = get_crs_java_sched_flag_path()
        await atomic_write_file(sched_flag, "scheduled")
        self.logH(None, f"Created scheduled flag file {sched_flag}")

    async def _try_diff_ana_based_schedule(self):
        current_time = time.time()
        if current_time < self.min_sched_time:
            self.logH(
                None, "Min schedule time not reached yet, skipping diff scheduling"
            )
            return

        diff_analysis_files = get_all_crs_java_diff_ana_paths()
        if not diff_analysis_files:
            self.logH(None, "No diff analysis files found, skipping diff scheduling")
            return

        ready_to_schedule, diff_results = await self._is_ready_to_sched(
            diff_analysis_files
        )
        if ready_to_schedule:
            await self._do_schedule(diff_results)

    async def _async_run(self, _):
        """NOTE: till now we only do one-time scheduling for diff analysis."""
        if not self.enabled:
            self.logH(None, f"Module {self.name} is disabled")
            return

        if self.crs.meta.is_diff_mode() is False:
            self.logH(None, "DiffScheduler module is only supported in diff mode, skip")
            return

        if self.diff_schedule_dir is None:
            self.logH(
                None,
                f"{CRS_WARN} CRS_JAVA_SHARE_DIR environment variable not set. Diff scheduler monitoring disabled.",
            )
            return

        if self.pod_id is None:
            self.logH(
                None,
                f"{CRS_WARN} CRS_JAVA_POD_NAME environment variable not set, so pod_id is None. Diff scheduler monitoring disabled.",
            )
            return

        cpu_list = await self.crs.cpuallocator.poll_allocation(None, self.name)
        cp_name = self.crs.cp.name
        self.logH(
            None,
            f"Module {self.name} for CP '{cp_name}' will use CPU cores: {cpu_list}",
        )

        try:
            self.logH(None, f"Monitoring diff schedule dir: {self.diff_schedule_dir}")

            first = True
            while self.crs.should_continue():
                try:
                    if first:
                        await self._upload_this_node_crs_cfg()
                        first = False

                    flag_path = get_crs_java_sched_flag_path()
                    has_sched = flag_path and flag_path.exists()
                    if not has_sched:
                        await self._upload_this_node_diff_ana_results()
                        if self.crs.is_leader():
                            await self._try_diff_ana_based_schedule()

                    await self._check_this_node_crs_cfg()

                except Exception as e:
                    self.logH(
                        None,
                        f"{CRS_ERR} Error in diff scheduler: {str(e)} {traceback.format_exc()}",
                    )

                finally:
                    await asyncio.sleep(self.check_interval)

        except Exception as e:
            self.logH(
                None,
                f"{CRS_ERR} Diff scheduler failed: {str(e)}, traceback: {traceback.format_exc()}",
            )
        finally:
            self.logH(None, f"{self.name} completed")
