import asyncio
import glob
import json
import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Tuple

import aiofiles

from vuli.common.decorators import SEVERITY, async_lock, step
from vuli.common.setting import Setting
from vuli.common.singleton import Singleton
from vuli.query_loader import QueryLoader
from vuli.struct import Sanitizer
from vuli.util import async_process_run_and_exit


class CP(metaclass=Singleton):
    def __init__(self):
        self._logger = logging.getLogger("CP")
        self.harnesses: dict = {}
        self.sanitizers: list[Sanitizer] = []
        self.source_dir: Optional[Path] = None
        self._cg_paths: list[Path] = []
        self._diff_path: Optional[Path] = None
        self._lock = asyncio.Lock()
        self._sink_path: Optional[Path] = None
        self._server_dir: Optional[Path] = None

    @property
    def cg_paths(self) -> list[Path]:
        return self._cg_paths

    def _load_cp_meta(self, meta_file: Path):
        if not meta_file.exists():
            raise RuntimeError(f"CP metadata file not found: {meta_file}")
        with meta_file.open("r") as f:
            self.meta = json.load(f)

    def load(self, meta_file: Path, harnesses: list[str], cg_paths: list[Path] = []):
        self._cg_paths = cg_paths
        self._load_cp_meta(meta_file)

        try:
            self._set_diff_path(Path(self.meta["ref_diff_path"]))
        except Exception:
            self._logger.info("No Delta Mode")

        try:
            self._sink_path = Path(self.meta["sinkpoint_path"])
        except Exception:
            self._logger.info("Update SinkPoint Service Will Not Work")

        if "cp_full_src" not in self.meta:
            raise RuntimeError("cp_full_src not in metafile")
        if not Path(self.meta["cp_full_src"]).exists():
            raise RuntimeError(
                f"CP source directory not exist: {self.meta["cp_full_src"]}"
            )
        self.source_dir = self.meta["cp_full_src"]

        harness_meta: dict = self.meta.get("harnesses", {})
        self.harnesses: dict = harness_meta
        if len(harnesses) > 0:
            self.harnesses: dict = {
                key: value for key, value in self.harnesses.items() if key in harnesses
            }
        if len(self.harnesses) == 0:
            self._logger.warning("No Target Harness Found")
        else:
            self._logger.info(
                f"Target Harnesses: {", ".join(harness for harness in self.harnesses)}"
            )

        # truncate harness['src_path'] inside for correct Joern query results

        self.built_path = Path(self.meta.get("built_path", ""))
        if not self.built_path.exists():
            raise RuntimeError(f"CP built directory not found: {self.built_path}")

        self.sanitizers = [
            Sanitizer("sink-OsCommandInjection", ["jazze"]),
            Sanitizer("sink-ServerSideRequestForgery", ["jazzer.example.com"]),
            Sanitizer(
                "sink-UnsafeDeserialization",
                [
                    b"\xac\xed\x00\x05sr\x00\x07jaz.Zer\x00\x00\x00\x00\x00\x00\x00*\x02\x00\x01B\x00\tsanitizerxp\x02\n"
                ],
            ),
            Sanitizer("sink-SqlInjection", ["'"]),
            Sanitizer(
                "sink-RemoteJNDILookup", ["${jndi:ldap://g.co/}", "${ldap://g.co/}"]
            ),
            Sanitizer("sink-LdapInjection", ["("]),
            Sanitizer("sink-XPathInjection", ["document(2)"]),
            Sanitizer("sink-LoadArbitraryLibrary", ["jazzer_honeypot"]),
            Sanitizer("sink-RegexInjection", ["*"]),
            Sanitizer("sink-ScriptEngineInjection", ['"jaz"+"zer"']),
            Sanitizer("sink-FilePathTraversal", ["../jazzer-traversal"]),
            Sanitizer(
                "sink-ExpressionLanguageInjection",
                [['Byte.class.forName("jaz.Zer").getMethod("el").invoke(null)']],
            ),
        ]

    def get_dependent_jars(self):
        """Jars of all harnesses under one CP."""
        cp_built_path = self.built_path
        if cp_built_path is None or not os.path.exists(cp_built_path):
            raise RuntimeError(
                f"Invalid CP_BUILT_PATH {cp_built_path}: not set or not exists"
            )

        jars = {}
        for jar in glob.glob(
            os.path.join(cp_built_path, "**", "*.jar"), recursive=True
        ):
            name = os.path.basename(jar)
            if name in jars or name == "jazzer_agent_deploy.jar":
                continue
            jars[name] = os.path.abspath(jar)
        return list(jars.values())

    @step([], SEVERITY.NORMAL, "CP")
    def get_harnesses(self) -> list[str]:
        return list(set(self.harnesses.keys()))

    @step(None, SEVERITY.NORMAL, "CP")
    def get_harness_path(self, id: str) -> Path:
        return Path(self.harnesses[id]["src_path"])

    @step(None, SEVERITY.NORMAL, "CP")
    def get_harness_bin_path(self, id: str) -> Path:
        return Path(self.harnesses[id]["bin_path"])

    @step(None, SEVERITY.NORMAL, "CP")
    def get_harness_path_by_name(self, harness_name: str) -> Path:
        harness = self.harnesses.get(harness_name)
        if harness:
            return Path(harness.get("src_path", ""))
        return Path("")

    def get_harness_name(self, harness_file_path: Path) -> str:
        for name, harness in self.harnesses.items():
            if harness.get("src_path", "") == str(harness_file_path):
                return name
        return ""

    def get_harness_names(self) -> list[str]:
        return list(self.harnesses.keys())

    def get_jars(self, harness_path: Path):
        for harness in self.harnesses.values():
            if harness.get("src_path", "") == str(harness_path):
                jars: list[str] = harness["classpath"]
                return jars
        return []

    def get_sanitizer(self, name: str) -> Optional[Sanitizer]:
        return {sanitizer.name: sanitizer for sanitizer in self.sanitizers}.get(
            name, None
        )

    def get_fuzzer_exception_log(self, log: str):
        result = ""
        libfuzzer_log = [
            "INFO: seed corpus",
            "#2\tINITED",
            "#2\tDONE",
            "Done",
            "INFO: Instrumented",
        ]
        for idx, line in enumerate(log):
            if (
                not line.startswith("INFO: Instrumented")
                and "exception" in line.lower()
            ):
                result = log[idx:]
                break
        filtered_log = [
            line
            for line in result
            if not any(line.startswith(exclude) for exclude in libfuzzer_log)
        ]

        return "\n".join(filtered_log)

    @async_lock("_lock")
    # TODO: Delegate this method and make two version. c or java.
    async def run_pov(
        self,
        blob: bytes,
        enable_integer_overflow: bool,
        harness_path: Path,
        use_jazzer: bool,
        output: Path = None,
    ) -> Tuple[bool, str]:
        harness = None
        for h in self.harnesses.values():
            if h.get("src_path", "") == str(harness_path):
                harness = h
                break
        if harness is None:
            raise RuntimeError(f"Invalid harness_path: {harness_path}")

        with tempfile.TemporaryDirectory(prefix="llmpocgen-", dir="/") as tmp_dir:
            queue_dir = Path(tmp_dir, "queue")
            queue_dir.mkdir()

            blob_file = queue_dir / "blob"
            async with aiofiles.open(blob_file, mode="wb") as f:
                await f.write(blob)

            if use_jazzer:
                cmd, env, expected_code = self.set_jazzer_cmd(harness, queue_dir)
            else:
                cmd, env, expected_code = self.set_libfuzzer_cmd(harness)
                cmd.append(str(queue_dir))

            self._logger.info(f"Run Pov: {" ".join(cmd)}")
            p = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=tmp_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=env,
            )
            try:
                returncode, stdout, _ = await async_process_run_and_exit(p, 10)

                if returncode == expected_code:
                    return True, ""

                fuzzer_log = stdout.decode("utf-8", errors="ignore").split("\n")
                return False, self.get_fuzzer_exception_log(fuzzer_log)

            except TimeoutError:
                return (False, "")

    def set_jazzer_cmd(
        self, harness: dict, blob_dir: Path
    ) -> Tuple[list[str], None, int]:
        jazzer_dir = Setting().jazzer_path.parent
        agent_path = jazzer_dir / "jazzer_standalone_deploy.jar"
        cmd: list[str] = [
            "timeout",
            "-s",
            "SIGKILL",
            "30",
            "run_fuzzer",
            harness["name"],
            f"--agent_path={str(agent_path)}",
            "-runs=0",
        ]
        env = os.environ.copy()
        env["JAZZER_DIR"] = str(jazzer_dir)
        env["CORPUS_DIR"] = blob_dir.absolute()
        return cmd, env, 77

    def set_libfuzzer_cmd(self, harness: dict) -> Tuple[list[str], dict, int]:
        env = os.environ.copy()
        env["ASAN_OPTIONS"] = "detect_leaks=0"
        env["LSAN_OPTIONS"] = "detect_leaks=0"
        cmd = [harness["bin_path"], "-runs=1", "-timeout=10"]
        return cmd, env, 1

    def _set_diff_path(self, diff_path: Path) -> None:
        if diff_path.exists() and diff_path.is_file():
            self._diff_path = diff_path
        else:
            self._diff_path = None

    def _set_sink_path(self, sink_path: Path) -> None:
        self._sink_path = None

    @property
    @step("", SEVERITY.NORMAL, "CP")
    def name(self) -> str:
        return self.meta["cp_name"]

    @step(None, SEVERITY.NORMAL, "CP")
    def harness_bin_path(self, harness_id: str) -> Optional[Path]:
        return Path(self.meta["harnesses"][harness_id]["bin_path"])

    def target_method(self, harness_name: str) -> str:
        try:
            return self.meta["harnesses"][harness_name]["target_method"]
        except Exception:
            return QueryLoader().get("fuzzer_entry")
