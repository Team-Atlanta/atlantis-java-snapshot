import sys
from pathlib import Path

import aiofiles

from vuli.joern import Joern
from vuli.struct import CodePoint


async def create_code_table(path: list[CodePoint]) -> dict:
    methods: list[str] = [method for method in dict.fromkeys([x.method for x in path])]
    joern_query: str = f"""
List({",".join([f"\"{method}\"" for method in methods])})
    .flatMap(x => cpg.method.fullNameExact(x))
    .collect{{case x => (x.filename, x.lineNumber, x.lineNumberEnd)}}
    .collect{{case (a, Some(b), Some(c)) =>  Map("filename" -> a, "lineNumber" -> b, "lineNumberEnd" -> c)}}
    .l"""
    joern_result: list[dict] = await Joern().run_query(joern_query)
    if len(joern_result) == 0:
        return {}

    harness_path: str = joern_result[0]["filename"]
    code_table: dict = {}
    [
        code_table.setdefault(x["filename"], []).append(
            (x["lineNumber"], x["lineNumberEnd"])
        )
        for x in joern_result
    ]
    code_table: dict = {
        key: sorted(value, key=lambda x: int(x[0])) for key, value in code_table.items()
    }
    code_table[harness_path] = [(1, sys.maxsize)]
    return code_table


class BaseReader:
    def __init__(self, source_dir: Path):
        self.__source_dir = source_dir

    def read(self, path: Path, with_line: bool = False):
        lines = self.readlines(path, with_line)
        return "".join(lines)

    async def read_by_table(self, table: dict) -> str:
        result: str = ""
        for file, info in table.items():
            lines: list[str] = await self.readlines(Path(file), True)
            for i in reversed(range(0, len(lines))):
                keep: bool = False
                for start_idx, end_idx in info:
                    if (i + 1 <= end_idx) and (i + 1 >= start_idx):
                        keep = True
                        break
                if not keep:
                    del lines[i]
            if len(result) != 0:
                result += "\n"
            result += f"{file}:\n{"".join(lines)}"
        return result

    async def readlines(self, path: Path, with_line: bool = False):
        async with aiofiles.open(self.__source_dir / path) as f:
            lines: list[str] = await f.readlines()

        if with_line:
            line_number_width: int = len(str(len(lines)))
            lines: list[str] = [
                f"{str(index + 1).rjust(line_number_width)}   {line}"
                for index, line in enumerate(lines)
            ]
        return lines
