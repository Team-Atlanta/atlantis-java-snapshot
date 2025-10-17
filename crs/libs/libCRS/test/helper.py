import dataclasses
from pathlib import Path
import subprocess

from libCRS import CP


@dataclasses.dataclass
class CP_Info:
    key: str   # folder name
    name: str  # name in project.yaml
    git_url: str

def set_up_cp(path: Path, cp_info: CP_Info) -> CP:
    path /= cp_info.key
    if not path.exists():
        subprocess.check_call(["git", "clone", str(cp_info.git_url), str(path)])
        for sub in ["cpsrc-prepare", "docker-build", "docker-config-local"]:
            subprocess.check_call(["make", sub], cwd = str(path))
    return CP(path)

def makedirs(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)

def remove(path: Path) -> None:
    subprocess.check_call(["rm", "-rf", str(path)])
