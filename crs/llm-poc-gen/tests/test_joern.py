import json
import os
import tempfile
from pathlib import Path
from typing import Optional
from unittest.mock import AsyncMock, patch

import pytest

from vuli.common.setting import Setting
from vuli.cp import CP
from vuli.joern import CPG, Joern, JoernServer
from vuli.runner import Runner

counter: int = 0
real_query = JoernServer.query


@pytest.mark.asyncio
@patch.object(JoernServer, "query", new_callable=AsyncMock)
async def test_set_cpg_fail(mock):

    async def mock_query(*args, **kwargs) -> tuple[dict, bool]:
        global counter
        try:
            script: str = args[0]
            if "importCpg" in script:
                if counter == 0:
                    counter += 1
                    return (
                        {
                            "success": True,
                            "stdout": "\u001b[33mval\u001b[0m \u001b[36mres0\u001b[0m: \u001b[32mOption\u001b[0m[io.shiftleft.codepropertygraph.Cpg] = None\n",
                            "uuid": "13eb4187-7c29-4143-9a9a-94e7f6055332",
                        },
                        True,
                    )
                else:
                    return (
                        {
                            "success": True,
                            "stdout": "\u001b[33mval\u001b[0m \u001b[36mres0\u001b[0m: \u001b[32mOption\u001b[0m[io.shiftleft.codepropertygraph.Cpg] = Some(value = Cpg (Graph [1315999 nodes]))\n",
                            "uuid": "50547ada-c382-4318-82df-2923ffa95c60",
                        },
                        True,
                    )
            res = await real_query(Joern()._server, *args, **kwargs)
            return res
        except Exception as e:
            raise e

    mock.side_effect = mock_query
    output_dir = tempfile.TemporaryDirectory()
    Setting().load(
        Path(os.getenv("JOERN_DIR")),
        Path(os.getenv("JOERN_DIR")),
        Path(output_dir.name),
        Path(__file__).parent.parent,
        True,
    )
    cpg = CPG(Setting().cpg_path)
    Joern().set_path(Setting().joern_cli_path)
    try:
        # If any exception raises here, test will fail.
        await Joern().run_server(cpg, Setting().query_path, Setting().semantic_dir)
    finally:
        await Joern().close_server()


class MockRunner(Runner):
    async def _run(self) -> None:
        pass

    async def run(self) -> None:
        pass


@pytest.mark.asyncio
async def test_joern_clean_no_cpg():
    output_dir = tempfile.TemporaryDirectory()
    Setting().load(
        Path(os.getenv("JOERN_DIR")),
        Path(os.getenv("JOERN_DIR")),
        Path(output_dir.name),
        Path(__file__).parent.parent,
        True,
    )
    cpg = CPG(Setting().cpg_path)
    Joern().set_path(Setting().joern_cli_path)
    try:
        await Joern().run_server(cpg, Setting().query_path, Setting().semantic_dir)
    finally:
        await Joern().close_server()


@pytest.mark.asyncio
async def test_joern_clean_with_cpg():
    sample_dir: Path = Path(__file__).parent / "sample" / "java"
    meta: dict = {"cp_full_src": str(sample_dir / "src")}
    meta_file = tempfile.NamedTemporaryFile()
    with Path(meta_file.name).open("w") as f:
        json.dump(meta, f)
        f.flush()

    root_dir: Path = Path(__file__).parent.parent
    output_dir = tempfile.TemporaryDirectory()
    Setting().load(
        Path(""), Path(os.getenv("JOERN_DIR")), Path(output_dir.name), root_dir, False
    )
    CP().load(Path(meta_file.name), [])
    try:
        await MockRunner()._initialize_joern()
        workspace: Optional[Path] = Path(Joern()._workspace)
        assert workspace is not None
        assert workspace.exists()
        assert workspace.is_dir()
    finally:
        await Joern().close_server()
        assert not workspace.exists()
