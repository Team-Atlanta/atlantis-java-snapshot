#!/usr/bin/env python3
import ast
import asyncio
import json
import random
import shutil
import traceback
from asyncio.subprocess import PIPE
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import aiofiles
from libCRS import CRS, HarnessRunner, Module
from pydantic import BaseModel, Field, field_validator

from .base_objs import BeepSeed
from .utils import CRS_ERR_LOG, CRS_WARN_LOG, atomic_write_file, get_env_or_abort

CRS_ERR = CRS_ERR_LOG("dictgen-mod")
CRS_WARN = CRS_WARN_LOG("dictgen-mod")


class DictgenParams(BaseModel):
    enabled: bool = Field(
        ..., description="**Mandatory**, true/false to enable or disable this module."
    )
    gen_models: str = Field(
        default="gpt-4o:10,claude-3-5-sonnet:10",
        description="**Optional**, comma-separated list of generation models with weights. Format: 'model1:weight1,model2:weight2,...'. Supported models: gpt-4o, o1, gemini-1.5, claude-3-5-sonnet, claude-3-5-opus, claude-3-5-haiku. Example: 'gpt-4o:10,claude-3-5-sonnet:10,o1:5'",
    )

    @field_validator("enabled")
    def enabled_should_be_boolean(cls, v):
        if not isinstance(v, bool):
            raise ValueError("enabled must be a boolean")
        return v

    @field_validator("gen_models")
    def models_should_be_valid(cls, v):
        if not isinstance(v, str):
            raise ValueError("gen_models must be a string")

        valid_models = [
            "gpt-4o",
            "o1",
            "gemini-1.5",
            "claude-3-5-sonnet",
            "claude-3-5-opus",
            "claude-3-5-haiku",
        ]
        models = v.split(",")

        for model in models:
            if ":" not in model:
                raise ValueError(
                    "Invalid format for gen_models. Expected 'model:weight'"
                )
            model_name, weight = model.split(":")

            # Validate model name
            if model_name not in valid_models:
                raise ValueError(
                    f"Invalid model: {model_name}. Valid models are: {', '.join(valid_models)}"
                )

            # Validate weight
            if not weight.isdigit() or int(weight) <= 0:
                raise ValueError(
                    "Weight must be a positive integer in the format 'model:weight'"
                )
        return v


@dataclass
class DictGenReqBase:
    """Base request for dictionary generation."""

    pass


@dataclass
class InitialDictGenReq(DictGenReqBase):
    """Request for initial dictionary generation."""

    def get_cache_key(self) -> Tuple:
        """Get a unique key for caching the dictionary."""
        return ("initial", None, None)


@dataclass
class RefDiffDictGenReq(DictGenReqBase):
    """Request for reference diff dictionary generation."""

    def get_cache_key(self) -> Tuple:
        """Get a unique key for caching the dictionary."""
        return ("ref.diff", None, None)


@dataclass
class OSSDictGenReq(DictGenReqBase):
    """Request for OSS dictionary generation."""

    def get_cache_key(self) -> Tuple:
        """Get a unique key for caching the dictionary."""
        return ("ossdict", None, None)


@dataclass
class BEEPSeedDictGenReq(DictGenReqBase):
    """Request for BEEP seed dictionary generation."""

    beep_seed: BeepSeed = None

    def get_cache_key(self) -> Tuple:
        """Get a unique key for caching the dictionary."""
        return ("beepseedexp", self.beep_seed.stack_hash, hash(self.beep_seed.coord))


class FuzzDict:

    def __init__(self):
        self.entries = set()

    def add_entry(self, entry: str):
        self.entries.add(entry)

    def merge(self, other: "FuzzDict"):
        self.entries.update(other.entries)

    async def to_file(self, file_path: Path, logger):
        """Atomically write the dictionary to a file."""
        content = "# placeholder\n"
        for i, entry in enumerate(self.entries):
            try:
                val = "".join("\\x{:02x}".format(c) for c in entry.encode("utf-8"))
                content += f'str{i}="{val}"\n'
            except Exception as e:
                logger(
                    f"{CRS_ERR} Error encoding entry {i}: {e} {traceback.format_exc()}"
                )

        await atomic_write_file(file_path, content)

    def to_json(self) -> Dict:
        return {"entries": list(self.entries)}

    @classmethod
    def from_json(cls, json_obj: Dict) -> "FuzzDict":
        fuzz_dict = cls()
        for entry in json_obj.get("entries", []):
            fuzz_dict.add_entry(entry)
        return fuzz_dict

    @staticmethod
    def load_literal_str(value: str, logger) -> Optional[str]:
        try:
            result = ast.literal_eval(value)
            if isinstance(result, str):
                return result
            return None
        except Exception as e:
            logger(f"{CRS_ERR} loading literal string: {e} {traceback.format_exc()}")
            return None

    @classmethod
    def from_file(cls, file_path: Path, logger) -> "FuzzDict":
        fuzz_dict = cls()
        if not file_path.exists():
            return fuzz_dict

        with open(file_path, errors="ignore") as f:
            for i, line in enumerate(f, 1):
                try:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        logger("Skipping empty or comment line")
                        continue

                    logger(f"Processing line {i}: {line!r}")
                    entry = None
                    eq_pos = line.find("=")
                    if eq_pos >= 0 and len(line) > eq_pos + 1:
                        # Try extract the value after the '=' sign
                        value = line[eq_pos + 1 :].strip()
                        entry = cls.load_literal_str(value, logger)
                    if not entry:
                        # Try to extract the whole line as a dict entry
                        entry = cls.load_literal_str(line, logger)
                    if entry:
                        fuzz_dict.add_entry(entry)

                except Exception as e:
                    logger(
                        None,
                        f"{CRS_ERR} parsing dict line {i}: {line!r} - {e}\n{traceback.format_exc()}",
                    )
                    continue

        return fuzz_dict


class Dictgen(Module):
    def __init__(
        self,
        name: str,
        crs: CRS,
        params: DictgenParams,
        run_per_harness: bool,
    ):
        super().__init__(name, crs, run_per_harness)
        self.params = params
        self.enabled = self.params.enabled

        # Parse gen_models at init time
        self.models_with_weights = []
        self.total_weight = 0
        for model_spec in self.params.gen_models.split(","):
            model_name, weight_str = model_spec.split(":")
            weight = int(weight_str)
            self.models_with_weights.append((model_name, weight))
            self.total_weight += weight

        self.dictgen_tool = Path(get_env_or_abort("DICTGEN_DIR")) / "src" / "dictgen.py"
        self.workdir = self.get_workdir("")

        self.dict_cache = {}
        self.cache_lock = asyncio.Lock()
        self.request_queue = asyncio.Queue()

    def _pick_model(self) -> str:
        """Pick a model based on the parsed weights."""
        if not self.models_with_weights:
            return "gpt-4o"  # Default fallback

        r = random.randint(1, self.total_weight)
        cumulative_weight = 0

        for model_name, weight in self.models_with_weights:
            cumulative_weight += weight
            if r <= cumulative_weight:
                return model_name

        # Fallback to the first model if something goes wrong
        return self.models_with_weights[0][0]

    def _init(self):
        pass

    async def _async_prepare(self):
        pass

    async def _async_test(self, hrunner: HarnessRunner):
        pass

    async def _async_get_mock_result(self, hrunner: Optional[HarnessRunner]):
        pass

    async def _get_dict_from_cache(
        self, harness_name: str, context_id: str
    ) -> Optional[FuzzDict]:
        async with self.cache_lock:
            if (
                harness_name in self.dict_cache
                and context_id in self.dict_cache[harness_name]
            ):
                return self.dict_cache[harness_name][context_id]
            return None

    async def _add_dict_to_cache(
        self, harness_name: str, context_id: str, fuzz_dict: FuzzDict
    ):
        async with self.cache_lock:
            if harness_name not in self.dict_cache:
                self.dict_cache[harness_name] = {}

            self.dict_cache[harness_name][context_id] = fuzz_dict

    async def _gen_command_script(
        self, output_dir: Path, command_str: str, run_log: Path
    ) -> Path:
        """Generates a command script to run dictgen."""
        command_sh_content = f"""#!/bin/bash
cd "{str(self.dictgen_tool.parent.resolve())}"
{command_str} > "{run_log.resolve()}" 2>&1
"""

        command_sh = output_dir / "command.sh"
        async with aiofiles.open(command_sh, "w") as f:
            await f.write(command_sh_content)
        command_sh.chmod(0o755)

        return command_sh

    async def _run_dictgen_tool(self, workdir: Path, command_str: str) -> int:
        """Runs the dictgen tool with the provided command."""
        run_log = workdir / "run.log"
        command_sh = await self._gen_command_script(workdir, command_str, run_log)
        self.logH(None, f"Executing dictgen command: {command_sh.resolve()}")

        proc = await asyncio.create_subprocess_exec(
            str(command_sh),
            stdout=PIPE,
            stderr=PIPE,
        )
        _, _ = await proc.communicate()
        return proc.returncode

    async def _generate_initial_dict(self, harness_name: str, workdir: Path) -> Path:
        """Generate dictionary for initial context."""
        workdir = workdir / f"{harness_name}_initial"
        workdir.mkdir(parents=True, exist_ok=True)
        output_file = workdir / "fuzz.dict"

        hrunner = next(
            (h for h in self.crs.hrunners if h.harness.name == harness_name), None
        )
        if not hrunner:
            self.logH(
                None,
                f"{CRS_ERR} hrunner {harness_name} not found\n{traceback.format_exc()}",
            )
            return None

        src_path = self.crs.meta.get_harness_src_path(hrunner.harness)
        harness_entrypoint = self.crs.meta.get_harness_entrypoint(hrunner.harness)

        # Pick a model for this run
        model = self._pick_model()
        self.logH(None, f"Using model {model} for initial dictionary generation")

        command_str = (
            f"python3.12 {self.dictgen_tool} "
            f"--workdir {workdir} "
            f"--exact-match "
            f"--output {output_file} "
            f"--no-extract-trigger "
            f"--no-extract-parsable-string "
            f"--model-name {model} "
            f"--path {src_path} "
            # TODO: perhaps use more funcs here (need certain static analysis knowledge)
            f"--funcs {harness_entrypoint}"
        )

        ret = await self._run_dictgen_tool(workdir, command_str)
        if ret != 0:
            self.logH(
                None,
                f"{CRS_ERR} Error running dictgen for initial context: {ret}\n{traceback.format_exc()}",
            )
            return None
        return output_file

    async def _generate_refdiff_dict(self, harness_name: str, workdir: Path) -> Path:
        """Generate dictionary for ref.diff context."""
        workdir = workdir / f"{harness_name}_refdiff"
        workdir.mkdir(parents=True, exist_ok=True)
        output_file = workdir / "fuzz.dict"

        if not self.crs.meta.is_diff_mode():
            self.logH(
                None,
                f"{CRS_WARN} Not in diff mode, skipping ref.diff dictionary generation",
            )
            return None

        ref_diff_path = self.crs.meta.get_ref_diff_path()
        cp_full_src = self.crs.meta.cp_full_src

        # Pick a model for this run
        model = self._pick_model()
        self.logH(None, f"Using model {model} for refdiff dictionary generation")

        command_str = (
            f"python3.12 {self.dictgen_tool} "
            f"--workdir {workdir} "
            f"--exact-match "
            f"--output {output_file} "
            f"--no-extract-trigger "
            f"--no-extract-parsable-string "
            f"--model-name {model} "
            f"--delta "
            f"--refdiff {ref_diff_path} "
            f"--path {cp_full_src}"
        )

        ret = await self._run_dictgen_tool(workdir, command_str)
        if ret != 0:
            self.logH(
                None,
                f"{CRS_ERR} Error running dictgen for ref.diff context: {ret}\n{traceback.format_exc()}",
            )
            return None
        return output_file

    async def _generate_ossdict(self, harness_name: str, workdir: Path) -> Path:
        """Generate dictionary from OSS dictionary file if available."""
        workdir = workdir / f"{harness_name}_ossdict"
        workdir.mkdir(parents=True, exist_ok=True)
        output_file = workdir / "fuzz.dict"

        hrunner = next(
            (h for h in self.crs.hrunners if h.harness.name == harness_name), None
        )
        if not hrunner:
            self.logH(
                None,
                f"{CRS_ERR} hrunner {harness_name} not found\n{traceback.format_exc()}",
            )
            return None

        ossdict_path = self.crs.meta.get_harness_ossdict_path(hrunner.harness)
        if not ossdict_path:
            self.logH(None, f"No OSS dictionary path available for {harness_name}")
            # Create an empty dictionary file
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, "w") as f:
                f.write("# empty ossdict\n")
            return output_file

        # Copy the existing OSS dictionary file
        try:
            shutil.copy(ossdict_path, output_file)
            self.logH(
                None, f"Copied OSS dictionary from {ossdict_path} to {output_file}"
            )
            return output_file
        except Exception as e:
            self.logH(
                None,
                f"{CRS_ERR} Error copying OSS dictionary: {e}\n{traceback.format_exc()}",
            )
            return None

    async def _generate_beepseedexp_dict(
        self, harness_name: str, workdir: Path, cache_key: Tuple, beepseed: BeepSeed
    ) -> Path:
        """Generate dictionary for beepseedexp context."""
        workdir = workdir / f"{harness_name}_beep_{cache_key[1]}_{cache_key[2]}"
        workdir.mkdir(parents=True, exist_ok=True)
        output_file = workdir / "fuzz.dict"

        cp_full_src = self.crs.meta.cp_full_src

        funcs = ",".join([f["method_name"] for f in beepseed.stack_trace])
        if not funcs:
            self.logH(
                None,
                f"{CRS_WARN} No stacktrace funcs found in beepseed for {harness_name}\n{traceback.format_exc()}",
            )
            return None

        # Pick a model for this run
        model = self._pick_model()
        self.logH(None, f"Using model {model} for beepseed dictionary generation")

        command_str = (
            f"python3.12 {self.dictgen_tool} "
            f"--workdir {workdir} "
            f"--exact-match "
            f"--output {output_file} "
            f"--model-name {model} "
            f"--path {cp_full_src} "
            f"--funcs {funcs}"
        )

        ret = await self._run_dictgen_tool(workdir, command_str)
        if ret != 0:
            self.logH(
                None,
                f"{CRS_ERR} Error running dictgen for beepseedexp context: {ret}\n{traceback.format_exc()}",
            )
            return None
        return output_file

    async def _process_dict_request(
        self, harness_name: str, req: DictGenReqBase
    ) -> FuzzDict:
        """Process a dictionary generation request."""
        cp_name = self.crs.meta.cp_name
        workdir = self.workdir / cp_name / harness_name
        workdir.mkdir(parents=True, exist_ok=True)

        cache_key = req.get_cache_key()

        cached_dict = await self._get_dict_from_cache(harness_name, cache_key)
        if cached_dict:
            self.logH(
                None, f"Using cached dictionary for {harness_name}/{cache_key[0]}"
            )
            return cached_dict

        output_file = None

        if isinstance(req, InitialDictGenReq):
            output_file = await self._generate_initial_dict(harness_name, workdir)
        elif isinstance(req, RefDiffDictGenReq):
            output_file = await self._generate_refdiff_dict(harness_name, workdir)
        elif isinstance(req, OSSDictGenReq):
            output_file = await self._generate_ossdict(harness_name, workdir)
        elif isinstance(req, BEEPSeedDictGenReq):
            output_file = await self._generate_beepseedexp_dict(
                harness_name, workdir, cache_key, req.beep_seed
            )
        else:
            self.logH(
                None,
                f"{CRS_WARN} Unknown request type {type(req).__name__} for {harness_name}",
            )

        if not output_file or not output_file.exists():
            self.logH(
                None,
                f"{CRS_WARN} No dictionary file generated for {harness_name}/{cache_key}",
            )
            result_dict = FuzzDict()
        else:
            result_dict = FuzzDict.from_file(
                output_file, logger=lambda m: self.logH(None, m)
            )
            self.logH(
                None,
                f"Generated dictionary for {harness_name}/{cache_key[0]} with {len(result_dict.entries)} entries",
            )

        await self._add_dict_to_cache(harness_name, cache_key, result_dict)

        return result_dict

    async def _process_dict_requests(
        self, harness_name: str, requests: List[DictGenReqBase]
    ) -> FuzzDict:
        """Process a list of dictionary requests and merge the results."""
        merged_dict = FuzzDict()

        for req in requests:
            try:
                dict_to_merge = await self._process_dict_request(harness_name, req)
                merged_dict.merge(dict_to_merge)
            except Exception as e:
                self.logH(
                    None,
                    f"{CRS_ERR} Error processing request {req.__class__.__name__} for {harness_name}: {e}\n{traceback.format_exc()}",
                )
                continue

        if not merged_dict.entries:
            self.logH(
                None,
                f"{CRS_WARN} No dictionary entries found or generated for {harness_name}",
            )
        return merged_dict

    async def _dict_gen_loop(self):
        self.logH(None, "Dictionary generation loop started")

        while self.crs.should_continue():
            try:
                request = None

                try:
                    request = await asyncio.wait_for(
                        self.request_queue.get(), timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue

                harness_name = request["harness_name"]
                target_dict_path = request["target_dict_path"]
                dict_gen_reqs = request["dict_gen_reqs"]

                self.logH(
                    None,
                    f"Processing dictionary request for {harness_name} with {len(dict_gen_reqs)} request types",
                )

                fuzz_dict = await self._process_dict_requests(
                    harness_name, dict_gen_reqs
                )
                await fuzz_dict.to_file(
                    target_dict_path, logger=lambda m: self.logH(None, m)
                )
                self.logH(
                    None, f"Dictionary written to {target_dict_path} for {harness_name}"
                )

            except Exception as e:
                self.logH(
                    None,
                    f"{CRS_ERR} in dictionary generation loop: {e}\n{traceback.format_exc()}",
                )
                await asyncio.sleep(1)

            finally:
                if request is not None:
                    self.request_queue.task_done()

        self.logH(None, "Dictionary generation loop ended")

    async def request_dict_gen(
        self,
        harness_name: str,
        target_dict_path: Path,
        dict_gen_reqs: List[DictGenReqBase],
    ):
        """Request dictionary generation using structured request objects."""
        if not self.enabled:
            self.logH(
                None,
                f"{CRS_WARN} Dictionary generation module is not enabled, request ignored",
            )
            return

        await self.request_queue.put(
            {
                "harness_name": harness_name,
                "target_dict_path": target_dict_path,
                "dict_gen_reqs": dict_gen_reqs,
            }
        )

        self.logH(
            None,
            f"Dictionary generation requested for {harness_name} to {target_dict_path} with {len(dict_gen_reqs)} request types",
        )

    async def _serialize_cache_to_json(self) -> str:
        """Serialize the dictionary cache to a JSON string."""
        async with self.cache_lock:
            serializable_cache = {}
            for harness_name, contexts in self.dict_cache.items():
                serializable_cache[harness_name] = {}
                for context_id, fuzz_dict in contexts.items():
                    serializable_cache[harness_name][
                        str(context_id)
                    ] = fuzz_dict.to_json()
            return json.dumps(serializable_cache, indent=2)

    async def _dump_dict_cache(self, all_dicts_path: Path, is_final: bool = False):
        """Dump dictionary cache to a JSON file."""
        prefix = "Final" if is_final else "Periodic"

        try:
            if is_final:
                self.logH(None, "Performing final dictionary cache dump before exit")

            json_content = await self._serialize_cache_to_json()
            await atomic_write_file(all_dicts_path, json_content)
            self.logH(None, f"{prefix} dictionary cache saved to {all_dicts_path}")

        except Exception as e:
            self.logH(
                None,
                f"{CRS_ERR} Error in {prefix.lower()} dictionary dump: {e}\n{traceback.format_exc()}",
            )

    async def _dict_sync_loop(self):
        """Periodically save all dictionaries from the cache to a JSON file."""
        self.logH(None, "Dictionary sync loop started")
        cp_name = self.crs.meta.cp_name
        all_dicts_path = self.workdir / cp_name / "all-dicts.json"
        all_dicts_path.parent.mkdir(parents=True, exist_ok=True)

        while self.crs.should_continue():
            await self._dump_dict_cache(all_dicts_path)

            for _ in range(60):
                if not self.crs.should_continue():
                    break
                await asyncio.sleep(1)

        await self._dump_dict_cache(all_dicts_path, is_final=True)
        self.logH(None, "Dictionary sync loop ended")

    async def _async_run(self, _):
        if not self.enabled:
            self.logH(None, f"Module {self.name} is disabled")
            return

        try:
            dict_gen_task = asyncio.create_task(self._dict_gen_loop())
            dict_sync_task = asyncio.create_task(self._dict_sync_loop())

            await asyncio.gather(dict_gen_task, dict_sync_task)

            self.logH(None, f"Module {self.name} completed")

        except Exception as e:
            self.logH(
                None,
                f"{CRS_ERR} Error in dictionary generation: {e}\n{traceback.format_exc()}",
            )
