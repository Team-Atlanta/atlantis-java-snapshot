#!/usr/bin/env python3
import asyncio
import hashlib
import json
import traceback
import uuid
from pathlib import Path
from typing import List
from uuid import UUID

import aiofiles
from libCRS import CRS, HarnessRunner, Module, util
from pydantic import BaseModel, Field, field_validator

from .base_objs import SarifAnalysisResult
from .utils import CRS_ERR_LOG, CRS_WARN_LOG, atomic_write_file
from .utils_nfs import get_sarif_ana_result_dir, get_sarif_share_full_cg_dir

CRS_ERR = CRS_ERR_LOG("sariflistener-mod")
CRS_WARN = CRS_WARN_LOG("sariflistener-mod")


class SARIFListenerParams(BaseModel):
    enabled: bool = Field(
        ..., description="**Mandatory**, true/false to enable/disable this module."
    )

    @field_validator("enabled")
    def enabled_should_be_boolean(cls, v):
        if not isinstance(v, bool):
            raise ValueError("enabled must be a boolean")
        return v


class SARIFListener(Module):
    def __init__(
        self,
        name: str,
        crs: CRS,
        params: SARIFListenerParams,
        run_per_harness: bool,
    ):
        super().__init__(name, crs, run_per_harness)
        self.params = params
        self.enabled = self.params.enabled
        self.workdir = self.get_workdir("") / self.crs.cp.name
        self.sarif_dir = get_sarif_ana_result_dir()
        self.sarif_full_cg_dir = get_sarif_share_full_cg_dir()
        self.full_cg_file = self.workdir / "sarif-cg.json"
        self.full_cg_file.parent.mkdir(parents=True, exist_ok=True)
        self.processed_json_hashes = set()
        self.processed_done_files = set()
        self.processed_cg_files = set()

    def _init(self):
        pass

    async def _async_prepare(self):
        pass

    async def _async_test(self, hrunner: HarnessRunner):
        util.TODO("Add test")

    async def _async_get_mock_result(self, hrunner: HarnessRunner | None):
        util.TODO("Add mock result")

    async def _find_sarif_files(self) -> List[Path]:
        """Find all SARIF files in the monitoring directory"""
        if not self.sarif_dir:
            return []

        json_files = []
        for file_path in self.sarif_dir.glob("*/*.json"):
            json_files.append(file_path)

        return json_files

    async def _find_done_sarif_files(self) -> List[Path]:
        """Find all SARIF .done files in the monitoring directory"""
        if not self.sarif_dir:
            return []

        done_files = []
        for file_path in self.sarif_dir.glob("*/*.done"):
            done_files.append(file_path)

        return done_files

    async def _find_cg_files(self) -> List[Path]:
        """Find all SARIF full callgraph files in the monitoring directory"""
        cg_files = []

        if self.sarif_full_cg_dir:
            for file_path in self.sarif_full_cg_dir.glob("whole-*.json"):
                cg_files.append(file_path)

        return cg_files

    def _extract_timestamp_from_filename(self, filename: str) -> tuple[int, int]:
        """
        Extract unix timestamp from filename format: whole-{unix_timestamp}-{md5sum}.json
        Returns a tuple of (extracted_timestamp, file_system_timestamp)
        """
        file_path = Path(filename) if isinstance(filename, str) else filename
        fs_timestamp = int(file_path.stat().st_mtime)

        try:
            # Split by '-' and get the timestamp part (second element)
            parts = file_path.name.split("-")
            if len(parts) >= 3 and parts[0] == "whole":
                return (int(parts[1]), fs_timestamp)
        except (ValueError, IndexError):
            self.logH(
                None,
                f"{CRS_WARN} Failed to extract timestamp from filename: {file_path.name}",
            )

        # Fallback to file system timestamp
        return (0, fs_timestamp)

    async def _notify_new_sarif(self, result: SarifAnalysisResult):
        """Notify when a new SARIF analysis result is found."""
        # NOTE: it is safe to directly call this at this stage
        await self.crs.sinkmanager.on_event_new_sarif_challenge(result)

    async def _notify_solved_sarif(self, sarif_id: UUID):
        """Notify when a SARIF analysis is marked as solved."""
        # NOTE: it is safe to directly call this at this stage
        await self.crs.sinkmanager.on_event_sarif_challenge_solved(sarif_id)

    async def _process_new_sarif_files(self):
        """Process new SARIF JSON files"""
        json_files = await self._find_sarif_files()
        for json_file in json_files:
            try:
                if self.crs.verbose:
                    self.logH(None, f"Processing SARIF file: {json_file}")

                async with aiofiles.open(json_file, "r") as f:
                    content = await f.read()

                    content_hash = hashlib.md5(content.encode()).hexdigest()
                    if content_hash in self.processed_json_hashes:
                        if self.crs.verbose:
                            self.logH(
                                None,
                                f"Skipping already processed content in file: {json_file}",
                            )
                        continue

                    self.logH(None, f"Found new SARIF content in file: {json_file}")
                    data = json.loads(content)
                    result = SarifAnalysisResult(**data["analysis_result"])
                    await self._notify_new_sarif(result)

                    self.processed_json_hashes.add(content_hash)
            except Exception as e:
                # NOTE: it can fail since it is created by sarif system: 1) read in the middle of the write; 2) content itself is invalid
                self.logH(
                    None,
                    f"{CRS_WARN} processing SARIF file {json_file}: {str(e)} {traceback.format_exc()}",
                )

    async def _process_done_sarif_files(self):
        """Process SARIF .done files"""
        done_files = await self._find_done_sarif_files()
        for done_file in done_files:
            if done_file not in self.processed_done_files:
                try:
                    self.logH(None, f"Found SARIF .done file: {done_file}")

                    sarif_id_str = done_file.stem
                    sarif_id = uuid.UUID(sarif_id_str)
                    await self._notify_solved_sarif(sarif_id)

                    self.processed_done_files.add(done_file)
                except Exception as e:
                    # NOTE: .done file is empty, so should be processed correctly
                    self.logH(
                        None,
                        f"{CRS_ERR} processing .done file {done_file}: {str(e)} {traceback.format_exc()}",
                    )

    async def _process_new_cg_files(self):
        """Find all SARIF full callgraph files in the monitoring directory"""
        try:
            cg_files = await self._find_cg_files()
            if not cg_files:
                return

            timestamp_tuples = [
                self._extract_timestamp_from_filename(f) for f in cg_files
            ]
            if any(ts[0] > 0 for ts in timestamp_tuples):
                # Use extracted timestamps when available
                latest_index = max(
                    range(len(timestamp_tuples)), key=lambda i: timestamp_tuples[i][0]
                )
            else:
                # Fall back to file system timestamps
                latest_index = max(
                    range(len(timestamp_tuples)), key=lambda i: timestamp_tuples[i][1]
                )

            latest_cg_file = cg_files[latest_index]
            if latest_cg_file.name in self.processed_cg_files:
                if self.crs.verbose:
                    self.logH(
                        None, f"Skipping already processed CG file: {latest_cg_file}"
                    )
                return

            async with aiofiles.open(latest_cg_file, "r") as f:
                content = await f.read()
                # Verify JSON is valid by parsing it
                json.loads(content)

            self.logH(None, f"Found new valid callgraph file: {latest_cg_file}")
            await atomic_write_file(self.full_cg_file, content)
            self.processed_cg_files.add(latest_cg_file.name)

        except Exception as e:
            # NOTE: it can fail since it is created by sarif system: 1) read in the middle of the write; 2) content itself is invalid
            self.logH(
                None,
                f"{CRS_WARN} processing SARIF full callgraph files: {str(e)} {traceback.format_exc()}",
            )

    async def _async_run(self, _):
        if not self.enabled:
            self.logH(None, f"Module {self.name} is disabled")
            return

        if not self.sarif_dir:
            self.logH(
                None,
                f"{CRS_WARN} SARIF_ANA_RESULT_DIR environment variable not set. SARIF monitoring disabled.",
            )
            return

        cpu_list = await self.crs.cpuallocator.poll_allocation(None, self.name)
        cp_name = self.crs.cp.name
        self.logH(
            None,
            f"Module {self.name} for CP '{cp_name}' will use CPU cores: {cpu_list}",
        )

        try:
            self.logH(None, f"Monitoring SARIF analysis result dir: {self.sarif_dir}")

            while self.crs.should_continue():
                # Files from the SARIF analysis result dir
                await self._process_new_sarif_files()
                await self._process_done_sarif_files()
                # Files from the SARIF full callgraph dir
                await self._process_new_cg_files()
                await asyncio.sleep(10)

        except Exception as e:
            self.logH(
                None,
                f"{CRS_ERR} SARIF listener failed: {str(e)}, traceback: {traceback.format_exc()}",
            )
        finally:
            self.logH(None, f"{self.name} completed")
