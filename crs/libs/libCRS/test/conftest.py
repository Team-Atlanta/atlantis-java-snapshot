from pathlib import Path

import pytest

from helper import CP_Info, makedirs


# from https://docs.pytest.org/en/8.3.x/example/simple.html#control-skipping-of-tests-according-to-command-line-option

def pytest_addoption(parser):
    parser.addoption(
        "--runslow", action="store_true", default=False, help="run slow tests"
    )

def pytest_configure(config):
    config.addinivalue_line("markers", "slow: mark test as slow to run")

def pytest_collection_modifyitems(config, items):
    if config.getoption("--runslow"):
        # --runslow given in cli: do not skip slow tests
        return
    skip_slow = pytest.mark.skip(reason="need --runslow option to run")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)


@pytest.fixture(scope="session")
def monkeysession() -> pytest.MonkeyPatch:
    """https://stackoverflow.com/a/74659732"""
    with pytest.MonkeyPatch.context() as mp:
        yield mp

@pytest.fixture
def sample_cp_infos(pytestconfig) -> list[CP_Info]:
    cps = [
        CP_Info("mock-cp", "Mock CP", "git@github.com:Team-Atlanta/mock-cp.git"),
    ]

    if pytestconfig.getoption("runslow"):
        cps += [
            CP_Info("linux-cp", "linux kernel", "git@github.com:Team-Atlanta/challenge-001-linux-cp.git"),
            CP_Info("jenkins-cp", "jenkins", "git@github.com:Team-Atlanta/asc-challenge-002-jenkins-cp.git"),
        ]

    return cps

@pytest.fixture
def sample_cp_info(pytestconfig) -> CP_Info:
    return CP_Info("mock-cp", "Mock CP", "git@github.com:Team-Atlanta/mock-cp.git")

@pytest.fixture(scope="session")
def shared_cp_root(monkeysession, tmp_path_factory) -> Path:
    path = tmp_path_factory.getbasetemp() / "cp_root"
    makedirs(path)
    monkeysession.setenv("AIXCC_CP_ROOT", str(path))
    yield path

@pytest.fixture(scope="session")
def shared_crs_scratch_space(monkeysession, tmp_path_factory) -> Path:
    path = tmp_path_factory.getbasetemp() / "crs_scratch"
    makedirs(path)
    monkeysession.setenv("AIXCC_CRS_SCRATCH_SPACE", str(path))
    yield path
