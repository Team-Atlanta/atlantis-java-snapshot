import os
import pytest
import signal
import tempfile
from multiprocessing import Process, Queue
from pathlib import Path
from libAgents.tools.code_browser import CodeBrowser
from libAgents.utils.osf import Project


def code_browser_worker(repo_path):
    try:
        # Create CodeBrowser in the subprocess
        code_browser = CodeBrowser("nginx", repo_path)
        # Verify it works by getting a function definition
        result = code_browser.get_function_definition("ngx_decode_base64")
        return {
            "server_port": code_browser.server_port,
            "success": result is not None,
            "pid": os.getpid(),
        }
    except Exception as e:
        return {"error": str(e)}


def test_code_browser():
    oss_repo = pytest.get_oss_repo("aixcc/c/asc-nginx")
    code_browser = CodeBrowser("nginx", oss_repo)
    assert code_browser.db_client is not None
    assert code_browser.server_port is not None
    result = code_browser.get_function_definition("ngx_decode_base64")
    print(result)
    assert result is not None
    assert "ngx_decode_base64" in result


def test_r2_sqlite3():
    oss_repo = pytest.get_oss_repo("aixcc/c/r2-sqlite3-diff-1")
    code_browser = CodeBrowser("r2-sqlite3-diff-1", oss_repo)
    assert code_browser.db_client is not None
    assert code_browser.server_port is not None
    result = code_browser.get_function_definition("base85")
    print(result)


def test_multiple_same_src_path():
    oss_repo = pytest.get_oss_repo("aixcc/c/asc-nginx")
    code_browser1 = CodeBrowser("nginx", oss_repo)
    code_browser2 = CodeBrowser("nginx", oss_repo)
    assert code_browser1.db_client is not None
    assert code_browser2.db_client is not None

    print(code_browser1.server_port, code_browser2.server_port)
    assert code_browser1.server_port == code_browser2.server_port
    assert code_browser1.get_function_definition(
        "ngx_decode_base64"
    ) == code_browser2.get_function_definition("ngx_decode_base64")


# Helper function to run in subprocess
def run_code_browser_test(repo_path, result_queue):
    try:
        # Set an alarm to prevent indefinite hanging
        signal.alarm(30)  # 30 second timeout

        # Create CodeBrowser instance
        code_browser = CodeBrowser("nginx", repo_path)

        # Test functionality
        result = code_browser.get_function_definition("ngx_decode_base64")

        # Put results in queue
        result_queue.put(
            {
                "success": True,
                "server_port": code_browser.server_port,
                "has_result": result is not None,
            }
        )
    except Exception as e:
        # Report any errors
        result_queue.put({"success": False, "error": str(e)})
    finally:
        # Make sure process terminates
        signal.alarm(0)


def test_multiple_processes():
    oss_repo = pytest.get_oss_repo("aixcc/c/asc-nginx")

    # Create initial CodeBrowser instance in main process
    code_browser1 = CodeBrowser("nginx", oss_repo)
    code_browser2 = CodeBrowser("nginx", oss_repo)
    assert code_browser1.db_client is not None
    assert code_browser2.db_client is not None

    print(code_browser1.server_port, code_browser2.server_port)
    assert code_browser1.server_port == code_browser2.server_port
    assert code_browser1.get_function_definition(
        "ngx_decode_base64"
    ) == code_browser2.get_function_definition("ngx_decode_base64")

    # Create a queue to get results from subprocess
    result_queue = Queue()

    # Run test in subprocess
    proc = Process(target=run_code_browser_test, args=(oss_repo, result_queue))
    proc.start()

    # Wait up to 10 seconds for process to finish
    proc.join(10)

    # Check if process completed
    if proc.is_alive():
        print("Process still running after timeout, terminating")
        proc.terminate()
        proc.join(2)
        assert False, "Test in subprocess did not complete within timeout"

    # Check result
    if not result_queue.empty():
        result = result_queue.get()
        print(f"Subprocess result: {result}")
        assert result.get("success", False), (
            f"Test in subprocess failed: {result.get('error', 'unknown error')}"
        )
        assert result.get("server_port") == code_browser1.server_port, (
            "Server port mismatch"
        )
        assert result.get("has_result", False), "Function lookup failed in subprocess"
    else:
        assert False, "No result from subprocess"


def test_project_bundle_query():
    oss_fuzz_home = pytest.get_oss_fuzz_home()
    oss_repo = pytest.get_oss_repo("aixcc/c/asc-nginx")
    project = Project(
        oss_fuzz_home=oss_fuzz_home,
        project_name="aixcc/c/asc-nginx",
        local_repo_path=oss_repo,
    )

    with tempfile.TemporaryDirectory() as temp_path:
        bundle = project.prepare_project_bundle(temp_path)
        assert bundle.name == "aixcc/c/asc-nginx"
        assert (
            bundle.harness_path_by_name("pov_harness")
            == bundle.project_path / "fuzz" / "pov_harness.cc"
        )

        code_browser = CodeBrowser("nginx", bundle.repo_path)
        assert code_browser.db_client is not None
        assert code_browser.server_port is not None
        result = code_browser.get_function_definition("ngx_decode_base64")
        assert result is not None
        assert "ngx_decode_base64" in result


def test_code_brower_with_clean_state():
    DB_FILE = Path(tempfile.gettempdir()) / "code_browser_registry.db"
    LOCK_FILE = Path(tempfile.gettempdir()) / "code_browser_registry.db.lock"
    if DB_FILE.exists():
        DB_FILE.unlink()
    if LOCK_FILE.exists():
        LOCK_FILE.unlink()

    test_code_browser()
    test_multiple_same_src_path()
    test_multiple_processes()
    test_project_bundle_query()
