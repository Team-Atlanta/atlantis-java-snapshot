#!/usr/bin/env python3
import os
import shlex
import traceback
from pathlib import Path
from typing import List

import aiofiles
from libCRS import CRS, HarnessRunner, Module, util
from pydantic import BaseModel, Field, field_validator

from .utils import (
    CRS_ERR_LOG,
    CRS_WARN_LOG,
    get_env_exports,
    get_env_or_abort,
    run_process_and_capture_output,
)

CRS_ERR = CRS_ERR_LOG("deepgen-mod")
CRS_WARN = CRS_WARN_LOG("deepgen-mod")


class DeepGenParams(BaseModel):
    enabled: bool = Field(
        ..., description="**Mandatory**, true/false to enable/disable this module."
    )

    models: str = Field(
        default="claude-3-7-sonnet-20250219:1,gpt-4o:1",
        description="Comma-separated list of generation models with weights. Format: 'model1:weight1,model2:weight2,...'",
    )

    spa_interval: int = Field(
        default=300,
        description="Interval in seconds between SPA (Stuck Point Analysis) cycles (default: 300)",
    )

    spa_max_stuck_points: int = Field(
        default=5,
        description="Maximum number of stuck points to process per SPA analysis cycle (default: 5)",
    )

    @field_validator("enabled")
    def enabled_should_be_boolean(cls, v):
        if not isinstance(v, bool):
            raise ValueError("enabled must be a boolean")
        return v


class DeepGenModule(Module):
    def __init__(
        self,
        name: str,
        crs: CRS,
        params: DeepGenParams,
        run_per_harness: bool = False,
    ):
        super().__init__(name, crs, run_per_harness)
        self.ttl_fuzz_time: int = self.crs.ttl_fuzz_time
        self.params = params
        self.enabled = self.params.enabled
        self.workdir = self.get_workdir("") / self.crs.cp.name
        self.workdir.mkdir(parents=True, exist_ok=True)
        self.zmq_url = f"ipc://{self.workdir}/deepgen-zmq-socket"
        self.cli_tool_path = (
            Path(get_env_or_abort("JAVA_CRS_SRC")) / "deepgen" / "cli.py"
        )
        self.task_req_dir = self.workdir / "task_reqs"
        self.task_req_dir.mkdir(parents=True, exist_ok=True)

    def _init(self):
        pass

    async def _async_prepare(self):
        if not self.enabled:
            self.logH(None, f"Module {self.name} is disabled, skipping _async_prepare.")
            return

    async def _async_test(self, hrunner: HarnessRunner):
        util.TODO("Add test")

    async def _async_get_mock_result(self, hrunner: HarnessRunner | None):
        util.TODO("Add mock result")

    def get_task_req_dir(self) -> Path:
        if not self.enabled:
            self.logH(None, f"Module {self.name} is disabled, returning empty path.")
            return Path()
        return self.task_req_dir

    async def _create_command_sh(
        self,
        cmd: List[str],
        script_name: str,
        working_dir: str = None,
        timeout: int = None,
        cpu_list: List[int] = None,
        buffer_output: bool = True,
    ) -> Path:
        if timeout:
            cmd = ["timeout", "-s", "SIGKILL", f"{timeout}s"] + cmd
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
{cmd_str}
"""
        command_sh = self.workdir / script_name
        async with aiofiles.open(command_sh, "w") as f_sh:
            await f_sh.write(command_sh_content)
        command_sh.chmod(0o755)
        return command_sh

    async def _collect_exec_files(self) -> List[str]:
        """Collect all expected JaCoCo exec files from all Jazzer fuzzing modules."""
        exec_files = []
        
        # Get all enabled Jazzer modules that have JaCoCo coverage dumping enabled
        jazzer_mods = [
            mod for mod in self.crs.modules 
            if hasattr(mod, 'get_expected_exec_files') and mod.enabled
            and hasattr(mod, 'params') and hasattr(mod.params, 'jacoco_cov_dump_period')
            and mod.params.jacoco_cov_dump_period is not None
        ]
        
        # Collect exec files from all harnesses and jazzer modules
        for hrunner in self.crs.hrunners:
            for jazzer_mod in jazzer_mods:
                try:
                    paths = await jazzer_mod.get_expected_exec_files(hrunner)
                    exec_files.extend([str(path) for path in paths])
                    self.logH(
                        hrunner,
                        f"Added exec files from {jazzer_mod.name} (JaCoCo period: {jazzer_mod.params.jacoco_cov_dump_period}s)"
                    )
                except Exception as e:
                    self.logH(
                        hrunner,
                        f"{CRS_WARN} Failed to get exec files from {jazzer_mod.name}: {e}"
                    )
        
        return exec_files

    async def _run_deepgen(self, cpu_list: List[int]):
        try:
            cp_metadata_path = self.crs.meta.meta_path
            
            # Collect exec files from all Jazzer instances
            exec_files = await self._collect_exec_files()
            if exec_files:
                self.logH(None, f"Collected {len(exec_files)} exec file paths for SPA analysis")

            cmd = ["python3.12", "-u", "-m", "deepgen.cli"]
            cmd.append("--cores")
            for cpu in cpu_list:
                cmd.append(str(cpu))
            cmd.extend(
                [
                    "--models",
                    self.params.models,
                    "--metadata",
                    cp_metadata_path,
                    "--workdir",
                    str(self.workdir),
                    "--zmq-url",
                    self.zmq_url,
                    "--run-time",
                    str(max(self.ttl_fuzz_time - 5, 0)),
                    "--para",
                    3,
                    "--spa-interval",
                    str(self.params.spa_interval),
                    "--spa-max-stuck-points",
                    str(self.params.spa_max_stuck_points),
                ]
            )
            
            # Add exec files if available
            if exec_files:
                cmd.append("--exec-files")
                cmd.extend(exec_files)

            command_sh = await self._create_command_sh(
                cmd,
                "deepgen-cli-command.sh",
                timeout=self.ttl_fuzz_time,
                cpu_list=cpu_list,
            )
            log_file = self.workdir / "deepgen.log"

            self.logH(
                None,
                f"Running DeepGen CLI command: {' '.join(str(item) for item in cmd)}",
            )
            ret = await run_process_and_capture_output(command_sh, log_file)

            if ret == 137 and not self.crs.should_continue():
                self.logH(
                    None,
                    f"DeepGen CLI was force ended (ret: {ret})",
                )
            elif ret != 0:
                self.logH(
                    None,
                    f"{CRS_WARN} DeepGen CLI unexpectedly exits with ret {ret}",
                )
            else:
                self.logH(None, "DeepGen CLI completed successfully")

        except Exception as e:
            exception_trace = "".join(
                traceback.format_exception(type(e), e, e.__traceback__)
            )
            self.logH(
                None,
                f"{CRS_ERR} DeepGen CLI failed: {str(e)}, traceback: {exception_trace}",
            )

    async def _async_run(self, _):
        if not self.enabled:
            self.logH(None, f"Module {self.name} is disabled")
            return

        cpu_list = await self.crs.cpuallocator.poll_allocation(None, self.name)
        if not cpu_list:
            self.logH(None, f"No CPUs allocated for module {self.name}, skipping.")
            return

        self.logH(None, f"Starting DeepGen module using cores: {cpu_list}")

        try:
            await self._run_deepgen(cpu_list)
        except Exception as e:
            exception_trace = "".join(
                traceback.format_exception(type(e), e, e.__traceback__)
            )
            self.logH(
                None,
                f"{CRS_ERR} Module {self.name} encountered an exception:\n{exception_trace}",
            )
