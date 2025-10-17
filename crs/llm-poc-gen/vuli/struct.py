import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CodeLocation:
    path: str
    line: int
    column: int = -1

    @staticmethod
    def create(msg: str):
        tokens: list[str] = [x.strip() for x in msg.split(":")]
        if len(tokens) != 2 and len(tokens) != 3:
            raise ValueError(f"Invalid Argument: {msg}")
        path: str = tokens[0]
        line: int = int(tokens[1])
        column: int = int(tokens[2]) if len(tokens) == 3 else -1
        return CodeLocation(path=path, line=line, column=column)

    def to_dict(self):
        return {"path": self.path, "line": self.line, "column": self.column}


@dataclass(frozen=True)
class CodePoint:
    path: str
    method: str
    line: int
    column: int = -1

    def __str__(self) -> str:
        pattern = r"\.(\w+)(?=:)"
        matched = re.search(pattern, self.method)
        name: str = matched.group(1) if matched else self.method
        return f"{Path(self.path).name}:{name}:{self.line}:{self.column if self.column != -1 else ""}"

    def to_dict(self):
        return {
            "path": self.path,
            "method": self.method,
            "line": self.line,
            "column": self.column,
        }


@dataclass(frozen=True)
class TaskKey:
    v_point: CodeLocation
    v_type: str


@dataclass
class Task:
    code: str
    files: list[str]
    v_point: CodeLocation
    v_type: str


@dataclass
class Sanitizer:
    name: str
    sentinel: list[str]


@dataclass
class VulInfo:
    harness_id: str
    sink_id: int
    v_paths: list[CodePoint]
    v_point: CodeLocation

    def __str__(self) -> str:
        return (
            f"{self.v_point}] with [{len(self.v_paths)} paths from {self.harness_id}]"
        )

    def to_dict(self):
        return {
            "harness_id": self.harness_id,
            "sink_id": self.sink_id,
            "v_paths": [cp.to_dict() for cp in self.v_paths],
            "v_point": self.v_point.to_dict(),
        }


@dataclass
class SinkCandidate:
    v_type: str
    v_point: CodeLocation
    method: str
    id: int


class LLMBudgetExceed(Exception):
    def __init__(self, message=""):
        super().__init__(message)


class LLMParseException(Exception):
    def __init__(self, message=""):
        super().__init__(message)


class LLMRetriable(Exception):
    def __init__(self, message=""):
        super().__init__(message)
