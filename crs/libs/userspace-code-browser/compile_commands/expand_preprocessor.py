#!/usr/bin/env python3

import json
from pathlib import Path
import subprocess
import shutil

def get_expansion_command(arguments: list[str], filename: str, outfile: Path) -> list[str]:
    ret = [
        "clang",
        "-E",
        "-C",
        "-dD",
    ]
    getnext = False
    for arg in arguments:
        if arg == "-I" or arg == "-D":
            ret.append(arg)
            getnext = True
        elif arg.startswith("-I") or arg.startswith("-D"):
            ret.append(arg)
        elif getnext:
            ret.append(arg)
            getnext = False
    ret.extend([
        "-o",
        str(outfile),
        filename
    ])
    return ret
    
def expand_all_source_code():
    ccs = Path("/out/compile_commands.json").read_text()
    ccj = json.loads(ccs)
    for obj in ccj:
        directory = obj["directory"]
        filename = obj["file"]
        arguments = obj["arguments"]
        outfile = (Path("/out/expanded") / filename).resolve()
        outfile.parent.mkdir(parents=True, exist_ok=True)
        cmd = get_expansion_command(arguments, filename, outfile)
        # print("Executing", ' '.join(cmd))
        subprocess.run(cmd, cwd=directory, check=True)

    # Copy remaining files that weren't expanded
    for path in Path().rglob('*'):
        if not path.is_file():
            continue
        expanded_path = Path("/out/expanded") / path
        if not expanded_path.exists():
            expanded_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, expanded_path)

if __name__ == "__main__":
    expand_all_source_code()
