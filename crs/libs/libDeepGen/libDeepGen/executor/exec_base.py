from dataclasses import dataclass
from abc import ABC, abstractmethod

from typing import Optional


@dataclass
class ExecResult:
    """Result of each execution, for result submission, script management, and do statistics."""
    success: bool

    result: Optional[bytes] = None

    output: Optional[str] = None

    error: Optional[Exception] = None

    exec_time: Optional[float] = None


class Exec(ABC):
    """Exec is an abstract base class for different exec implementations."""

    @abstractmethod
    def exec(self, script_args: list[str] = None, verbose: bool = False) -> ExecResult:
        pass

