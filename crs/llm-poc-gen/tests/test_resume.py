import datetime
import tempfile
from pathlib import Path
from unittest.mock import patch

import aiofiles
import pytest

from vuli.common.setting import Setting
from vuli.resume import Resume


@pytest.fixture(autouse=True)
def setup():
    Setting().output_dir = None


@pytest.mark.asyncio
async def test_resume__download():
    output_dir = tempfile.TemporaryDirectory()
    server_dir = tempfile.TemporaryDirectory()
    src = tempfile.NamedTemporaryFile(dir=Path(output_dir.name))
    Setting().output_dir = Path(output_dir.name)

    resume = Resume(Path(server_dir.name), [src.name])
    server_file = Path(server_dir.name) / Path(src.name).name
    server_checksum_file = server_file.parent / resume._checksum_name(server_file)
    async with aiofiles.open(server_file, mode="w") as f:
        await f.write("hello")
        await f.flush()
    async with aiofiles.open(server_checksum_file, mode="w") as f:
        await f.write(resume._key(server_file))
        await f.flush()
    await resume.download()

    async with aiofiles.open(src.name) as f:
        assert (await f.read()) == "hello"


@pytest.mark.asyncio
async def test_resume__download_checksum_fail():
    output_dir = tempfile.TemporaryDirectory()
    server_dir = tempfile.TemporaryDirectory()
    src = tempfile.NamedTemporaryFile(dir=Path(output_dir.name))
    Setting().output_dir = Path(output_dir.name)

    resume = Resume(Path(server_dir.name), [src.name])
    server_file = Path(server_dir.name) / Path(src.name).name
    server_checksum_file = server_file.parent / resume._checksum_name(server_file)
    with server_file.open("w") as f:
        f.write("hello")
        f.flush()
    with server_checksum_file.open("w") as f:
        f.write("world")
        f.flush()
    await resume.download()

    with Path(src.name).open() as f:
        assert len(f.read()) == 0


@pytest.mark.asyncio
async def test_resume__upload():
    output_dir = tempfile.TemporaryDirectory()
    server_dir = tempfile.TemporaryDirectory()
    src = tempfile.NamedTemporaryFile(dir=Path(output_dir.name))
    src_path: Path = Path(src.name)
    async with aiofiles.open(src_path, mode="w") as f:
        await f.write("hello")
        await f.flush()

    Setting().output_dir = Path(output_dir.name)
    resume: Resume = Resume(Path(server_dir.name), [src.name])
    dst_path: Path = Path(server_dir.name) / Path(src.name).name

    await resume._upload()
    async with aiofiles.open(dst_path) as f:
        assert (await f.read()) == "hello"
    mtime = datetime.datetime.fromtimestamp(dst_path.stat().st_mtime)

    await resume._upload()
    assert datetime.datetime.fromtimestamp(dst_path.stat().st_mtime) == mtime

    async with aiofiles.open(src_path, mode="w") as f:
        await f.write("world")
        await f.flush()
    await resume._upload()
    async with aiofiles.open(dst_path) as f:
        assert (await f.read()) == "world"


@pytest.mark.asyncio
async def test_resume__upload_failure():
    output_dir = tempfile.TemporaryDirectory()
    server_dir = tempfile.TemporaryDirectory()
    src = tempfile.NamedTemporaryFile(dir=Path(output_dir.name))
    src_path: Path = Path(src.name)
    async with aiofiles.open(src_path, mode="w") as f:
        await f.write("hello")
        await f.flush()

    Setting().output_dir = Path(output_dir.name)
    resume: Resume = Resume(Path(server_dir.name), [src.name])
    dst_path: Path = Path(server_dir.name) / Path(src.name).name

    with patch("vuli.resume.Resume._upload_by_copy") as mock:

        def error(*args, **kwargs) -> bool:
            return False

        mock.side_effect = error
        await resume._upload()
        assert dst_path.exists() is False

    await resume._upload()
    async with aiofiles.open(dst_path) as f:
        assert (await f.read()) == "hello"
