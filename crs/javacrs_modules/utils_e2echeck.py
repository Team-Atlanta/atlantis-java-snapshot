import asyncio
import traceback
from pathlib import Path
from typing import List

import aiofiles

from .utils import CRS_ERR_LOG, CRS_WARN_LOG, run_process_and_capture_output
from .utils_leader import CRS_JAVA_POD_NAME
from .utils_nfs import get_crs_java_logs_dir

CRS_ERR = CRS_ERR_LOG("e2echeck")
CRS_WARN = CRS_WARN_LOG("e2echeck")


def get_sync_files_cmd(files: List[Path], target_dir: Path) -> List[str]:
    """Add commands to sync files to a subdirectory."""
    cmd = [f"mkdir -p {target_dir}"]
    for local_file in files:
        cmd.append(f"rsync -a {local_file} {target_dir}")
    return cmd


def get_sync_glob_cmd(base_dir: Path, pattern: str, target_base_dir: Path) -> List[str]:
    """Add commands to sync files matching a glob pattern, preserving directory structure."""
    cmd = []
    for path in base_dir.glob(pattern):
        target_dir = target_base_dir / path.parent.relative_to(base_dir)
        cmd.append(f"mkdir -p {target_dir}")
        cmd.append(f"rsync -a {path} {target_dir}")
    return cmd


def get_sync_tail_glob_cmd(
    base_dir: Path, pattern: str, target_base_dir: Path, tail_lines: int
) -> List[str]:
    """Add commands to sync the last N lines of files matching a glob pattern, preserving directory structure."""
    cmd = []
    for path in base_dir.glob(pattern):
        target_dir = target_base_dir / path.parent.relative_to(base_dir)
        target_file = target_dir / path.name
        cmd.append(f"mkdir -p {target_dir}")
        cmd.append(f"tail -n {tail_lines} {path} > {target_file}")
    return cmd


def gen_log_sync_cmd(crs, logger, local_check_file) -> str:
    """Generate shell commands to sync logs to NFS directory."""
    logs_dir = get_crs_java_logs_dir(CRS_JAVA_POD_NAME)
    if not logs_dir:
        logger(f"{CRS_ERR} E2E check file path is None. Aborting E2E check loop.")
        return ""

    cmd = []

    # E2E check file
    cmd.append(f"rsync -a {local_check_file} {logs_dir}/e2e-check.txt")

    # CRS core logs
    cmd.append(f"rsync -a $JAVA_CRS_SRC/crs-java.config {logs_dir}")
    cmd.append(f"rsync -a $JAVA_CRS_SRC/crs-java.log {logs_dir}")
    cmd.append(f"python3.12 -m libCRS.submit show > {logs_dir}/submit.log")

    # Module logs organized by category
    module_logs = {
        "static_analysis": [
            crs.staticanalysis.workdir / "soot-cg.json",
            crs.staticanalysis.workdir / "static-analysis-cfg.json",
            crs.staticanalysis.workdir / "static-analysis-result.json",
            crs.staticanalysis.workdir / "static-analysis.log",
        ],
        "codeql": [
            crs.codeql.workdir / "codeql_result.json",
            crs.codeql.workdir / "query.log",
        ],
        "llmpocgen": [
            crs.llmpocgen.workdir / "run.log",
            crs.llmpocgen.workdir / "joern-cg.json",
            crs.llmpocgen.workdir / "blackboard",
        ],
        "sinkmanager": [
            crs.sinkmanager.sink_conf_path,
        ],
        "metadata": [
            crs.meta.workdir / "cpmeta.json",
            crs.meta.sinkpoint_path,
        ],
        "deepgen": [
            crs.deepgen.workdir / "deepgen.log",
            crs.deepgen.workdir / "summary.json",
        ],
    }

    # Sync all module logs
    for subdir, files in module_logs.items():
        cmd.extend(get_sync_files_cmd(files, logs_dir / subdir))

    # Sync logs from glob patterns
    cmd.extend(get_sync_glob_cmd(crs.workdir, "concolic/**/concolic*.log", logs_dir))
    cmd.extend(get_sync_glob_cmd(crs.workdir, "dictgen/**/all-dicts.json", logs_dir))

    # Fuzzer logs
    fuzzer_patterns = [
        "HarnessRunner/*/fuzz/*/result.json",
        "HarnessRunner/*/fuzz/*/fuzz.dict",
        "HarnessRunner/*/fuzz/seedmerger*/fuzz.log",
    ]
    for pattern in fuzzer_patterns:
        cmd.extend(get_sync_glob_cmd(crs.workdir, pattern, logs_dir))

    # Fuzzer log files with tail (last 20K lines only)
    cmd.extend(
        get_sync_tail_glob_cmd(
            crs.workdir, "HarnessRunner/*/fuzz/a*/fuzz.log", logs_dir, 20000
        )
    )

    return "\n".join(cmd)


async def run_e2e_check(workdir: Path, logger) -> int:
    """Run the E2E check command."""
    local_check_file = workdir / "e2e-check.txt"
    command_sh = workdir / "e2e-check-command.sh"

    command_content = f"""#!/bin/bash
python3.12 ${{JAVA_CRS_SRC}}/tests/e2e_result_checker.py > {local_check_file} 2>&1
"""

    try:
        async with aiofiles.open(command_sh, "w") as f:
            await f.write(command_content)
        command_sh.chmod(0o755)

        return await run_process_and_capture_output(command_sh, local_check_file)
    except Exception as e:
        logger(f"{CRS_ERR} Error running E2E check command: {str(e)}")
        return 1


async def sync_logs_to_nfs(crs, local_check_file: Path, logger):
    """Sync logs to NFS storage."""
    try:
        command_sh = local_check_file.parent / "sync-log-command.sh"

        sync_commands = gen_log_sync_cmd(crs, logger, local_check_file)
        if not sync_commands:
            logger(f"{CRS_WARN} No sync commands generated, skipping log sync")
            return

        command_content = f"""#!/bin/bash
echo "Syncing logs to NFS..."
{sync_commands}
"""

        async with aiofiles.open(command_sh, "w") as f:
            await f.write(command_content)
        command_sh.chmod(0o755)

        ret = await run_process_and_capture_output(
            command_sh, local_check_file.parent / "sync_logs.log"
        )
        if ret == 0:
            logger("Log sync completed successfully")
        else:
            logger(f"{CRS_WARN} Log sync command returned non-zero exit code: {ret}")
    except Exception as e:
        logger(f"{CRS_ERR} Error syncing logs: {str(e)} {traceback.format_exc()}")


async def e2e_check_loop(
    crs, enabled, sync_log, should_continue_fn, logger, workdir: Path
):
    """End-to-end check loop with optional log syncing."""
    workdir.mkdir(parents=True, exist_ok=True)

    if not enabled:
        logger("E2E check loop is disabled. Skipping E2E checks.")
        return
    logger(f"Log sync is {'enabled' if sync_log else 'disabled'}.")

    local_check_file = workdir / "e2e-check.txt"

    cur_iteration = 1
    period = 1800

    while should_continue_fn():
        if cur_iteration % period == 0:
            iteration_num = cur_iteration // period + 1

            # Step 1: Run the E2E check
            try:
                logger(f"Running E2E check (iteration {iteration_num})")
                e2e_result = await run_e2e_check(workdir, logger)

                if e2e_result == 0:
                    logger("E2E check completed successfully")
                else:
                    logger(
                        f"{CRS_WARN} E2E check command returned non-zero exit code: {e2e_result}"
                    )
            except Exception as e:
                logger(
                    f"{CRS_ERR} Error in E2E check: {str(e)} {traceback.format_exc()}"
                )

            # Step 2: Sync logs (if enabled)
            if sync_log:
                try:
                    logger("Syncing logs to NFS...")
                    await sync_logs_to_nfs(crs, local_check_file, logger)
                except Exception as e:
                    logger(
                        f"{CRS_ERR} Error syncing logs: {str(e)} {traceback.format_exc()}"
                    )

        await asyncio.sleep(1)
        cur_iteration += 1

    logger("E2E check loop has been completed.")
