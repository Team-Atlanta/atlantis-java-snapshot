from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from vuli.debugger import JDB
from vuli.struct import CodeLocation, CodePoint
from vuli.verifier import DebuggerVerifier, DebuggerVerifierCache, GDBVerifier


@pytest.mark.asyncio
@patch("vuli.joern.Joern.run_query")
@patch("vuli.debugger.JDB.stop")
@patch("vuli.debugger.JDB.run")
async def test_visited_for_path(patch_run, patch_stop, patch_run_query):
    def mock_stop(*args, **kwargs) -> None:
        pass

    def mock_run(*args, **kwargs) -> bool:
        return """
main[1] Deferring breakpoint Path:1.
It will be set after the class is loaded.
main[1] Deferring breakpoint Path:2.
It will be set after the class is loaded.
main[1] Deferring breakpoint Path:3.
It will be set after the class is loaded.

Breakpoint hit: "thread=main", Path.method(), line=1 bci=0
>
Breakpoint hit: "thread=main", Path.method(), line=2 bci=8
>
Breakpoint hit: "thread=main", Path.method(), line=3 bci=16
>
The application exited
"""

    def mock_run_query(*args, **kwargs) -> Any:
        if args[0].startswith("\ncpg"):
            return "path.java"
        else:
            return []

    patch_stop.side_effect = mock_stop
    patch_run.side_effect = mock_run
    patch_run_query.side_effect = mock_run_query
    DebuggerVerifierCache().class_to_file = {
        "Path": "path.java",
    }
    verifier = DebuggerVerifier(JDB())
    visited: list[CodeLocation] = await verifier.visited_for_path(
        b"blob",
        Path("harness_path"),
        [
            CodePoint("path.java", "method", 1),
            CodePoint("path.java", "method", 2),
            CodePoint("path.java", "method", 3),
        ],
    )
    assert visited == [
        CodeLocation("path.java", 1),
        CodeLocation("path.java", 2),
        CodeLocation("path.java", 3),
    ]


@pytest.mark.asyncio
@patch("vuli.debugger.GDB.run")
async def test_gdbverifier_visited_for_path(patch_1):
    def mock_1(*args, **kwargs) -> bool:
        return """
GNU gdb (Ubuntu 9.2-0ubuntu1~20.04.2) 9.2
Copyright (C) 2020 Free Software Foundation, Inc.
License GPLv3+: GNU GPL version 3 or later <http://gnu.org/licenses/gpl.html>
This is free software: you are free to change and redistribute it.
There is NO WARRANTY, to the extent permitted by law.
Type "show copying" and "show warranty" for details.
This GDB was configured as "x86_64-linux-gnu".
Type "show configuration" for configuration details.
For bug reporting instructions, please see:
<http://www.gnu.org/software/gdb/bugs/>.
Find the GDB manual and other documentation resources online at:
    <http://www.gnu.org/software/gdb/documentation/>.

For help, type "help".
Type "apropos word" to search for commands related to "word"...
Reading symbols from /app/crs-cp-java/llm-poc-gen/tests/sample/c/build/harness...
(gdb) (gdb) (gdb) Breakpoint 1 at 0x54dbf8: file path.c, line 1.
(gdb) Breakpoint 2 at 0x54d91b: file path.c, line 2.
(gdb) Breakpoint 3 at 0x54d9f0: file path.c, line 3.
(gdb) Starting program: harness -runs=1 -timeout=5 blob
[Thread debugging using libthread_db enabled]
Using host libthread_db library "/lib/x86_64-linux-gnu/libthread_db.so.1".
[New Thread 0x7ffff3a3e700 (LWP 2944)]

Thread 1 "harness" hit Breakpoint 1, LLVMFuzzerTestOneInput (Data=0x6020000000b0 "2", Size=1) at /src/path.c:1
1           XXXX
(gdb) (gdb) Continuing.

Thread 1 "harness" hit Breakpoint 2, target_1 (Data=0x6020000000b1 "", Size=0) at /src/path.c:2
2           XXXX
(gdb) Continuing.

Thread 1 "harness" hit Breakpoint 3, target_1 (Data=0x6020000000b1 "", Size=0) at /src/path.c:3
3           XXXX
(gdb) Continuing.
[Thread 0x7ffff3a3e700 (LWP 2944) exited]
[Inferior 1 (process 2940) exited normally]
(gdb)
"""

    patch_1.side_effect = mock_1
    result: list[CodeLocation] = await GDBVerifier().visited_for_path(
        b"blob",
        Path("harness_path"),
        [
            CodePoint("path.c", "func", 1),
            CodePoint("path.c", "func", 2),
            CodePoint("path.c", "func", 3),
        ],
    )
    assert result == [
        CodeLocation("path.c", 1),
        CodeLocation("path.c", 2),
        CodeLocation("path.c", 3),
    ]


@pytest.mark.asyncio
async def test_gdbverifier_visited_for_method():
    result: list[CodeLocation] = await GDBVerifier().visited_for_method(
        b"", Path(""), ""
    )
    assert result == []
