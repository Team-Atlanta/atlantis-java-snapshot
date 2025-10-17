#!/usr/bin/env python3
import asyncio
import json
import os
import shlex
import shutil
import tarfile
import time
import traceback
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List

import aiofiles
from libCRS import CRS, HarnessRunner, Module
from pydantic import BaseModel, Field, field_validator

from .base_objs import Sinkpoint
from .utils import (
    CRS_ERR_LOG,
    CRS_WARN_LOG,
    download_file_async,
    get_env_exports,
    get_env_or_abort,
    run_process_and_capture_output,
)
from .utils_nfs import (
    get_sarif_shared_codeql_db_done_file,
    get_sarif_shared_codeql_db_path,
)

CRS_ERR = CRS_ERR_LOG("codeql-mod")
CRS_WARN = CRS_WARN_LOG("codeql-mod")


class CodeQLParams(BaseModel):
    enabled: bool = Field(
        ..., description="**Mandatory**, true/false to enable or disable this module."
    )

    @field_validator("enabled")
    def enabled_should_be_boolean(cls, v):
        if not isinstance(v, bool):
            raise ValueError("enabled must be a boolean")
        return v


class CodeQL(Module):
    """CodeQL analysis module for Java CRS."""

    def __init__(
        self,
        name: str,
        crs: CRS,
        params: CodeQLParams,
        run_per_harness: bool,
    ):
        super().__init__(name, crs, run_per_harness)
        self.params = params
        self.enabled = self.params.enabled
        self.workdir = self.get_workdir("") / self.crs.cp.name
        self.workdir.mkdir(parents=True, exist_ok=True)
        self.db_dir = self.workdir / "codeql-db"
        self.db_dir.mkdir(parents=True, exist_ok=True)
        self.db = self.db_dir / "codeql"
        self.results_file = self.workdir / "codeql_result.json"
        self.results_file.parent.mkdir(parents=True, exist_ok=True)
        self.tool_cwd = Path(get_env_or_abort("JAVA_CRS_SRC")) / "codeql"

    def _init(self):
        pass

    async def _async_prepare(self):
        pass

    async def _async_test(self, hrunner: HarnessRunner):
        pass

    async def _async_get_mock_result(self, hrunner):
        self.logH(hrunner, "Mock result for CodeQL")

    async def _extract_tarball(self, tarball: Path, outdir: Path):
        try:
            if outdir.exists():
                shutil.rmtree(outdir)

            outdir.mkdir(parents=True, exist_ok=True)

            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None, lambda: tarfile.open(tarball, "r:gz").extractall(path=outdir)
            )

            self.logH(None, f"Extracted {tarball.name} to {outdir}")
            return True
        except Exception as e:
            self.logH(
                None, f"{CRS_ERR} Extraction error: {str(e)} {traceback.format_exc()}"
            )
            return False

    async def _monitor_codeql_database(self) -> bool:
        self.logH(None, "Monitoring for CodeQL database")

        interval = 60
        counter = 0

        while self.crs.should_continue():
            try:
                if counter % interval != 0:
                    counter += 1
                    await asyncio.sleep(1)
                    continue
                else:
                    counter += 1

                # Check SARIF shared path
                sarif_db = get_sarif_shared_codeql_db_path()
                sarif_db_done = get_sarif_shared_codeql_db_done_file()

                db_files_exist = (
                    sarif_db_done
                    and sarif_db_done.exists()
                    and sarif_db
                    and sarif_db.exists()
                )
                if not db_files_exist:
                    continue

                self.logH(None, f"Found codeql.db at: {sarif_db}")
                local_db, file_ok = await download_file_async(
                    src_path=sarif_db,
                    dst_dir=self.workdir,
                    logger=lambda msg: self.logH(None, msg),
                    err_tag=CRS_ERR,
                )

                if not file_ok:
                    self.logH(
                        None,
                        f"{CRS_WARN} Failed to download codeql.db {sarif_db}, retry",
                    )
                    continue
                if await self._extract_tarball(local_db, self.db_dir):
                    if not self.db.exists():
                        self.logH(
                            None,
                            f"{CRS_ERR} Expected codeql db does not exist: {self.db}",
                        )
                        continue
                    self.logH(
                        None,
                        f"codeql.db extracted successfully to {self.db}",
                    )
                    return True
                else:
                    self.logH(
                        None,
                        f"{CRS_ERR} Failed to extract codeql.db {local_db}, retry",
                    )
            except Exception as e:
                self.logH(
                    None, f"{CRS_ERR} Monitor error: {str(e)} {traceback.format_exc()}"
                )

        self.logH(None, f"{CRS_WARN} Monitoring ended without finding database")
        return False

    async def _create_command_sh(
        self,
        cmd: List[str],
        script_name: str,
        working_dir: str,
        timeout: int,
        cpu_list: List[int],
        buffer_output: bool,
        log_prefix: str,
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
{cmd_str} > {str(self.workdir.resolve())}/{log_prefix}.log 2>&1
"""
        command_sh = self.workdir / script_name
        async with aiofiles.open(command_sh, "w") as f_sh:
            await f_sh.write(command_sh_content)
        command_sh.chmod(0o755)
        return command_sh

    async def _run_codeql_script(
        self, cpu_list: List[int], script_name: str, log_prefix: str
    ):
        """Shared logic for running CodeQL scripts."""
        self.logH(None, f"Running CodeQL {script_name} with CPUs: {cpu_list}")

        try:
            rest_time = self.crs.rest_time()
            if rest_time <= 0:
                self.logH(
                    None,
                    f"{CRS_WARN} No time left to run {script_name} (rest_time={rest_time})",
                )
                return

            script_path = self.tool_cwd / script_name
            if not script_path.exists():
                raise FileNotFoundError(f"CodeQL script not found: {script_path}")

            command_sh = await self._create_command_sh(
                [
                    str(script_path),
                    str(self.db),
                    str(self.results_file),
                ],
                f"command_{script_name}",
                str(self.tool_cwd),
                timeout=rest_time,
                cpu_list=cpu_list,
                buffer_output=True,
                log_prefix=log_prefix,
            )

            self.logH(None, f"Running CodeQL command: {command_sh}")
            log_file = self.workdir / "run.log"

            ret = await run_process_and_capture_output(command_sh, log_file)
            if ret == 0:
                self.logH(
                    None,
                    f"CodeQL {script_name} finished (ret: {ret}) in {time.time() - self.crs.start_time:.2f}s",
                )
            else:
                # Exit with != 0 and not killed by SIGKILL is unexpected
                self.logH(
                    None,
                    f"{CRS_ERR} CodeQL {script_name} unexpectedly exited with ret {ret} in {time.time() - self.crs.start_time:.2f}s",
                )
            return ret

        except Exception as e:
            self.logH(
                None,
                f"{CRS_ERR} CodeQL {script_name} error: {str(e)} {traceback.format_exc()}",
            )
            return -1

    async def _codeql_query(self, cpu_list: List[int]):
        """Run CodeQL queries."""
        return await self._run_codeql_script(cpu_list, "run.sh", "query")

    async def _update_sink(self, sink_dict: dict) -> bool:
        # Update sinkmanager
        try:
            sink_dict = sink_dict["coord"]
            code_coord = self.crs.query_code_coord(
                sink_dict["class_name"], sink_dict["line_num"]
            )
            if code_coord is None:
                self.logH(
                    None,
                    f"{CRS_WARN} Filter out sinkpoint {sink_dict['class_name']}:{sink_dict['line_num']} which has no code coordinate",
                )
                return False

            self.logH(
                None,
                f"Sinkpoint {sink_dict['class_name']}:{sink_dict['line_num']} found code coordinate: {code_coord}",
            )
            sink_dict.update(asdict(code_coord))
            sink = Sinkpoint.frm_dict(sink_dict)
            self.logH(None, f"CodeQL update sinkpoint to sinkmanager: {sink}")
            await self.crs.sinkmanager.on_event_update_sinkpoint(sink)
            return True
        except Exception as e:
            self.logH(
                None,
                f"{CRS_ERR} updating tgt sink {sink_dict} to sinkmanager: {str(e)} {traceback.format_exc()}",
            )
            return False

    async def _codeql_result_parsing(self):
        self.logH(None, "Parsing CodeQL results")
        try:
            if not self.results_file.exists():
                self.logH(
                    None, f"{CRS_ERR} Results file not found: {self.results_file}"
                )
                return

            async with aiofiles.open(self.results_file, "r") as f:
                results = await f.read()

            # Read json results
            sinkpoints = json.loads(results)
            if not isinstance(sinkpoints, list):
                self.logH(None, f"{CRS_ERR} Invalid results format: expected list")
                return

            total_sinks = len(sinkpoints)
            self.logH(None, f"Found {total_sinks} sinkpoints in results")

            kept_sinks = 0
            for sink_dict in sinkpoints:
                if await self._update_sink(sink_dict):
                    kept_sinks += 1

            filtered_sinks = total_sinks - kept_sinks
            self.logH(
                None, f"Sinkpoints stats: {filtered_sinks} filtered, {kept_sinks} kept"
            )

        except Exception as e:
            self.logH(
                None,
                f"{CRS_ERR} Result parsing error: {str(e)} {traceback.format_exc()}",
            )

    async def _run_codeql_analysis(self, cpu_list: List[int]):
        try:
            await self._codeql_query(cpu_list)
            await self._codeql_result_parsing()
        except Exception as e:
            self.logH(
                None, f"{CRS_ERR} Analysis error: {str(e)} {traceback.format_exc()}"
            )

    async def _async_run(self, _) -> Dict[str, Any]:
        if not self.enabled:
            self.logH(None, f"Module {self.name} is disabled")
            return

        self.logH(None, f"Starting {self.name}")

        try:
            cpu_list = await self.crs.cpuallocator.poll_allocation(None, self.name)
            self.logH(None, f"Allocated CPUs: {cpu_list}")

            if await self._monitor_codeql_database():
                await self._run_codeql_analysis(cpu_list)
            else:
                self.logH(None, f"{CRS_WARN} Skipping analysis (no database found)")
        except Exception as e:
            self.logH(
                None, f"{CRS_ERR} Module failed: {str(e)} {traceback.format_exc()}"
            )

        self.logH(None, f"{self.name} ended")
