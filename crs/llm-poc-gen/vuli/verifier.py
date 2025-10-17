import asyncio
import logging
import os
import re
import subprocess
import tempfile
from abc import ABC, abstractmethod
from functools import reduce
from pathlib import Path
from typing import Optional

import aiofiles

from vuli.common.decorators import SEVERITY, step
from vuli.common.setting import Setting
from vuli.common.singleton import Singleton
from vuli.cp import CP
from vuli.debugger import GDB, Debugger
from vuli.joern import Joern
from vuli.query_loader import QueryLoader
from vuli.struct import CodeLocation, CodePoint
from vuli.util import async_process_run_and_exit


class BlobVerifier(ABC):
    def __init__(self, enable_integer_overflow: bool = False):
        self._enable_integer_overflow: bool = enable_integer_overflow

    @abstractmethod
    async def visited_for_path(
        self, blob: bytes, harness_file_path: Path, path: list[CodePoint]
    ) -> list[CodeLocation]:
        pass

    @abstractmethod
    async def visited_for_method(
        self, blob: bytes, harness_file_path: Path, method_name: str
    ) -> list[CodeLocation]:
        pass

    async def verify(
        self, blob: bytes, harness_file_path: Path, use_jazzer: bool
    ) -> bool:
        result, _ = await CP().run_pov(
            blob,
            self._enable_integer_overflow,
            harness_file_path,
            use_jazzer,
        )
        return result


class JavaAgentVerifier(BlobVerifier):
    def __init__(self, tool: Path):
        super().__init__()
        self._logger = logging.getLogger("JavaAgentVerifier")
        self.__tool = tool

    async def visited_for_path(
        self, blob: bytes, harness_file_path: Path, path: list[CodePoint]
    ) -> list[CodeLocation]:
        points: list[CodeLocation] = [CodeLocation(x.path, x.line) for x in path]
        files: list[Path] = list({Path(x.path) for x in path})
        visited: list[CodeLocation] = await self._get_visited(
            blob, files, harness_file_path
        )
        valid_visited: list[CodeLocation] = [x for x in visited if x in points]
        return valid_visited

    async def visited_for_method(
        self, blob: bytes, harness_file_path: Path, method_name: str
    ) -> list[CodeLocation]:
        joern_query: str = f"""
cpg.method.where(_.fullNameExact({method_name}))
    .map(x => (
        x.filename.headOption.getOrElse(""),
        x.lineNumber.getOrElse(-1),
        x.lineNumberEnd.getOrElse(-1)))
    .headOption
    .getOrElse(("", -1, -1))
"""
        joern_result: dict = await Joern().run_query(joern_query)
        file_path: str = joern_result.get("_1", "")
        line: int = joern_result.get("_2", -1)
        line_end: int = joern_result.get("_3", -1)
        if file_path == "" or line == -1 or line_end == -1:
            return []

        visited: list[CodeLocation] = await self._get_visited(
            blob, [Path(file_path)], harness_file_path
        )
        valid_visited: list[CodeLocation] = [
            x for x in visited if x.line >= line and x.line <= line_end
        ]
        return valid_visited

    async def __from_harness_path_to_harness_class_name(
        self, harness_file_path: Path
    ) -> str:
        harness_name: str = CP().get_harness_name(harness_file_path)
        query: str = f"""
cpg.file.where(_.nameExact("{harness_file_path}")).method.where(_.nameExact("{CP().target_method(harness_name)}")).typeDecl.fullName.headOption.getOrElse("")
"""
        class_name: str = await Joern().run_query(query)
        return class_name

    async def __from_files_to_class_names(self, files: list[Path]) -> dict:
        query: str = f"""
val files: Set[String] = Set({", ".join([f"\"{x}\"" for x in files])})
files.map(file => (file -> cpg.file.where(_.nameExact(file)).typeDecl.fullName.l.distinct)).toMap
"""
        class_names: dict = await Joern().run_query(query)
        return class_names

    async def _get_visited(
        self,
        blob: bytes,
        files: list[Path],
        harness_file_path: Path,
    ) -> list[CodeLocation]:
        async def get_stdout(
            blob: bytes, file_and_class_names: dict, harness_file_path: Path
        ) -> str:
            blob_file = tempfile.NamedTemporaryFile(dir=Setting().tmp_dir, mode="wb")
            blob_file.write(blob)
            blob_file.flush()
            jars: list[str] = [
                jar
                for jar in CP().get_jars(harness_file_path)
                if not Path(jar).name.startswith("asm-")
            ]
            class_path: str = ":".join(jars)
            harness_name: str = await self.__from_harness_path_to_harness_class_name(
                harness_file_path
            )
            target_classes: list[str] = reduce(
                lambda y, x: y + x, file_and_class_names.values(), []
            )
            target_classes: list[str] = list(
                {target_class.replace(".", "/") for target_class in target_classes}
            )
            cmd: list[str] = [
                "java",
                f"-javaagent:{self.__tool}={','.join(target_classes)}",
                "-cp",
                class_path,
                "sr.AgentMain",
                harness_name,
                blob_file.name,
            ]
            stdout_file = tempfile.NamedTemporaryFile(dir=Setting().tmp_dir)
            work_dir = tempfile.TemporaryDirectory(dir=Setting().tmp_dir)
            # NOTE: The corner case here is that valid execution took more than 10 seconds.
            with Path(stdout_file.name).open("w") as f:
                p = await asyncio.create_subprocess_exec(
                    *cmd,
                    cwd=work_dir.name,
                    stdout=f,
                    stderr=subprocess.DEVNULL,
                )
                try:
                    await async_process_run_and_exit(p, 10)
                except TimeoutError:
                    pass

            async with aiofiles.open(stdout_file.name) as f:
                stdout: str = await f.read()
            return stdout

        def get_visited_lines(
            file_and_class_names: dict, stdout: str
        ) -> list[CodeLocation]:
            table: dict = {
                name: file
                for file, names in file_and_class_names.items()
                for name in names
            }
            visited_lines: list[list[str]] = [
                line[5:].split(":")
                for line in stdout.split("\n")
                if line.startswith("[BB] ")
            ]
            visited_lines: list[tuple[str, str]] = [
                (table.get(line[0].replace("/", "."), ""), line[1])
                for line in visited_lines
                if len(line) == 2
            ]
            visited_lines: list[CodeLocation] = [
                CodeLocation(path, int(line))
                for path, line in visited_lines
                if len(path) > 0 and line.isdigit()
            ]
            return visited_lines

        file_and_class_names = await self.__from_files_to_class_names(files)
        stdout: str = get_stdout(blob, file_and_class_names, harness_file_path)
        visited_lines: list[CodeLocation] = get_visited_lines(
            file_and_class_names, stdout
        )
        return visited_lines


# class JazzerJacocoVerifier(
#     BlobVerifier,
# ):
#     def __init__(self, cp: CP, enable_integer_overflow: bool = False):
#         self.__cp = cp
#         self.__enable_integer_overflow = enable_integer_overflow
#         self.__missed_lines: dict = {}

#     def get_visited_lines(self) -> list[CodeLocation]:
#         raise NotImplementedError

#     def verify(self, blob: bytes, harness_path: str, target: CodeLocation) -> bool:
#         self.__missed_lines: dict = {}
#         report_file = tempfile.NamedTemporaryFile("r")
#         crash_found, exception_log = self.__cp.run_pov(
#             blob, self.__enable_integer_overflow, harness_path, Path(report_file.name)
#         )
#         self.__missed_lines: dict = self.__get_missed_lines(Path(report_file.name))
#         visited: bool = self.__check_visited(self.__missed_lines, target)
#         raise NotImplementedError
#         return (crash_found, visited)

#     def __check_visited(self, missed_lines: dict, target: CodeLocation) -> bool:
#         file_name: str = Path(target.path).name
#         file_missed_lines: list[str] = missed_lines.get(file_name, [])
#         if len(file_missed_lines) == 0:
#             return False
#         return not target.line in file_missed_lines

#     def __get_missed_lines(self, report_file: Path) -> dict:
#         with report_file.open("r") as f:
#             lines: list[str] = f.readlines()
#         if len(lines) == 0:
#             return {}
#         start_idx: int = -1
#         end_idx: int = -1
#         for i, line in enumerate(lines):
#             if line.startswith("Missed lines:"):
#                 start_idx = i + 1
#                 continue
#             if start_idx != -1 and len(line) == 0:
#                 end_idx = i
#                 break

#         if start_idx == -1:
#             raise NotImplementedError("Handle This Error: Invalid Jacoco Format")
#         if end_idx == -1:
#             end_idx = len(lines)

#         result: dict = {}
#         for line in lines[start_idx : end_idx + 1]:
#             tokens = line.split(":")
#             file_name: str = tokens[0]
#             missed_lines: str = tokens[1].strip()[1:-1]
#             missed_lines: list[str] = missed_lines.split(",")
#             missed_lines: list[str] = [x.strip() for x in missed_lines]
#             missed_lines: list[int] = [
#                 int(x.strip()) for x in missed_lines if len(x) > 0
#             ]
#             result[file_name] = missed_lines
#         return result


class DebuggerVerifierCache(metaclass=Singleton):
    def __init__(self):
        self.class_to_file: dict[str, str] = {}
        self.method_to_class: dict[str, str] = {}
        self.method_to_lines: dict[str, list[int]] = {}


class DebuggerVerifier(BlobVerifier):
    def __init__(self, debugger: Debugger):
        super().__init__()
        self._logger = logging.getLogger("DebuggerVerifier")
        self._debugger = debugger

    async def visited_for_path(
        self, blob: bytes, harness_file_path: Path, path: list[CodePoint]
    ) -> list[CodeLocation]:
        async def to_breakpoints(path: list[CodePoint]) -> list[str]:
            # Identify method names that are queried
            names: set[str] = {
                x.method
                for x in path
                if x.method not in DebuggerVerifierCache().method_to_class
            }
            if len(names) > 0:
                # Run Query
                query: str = f"""
    List({",".join([f"\"{name}\"" for name in names])})
        .map(x => (x, cpg.method.fullNameExact(x).typeDecl.fullName.headOption.getOrElse("")))
        .toMap"""
                result: dict[str, str] = await Joern().run_query(query)

                # Update Result
                DebuggerVerifierCache().method_to_class.update(result)

            breaks: list[str] = [
                f"stop go at {DebuggerVerifierCache().method_to_class[x.method]}:{x.line}"
                for x in path
                if len(DebuggerVerifierCache().method_to_class.get(x.method, "")) > 0
                and x.line > 0
            ]
            return breaks

        debugger_commands: list[str] = await to_breakpoints(path)
        harness_name: str = CP().get_harness_name(harness_file_path)
        try:
            debugger_result: str = await self._debugger.run(
                harness_name, blob, debugger_commands
            )
            self._logger.debug(f"Debug Command:\n{"\n".join(debugger_commands)}")
            self._logger.debug(f"Debug Blob: {blob}")
            self._logger.debug(f"Debugger Result:\n{debugger_result}")
            breaks: list[str] = [
                x for x in debugger_result.split("\n") if "Breakpoint hit:" in x
            ]
            result: list[CodeLocation] = await self._to_locations(breaks)
            return result
        finally:
            await self._debugger.stop()

    async def visited_for_method(
        self, blob: bytes, harness_file_path: Path, method_name: str
    ) -> list[CodeLocation]:

        async def to_breakpoints(method_name: str) -> list[str]:
            if method_name not in DebuggerVerifierCache().method_to_class:
                query: str = f"""
cpg.method.fullNameExact("{method_name}").typeDecl.fullName.headOption.getOrElse("")
"""
                result: str = await Joern().run_query(query)
                DebuggerVerifierCache().method_to_class[method_name] = result

            if method_name not in DebuggerVerifierCache().method_to_lines:
                query: str = f"""
cpg.method.fullNameExact("{method_name}").lineNumber.distinct.sorted"""
                result: list[int] = await Joern().run_query(query)
                DebuggerVerifierCache().method_to_lines[method_name] = result

            class_name: str = DebuggerVerifierCache().method_to_class[method_name]
            if len(class_name) == 0:
                return []
            return [
                f"stop go at {class_name}:{x}"
                for x in DebuggerVerifierCache().method_to_lines[method_name]
            ]

        breakpoints: list[str] = await to_breakpoints(method_name)
        debugger_commands: list[str] = breakpoints + ["run"]
        harness_name: str = CP().get_harness_name(harness_file_path)
        try:
            debugger_result: str = await self._debugger.run(
                harness_name, blob, debugger_commands
            )
            breaks: list[str] = [
                x for x in debugger_result.split("\n") if "Breakpoint hit:" in x
            ]
            result: list[CodeLocation] = await self._to_locations(breaks)
            return result
        finally:
            await self._debugger.stop()

    async def _to_locations(self, breaks: list[str]) -> list[CodeLocation]:
        output_1: list[tuple[str, int]] = []
        for x in breaks:
            tokens: list[str] = x.split(" line=")
            if len(tokens) != 2:
                self._logger.warning(f"Unexpected Debugger Print: {x}")
                continue

            try:
                class_name: str = tokens[0][
                    tokens[0].rfind(" ") + 1 : tokens[0].rfind(".")
                ]
                line: int = int(tokens[1][: tokens[1].find(" ")].replace(",", ""))
                if len(class_name) > 0 and line > 0:
                    output_1.append((class_name, line))
            except Exception:
                self._logger.warning(f"Unexpected Debugger Print: {x}")
                continue

        names: set[str] = {
            x for x, _ in output_1 if x not in DebuggerVerifierCache().class_to_file
        }
        if len(names) > 0:
            query: str = f"""
    List({",".join([f"\"{x}\"" for x in names])})
        .map(x => (x, cpg.typeDecl.fullNameExact(x).filename.headOption.getOrElse("")))
        .toMap"""
            result: dict[str, str] = await Joern().run_query(query)
            DebuggerVerifierCache().class_to_file.update(result)

        result: list[tuple[str, int]] = [
            (DebuggerVerifierCache().class_to_file[x], y)
            for x, y in output_1
            if len(DebuggerVerifierCache().class_to_file.get(x, "")) > 0
        ]
        result: list[tuple[str, int]] = list(dict.fromkeys(result).keys())
        return [CodeLocation(x, y) for x, y in result]


class GDBVerifier(BlobVerifier):
    def __init__(self):
        super().__init__()
        self._logger = logging.getLogger("GDBVerifier")

    async def visited_for_path(
        self, blob: bytes, harness_file_path: Path, path: list[CodePoint]
    ) -> list[CodeLocation]:

        # Prepare GDB commands
        new_path = path
        cmd: list[str] = [
            f"{Path(*Path(x.path).parts[1:])}:{x.line}" for x in new_path if x.line > 0
        ]

        # Run
        gdb: str = await GDB().run(CP().get_harness_name(harness_file_path), blob, cmd)

        # Make Result
        @step(None, SEVERITY.NORMAL, "GDBVerifier")
        def _to_locations(lines: str, index: int) -> Optional[CodeLocation]:
            pattern = r"""
                (?:Thread\s+\d+\s+"[^"]+"\s+hit\s+)?
                Breakpoint\s+\d+,
                .+?
                \s+at\s+
                (?P<filepath>[^:]+)
                :
                (?P<linenum>\d+)
                \b
            """

            match = re.search(pattern, lines[index], re.VERBOSE)
            if match:
                file_path = match.group("filepath").strip()
                line_num = int(match.group("linenum"))

                # TODO: Do not use constant here, looks sarif system dependent.
                base_path = "/src"
                if file_path.startswith(base_path):
                    rel_path = os.path.relpath(file_path, base_path)
                    return CodeLocation(rel_path, line_num)
            return None

        lines: list[str] = [x.strip() for x in gdb.split("\n")]
        result: list[Optional[CodeLocation]] = [
            _to_locations(lines, x) for x in range(0, len(lines) - 1)
        ]
        result: list[CodeLocation] = [x for x in result if x is not None]
        result: list[CodeLocation] = list(dict.fromkeys(result))
        return result

    async def visited_for_method(
        self, blob: bytes, harness_file_path: Path, func_name: str
    ) -> list[CodeLocation]:
        return []
