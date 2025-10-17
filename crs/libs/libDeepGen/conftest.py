# conftest.py
import os
import subprocess
import pytest
import yaml

from dotenv import load_dotenv
from pathlib import Path

def pytest_configure(config):
    config.option.filterwarnings = ["ignore"]
    config.option.disable_warnings = True

def load_config(oss_fuzz_path, project_name):
    project_yaml = oss_fuzz_path / 'projects' / project_name / 'project.yaml'
    if not project_yaml.exists():
        raise ValueError(f'Could not find {project_yaml}')
    
    with open(project_yaml) as f:
        project_dict = yaml.safe_load(f)

    if "main_repo" not in project_dict:
        raise ValueError(f'Unable to find main_repo key in {project_yaml}')
    
    return project_dict
        

def get_repo_path(project_name):
    """Fetch or clone the repository for the given project name."""

    oss_fuzz_path = Path(os.getenv("OSS_FUZZ_REPO_PATH"))
    project_dict = load_config(oss_fuzz_path, project_name)
    main_repo = project_dict["main_repo"]

    repo_path = Path(os.getenv("REPO_CLONE_DIR")) / project_name
    if not repo_path.exists():
        subprocess.run(["git", "clone", main_repo, repo_path], check=True)
    else:
        subprocess.run(["git", "-C", repo_path, "clean", "-dfx"], check=True)
        subprocess.run(["git", "-C", repo_path, "pull"], check=True)

    return repo_path

def get_oss_project_path(project_name):
    oss_fuzz_path = Path(os.getenv("OSS_FUZZ_REPO_PATH"))
    return oss_fuzz_path / 'projects' / project_name
    

@pytest.fixture(scope="session", autouse=True)
def setup_environment():
    env_file_path = os.path.join(os.getcwd(), '.env.base')
    load_dotenv(dotenv_path=env_file_path)

    # pre-clone OSS-Fuzz repo
    repo_url = os.getenv("OSS_FUZZ_REPO_URL")
    branch = os.getenv("OSS_FUZZ_BRANCH", "main")
    oss_fuzz_dir = os.getenv("OSS_FUZZ_CLONE_DIR", "./oss-fuzz")

    if not os.path.isdir(oss_fuzz_dir):
        print(f"Cloning repository from {repo_url} into {oss_fuzz_dir}")
        subprocess.run(["git", "clone", "-b", branch, repo_url, oss_fuzz_dir], check=True)
    else:
        print(f"Repository already exists at {oss_fuzz_dir}, pulling latest changes.")
        subprocess.run(["git", "-C", oss_fuzz_dir, "clean", "-dfx"], check=True)

        subprocess.run(["git", "-C", oss_fuzz_dir, "pull"], check=True)

    os.environ['OSS_FUZZ_REPO_PATH'] = os.path.abspath(oss_fuzz_dir)


@pytest.fixture(scope="session", autouse=True)
def load_my_utils():
    """Provide the `get_repo()` function to tests."""
    pytest.get_oss_repo = get_repo_path
    pytest.get_oss_project = get_oss_project_path