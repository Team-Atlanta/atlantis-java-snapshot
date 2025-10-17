#!/usr/bin/env python3
import asyncio
import os
import shlex
import traceback
from pathlib import Path
from typing import List

import aiofiles
from libCRS import CRS, HarnessRunner, Module, util
from pydantic import BaseModel, Field, field_validator

from .jazzer import is_fuzzing_module
from .utils import (
    CRS_ERR_LOG,
    CRS_WARN_LOG,
    get_env_exports,
    get_env_or_abort,
    run_process_and_capture_output,
)

CRS_ERR = CRS_ERR_LOG("llmfuzzaug-mod")
CRS_WARN = CRS_WARN_LOG("llmfuzzaug-mod")


class LLMFuzzAugmentorParams(BaseModel):
    enabled: bool = Field(
        ..., description="**Mandatory**, true/false to enable/disable this module."
    )
    stuck_detection: int = Field(
        ..., description="**Mandatory**, time in seconds to detect stuck harness."
    )
    verbose: bool = Field(
        False, description="**Optional**, true/false to enable/disable verbose mode."
    )

    @field_validator("enabled", "verbose")
    def enabled_and_verbose_should_be_boolean(cls, v):
        if not isinstance(v, bool):
            raise ValueError("enabled and verbose must be booleans")
        return v

    @field_validator("stuck_detection")
    def stuck_detection_should_be_greater_than_10(cls, v):
        if not isinstance(v, int) or v < 3:
            raise ValueError("stuck_detection must be an integer >= 3 (s)")
        return v


class LLMFuzzAugmentor(Module):
    def __init__(
        self,
        name: str,
        crs: CRS,
        params: LLMFuzzAugmentorParams,
        run_per_harness: bool,
    ):
        super().__init__(name, crs, run_per_harness)
        self.ttl_fuzz_time: int = self.crs.ttl_fuzz_time
        self.params = params
        self.enabled = self.params.enabled
        self.verbose = self.params.verbose
        self.stuck_detection = self.params.stuck_detection
        self.tool_cwd = Path(get_env_or_abort("JAVA_CRS_SRC")) / "jazzer-llm-augmented"
        self.timeout = self.crs.ttl_fuzz_time

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

    async def _run_one_llm_fuzz_augmentor(
        self, hrunner: HarnessRunner, cpu_list: List[int], jazzer_mod, jazzer_dir: Path
    ):
        try:
            jazzer_dir.mkdir(parents=True, exist_ok=True)

            target_class = hrunner.crs.meta.get_harness_class(hrunner.harness)
            classpath = ":".join(
                hrunner.crs.meta.get_harness_classpath(hrunner.harness)
            )
            source_dir = hrunner.crs.meta.cp_full_src

            cmds = [
                "timeout",
                "-s",
                "SIGKILL",
                f"{str(self.timeout)}s",
                "taskset",
                "-c",
                ",".join(map(str, cpu_list)),
                "python3.12",
                "-u",
                "-m",
                "jazzer_llm",
                "--cp",
                classpath,
                "--target_class",
                target_class,
                "--source-directory",
                str(source_dir),
                "--jazzer-directory",
                str(jazzer_dir.resolve()),
                "--stuck-wait-time",
                str(self.stuck_detection),
                "--no-use-docker",
                "--debug",
                str(self.verbose),
            ]
            cmd_str = " ".join(map(shlex.quote, cmds))

            llmfuzzaug_dir = jazzer_dir / "llmfuzzaug"
            llmfuzzaug_dir.mkdir(parents=True, exist_ok=True)
            command_sh = llmfuzzaug_dir / "command.sh"
            run_log = llmfuzzaug_dir / "run.log"

            command_sh_content = f"""#!/bin/bash
# Env
{get_env_exports(os.environ)}
# Cmd
cd "{str(self.tool_cwd.resolve())}"
{cmd_str} > "{run_log.resolve()}" 2>&1
"""
            async with aiofiles.open(command_sh, "w") as f:
                await f.write(command_sh_content)
            command_sh.chmod(0o755)

            self.logH(
                hrunner,
                f"Executing command.sh in {llmfuzzaug_dir}",
            )

            self.logH(hrunner, f"Running llm-fuzz-aug command.sh at {jazzer_dir}...")
            ret = await run_process_and_capture_output(
                command_sh, llmfuzzaug_dir / "run.log"
            )

            if ret == 137 and not self.crs.should_continue():
                self.logH(hrunner, f"llm-fuzz-aug is forced killed with ret {ret})")
            else:
                self.logH(
                    hrunner,
                    f"llm-fuzz-aug of {jazzer_mod.name}/{jazzer_dir.name} unexpectedly exits with ret {ret})",
                )

        except Exception as e:
            exception_trace = "".join(
                traceback.format_exception(type(e), e, e.__traceback__)
            )
            self.logH(
                hrunner,
                f"{CRS_ERR} _run_one_llm_fuzz_augmentor encountered an exception:\n{exception_trace}",
            )

    async def _async_run(self, hrunner: HarnessRunner):
        if not self.enabled:
            self.logH(hrunner, f"Module {self.name} is disabled, skipping _async_run.")
            return

        cpu_list = await self.crs.cpuallocator.poll_allocation(hrunner, self.name)
        if not cpu_list:
            self.logH(hrunner, f"No CPUs allocated for module {self.name}, skipping.")
            return

        self.logH(
            hrunner,
            f"Module {self.name} for {hrunner.harness.name} is running with CPUs {cpu_list}",
        )

        jazzer_mods = [
            mod for mod in self.crs.modules if is_fuzzing_module(mod) and mod.enabled
        ]
        if not jazzer_mods:
            self.logH(hrunner, "No enabled Jazzer modules found, skipping.")
            return

        try:
            tasks = []
            for jazzer_mod in jazzer_mods:
                jazzer_dirs = await jazzer_mod.get_expected_fuzz_instance_dirs(hrunner)
                if not jazzer_dirs:
                    self.logH(
                        hrunner,
                        f"No fuzz instance directories found for Jazzer module {jazzer_mod.name}, skipping.",
                    )
                    continue

                num = (len(jazzer_dirs) + 19) // 20
                self.logH(
                    hrunner, f"Launching {num} llmfuzzaug on {jazzer_dirs[:num]}."
                )
                for jazzer_dir in jazzer_dirs[:num]:
                    task = asyncio.create_task(
                        self._run_one_llm_fuzz_augmentor(
                            hrunner, cpu_list, jazzer_mod, jazzer_dir
                        )
                    )
                    tasks.append(task)

            self.logH(hrunner, f"Starting {len(tasks)} llm-fuzz-aug tasks.")
            await asyncio.gather(*tasks)

        except Exception as e:
            exception_trace = "".join(
                traceback.format_exception(type(e), e, e.__traceback__)
            )
            self.logH(
                hrunner,
                f"{CRS_ERR} Module {self.name} encountered an exception:\n{exception_trace} {traceback.format_exc()}",
            )
