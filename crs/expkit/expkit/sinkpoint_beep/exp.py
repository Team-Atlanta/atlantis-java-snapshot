#!/usr/bin/env python3

import json
import logging
import os
import random
import traceback
import uuid
from pathlib import Path

import litellm
import openai

from ..beepobjs import BeepSeed
from ..cpmeta import CPMetadata
from ..fuzzer.jazzer import JazzerFuzzer
from ..llm import LLMClient
from ..redis import RedisCacheClient
from ..utils import CRS_ERR_LOG, CRS_WARN_LOG, get_usable_cpu_id
from .prompt import PromptGenerator

logger = logging.getLogger(__name__)


CRS_ERR = CRS_ERR_LOG("sinkexp")
CRS_WARN = CRS_WARN_LOG("sinkexp")


class SinkpointExpTool:
    """Handles exploitation of sinkpoint BEEPs."""

    def __init__(
        self,
        llm_client: LLMClient,
        redis_client: RedisCacheClient,
        beepseed: BeepSeed,
        exp_time: int,
        cp_meta: CPMetadata,
        workdir: Path = None,
        gen_models: list = None,
        x_models: list = None,
    ):
        self.beepseed = beepseed
        self.llm_client = llm_client
        self.redis_client = redis_client
        self.gen_models = gen_models
        self.x_models = x_models
        self.gen_model = self._pick_gen_model()
        self.x_model = self._pick_x_model()
        self.exp_time = exp_time
        self.cp_meta = cp_meta
        self.workdir = workdir
        self.cpu_id = get_usable_cpu_id()
        self.prompt_generator = PromptGenerator(cp_meta, beepseed)

    def _pick_gen_model(self) -> str:
        """Select a model for generating POCs based on weighted probabilities."""
        selected = random.choice(self.gen_models)
        logger.info(f"Selected generation model: {selected}")
        return selected

    def _pick_x_model(self) -> str:
        """Select a model for extracting hex strings based on weighted probabilities."""
        selected = random.choice(self.x_models)
        logger.info(f"Selected extraction model: {selected}")
        return selected

    def check_exp_status(self, fuzz_log: Path) -> bool:
        if not fuzz_log.exists():
            logger.warning(f"{CRS_ERR} Fuzz log file {fuzz_log} does not exist")
            return False

        try:
            with open(fuzz_log, "rb") as f:
                in_stack_trace = False

                for line in f:
                    try:
                        line_str = line.decode("utf-8", errors="ignore").strip()
                    except UnicodeDecodeError as e:
                        logger.warning(f"Error decoding line: {e}")
                        continue

                    if "== Java Exception:" in line_str:
                        if "FuzzerSecurityIssue" not in line_str:
                            continue

                        if "Stack overflow" in line_str or "Out of memory" in line_str:
                            continue

                        in_stack_trace = True

                    elif in_stack_trace:
                        if "== libFuzzer crashing input ==" in line_str:
                            in_stack_trace = False
                            continue

                        # match if sinkpoint location is in the stack trace line
                        class_name = self.beepseed.coord.class_name.replace("/", ".")
                        method_name = self.beepseed.coord.method_name
                        line_no = self.beepseed.coord.line_num
                        file_name = self.beepseed.coord.file_name
                        signature = f"{class_name}.{method_name}({file_name}:{line_no})"
                        if signature in line_str:
                            logger.info("Found successful exploitation in logs")
                            return True

                logger.info("No successful exploitation found in logs")
                return False

        except Exception as e:
            logger.error(f"Error checking exploitation status: {e}")
            return False

    def _dump_deepgen_task(self):
        """Dump the exploitation script to crs."""
        try:
            task_req_dir = os.environ.get("DEEPGEN_TASK_REQ_DIR", None)
            if task_req_dir is None:
                logger.warning(
                    f"{CRS_WARN} Environment variable DEEPGEN_TASK_REQ_DIR is not set, skipping script dump"
                )
            task_req_dir = Path(task_req_dir)
            if not task_req_dir.exists():
                task_req_dir.mkdir(parents=True, exist_ok=True)

            task_id = (
                f"exp-{self.beepseed.target_harness}-{self.beepseed.coord.key_shasum()}"
            )
            task_json = task_req_dir / f"{task_id}.json"
            script_prompt = self.prompt_generator.generate_poc_script()
            local_task_json = self.workdir / f"{task_id}.json"
            with open(local_task_json, "w") as f:
                f.write(
                    json.dumps(
                        [
                            {
                                "task_id": task_id,
                                "target_harness": self.beepseed.target_harness,
                                "script_prompt": script_prompt,
                            }
                        ],
                        indent=2,
                    )
                )
            # atomically replace the file in the task request directory
            os.replace(local_task_json, task_json)
            logger.info(f"Exploitation script dumped successfully to {task_json}")
        except Exception as e:
            logger.error(f"{CRS_ERR} Failed to dump exploitation script: {e}")

    def _add_beepseed_to_corpus(self, jazzer):
        """Extract beepseed data and add it to the corpus."""
        if not self.beepseed.data_hex_str:
            logger.warning("Data is empty in beepseed")
            return None

        try:
            beepseed_bytes = bytes.fromhex(self.beepseed.data_hex_str)
            beepseed_file = jazzer.add_corpus_file(beepseed_bytes, "beepseed")
            logger.info(f"Added beepseed to corpus ({len(beepseed_bytes)} bytes)")
            return beepseed_file
        except Exception as e:
            logger.error(f"{CRS_ERR} Failed to add beepseed to corpus: {e}")
            return None

    def _add_poc_to_corpus(self, jazzer):
        """Generate POC content using LLM and add to corpus."""
        try:
            # Check if either model is 'none' to skip LLM queries
            if self.gen_model.lower() == "none" or self.x_model.lower() == "none":
                logger.info(
                    f"Skipping POC generation as model selection includes 'none' (gen_model={self.gen_model})"
                )
                return None

            logger.info("Generating POC using LLM")
            # check cache first
            x_hexstr = self.redis_client.get(self.beepseed, self.gen_model, "x_hexstr")
            if x_hexstr is not None:
                logger.info(
                    f"CACHE: Found cached x_hexstr in Redis: {x_hexstr} for {self.beepseed.redis_key()}"
                )
            else:
                logger.info(
                    f"CACHE: No cached x_hexstr found, generating new one for {self.beepseed.redis_key()}"
                )
                try:
                    poc_content = self.redis_client.get(
                        self.beepseed, self.gen_model, "poc_content"
                    )
                    if poc_content is None:
                        logger.info(
                            f"CACHE: No cached poc_content found, generating new one for {self.beepseed.redis_key()}"
                        )

                        poc_prompt = self.prompt_generator.generate_poc_prompt()
                        poc_response = self.llm_client.completion(
                            prompt=poc_prompt,
                            model=self.gen_model,
                            temperature=1.0,
                        )
                        poc_content = poc_response["content"]

                        logger.info(
                            f"CACHE: Caching poc_content for {self.beepseed.redis_key()}"
                        )
                        self.redis_client.set(
                            self.beepseed, self.gen_model, "poc_content", poc_content
                        )

                    x_hexstr_prompt = self.prompt_generator.generate_x_hexstr_prompt(
                        poc_content
                    )
                    x_response = self.llm_client.completion(
                        prompt=x_hexstr_prompt,
                        model=self.x_model,
                        temperature=0.1,
                    )
                    x_hexstr = x_response["content"]
                    if x_hexstr is None:
                        logger.warning(
                            "CACHE: LLM returned None for x_hexstr, set it as empty string"
                        )
                        x_hexstr = ""

                except (
                    litellm.InternalServerError,
                    litellm.Timeout,
                    litellm.ServiceUnavailableError,
                    litellm.RateLimitError,
                    openai.APITimeoutError,
                    openai.RateLimitError,
                    openai.InternalServerError,
                    openai.APIStatusError,
                ) as e:
                    logger.info(
                        f"CACHE: Meet LLM error: {e}, do not cache POC hex string, will retry later: {traceback.format_exc()}"
                    )
                    return None

                except Exception as e:
                    logger.error(
                        f"CACHE: Meet unexpected error while generating POC: {e}, will not retry: {traceback.format_exc()}"
                    )
                    x_hexstr = ""

                logger.info(
                    f"CACHE: Set POC hex string in Redis cache for {self.beepseed.redis_key()}"
                )
                self.redis_client.set(
                    self.beepseed, self.gen_model, "x_hexstr", x_hexstr
                )

            # Parse hex strings from using bytes
            try:
                poc_bytes = bytes.fromhex(x_hexstr)
                if poc_bytes:
                    poc_file = jazzer.add_corpus_file(poc_bytes, "poc")
                    logger.info(f"Added POC to corpus ({len(poc_bytes)} bytes)")
                    return poc_file
            except Exception as e:
                logger.warning(f"Invalid LLM-generated hex string in POC content: {e}")
                return None

        except Exception as e:
            logger.error(
                f"Failed to generate and add POC to corpus: {e} {traceback.format_exc()}"
            )
            return None

    def exploit(self) -> dict:
        """Perform sinkpoint beepseed exploitation."""
        try:
            target_harness = self.beepseed.target_harness
            target_classpath = self.cp_meta.get_classpath(target_harness)

            if self.workdir:
                work_dir = self.workdir
                fuzz_id = f"exp-{self.beepseed.data_sha1[:8]}"
                logger.info(f"Using provided working directory: {work_dir}")
            else:
                fuzz_id = (
                    f"exploit-{self.beepseed.data_sha1[:8]}-{uuid.uuid4().hex[:8]}"
                )
                work_dir = Path(f"/tmp/{fuzz_id}")
                logger.info(f"Using generated working directory: {work_dir}")

            if not target_classpath or not target_harness:
                raise ValueError(
                    f"Missing classpath {target_classpath} or {target_harness} in CP metadata"
                )

            logger.info(
                f"Initializing fuzzer for {target_harness} with classpath {target_classpath}"
            )

            jazzer = JazzerFuzzer(
                jazzer_dir=os.environ.get("AIXCC_JAZZER_DIR"),
                work_dir=work_dir,
                cp_name=self.cp_meta.get_cp_name(),
                target_harness=target_harness,
                fuzz_target=self.cp_meta.get_target_class(target_harness),
                target_classpath=target_classpath,
                custom_sink_conf_path=self.cp_meta.get_custom_sink_conf_path(),
                cpu_id=self.cpu_id,
                custom_args=[
                    '-use_value_profile=1 --trace=none --instrumentation_includes="some.package.names.never.exist" '
                ],
            )

            # self._dump_deepgen_task()
            self._add_beepseed_to_corpus(jazzer)
            self._add_poc_to_corpus(jazzer)

            logger.info(f"Running fuzzer for {self.exp_time}s with ID {fuzz_id}")

            result_json = jazzer.fuzz(
                fuzz_id=fuzz_id, fuzz_time=self.exp_time, mem_size=4096
            )
            exp_succ = self.check_exp_status(jazzer.fuzz_log)
            result = {
                "status": exp_succ,
                "cp_name": self.cp_meta.get_cp_name(),
                "coordinate": self.beepseed.coord.to_dict(),
                "workdir": str(work_dir),
                "fuzz_id": fuzz_id,
                "results_json": str(result_json) if result_json else None,
            }

            logger.info(f"Exploitation completed with status: {exp_succ}")
            logger.info(self.llm_client.print_usage_stats())
            return result

        except Exception as e:
            err_str = f"{CRS_ERR} Exception {e}"
            logger.error(f"{err_str} with traceback:\n{traceback.format_exc()}")
            return {"status": False, "error": err_str}
