from pathlib import Path

import pytest

from tests.test_util import prepare_sample_cp_c
from vuli.common.setting import Setting
from vuli.cp import CP
from vuli.debugger import GDB, JDB


@pytest.mark.asyncio
async def test_jdb_basic():
    Setting().agent_path = (
        Path(__file__).parent.parent
        / "javaagent"
        / "target"
        / "java-agent-1.0-SNAPSHOT.jar"
    )
    Setting().root_dir = Path(__file__).parent.parent
    sample_cp: Path = Path(__file__).parent / "sample" / "java"
    sample_harness_out: Path = sample_cp / "out" / "harnesses" / "one"
    sample_harness_path: Path = (
        sample_cp
        / "src"
        / "sample-harness-one"
        / "src"
        / "main"
        / "java"
        / "sample"
        / "one"
        / "SampleOne.java"
    )
    jars: list[str] = [
        str(jar) for jar in sample_harness_out.iterdir() if str(jar).endswith(".jar")
    ]
    CP().harnesses = {
        "SampleOne": {
            "target_class": "sample.one.SampleOne",
            "classpath": jars,
            "src_path": str(sample_harness_path),
        }
    }
    debugger = JDB()
    try:
        stdout: str = await debugger.run(
            "SampleOne",
            b"\x00\x00\x00\x0a\x00\x00\x00\x01HELLO",
            ["stop go at sample.one.SampleOne.fuzzerTestOneInput"],
        )
        assert "The application exited" in stdout
        assert (
            len(
                [
                    line
                    for line in stdout.split("\n")
                    if line.startswith("Breakpoint hit:")
                    and "sample.one.SampleOne.fuzzerTestOneInput" in line
                ]
            )
            == 1
        )
    finally:
        await debugger.stop()


@pytest.mark.asyncio
@pytest.mark.timeout(15)
async def test_timeout():
    Setting().agent_path = (
        Path(__file__).parent.parent
        / "javaagent"
        / "target"
        / "java-agent-1.0-SNAPSHOT.jar"
    )
    Setting().root_dir = Path(__file__).parent.parent
    sample_cp: Path = Path(__file__).parent / "sample" / "java"
    sample_harness_out: Path = sample_cp / "out" / "harnesses" / "one"
    sample_harness_path: Path = (
        sample_cp
        / "src"
        / "sample-harness-one"
        / "src"
        / "main"
        / "java"
        / "sample"
        / "one"
        / "SampleOne.java"
    )
    jars: list[str] = [
        str(jar) for jar in sample_harness_out.iterdir() if str(jar).endswith(".jar")
    ]
    CP().harnesses = {
        "SampleOne": {
            "target_class": "sample.one.SampleOne",
            "classpath": jars,
            "src_path": str(sample_harness_path),
        }
    }
    debugger = JDB()
    debugger._timeout = 5.0
    try:
        stdout: str = await debugger.run(
            "SampleOne",
            b"\x00\x00\x00\x0c\x00\x00\x00\x01HELLO",
            ["stop go at sample.one.SampleOne.fuzzerTestOneInput"],
        )
        assert (
            len(
                [
                    line
                    for line in stdout.split("\n")
                    if line.startswith("Breakpoint hit:")
                    and "sample.one.SampleOne.fuzzerTestOneInput" in line
                ]
            )
            == 1
        )
    finally:
        await debugger.stop()


@pytest.mark.asyncio
async def test_gdb_run():
    await prepare_sample_cp_c()
    debugger = GDB(timeout=5.0)
    content: str = await debugger.run(
        "harness",
        b"",
        ["harness.cpp:6", "target/target.c:4", "target/target.c:13"],
    )
    assert ("harness.cpp:6" in content) is True

    content: str = await debugger.run(
        "harness",
        b"\x32",
        ["harness.cpp:6", "target/target.c:4", "target/target.c:13"],
    )
    assert ("harness.cpp:6" in content and "target.c:4" in content) is True


@pytest.mark.asyncio
async def test_gdb_run_invalid_harness():
    await prepare_sample_cp_c()
    debugger = GDB(timeout=5.0)
    content: str = await debugger.run(
        "invalid",
        b"",
        ["harness.cpp:6", "target/target.c:4", "target/target.c:13"],
    )
    assert (
        "harness.cpp:6" not in content
        and "target.c:4" not in content
        and "target.c:13" not in content
    )


@pytest.mark.asyncio
async def test_gdb_run_crash():
    await prepare_sample_cp_c()
    debugger = GDB(timeout=5.0)
    content: str = await debugger.run(
        "harness",
        b"\x32\x00\x00",
        ["harness.cpp:6", "target/target.c:4", "target/target.c:13"],
    )
    assert (
        "harness.cpp:6" in content
        and "target.c:4" in content
        and "target.c:13" in content
    ) is True


@pytest.mark.asyncio
async def test_gdb_run_timeout():
    await prepare_sample_cp_c()
    debugger = GDB(timeout=5.0)
    content: str = await debugger.run(
        "harness",
        b"\x33\x00\x00",
        ["harness.cpp:6", "target/target.c:17", "target/target.c:21"],
    )
    assert content == ""
