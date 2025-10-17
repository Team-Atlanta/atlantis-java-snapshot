# Copyright 2016 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
################################################################################
import logging
import os
import re
import shlex
import subprocess
import sys
import yaml
import shutil
from pathlib import Path
from .cmd import run_cmd, copy_dir

logger = logging.getLogger(__name__)

PROJECT_LANGUAGE_REGEX = re.compile(r"\s*language\s*:\s*([^\s]+)")
WORKDIR_REGEX = re.compile(r"\s*WORKDIR\s*([^\s]+)")


def _get_command_string(command):
    """Returns a shell escaped command string."""
    return " ".join(shlex.quote(part) for part in command)


def get_tooling_dir(oss_fuzz_home: Path):
    """Returns the tooling directory path based on current fuzzing tools directory."""
    return oss_fuzz_home


def get_build_dir(oss_fuzz_home: Path = None):
    """Returns the build directory path based on current fuzzing tools directory."""
    return Path(os.path.join(get_tooling_dir(oss_fuzz_home), "build"))


def _get_project_build_subdir(project, subdir_name, oss_fuzz_home: Path = None):
    """Creates the |subdir_name| subdirectory of the |project| subdirectory in
    |BUILD_DIR| and returns its path."""
    directory = os.path.join(get_build_dir(oss_fuzz_home), subdir_name, project)
    os.makedirs(directory, exist_ok=True)
    return Path(directory)


def _get_out_dir(project_name: str, oss_fuzz_home: Path = None):
    """Creates and returns path to /out directory for the given project (if
    specified)."""
    return _get_project_build_subdir(project_name, "out", oss_fuzz_home)


def _workdir_from_lines(lines, default="/src"):
    """Gets the WORKDIR from the given lines."""
    for line in reversed(lines):  # reversed to get last WORKDIR.
        match = re.match(WORKDIR_REGEX, line)
        if match:
            workdir = match.group(1)
            workdir = workdir.replace("$SRC", "/src")

            if not os.path.isabs(workdir):
                workdir = os.path.join("/src", workdir)

            return os.path.normpath(workdir)

    return default


def _env_to_docker_args(env_list):
    """Turns envirnoment variable list into docker arguments."""
    return sum([["-e", v] for v in env_list], [])


def _workdir_from_dockerfile(project):
    """Parses WORKDIR from the Dockerfile for the given project."""
    with open(project.dockerfile_path) as file_handle:
        lines = file_handle.readlines()

    return _workdir_from_lines(lines, default=os.path.join("/src", project.name))


def _get_absolute_path(path):
    """Returns absolute path with user expansion."""
    return os.path.abspath(os.path.expanduser(path))


def build_oss_fuzz_fuzzers(
    project: "Project", engine="libfuzzer", sanitizer="address", env: list[str] = []
):
    env_args = _env_to_docker_args(env)

    # Print debug information
    logger.debug(f"Building fuzzers for project: {project.name}")
    logger.debug(f"Sanitizer: {sanitizer}")
    logger.debug(f"Environment variables: {env}")
    logger.debug(f"Environment args: {env_args}")

    run_args = [
        "python3",
        "infra/helper.py",
        "build_fuzzers",
        f"--sanitizer={sanitizer}",
        f"--engine={engine}",
    ]

    # Add environment variables
    for e in env:
        run_args.extend(["-e", e])

    # Add project name and source directory
    run_args.extend(
        [
            project.name,
            project.local_src_dir,
        ]
    )

    run_cmd(run_args, cwd=project.oss_fuzz_home, debug=True)


def run_custom(
    project: "Project",  # oss-fuzz project
    custom_command: str,  # for run_pov, it is the fuzzer name
    pov_path: Path,  # the test case we want to run
    file_to_return: str = None,
    env: list[str] = None,  # environment variables
    timeout: int = 300,
):
    if env is None:
        env = []
    run_args = _env_to_docker_args(env)
    work_dir = _workdir_from_dockerfile(project)

    # mount source code so we can do source code level debugging
    run_args.extend(
        [
            "-v",
            "%s:%s" % (project.local_src_dir, work_dir),
            "-v",
            "%s:/pov_blob" % pov_path,
        ]
    )

    run_args.extend(
        [
            "-v",
            "%s:/out" % project.out,
            "-v",
            "%s:/work" % project.work,
            "gcr.io/%s/%s"
            % (
                "oss-fuzz",
                project.name,
            ),  # TODO: check if oss-fuzz is the correct image
            custom_command,  # the final command
            "/pov_blob",  # the POV blob
        ]
    )

    try:
        # print(f"Running docker run with args: {run_args}")
        stdout, stderr = docker_run(run_args, timeout)
        if file_to_return:
            return open(project.out / file_to_return).read(), stdout, stderr
        else:
            return "", stdout, stderr
    except Exception as e:
        raise RuntimeError(f"Failed to run docker run: {e}")


def docker_run(run_args, print_output=True, architecture="x86_64", timeout=300):
    """Calls `docker run`.
    Args:
      run_args: Arguments to pass to docker run.
      print_output: Whether to print the output of the docker run command.
      architecture: The architecture of the docker image to run.

      Copied from oss-fuzz
    """
    platform = "linux/arm64" if architecture == "aarch64" else "linux/amd64"
    command = ["docker", "run", "--privileged", "--shm-size=2g", "--platform", platform]
    if os.getenv("OSS_FUZZ_SAVE_CONTAINERS_NAME"):
        command.append("--name")
        command.append(os.getenv("OSS_FUZZ_SAVE_CONTAINERS_NAME"))
    else:
        command.append("--rm")

    # Support environments with a TTY.
    if sys.stdin.isatty():
        command.append("-i")

    command.extend(run_args)

    logger.info("Running: %s.", _get_command_string(command))
    _stdout = None
    if not print_output:
        _stdout = open(os.devnull, "w")

    try:
        res = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
        return res.stdout, res.stderr
    except subprocess.CalledProcessError:
        return None, None


class Project:
    """Class representing a project that is in OSS-Fuzz or an external project
    (ClusterFuzzLite user)."""

    def __init__(self, *args, **kwargs):
        """
        Initialize a Project instance.

        There are several ways to initialize a Project:
        1. With oss_fuzz_home, project_name, and local_repo_path
        2. With project_path, repo_path, and project_name
        3. With just project_path and repo_path (name inferred from project_path)

        Args:
            oss_fuzz_home: The path to the OSS-Fuzz home directory.
            project_name: The name of the project in OSS-Fuzz.
            local_repo_path: The local source directory of the project.
            project_path: Direct path to the project directory (alternative to oss_fuzz_home + project_name)
            repo_path: Direct path to the repository (alternative to local_repo_path)
        """
        # Initialize basic attributes
        self.name = None
        self.oss_fuzz_home = None
        self.project_path = None
        self.repo_path = None

        # Handle configuration from kwargs
        self._configure_from_kwargs(kwargs)

        # Initialize derived attributes
        self.aixcc_config = self._init_aixcc_config()
        self.harnesses = self._init_harnesses()

    def _configure_from_kwargs(self, kwargs):
        """Configure the project from keyword arguments."""
        # Ensure paths are Path objects
        for path_arg in ["local_repo_path", "project_path", "repo_path"]:
            if path_arg in kwargs and not isinstance(kwargs[path_arg], Path):
                kwargs[path_arg] = Path(kwargs[path_arg])

        # OSS-Fuzz home, project name, and local repo path
        if (
            "oss_fuzz_home" in kwargs
            and "project_name" in kwargs
            and "local_repo_path" in kwargs
        ):
            self.name = kwargs["project_name"]
            self.oss_fuzz_home = get_tooling_dir(kwargs["oss_fuzz_home"])
            self.repo_path = kwargs["local_repo_path"]
            self.project_path = os.path.join(self.oss_fuzz_home, "projects", self.name)

        # Direct project path, repo path, and explicit name
        elif (
            "project_path" in kwargs
            and "repo_path" in kwargs
            and "project_name" in kwargs
        ):
            self.name = kwargs["project_name"]
            self.project_path = kwargs["project_path"]
            self.repo_path = kwargs["repo_path"]

        # Direct project path and repo path (infer name)
        elif "project_path" in kwargs and "repo_path" in kwargs:
            self.project_path = kwargs["project_path"]
            self.repo_path = kwargs["repo_path"]
            self.name = self.project_path.name

        else:
            raise ValueError(
                "Invalid arguments for Project initialization."
                "Required: (oss_fuzz_home, project_name, local_repo_path) OR "
                "(project_path, repo_path, [project_name])"
            )

    def _init_aixcc_config(self):
        """Initializes the AIXCC config for the project."""
        config_path = os.path.join(self.project_path, ".aixcc", "config.yaml")
        if os.path.exists(config_path):
            cfg_content = open(config_path).read()
            cfg = yaml.safe_load(cfg_content)
        return cfg

    def _init_harnesses(self):
        """Init harnesses from the AIXCC config."""
        if not hasattr(self, "aixcc_config"):
            raise ValueError(
                "AIXCC config not found (We reply on a custom config file)"
            )

        res = {}

        for harness in self.aixcc_config["harness_files"]:
            harness_path = harness.get("path")

            if not harness_path:
                harness_path = "[Not Available]"
            elif harness_path.startswith("$PROJECT"):
                harness_path = harness_path.replace(
                    "$PROJECT", str(self.project_path), 1
                )
            elif harness_path.startswith("$REPO"):
                harness_path = harness_path.replace("$REPO", str(self.repo_path), 1)

            res[harness["name"]] = harness
            res[harness["name"]]["path"] = harness_path

        return res

    def prepare_project_bundle(self, dst: Path, oss_fuzz_dir_name: str = "oss-fuzz"):
        """
        Pack the project to the given destination directory.

        This copies both the repository code and OSS-Fuzz project metadata to a
        subdirectory of the destination, creating a standalone project bundle.

        Args:
            dst: Destination path for the bundled project
            oss_fuzz_dir_name: Name of the directory to store OSS-Fuzz metadata

        Returns:
            A new Project instance configured with the bundled paths
        """
        # Ensure dst is a Path object
        dst = Path(dst) if not isinstance(dst, Path) else dst

        # Create destination paths
        base_name = os.path.basename(self.repo_path)
        dst_path = dst / base_name
        new_project_path = dst_path / oss_fuzz_dir_name / self.name

        if dst_path.exists():
            shutil.rmtree(dst_path)

        dst_path.mkdir(parents=True, exist_ok=True)
        new_project_path.mkdir(parents=True, exist_ok=True)

        # Copy files
        copy_dir(self.repo_path, dst_path)
        copy_dir(self.project_path, new_project_path)

        # Create and return a new Project instance
        return Project(
            project_path=new_project_path, repo_path=dst_path, project_name=self.name
        )

    @property
    def dockerfile_path(self):
        """Returns path to the project Dockerfile."""
        return os.path.join(self.project_path, "Dockerfile")

    @property
    def mode(self):
        """Returns the mode of the project."""
        dot_ref_diff = os.path.join(self.project_path, ".aixcc", "ref.diff")
        if os.path.exists(dot_ref_diff):
            return "delta"
        return "full"

    @property
    def ref_diff(self):
        """Returns the diff of the reference commit."""
        path = self.ref_diff_path

        if path is not None and os.path.exists(path):
            return open(path).read()

        return None

    @property
    def ref_diff_path(self):
        """Returns the path to the diff of the reference commit."""
        path = os.path.join(self.project_path, ".aixcc", "ref.diff")
        if os.path.exists(path):
            return path
        return None

    @property
    def language(self):
        """Returns project language."""
        project_yaml_path = os.path.join(self.project_path, "project.yaml")
        logger.debug(f"project_yaml_path: {project_yaml_path}")
        if not os.path.exists(project_yaml_path):
            logger.warning("No project.yaml. Assuming c++.")
            return "c++"

        with open(project_yaml_path) as file_handle:
            content = file_handle.read()
            for line in content.splitlines():
                match = PROJECT_LANGUAGE_REGEX.match(line)
                if match:
                    return match.group(1)

        logger.warning("Language not specified in project.yaml. Assuming c++.")
        return "c++"

    @property
    def coverage_extra_args(self):
        """Returns project coverage extra args."""
        project_yaml_path = os.path.join(self.project_path, "project.yaml")
        if not os.path.exists(project_yaml_path):
            logger.warning("project.yaml not found: %s.", project_yaml_path)
            return ""

        with open(project_yaml_path) as file_handle:
            content = file_handle.read()

        coverage_flags = ""
        read_coverage_extra_args = False
        # Pass the yaml file and extract the value of the coverage_extra_args key.
        # This is naive yaml parsing and we do not handle comments at this point.
        for line in content.splitlines():
            if read_coverage_extra_args:
                # Break reading coverage args if a new yaml key is defined.
                if len(line) > 0 and line[0] != " ":
                    break
                coverage_flags += line
            if "coverage_extra_args" in line:
                read_coverage_extra_args = True
                # Include the first line only if it's not a multi-line value.
                if "coverage_extra_args: >" not in line:
                    coverage_flags += line.replace("coverage_extra_args: ", "")
        return coverage_flags

    @property
    def out(self):
        """Returns the out dir for the project. Creates it if needed."""
        return _get_out_dir(self.name, self.oss_fuzz_home)

    @property
    def work(self):
        """Returns the out dir for the project. Creates it if needed."""
        return _get_project_build_subdir(self.name, "work", self.oss_fuzz_home)

    @property
    def corpus(self):
        """Returns the out dir for the project. Creates it if needed."""
        return _get_project_build_subdir(self.name, "corpus", self.oss_fuzz_home)

    @property
    def harness_files(self):
        """Returns the harness files for the project."""
        return self.harnesses

    def harness_path_by_name(self, harness_name: str):
        """Returns the harness file for the given harness name."""
        return Path(self.harnesses[harness_name]["path"])

    def cpvs_by_harness(self, harness_name: str):
        """Returns the cpvs for the given harness name."""
        return self.harnesses[harness_name]["cpvs"]
