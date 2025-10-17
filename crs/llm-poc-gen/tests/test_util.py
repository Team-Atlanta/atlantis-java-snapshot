import json
import os
import shutil
import tempfile
from pathlib import Path

import aiofiles

from vuli.blackboard import Blackboard
from vuli.common.setting import Setting
from vuli.cp import CP
from vuli.query_loader import QueryLoader


async def prepare_sample_cp_c() -> None:
    sample_dir: Path = Path(__file__).parent / "sample"
    sample_output_dir: Path = sample_dir / "output"
    if sample_output_dir.exists():
        shutil.rmtree(sample_output_dir)
    Setting().load(
        Path("."),
        Path(os.getenv("JOERN_DIR")),
        sample_output_dir,
        Path(__file__).parent.parent,
        False,
    )
    sample_cp: Path = sample_dir / "c"
    sample_harness_out: Path = sample_cp / "build"
    sample_harness_path: Path = sample_cp / "harness.cpp"
    meta_t = tempfile.NamedTemporaryFile()
    async with aiofiles.open(meta_t.name, mode="w") as f:
        await f.write(
            json.dumps(
                {
                    "cp_full_src": str(sample_cp),
                    "built_path": str(sample_harness_out),
                    "harnesses": {
                        "harness": {
                            "src_path": str(sample_harness_path),
                        }
                    },
                },
            )
        )
        await f.flush()
    CP().load(Path(meta_t.name), [], [])
    await Blackboard().set_path(Setting().blackboard_path)


async def prepare_sample_cp() -> None:
    sample_dir: Path = Path(__file__).parent / "sample"
    sample_output_dir: Path = sample_dir / "output"
    if sample_output_dir.exists():
        shutil.rmtree(sample_output_dir)
    Setting().load(
        Path("."),
        Path(os.getenv("JOERN_DIR")),
        sample_output_dir,
        Path(__file__).parent.parent,
        False,
    )
    QueryLoader().load(Setting().root_dir / "queries" / "java.yaml")
    sample_cp: Path = sample_dir / "java"
    sample_harness_out: Path = sample_cp / "out" / "harnesses" / "one"
    sample_harness_path: Path = Path(
        "sample-harnesses",
        "sample-harness-one",
        "src",
        "main",
        "java",
        "sample",
        "one",
        "SampleOne.java",
    )
    jars: list[str] = [
        str(jar) for jar in sample_harness_out.iterdir() if str(jar).endswith("jar")
    ]
    meta_t = tempfile.NamedTemporaryFile()
    sarif_t = tempfile.NamedTemporaryFile()
    async with aiofiles.open(meta_t.name, mode="w") as f:
        await f.write(
            json.dumps(
                {
                    "cp_full_src": str(Path("tests", "sample", "java", "src")),
                    "harnesses": {
                        "SampleOne": {
                            "target_class": "sample.one.SampleOne",
                            "classpath": jars,
                            "src_path": str(sample_harness_path),
                            "name": "SampleOne",
                        }
                    },
                    "sinkpoint_path": sarif_t.name,
                },
            )
        )
        await f.flush()
    CP().load(Path(meta_t.name), [], [])
    await Blackboard().set_path(Setting().blackboard_path)
