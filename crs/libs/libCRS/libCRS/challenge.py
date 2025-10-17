import os
import glob
import logging
import yaml
import json
import base64
import asyncio
from pathlib import Path
from .ossfuzz_lib import get_harness_names


__all__ = ["CP_Harness", "CP", "init_cp_in_runner"]

UNIAFL_BIN = Path("/home/crs/uniafl/target/release/uniafl")


class CP_Harness:
    def __init__(self, cp: "CP", name: str, bin_path: Path, src_path: Path):
        self.cp = cp
        self.name = name
        self.bin_path = bin_path
        self.src_path = src_path
        self.runner = None
        self._loop = None

    def get_given_corpus(self) -> Path | None:
        corpus = Path(str(self.bin_path) + "_seed_corpus.zip")
        if corpus.exists():
            return corpus
        return None

    def get_given_dict(self) -> Path | None:
        dic = Path(str(self.bin_path) + ".dict")
        if dic.exists():
            return dic
        return None

    def get_answer_povs(self) -> list[Path]:
        pov_dir = self.cp.aixcc_path / "povs"
        return list(map(Path, glob.glob(f"{pov_dir / self.name}/*")))

    def get_answer_seeds(self) -> list[Path]:
        seed_dir = self.cp.aixcc_path / "seeds"
        return list(map(Path, glob.glob(f"{seed_dir / self.name}/*")))

    def get_answer_testlangs(self) -> list[Path]:
        testlang_dir = self.cp.aixcc_path / "testlangs"
        return list(map(Path, glob.glob(f"{testlang_dir / self.name}/*")))

    def run_input(
        self, file_path, worker_idx="0"
    ) -> (bytes, bytes, bytes | None, bytes | None):
        """
        DO NOT INVOKE THIS IN MULTI-THREADS
        return (stdout, stderr, cov json data if possible, crash_log if crashed)
        """
        # Check if loop is closed or in invalid state
        if self._loop is None or self._loop.is_closed():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)

        return self._loop.run_until_complete(
            self.async_run_input(file_path, worker_idx)
        )

    async def async_run_input(
        self, file_path, worker_idx="0"
    ) -> tuple[bytes, bytes, bytes | None, bytes | None]:
        """
        DO NOT INVOKE THIS IN MULTI-THREADS
        return (stdout, stderr, cov json data if possible, crash_log if crashed)
        """
        worker_idx = int(os.environ.get("CUR_WORKER", worker_idx))
        conf_path = Path(f"/executor/{self.name}/config_{worker_idx}")
        if UNIAFL_BIN.exists() and conf_path.exists():
            return await self.__run_fast_reproduce(conf_path, file_path)
        else:
            return await self.__run_reproduce(file_path)

    async def __run_reproduce(
        self, file_path
    ) -> tuple[bytes, bytes, bytes | None, bytes | None]:
        # TODO
        raise Exception("TODO: __run_reproduce")

    async def __run_fast_reproduce(
        self, conf_path, file_path
    ) -> tuple[bytes, bytes, None, None]:
        # TODO: do we need to consider if self.runner != None but uniafl dies?
        if self.runner is None:
            self.runner = await self.__boot_up_fast_reproduce(conf_path)
        self.runner.stdin.write(bytes(str(file_path) + "\n", "utf-8"))
        await self.runner.stdin.drain()
        line = await self.runner.stdout.readline()
        with open(line.strip()) as f:
            out = json.load(f)
        ret = []
        for key in ["stdout", "stderr", "coverage", "crash_log"]:
            if key in out:
                ret.append(base64.b64decode(out[key]))
            else:
                ret.append(None)
        return tuple(ret)

    async def __boot_up_fast_reproduce(self, conf_path) -> asyncio.subprocess.Process:
        cmd = ["setarch", "x86_64", "-R"]
        cmd += [str(UNIAFL_BIN), "-c", conf_path, "-e"]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            start_new_session=True,
        )
        return proc


class CP:
    def __init__(
        self, name: str, proj_path: str, cp_src_path: str, built_path: str | None
    ):
        self.name = name
        self.proj_path = Path(str(proj_path))
        self.aixcc_path = self.proj_path / ".aixcc"
        diff_path = self.proj_path / "ref.diff"
        if diff_path.exists():
            self.diff_path = diff_path
        else:
            self.diff_path = None
        self.cp_src_path = Path(str(cp_src_path))
        self.built_path = None
        if built_path:
            self.built_path = Path(str(built_path))

        with open(self.proj_path / "project.yaml", "r") as f:
            info = yaml.safe_load(f)
            self.language = info["language"]

        self.harnesses = self.get_harnesses()

    def get_harnesses(self) -> dict[str, CP_Harness]:
        harnesses = {}
        config = self.aixcc_path / "config.yaml"
        if not config.exists():
            for name in get_harness_names(self.built_path):
                bin_path = None
                if self.built_path:
                    bin_path = self.built_path / name
                harnesses[name] = CP_Harness(self, name, bin_path, None)
            return harnesses
        with open(self.aixcc_path / "config.yaml", "r") as f:
            aixcc_conf = yaml.safe_load(f)
            for name, src_path in self.get_harness_srcs(aixcc_conf).items():
                bin_path = None
                if self.built_path:
                    bin_path = self.built_path / name
                harnesses[name] = CP_Harness(self, name, bin_path, src_path)
        return harnesses

    def get_harness_srcs(self, aixcc_conf) -> dict[str, Path]:
        ret = {}
        cp_src = str(self.cp_src_path)
        cp_proj_path = str(self.proj_path)
        for item in aixcc_conf["harness_files"]:
            src = (
                item["path"].replace("$PROJECT", cp_proj_path).replace("$REPO", cp_src)
            )
            ret[item["name"]] = Path(src)
        return ret

    def log(self, msg: str):
        logging.info(f"[CP] {msg}")


def init_cp_in_runner() -> CP:
    return CP(os.environ.get("CRS_TARGET"), "/src/", "/src/repo", "/out")
