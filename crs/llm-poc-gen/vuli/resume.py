import hashlib
import logging
import os
from pathlib import Path
from typing import Optional

import aiofiles

from vuli.common.decorators import SEVERITY, async_safe, step
from vuli.common.setting import Setting
from vuli.task import ServiceHandler


class Resume(ServiceHandler):
    def __init__(self, dst: Path, srcs: list[str], interval: int = 60):
        super().__init__(interval)
        self._logger = logging.getLogger(self.__class__.__name__)
        self._dst = dst
        self._srcs: list[Path] = [Setting().output_dir / src for src in srcs]
        self._table = {}

    async def download(self) -> None:
        output_dir: Path = Setting().output_dir
        if not isinstance(output_dir, Path) or not output_dir.exists():
            self._logger.info(
                f"Skip Download [reason=NO_OUTPUT_DIR, output_dir={output_dir}"
            )
            return

        result: list[tuple[Path, Path]] = [
            (self._dst / src.name, src) for src in self._srcs
        ]
        self._logger.info(f"Download Targets: {result}")
        result: list[tuple[Path, Path]] = [
            (src, dst) for src, dst in result if src.exists()
        ]
        if len(result) == 0:
            self._logger.info("Skip Download [reason=NOTHING EXIST]")

        result: list[tuple[Path, bool]] = [
            (dst, await self._download_file(src, dst)) for src, dst in result
        ]
        result: list[Path] = [dst for dst, flag in result if flag is True]
        if len(result) > 0:
            self._logger.info(
                f"Downloaded [targets={",".join([str(dst) for dst in result])}]"
            )

    @step(False, SEVERITY.WARNING, "Resume")
    async def _download_file(self, src: Path, dst: Path) -> bool:
        if not src.exists():
            return False

        checksum_path: Path = src.parent / self._checksum_name(src)
        if not checksum_path.exists():
            return False

        limit: int = 3
        content: str = ""
        while limit > 0:
            try:
                async with aiofiles.open(checksum_path) as f:
                    checksum: str = await f.read()
                if self._key(src) == str(checksum):
                    async with aiofiles.open(src, mode="rb") as f:
                        content = await f.read()
                    break
            finally:
                limit -= 1

        if len(content) > 0:
            async with aiofiles.open(dst, mode="wb") as f:
                await f.write(content)
            return True

        self._logger.warning(f"Download Failed [path={src}]")
        return False

    async def _run(self) -> None:
        await self._upload()

    async def _upload(self) -> None:
        result: list[tuple[Path, Optional[str]]] = [
            (src, self._key(src)) for src in self._srcs
        ]
        failures: list[Path] = [src for src, key in result if key is None]
        if len(failures) > 0:
            self._logger.info(
                f"Skip Upload [reason=FAIL_TO_READ, srcs={",".join([str(src) for src in failures])}]"
            )

        result: list[tuple[Path, str, bool]] = [
            (src, key, self._table.get(src.name, "") != key)
            for src, key in result
            if key is not None
        ]
        failures: list[Path] = [src for src, _, flag in result if flag is False]
        if len(failures) > 0:
            self._logger.info(
                f"Skip Upload [reason=NO_CHANGE, srcs={",".join([str(src) for src in failures])}]"
            )

        result: list[tuple[Path, str, bool]] = [
            (src, key, await self._upload_file(src))
            for src, key, flag in result
            if flag is True
        ]
        failures: list[Path] = [src for src, _, flag in result if flag is False]
        if len(failures) > 0:
            self._logger.info(
                f"Skip Upload [reason=FAIL_TO_UPLOAD, srcs={",".join([str(src) for src in failures])}]"
            )

        result: list[tuple[Path], bool] = [
            (src, self.__update(src, key)) for src, key, flag in result if flag is True
        ]
        if len(result) > 0:
            self._logger.info(
                f"Uploaded [srcs={",".join([str(src) for src, _ in result])}]"
            )

    @step(None, SEVERITY.ERROR, "Upload")
    def _key(self, path: Path) -> Optional[str]:
        if not isinstance(path, Path) or not path.exists():
            return None

        with path.open(mode="rb") as f:
            hasher = hashlib.sha256()
            hasher.update(f.read())
        return hasher.hexdigest()

    def _checksum_name(self, path: Path) -> str:
        return f"{path.name}.checksum"

    @step(None, SEVERITY.ERROR, "Upload")
    def __update(self, path: Path, key: str) -> None:
        self._table[path.name] = key

    async def _upload_file(self, path: Path) -> bool:
        checksum: str = self._key(path)
        checksum_path: Path = Setting().tmp_dir / self._checksum_name(path)
        async with aiofiles.open(checksum_path, mode="wb") as f:
            await f.write(checksum.encode("utf-8"))
            await f.flush()
        if not await self._upload_by_copy(checksum_path):
            return False
        return await self._upload_by_copy(path)

    @async_safe(False, SEVERITY.WARNING, "Upload")
    async def _upload_by_copy(self, path: Path) -> bool:
        """Write content to a temporary file and then atomically move it to the target path."""
        temp_path = self._dst / f".hidden.{path.name}"
        try:
            async with aiofiles.open(path, mode="rb") as f:
                content = await f.read()
            async with aiofiles.open(temp_path, mode="wb") as f:
                await f.write(content)
                await f.flush()
                os.fsync(f.fileno())
            os.replace(temp_path, self._dst / path.name)
            return True
        except Exception:
            try:
                os.unlink(temp_path)
            except Exception:
                pass
            return False
