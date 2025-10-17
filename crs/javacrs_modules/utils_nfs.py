#!/usr/bin/env python3

import glob
import os
from pathlib import Path

from .utils import get_env_or_abort


def get_crs_multilang_nfs_seedshare_dir(harness_id: str) -> Path | None:
    """Get the nfs seedshare dir for crs-multilang."""
    crs_seedshare_dir = os.getenv("SEED_SHARE_DIR", None)
    if crs_seedshare_dir:
        multilang_seed_dir = Path(crs_seedshare_dir) / "crs-multilang" / harness_id
        if not multilang_seed_dir.exists():
            multilang_seed_dir.mkdir(parents=True, exist_ok=True)
        return multilang_seed_dir

    return None


def get_crs_java_nfs_seedshare_dir(harness_id: str) -> Path | None:
    """Get the seedshare dir for crs-java."""
    crs_seedshare_dir = os.getenv("SEED_SHARE_DIR", None)
    if crs_seedshare_dir:
        java_seed_dir = Path(crs_seedshare_dir) / "crs-java" / harness_id
        if not java_seed_dir.exists():
            java_seed_dir.mkdir(parents=True, exist_ok=True)
        return java_seed_dir

    return None


def get_sarif_share_dir() -> Path | None:
    """Get the SARIF share dir for callgraph etc."""
    sarif_share_dir = os.getenv("SARIF_SHARE_DIR", None)
    if sarif_share_dir:
        share_dir = Path(sarif_share_dir)
        if not share_dir.exists():
            share_dir.mkdir(parents=True, exist_ok=True)
        return share_dir

    return None


def get_sarif_share_full_cg_dir() -> Path | None:
    """Get the SARIF share full callgraph path."""
    sarif_reachability_dir = os.getenv("SARIF_REACHABILIY_SHARE_DIR", None)
    if sarif_reachability_dir:
        share_dir = Path(sarif_reachability_dir)
        if not share_dir.exists():
            share_dir.mkdir(parents=True, exist_ok=True)
        return share_dir

    return None


def get_sarif_ana_result_dir() -> Path | None:
    """Get the SARIF analysis result dir."""
    sarif_ana_result_dir = os.getenv("SARIF_ANA_RESULT_DIR", None)
    if sarif_ana_result_dir:
        share_dir = Path(sarif_ana_result_dir)
        if not share_dir.exists():
            share_dir.mkdir(parents=True, exist_ok=True)
        return share_dir

    return None


def get_crs_java_share_dir() -> Path | None:
    """Get the base share dir for crs-java."""
    crs_java_share_dir = os.getenv("CRS_JAVA_SHARE_DIR", None)
    if crs_java_share_dir:
        share_dir = Path(crs_java_share_dir)
        if not share_dir.exists():
            share_dir.mkdir(parents=True, exist_ok=True)
        return share_dir

    return None


def get_crs_java_share_diff_schedule_dir() -> Path | None:
    """Get the diff schedule dir for crs-java."""
    crs_java_share_dir = os.getenv("CRS_JAVA_SHARE_DIR", None)
    if crs_java_share_dir:
        diff_schedule_dir = Path(crs_java_share_dir) / "diff_schedule"
        if not diff_schedule_dir.exists():
            diff_schedule_dir.mkdir(parents=True, exist_ok=True)
        return diff_schedule_dir

    return None


def get_crs_java_share_cpmeta_path(hash: str) -> Path | None:
    """Get the shared cpmeta.json path for crs-java."""
    crs_java_share_dir = get_crs_java_share_dir()
    if crs_java_share_dir:
        cpmeta_json = Path(crs_java_share_dir) / f"cpmeta-{hash}.json"
        return cpmeta_json

    return None


def get_crs_java_cfg_path(pod_id: str) -> Path | None:
    """Get the path to the current CRS config for a specific pod."""
    diff_schedule_dir = get_crs_java_share_diff_schedule_dir()
    if diff_schedule_dir:
        return diff_schedule_dir / f"cur-crs-cfg-{pod_id}.json"
    return None


def get_all_crs_java_cfg_paths() -> list[tuple[str, Path]]:
    """Get all current CRS config files and their corresponding pod IDs."""
    diff_schedule_dir = get_crs_java_share_diff_schedule_dir()
    if not diff_schedule_dir:
        return []

    crs_config_files = []
    pod_id_pattern = glob.escape(str(diff_schedule_dir)) + "/cur-crs-cfg-*.json"
    for file_path in glob.glob(pod_id_pattern):
        pod_id = (
            os.path.basename(file_path).replace("cur-crs-cfg-", "").replace(".json", "")
        )
        crs_config_files.append((pod_id, Path(file_path)))
    return crs_config_files


def get_planned_crs_java_cfg_path(pod_id: str) -> Path | None:
    """Get the path to the planned CRS config for a specific pod."""
    diff_schedule_dir = get_crs_java_share_diff_schedule_dir()
    if diff_schedule_dir:
        return diff_schedule_dir / f"planned-crs-cfg-{pod_id}.json"
    return None


def get_crs_java_diff_ana_path(pod_id: str) -> Path | None:
    """Get the path to the diff analysis result for a specific pod."""
    diff_schedule_dir = get_crs_java_share_diff_schedule_dir()
    if diff_schedule_dir:
        return diff_schedule_dir / f"diff-ana-{pod_id}.json"
    return None


def get_all_crs_java_diff_ana_paths() -> list[tuple[str, Path]]:
    """Get all diff analysis files and their corresponding pod IDs."""
    diff_schedule_dir = get_crs_java_share_diff_schedule_dir()
    if not diff_schedule_dir:
        return []

    diff_analysis_files = []
    pod_id_pattern = glob.escape(str(diff_schedule_dir)) + "/diff-ana-*.json"
    for file_path in glob.glob(pod_id_pattern):
        pod_id = (
            os.path.basename(file_path).replace("diff-ana-", "").replace(".json", "")
        )
        diff_analysis_files.append((pod_id, Path(file_path)))
    return diff_analysis_files


def get_crs_java_sched_flag_path() -> Path | None:
    """Get the path to the scheduled flag file."""
    diff_schedule_dir = get_crs_java_share_diff_schedule_dir()
    if diff_schedule_dir:
        return diff_schedule_dir / "scheduled.flag"
    return None


def get_crs_java_pod_cache_dir() -> Path | None:
    """Get the pod cache directory for crs-java."""
    crs_java_share_dir = get_crs_java_share_dir()
    if crs_java_share_dir:
        pod_cache_dir = (
            crs_java_share_dir / "pod_cache" / get_env_or_abort("CRS_JAVA_POD_NAME")
        )
        if not pod_cache_dir.exists():
            pod_cache_dir.mkdir(parents=True, exist_ok=True)
        return pod_cache_dir

    return None


def get_crs_java_pod_cache_static_ana_dir() -> Path | None:
    """Get the static analysis cache directory for crs-java."""
    pod_cache_dir = get_crs_java_pod_cache_dir()
    if pod_cache_dir:
        static_ana_dir = pod_cache_dir / "static-analyzer"
        if not static_ana_dir.exists():
            static_ana_dir.mkdir(parents=True, exist_ok=True)
        return static_ana_dir

    return None


def get_crs_java_pod_cache_llmpocgen_dir() -> Path | None:
    """Get the static analysis cache directory for crs-java."""
    pod_cache_dir = get_crs_java_pod_cache_dir()
    if pod_cache_dir:
        llmpocgen_dir = pod_cache_dir / "llmpocgen"
        if not llmpocgen_dir.exists():
            llmpocgen_dir.mkdir(parents=True, exist_ok=True)
        return llmpocgen_dir

    return None


def get_crs_java_logs_dir(pod_id: str) -> Path | None:
    """Get the dir for storing crs-java logs."""
    crs_java_share_dir = get_crs_java_share_dir()
    if crs_java_share_dir:
        logs_dir = crs_java_share_dir / "logs" / pod_id
        if not logs_dir.exists():
            logs_dir.mkdir(parents=True, exist_ok=True)
        return logs_dir

    return None


def get_tarball_fs_dir() -> Path | None:
    """Get the TARBALL share dir."""
    tarball_fs_dir = os.getenv("TARBALL_FS_DIR", None)
    if tarball_fs_dir:
        share_dir = Path(tarball_fs_dir)
        if not share_dir.exists():
            share_dir.mkdir(parents=True, exist_ok=True)
        return share_dir

    return None


def get_sarif_shared_codeql_db_path() -> Path | None:
    """Get the shared CodeQL database path."""
    tarball_fs_dir = get_tarball_fs_dir()
    if tarball_fs_dir:
        return tarball_fs_dir / "crs-sarif" / "out" / "codeql.tar.gz"

    return None


def get_sarif_shared_codeql_db_done_file() -> Path | None:
    """Get the shared CodeQL database checksum file path."""
    tarball_fs_dir = get_tarball_fs_dir()
    if tarball_fs_dir:
        return tarball_fs_dir / "crs-sarif" / "out" / "CODEQL_DONE"

    return None
