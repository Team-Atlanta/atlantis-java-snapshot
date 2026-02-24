#!/usr/bin/env python3
import os
import random
import traceback
from typing import Dict, List, Tuple

import aiofiles
from libCRS import CRS, HarnessRunner, Module, util
from pydantic import BaseModel, Field, field_validator

from .jazzer import is_fuzzing_module
from .utils import CRS_ERR_LOG

CRS_ERR = CRS_ERR_LOG("cpu-alloc")


class CPUAllocatorParams(BaseModel):
    cpubaseno: int = Field(
        0,
        description="**Optional**, a non-negative integer with default value 0, the base index to start allocating CPU cores.",
    )
    maxncpu: int = Field(
        0,
        description="**Optional**, a non-negative integer with default value 0 specifying the maximum number of CPU cores to allocate. If `maxncpu == 0 or maxncpu > os.cpu_count`, it will be `os.cpu_count`.",
    )
    ttl_core_ids: List[int] = Field(
        [],
        description="**Optional**, total list of CPU core ids used for this CRS instance. If specified, `cpubaseno` and `maxncpu` will be override. This eaze the evaluation.",
    )
    jazzer_cpu_ratio: float = Field(
        0.8,
        description="**Optional**, a float in [0, 1] with default value 0.8, the ratio of CPU cores allocated to Jazzer modules, will be override by `jazzer_ncpu` if specified.",
    )
    jazzer_ncpu: int = Field(
        0,
        description="**Optional**, a non-negative integer with default value 0 which means use the `jazzer_cpu_ratio`. It exactly specifies the number of CPU cores allocated to Jazzer modules.",
    )
    skipped_mods: List[str] = Field(
        [],
        description="**Optional**, a list of module names to skip, default is an empty list. The skipped modules will share all CPU cores. `cpuallocator` module is always skipped.",
    )

    @field_validator("jazzer_cpu_ratio")
    def jazzer_cpu_ratio_should_be_in_0_to_1(cls, v):
        if v < 0 or v > 1:
            raise ValueError("jazzer_cpu_ratio must be a float in [0,1]")
        return v

    @field_validator("jazzer_ncpu")
    def jazzer_ncpu_should_be_non_negative(cls, v):
        if v is not None and v < 0:
            raise ValueError("jazzer_ncpu must be a non-negative integer")
        return v

    @field_validator("cpubaseno")
    def cpubaseno_should_be_non_negative(cls, v):
        if v is not None and v < 0:
            raise ValueError("cpubaseno must be a non-negative integer")
        return v

    @field_validator("maxncpu")
    def maxncpu_should_be_non_negative(cls, v):
        if v is not None and v < 0:
            raise ValueError("maxncpu must be a non-negative integer")
        return v

    @field_validator("ttl_core_ids")
    def ttl_core_ids_should_be_non_negative(cls, v):
        if any([i < 0 for i in v]):
            raise ValueError("ttl_core_ids must be a list of non-negative integers")
        return v


class CPUAllocator(Module):
    def __init__(
        self,
        name: str,
        crs: CRS,
        params: CPUAllocatorParams,
        run_per_harness: bool,
    ):
        super().__init__(name, crs, run_per_harness)
        self.envs: Dict[str, str] = {}
        self.ttl_fuzz_time: int = self.crs.ttl_fuzz_time
        self.workdir = self.get_workdir("")
        # Allocation mapping: (harness id|None) -> {module name -> list of CPU ids}
        self.allocation = {}

        self.params = params
        self.enabled = True  # keep align with other modules
        self.ttl_core_ids, self.maxncpu = self._init_usable_core_ids()
        self.jazzer_cpu_ratio, self.jazzer_ncpu = self._init_jazzer_core_ids()

        self.skipped_mods = self.params.skipped_mods

    def _init_usable_core_ids(self):
        available_cpus = sorted(os.sched_getaffinity(0))
        host_ncpu = len(available_cpus)

        if len(self.params.ttl_core_ids) == 0:
            if host_ncpu < 2:
                raise ValueError(
                    "Available CPU cores less than 2"
                )

            cpubaseno: int = self.params.cpubaseno
            maxncpu: int = self.params.maxncpu if self.params.maxncpu > 0 else host_ncpu
            if cpubaseno + maxncpu > host_ncpu:
                raise ValueError(
                    f"cpubaseno({cpubaseno}) + maxncpu({maxncpu}) > available cpus({host_ncpu})"
                )
            ttl_core_ids = available_cpus[cpubaseno : cpubaseno + maxncpu]

            return ttl_core_ids, maxncpu
        else:
            if len(self.params.ttl_core_ids) < 2:
                raise ValueError("The total number of CPU cores must be greater than 1")

            self.params.ttl_core_ids.sort()
            available_set = set(available_cpus)
            invalid = [c for c in self.params.ttl_core_ids if c not in available_set]
            if invalid:
                raise ValueError(
                    f"Requested CPU cores {invalid} not in available set {available_cpus}"
                )

            return self.params.ttl_core_ids, len(self.params.ttl_core_ids)

    def _init_jazzer_core_ids(self):
        jazzer_cpu_ratio = self.params.jazzer_cpu_ratio
        jazzer_ncpu = self.params.jazzer_ncpu
        if jazzer_ncpu != 0:
            # override the ratio using user specified jazzer_ncpu
            jazzer_cpu_ratio = float(jazzer_ncpu) / self.maxncpu
        else:
            # or update the jazzer_ncpu using the ratio
            jazzer_ncpu = int(jazzer_cpu_ratio * self.maxncpu)

        if jazzer_ncpu > self.maxncpu:
            raise ValueError(f"jazzer_ncpu({jazzer_ncpu}) > maxncpu({self.maxncpu})")

        return jazzer_cpu_ratio, jazzer_ncpu

    def _init(self):
        pass

    async def _async_prepare(self):
        pass

    async def _async_test(self, hrunner: HarnessRunner):
        util.TODO("Add test")

    async def _async_get_mock_result(self, hrunner: HarnessRunner | None):
        util.TODO("Add mock result")

    async def poll_allocation(
        self, hrunner: HarnessRunner | None, module_name: str
    ) -> List[int]:
        # Wait for _async_run to complete
        await self.async_wait_done()

        if hrunner is None:
            # The None key follows libCRS convention for CP-level modules
            return self.allocation[None][module_name]
        else:
            return self.allocation[hrunner.harness.name][module_name]

    def _collect_enabled_modules(self) -> Tuple[Dict[str, Module], List[Module]]:
        """Collect enabled modules and skipped modules separately."""
        enabled_mods, skipped_mods = {}, []
        for mod in self.crs.modules:
            if not mod.enabled:
                continue
            if mod.name in self.skipped_mods or mod.name == "cpuallocator":
                skipped_mods.append(mod)
            else:
                enabled_mods[mod.name] = mod
        return enabled_mods, skipped_mods

    def _identify_module_types(
        self, enabled_mods: Dict[str, Module]
    ) -> Tuple[List[Module], List[Module]]:
        """Identify Jazzer and non-Jazzer modules."""
        jazzer_mods = []
        nonjazzer_mods = []
        for mod in enabled_mods.values():
            if is_fuzzing_module(mod):
                jazzer_mods.append(mod)
            else:
                nonjazzer_mods.append(mod)
        return jazzer_mods, nonjazzer_mods

    def _plan_cpu_allocation(
        self,
        ttl_cpu_ids: List[int],
        jazzer_mods: List[Module],
        nonjazzer_mods: List[Module],
        skipped_mods: List[Module],
    ):
        """Plan the CPU allocation."""
        if self.jazzer_ncpu > 0:
            nonjazzer_core_ids = ttl_cpu_ids[: (-1 * self.jazzer_ncpu)]
            jazzer_core_ids = ttl_cpu_ids[(-1 * self.jazzer_ncpu) :]
        else:
            nonjazzer_core_ids = ttl_cpu_ids
            jazzer_core_ids = []

        jazzer_ncpu = len(jazzer_core_ids)

        harness_ids = [hr.harness.name for hr in self.crs.hrunners]
        jazzer_n_instance = len(harness_ids) * len(jazzer_mods)
        if jazzer_n_instance == 0:
            n_times = 0
        elif jazzer_n_instance > jazzer_ncpu:
            # at least every jazzer instance has one core (shared if too few)
            n_times = 1
        else:
            n_times = jazzer_ncpu // jazzer_n_instance

        allocation_map = {id: {} for id in harness_ids}
        allocation_map[None] = {}

        # Jazzer modules
        core_idx = 0
        for harness_id in harness_ids:
            for mod in jazzer_mods:
                core_ids = [
                    jazzer_core_ids[i % jazzer_ncpu]
                    for i in range(core_idx, core_idx + n_times)
                ]
                allocation_map[harness_id][mod.name] = core_ids
                core_idx += n_times

        # remaining cores are randomly assigned to Jazzer modules
        for i in range(core_idx, jazzer_ncpu):
            # randomly pick harness_id and mod.name to assign
            rand_id = random.choice(harness_ids)
            rand_nm = random.choice(list(allocation_map[rand_id].keys()))
            allocation_map[rand_id][rand_nm].append(jazzer_core_ids[i % jazzer_ncpu])

        # Nonjazzer modules
        if self.crs.deepgen.enabled:
            # Assign deepgen cores to each harness
            self.logH(None, "Deepgen module cpu allocation")
            self.logH(None, f"nonjazzer_core_ids: {nonjazzer_core_ids}")
            if jazzer_ncpu <= 12:
                # node core <= 16
                num_cores = 1
            elif jazzer_ncpu <= 38:
                # node core <= 48
                num_cores = 1
            elif jazzer_ncpu <= 76:
                # node core <= 96
                num_cores = 2
            else:
                # node core > 96
                num_cores = 2

            num_cores = min(num_cores, len(nonjazzer_core_ids))
            allocation_map[None][self.crs.deepgen.name] = nonjazzer_core_ids[:num_cores]
            if num_cores < len(nonjazzer_core_ids):
                nonjazzer_core_ids = nonjazzer_core_ids[num_cores:]
                self.logH(
                    None,
                    f"Deepgen module assigned exclusive cores: {allocation_map[None][self.crs.deepgen.name]}",
                )
            else:
                self.logH(
                    None,
                    f"Deepgen module assigned shared cores: {allocation_map[None][self.crs.deepgen.name]}",
                )

        if self.crs.concolic.enabled:
            one_concolic_required_core_num = self.crs.concolic.get_num_cores()
            concolic_required_core_num = (
                len(harness_ids) * one_concolic_required_core_num
            )
            if concolic_required_core_num >= len(nonjazzer_core_ids):
                raise ValueError(
                    f"Not enough non-Jazzer cores for concolic execution: {len(nonjazzer_core_ids)} <= {concolic_required_core_num}"
                )
            # Assign concolic cores to each harness
            self.logH(
                None,
                f"Concolic harnesses: {harness_ids}, required cores: {concolic_required_core_num}, nonjazzer cores ids {nonjazzer_core_ids}",
            )
            for i in range(len(harness_ids)):
                harness_id = harness_ids[i]
                allocation_map[harness_id][self.crs.concolic.name] = nonjazzer_core_ids[
                    i
                    * one_concolic_required_core_num : (i + 1)
                    * one_concolic_required_core_num
                ]
                # print detail for debug
                self.logH(
                    None,
                    f"Concolic harness {harness_id} assigned cores: {allocation_map[harness_id][self.crs.concolic.name]}",
                )
                self.logH(
                    None,
                    f"Concolic harness {harness_id} assigned cores: {nonjazzer_core_ids[i * one_concolic_required_core_num : (i + 1) * one_concolic_required_core_num]}",
                )

            # Remove the cores assigned to concolic from nonjazzer_core_ids
            nonjazzer_core_ids = nonjazzer_core_ids[concolic_required_core_num:]

        for mod in nonjazzer_mods:
            if mod.run_per_harness:
                if mod.name != self.crs.concolic.name:
                    for harness_id in harness_ids:
                        allocation_map[harness_id][mod.name] = nonjazzer_core_ids
                else:
                    # add shared core to concolic harnesses
                    # at least 2 cores are exclusive for all nonjazzer modules
                    self.logH(
                        None,
                        f"len(nonjazzer_core_ids): {len(nonjazzer_core_ids)}, len(harness_ids): {len(harness_ids)}",
                    )
                    if len(nonjazzer_core_ids) >= len(harness_ids) + 2:
                        for harness_id in harness_ids:
                            allocation_map[harness_id][mod.name].extend(
                                nonjazzer_core_ids[-1 * len(harness_ids) :]
                            )
            else:
                if mod.name != self.crs.deepgen.name:
                    allocation_map[None][mod.name] = nonjazzer_core_ids

        # Skipped modules
        for mod in skipped_mods:
            if mod.run_per_harness:
                for harness_id in harness_ids:
                    allocation_map[harness_id][mod.name] = ttl_cpu_ids
            else:
                allocation_map[None][mod.name] = ttl_cpu_ids

        # Set crs main process cpu affinity to nonjazzer cores (if possible)
        if len(nonjazzer_core_ids) > 0:
            self.logH(
                None, f"Set CRS main process CPU affinity to {nonjazzer_core_ids}"
            )
            os.sched_setaffinity(0, nonjazzer_core_ids)
        else:
            self.logH(
                None, "No nonjazzer cores to set CRS main process CPU affinity, skip"
            )

        self.allocation = allocation_map

    def _pretty_print_allocation(self):
        lines = ["{"]
        for key, modules in self.allocation.items():
            key_str = "null" if key is None else f'"{key}"'
            lines.append(f"  {key_str}: {{")
            for module_name, cpu_ids in modules.items():
                lines.append(f'    "{module_name}": {cpu_ids},')
            lines.append("  },")
        lines.append("}")
        return "\n".join(lines)

    async def _async_run(self, _):
        """
        Allocation strategy:
          - Jazzer modules: exclusive CPU cores
            - # of ttl cores = jazzer_ncpu if jazzer_ncpu > 0 else jazzer_cpu_ratio * maxncpu
            - Core assign unit: 1 (Jazzer module, Harness id) <=> 1 core <=> 1 fuzz instance
          - Nonjazzer modules: share all nonjazzer cores
            - both CP-level modules & harness-level nonjazzer modules
          - User skipped modules: share all cores (testing/evaluation purpose)
            - 'cpuallocator' is always skipped
          - Disabled modules: excluded

        Format of self.allocation:
        {
          (harness id|None for CP-level module): {
            "module name" -> [list of CPU ids]
          }
        }
        """

        try:
            self.logH(None, f"Module {self.name} starts")

            enabled_mods, skipped_mods = self._collect_enabled_modules()
            jazzer_mods, nonjazzer_mods = self._identify_module_types(enabled_mods)

            self._plan_cpu_allocation(
                self.ttl_core_ids, jazzer_mods, nonjazzer_mods, skipped_mods
            )

            # asyncly dump the allocation to file
            alloc_json_ctnt = self._pretty_print_allocation()
            alloc_json_path = self.workdir / self.crs.cp.name / "allocation.json"
            alloc_json_path.parent.mkdir(parents=True, exist_ok=True)

            async with aiofiles.open(alloc_json_path, "w") as f:
                await f.write(alloc_json_ctnt)

            self.logH(None, f"CPU allocation: {alloc_json_ctnt}")

        except Exception as e:
            self.logH(
                None,
                f"{CRS_ERR} Module {self.name} failed: {e} {traceback.format_exc()}",
            )
