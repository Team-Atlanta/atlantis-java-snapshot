import os
import pytest
import tempfile
import yaml
from libAgents.utils import Project
from pathlib import Path


def test_project():
    """Test basic Project initialization and functionality."""
    oss_fuzz_home = pytest.get_oss_fuzz_home()
    nginx_oss = pytest.get_oss_project("aixcc/c/asc-nginx")
    nginx_repo = pytest.get_oss_repo("aixcc/c/asc-nginx")

    # Initialize with oss_fuzz_home, project_name, and local_repo_path
    project = Project(
        oss_fuzz_home=oss_fuzz_home,
        project_name="aixcc/c/asc-nginx",
        local_repo_path=nginx_repo,
    )

    # Verify basic properties
    assert project.name == "aixcc/c/asc-nginx"

    # Verify harness paths
    pov_harness_path = nginx_oss / "fuzz" / "pov_harness.cc"
    mail_request_harness_path = nginx_oss / "fuzz" / "mail_request_harness.cc"
    assert project.harness_path_by_name("pov_harness") == pov_harness_path
    assert (
        project.harness_path_by_name("mail_request_harness")
        == mail_request_harness_path
    )


def test_prepare_project_bundle():
    """Test creating a project bundle in a temporary directory."""
    oss_fuzz_home = pytest.get_oss_fuzz_home()
    _nginx_oss = pytest.get_oss_project("aixcc/c/asc-nginx")
    nginx_repo = pytest.get_oss_repo("aixcc/c/asc-nginx")

    # Initialize the project
    project = Project(
        oss_fuzz_home=oss_fuzz_home,
        project_name="aixcc/c/asc-nginx",
        local_repo_path=nginx_repo,
    )

    # Create a temporary directory for the test
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create the bundle
        bundle = project.prepare_project_bundle(temp_path)

        # Verify the bundle was created correctly
        assert os.path.exists(temp_path)
        repo_base_name = os.path.basename(nginx_repo)
        assert os.path.exists(temp_path / repo_base_name)
        assert os.path.exists(temp_path / repo_base_name / "oss-fuzz")

        # Verify the bundle has the correct properties
        assert bundle.name == "aixcc/c/asc-nginx"
        harness_path = bundle.harness_path_by_name("pov_harness")
        assert isinstance(harness_path, Path)
        assert isinstance(bundle.project_path, Path)
        assert harness_path == bundle.project_path / "fuzz" / "pov_harness.cc"


def test_empty_harness_path():
    """Test that an empty harness path is set to None."""
    # Create a temporary project structure
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create project and repo directories
        project_path = temp_path / "project"
        repo_path = temp_path / "repo"
        project_path.mkdir(parents=True)
        repo_path.mkdir(parents=True)

        # Create .aixcc directory and config
        aixcc_dir = project_path / ".aixcc"
        aixcc_dir.mkdir()

        # Create a config with a harness that has no path field
        config = {
            "harness_files": [
                {
                    "name": "harness_no_path",
                    "cpvs": ["some_cpv"],
                    # Note: no "path" field
                },
                {
                    "name": "harness_with_empty_path",
                    "path": "",
                    "cpvs": ["another_cpv"],
                },
            ]
        }

        config_path = aixcc_dir / "config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        # Initialize project
        project = Project(
            project_path=project_path, repo_path=repo_path, project_name="test_project"
        )

        # Test that harness without path field has None path
        assert project.harnesses["harness_no_path"]["path"] == "[Not Available]"

        # Test that harness with empty path also has None path
        assert project.harnesses["harness_with_empty_path"]["path"] == "[Not Available]"
