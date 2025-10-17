#!/usr/bin/env python3

import os
import subprocess
from pathlib import Path
import argparse
from dataclasses import dataclass
import re
import shutil

import yaml
try:
    from yaml import CSafeLoader as SafeLoader
except ImportError:
    from yaml import SafeLoader


ROOT = Path(__file__).parent

@dataclass
class RepoContext:
    oss_fuzz: str
    repo: str
    project: str
    project_dir: str
    sanitizer: str
    engine: str
    language: str

@dataclass
class MountContext:
    outdir: Path
    workdir: Path
    nixdir: Path

# ripped from infra/helper.py
WORKDIR_REGEX = re.compile(r'\s*WORKDIR\s*([^\s]+)')

def workdir_from_lines(lines, default='/src'):
  """Gets the WORKDIR from the given lines."""
  for line in reversed(lines):  # reversed to get last WORKDIR.
    match = re.match(WORKDIR_REGEX, line)
    if match:
      workdir = match.group(1)
      workdir = workdir.replace('$SRC', '/src')

      if not os.path.isabs(workdir):
        workdir = os.path.join('/src', workdir)

      # just pray that default works
      ret = os.path.normpath(workdir)
      return ret if ret != "/src" else default

  return default

def get_project_metadata(project: str, oss_fuzz: Path, repo: Path) -> RepoContext:
    oss_fuzz_project_path = oss_fuzz / "projects" / project

    dockerfile_path = oss_fuzz_project_path / "Dockerfile"
    dockerfile_lines = dockerfile_path.read_text().splitlines()

    # /src actually breaks on libucl
    project_dir = workdir_from_lines(dockerfile_lines, default=(Path("/src") / Path(project).name).as_posix())
    
    project_yaml_text = (oss_fuzz_project_path / "project.yaml").read_text()
    project_yaml = yaml.load(project_yaml_text, Loader=SafeLoader)

    if "sanitizers" not in project_yaml:
        sanitizer = "address"
    else:
        sanitizers = project_yaml["sanitizers"]
        if "address" in sanitizers:
            sanitizer = "address"
        else:
            sanitizer = sanitizers[0]

    if "fuzzing_engines" not in project_yaml:
        engine = "libfuzzer"
    else:
        engines = project_yaml["fuzzing_engines"]
        if "libfuzzer" in engines:
            engine = "libfuzzer"
        else:
            engine = engines[0]

    language = project_yaml["language"]

    return RepoContext(
        oss_fuzz = str(oss_fuzz),
        repo = str(repo),
        project = project,
        project_dir = project_dir,
        sanitizer = sanitizer,
        engine = engine,
        language = language,
    )
    

def populate_mounts(outdir: Path):
    # subprocess.run([ROOT / "populate-mounts.sh"], check=True)
    shutil.copy(ROOT / "compile-wrapper.sh", outdir)
    shutil.copy(ROOT / "expand_preprocessor.py", outdir)

def get_mount_context(ctx: RepoContext) -> MountContext:
    safe_project = ctx.project.replace("/", "_")
    outdir = ROOT / f"build/out/{safe_project}"
    workdir = ROOT / f"build/work/{safe_project}"
    nixdir = ROOT / "nix"

    outdir.mkdir(parents=True, exist_ok=True)
    workdir.mkdir(parents=True, exist_ok=True)

    populate_mounts(outdir)
    assert nixdir.is_dir()
    
    return MountContext(outdir=outdir, workdir=workdir, nixdir=nixdir)
    
    
def docker_run(rctx: RepoContext, mctx: MountContext, cmd: list[str]):
    subprocess.run([
        'docker',
        'run',
        '--privileged',
        '--shm-size=2g',
        '--platform',
        'linux/amd64',
        '--rm',
        '-i',
        '-e', f'FUZZING_ENGINE={rctx.engine}',
        '-e', f'SANITIZER={rctx.sanitizer}',
        '-e', 'ARCHITECTURE=x86_64',
        '-e', f'PROJECT_NAME={rctx.project}',
        '-e', 'HELPER=True',
        '-e', f'FUZZING_LANGUAGE={rctx.language}',
        '-v', f'{rctx.repo}:{rctx.project_dir}',
        '-v', f'{str(mctx.outdir)}:/out',
        '-v', f'{str(mctx.workdir)}:/work',
        '-v', f'{str(mctx.nixdir)}:/nix',
        '-t', f'aixcc-afc/{rctx.project}',
        *cmd
    ], check=True)
    
def build_fuzzers_compile_commands(rctx: RepoContext, mctx: MountContext):

    docker_run(rctx, mctx, ["/out/compile-wrapper.sh"])

    compile_commands_path = mctx.outdir / "compile_commands.json"
    assert compile_commands_path.is_file()
    
    
# e.g. python3 docker_build.py --oss-fuzz ~/oss-fuzz --repo ~/cp-user-nginx-asc-source --project "aixcc/c/asc-nginx"
def main(project: Path, oss_fuzz: Path, repo: Path):
    rctx = get_project_metadata(project, oss_fuzz, repo)
    mctx = get_mount_context(rctx)
    build_fuzzers_compile_commands(rctx, mctx)
    
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--oss-fuzz', type=Path, required=True)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--project', required=True)
    args = parser.parse_args()
    main(args.project, args.oss_fuzz, args.repo)
