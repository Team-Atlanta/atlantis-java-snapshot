#!/usr/bin/env python3

import asyncio
import json
import logging
import os
import traceback
from pathlib import Path
from typing import Any, Dict, List, Set

from libAgents.utils import Project
from libDeepGen.engine import DeepGenEngine
from libDeepGen.tasks.harness_seedgen import AnyHarnessSeedGen

from .exp_task import DeepGenExploitScriptTask
from .utils import CRS_ERR_LOG, CRS_WARN_LOG

CRS_ERR = CRS_ERR_LOG("cpmeta")
CRS_WARN = CRS_WARN_LOG("cpmeta")

logger = logging.getLogger(__name__)


class CPMetadata:
    """CP metadata handler"""

    def __init__(self, json_file: str):
        self.json_file = Path(json_file)
        self.metadata: Dict[str, Any] = self._load_metadata()
        self.cp_name = self.metadata["cp_name"]
        self.oss_fuzz_home = Path(self.metadata["cp_full_src"]) / "oss-fuzz"
        self.repo_src_path = Path(self.metadata["repo_src_path"])
        self.cp_full_src = Path(self.metadata["cp_full_src"])
        self.harnesses = self.metadata["harnesses"]
        self.processed_task_ids: Set[str] = set()

    def _load_metadata(self) -> Dict[str, Any]:
        """Load metadata from JSON file"""
        if not self.json_file.exists():
            raise FileNotFoundError(f"Metadata file not found: {self.json_file}")

        try:
            with open(self.json_file) as f:
                metadata = json.load(f)

            if not isinstance(metadata, dict):
                raise ValueError("Metadata must be a JSON object")

            return metadata
        except json.JSONDecodeError as e:
            logger.error(f"{CRS_ERR} Invalid JSON in metadata file: {e}")
            logger.error(f"Stack trace:\n{traceback.format_exc()}")
            raise ValueError(f"Invalid JSON in metadata file: {e}")

    def prepare_project(self, workdir: Path) -> Project:
        """Create Project object from metadata"""
        return Project(
            oss_fuzz_home=self.oss_fuzz_home,
            project_name=self.cp_name,
            local_repo_path=self.repo_src_path,
        )

    def create_harness_tasks(
        self, workdir: Path, weighted_models
    ) -> List[AnyHarnessSeedGen]:
        """Create AnyHarnessSeedGen tasks"""
        tasks = []

        project = self.prepare_project(workdir)
        bundle = project.prepare_project_bundle(workdir)

        # Store for later use in monitoring
        self.project_bundle = bundle
        self.weighted_models = weighted_models

        for harness_name, harness_info in self.harnesses.items():
            if "src_path" not in harness_info or "target_class" not in harness_info:
                logger.warning(
                    f"{CRS_WARN} Skipping harness {harness_name} due to missing required metadata"
                )
                continue

            target_method = harness_info["target_method"]
            harness_path = bundle.harness_path_by_name(harness_name)

            if not harness_path:
                logger.warning(
                    f"{CRS_WARN} Could not find harness path for {harness_name} in bundle"
                )
                continue

            task = AnyHarnessSeedGen(
                project_bundle=bundle,
                harness_name=harness_name,
                harness_entrypoint_func=target_method,
                is_jvm=True,
                weighted_models=weighted_models,
                priority=10,
                dev_attempts=5,
                dev_cost=2.0,
                num_repeat=1,
                max_exec=555555,
            )

            tasks.append(task)
            logger.info(f"Created task for harness: {harness_name}")

        return tasks

    async def _process_task_item(
        self, task_item: dict, task_file: Path, engine: DeepGenEngine
    ) -> None:
        task_id = task_item.get("task_id")
        if not task_id:
            return
        if task_id in self.processed_task_ids:
            return

        logger.info(f"Processing new task request: {task_id}")
        # Mark task as processed to avoid duplicates (including the case it will cause an error)
        self.processed_task_ids.add(task_id)

        harness_name = task_item.get("target_harness")
        script_prompt = task_item.get("script_prompt")

        if not script_prompt or not harness_name:
            logger.debug(
                f"Task {task_id} missing script_prompt or harness_name, skipping"
            )
            return

        target_method = "xxx"
        if harness_name in self.harnesses:
            target_method = self.harnesses[harness_name].get(
                "target_method", target_method
            )

        task = DeepGenExploitScriptTask(
            project_bundle=self.project_bundle,
            harness_name=harness_name,
            harness_entrypoint_func=target_method,
            weighted_models=self.weighted_models,
            task_id=task_id,
            prompt_content=script_prompt,
            priority=3,
            dev_attempts=2,
            dev_cost=2.0,
            num_repeat=1,
            max_exec=66666,
        )

        task_result_id = await engine.add_task(task)
        logger.info(f"Added task {task_id} to engine, result ID: {task_result_id}")

    async def _process_task_file(self, task_file: Path, engine: DeepGenEngine) -> None:
        try:
            with open(task_file) as f:
                task_data = json.load(f)

            if not isinstance(task_data, list):
                return

            for task_item in task_data:
                try:
                    await self._process_task_item(task_item, task_file, engine)
                except Exception as e:
                    logger.error(
                        f"{CRS_ERR} Error processing task item {task_item}: {e} {traceback.format_exc()}"
                    )
                    continue

        except json.JSONDecodeError:
            # Silently ignore malformed JSON files - they might be in the process of being written
            return

        except Exception as e:
            logger.error(
                f"{CRS_ERR} Error processing task file {task_file}: {e} {traceback.format_exc()}"
            )

    async def monitor_task_requests(self, engine: DeepGenEngine) -> None:
        task_req_dir_str = os.environ.get("DEEPGEN_TASK_REQ_DIR")
        if not task_req_dir_str:
            logger.warning(
                f"{CRS_WARN} DEEPGEN_TASK_REQ_DIR not set, skipping task request monitoring"
            )
            return

        task_req_dir = Path(task_req_dir_str)
        logger.info(f"Starting task request monitor for directory: {task_req_dir}")

        check_interval = 60
        counter = 0

        while True:
            try:
                counter = (counter + 1) % check_interval
                if counter == 0:
                    if task_req_dir.exists():
                        json_files = list(task_req_dir.glob("exp-*.json"))
                        if json_files:
                            for task_file in json_files:
                                await self._process_task_file(task_file, engine)
                    else:
                        logger.debug(
                            f"Task request directory does not exist: {task_req_dir}"
                        )
            except Exception as e:
                logger.error(
                    f"{CRS_ERR} Error during task request monitoring: {e} {traceback.format_exc()}"
                )

            await asyncio.sleep(1)
