import logging
import tempfile
from pathlib import Path
from typing import Optional

from vuli.common.singleton import Singleton


class Setting(metaclass=Singleton):
    mode: str = None

    # Joern
    joern_timeout: int = 30

    def __init__(self):
        self.agent_path: Optional[Path] = None
        self.blackboard_path: Optional[Path] = None
        self.calltree_db_path: Optional[Path] = None
        self.cpg_path: Optional[Path] = None
        self.model_cache_path: Optional[Path] = None
        self.jazzer_path: Optional[Path] = None
        self.joern_dir: Optional[Path] = None
        self.joern_cli_path: Optional[Path] = None
        self.joern_javasrc_path: Optional[Path] = None
        self.mode: str = ""
        self.output_dir: Optional[Path] = None
        self.path_path: Optional[Path] = None
        self.query_path: Optional[Path] = None
        self.semantic_dir: Optional[Path] = None
        self.root_dir: Optional[Path] = None
        self.shared_dir: Optional[Path] = None
        self.tmp_dir: Path = Path(tempfile.gettempdir())
        self._logger = logging.getLogger("Setting")

    def load(
        self,
        jazzer_path: Optional[Path],
        joern_dir: Path,
        output_dir: Path,
        root_dir: Path,
        dev: bool,
        shared_dir: Optional[Path] = None,
    ) -> None:
        self.jazzer_path = jazzer_path
        self.joern_dir = joern_dir
        self.output_dir = output_dir
        self.root_dir = root_dir
        self.dev = dev

        if self.joern_dir is None:
            self.joern_cli_path = Path("joern")
            self.joern_javasrc_path = Path("javasrc2cpg")
        self.joern_cli_path = self.joern_dir / "joern"
        self.joern_javasrc_path = (
            self.joern_dir / "joern-cli" / "frontends" / "javasrc2cpg" / "javasrc2cpg"
        )
        if self.output_dir.is_file():
            self.output_dir.unlink()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.blackboard_path = self.output_dir / "blackboard"
        self.calltree_db_path = self.output_dir / "joern-cg.json"
        self.cpg_path = (
            self.output_dir / "cpg"
            if not shared_dir
            else self.output_dir.parent / "cpg"
        )
        self.shared_dir = shared_dir
        self.model_cache_path = self.output_dir / "model-cache.db"
        self.agent_path: Path = (
            self.root_dir / "javaagent" / "target" / "java-agent-1.0-SNAPSHOT.jar"
        )
        self.query_path = self.root_dir / "script" / "script.sc"
        self.semantic_dir = self.root_dir / "script" / "semantics"
        self.tmp_dir = self.root_dir / "temp_dir"
        self.tmp_dir.mkdir(exist_ok=True)

        inputs: list[str] = [
            "joern_dir",
            "joern_cli_path",
            "joern_javasrc_path",
            "query_path",
            "root_dir",
            "semantic_dir",
        ] + (["jazzer_path", "agent_path"] if jazzer_path else ["shared_dir"])
        outputs: list[str] = ["blackboard_path", "calltree_db_path", "cpg_path"]
        invalid_inputs: list[Path] = [(x, getattr(self, x, None)) for x in inputs]
        invalid_inputs: list[Path] = [
            str(x)
            for x, value in invalid_inputs
            if (value is None) or (not isinstance(value, Path)) or (not value.exists())
        ]
        if len(invalid_inputs) > 0:
            msg: str = f"Invalid Paths: {", ".join(invalid_inputs)}"
            self._logger.error(msg)
            raise RuntimeError(msg)

        [
            self._logger.info(f"{x} is set to {self.__dict__.get(x, None)}")
            for x in sorted(inputs + outputs)
        ]
