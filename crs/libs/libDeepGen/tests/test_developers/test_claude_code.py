import pytest
from libDeepGen.developers.claude_code import ClaudeDeveloper, ClaudeCode
from libDeepGen.tasks import Task
from libAgents.tools import ClaudeConfig


class TestTask(Task):
    def __init__(self):
        nginx_src = pytest.get_oss_repo("aixcc/c/asc-nginx")
        nginx_oss_fuzz = pytest.get_oss_project("aixcc/c/asc-nginx")
        super().__init__(
            cp_name="asc-nginx",
            cp_src=nginx_src,
            fuzz_tooling_src=nginx_oss_fuzz,
            harness_src=nginx_src / "fuzz_harness.c",
            harness_entrypoint_func="LLVMFuzzerTestOneInput",
            dev_attempts=10,
            dev_cost=100.0
        )

    def get_cp_lang(self) -> str:
        return "c"

    def desc_to_developer(self) -> str:
        return "give me an overview of this codebase"

     
def test_claude_code():
    claude = ClaudeCode(ClaudeConfig(provider="openai"))
    res = claude.query("Write a python script to print 'Hello, world!'")
    assert res is not None
    print(res)
    assert "Hello, world!" in res

def test_claude_code_with_task():
    task = TestTask()
    claude = ClaudeDeveloper(ClaudeConfig(provider="openai"))
    res, cost = claude.gen(task)
    print(res)
    assert res is not None
    assert "nginx" in res.lower()  # Check case-insensitively
    assert cost >= 0.0  # Cost should be non-negative