import pytest
import re
from libDeepGen.developers import CodexDeveloper
from libDeepGen.tasks import Task
from libAgents.tools import OpenAICodexConfig

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

class TestCodingTask(TestTask):
    def desc_to_developer(self) -> str:
        return "Write a python function (gen_one_seed) that returns b'Hello, World!' (in bytes)."

class TestCodingTask2(TestTask):
    def desc_to_developer(self) -> str:
        return "Write a python function (gen_one_seed) that returns b'Hello, World!' (in bytes)."

    def post_process(self, res: str) -> str:
        match = re.search(r"```python(.*)```", res, re.DOTALL)
        if match:
            return match.group(1)
        return res

def test_codex_developer_with_task():
    task = TestTask()
    codex = CodexDeveloper(config=OpenAICodexConfig(model_name="gpt-4.1-mini"))
    res, _ = codex.gen(task)
    print(res)
    assert res is not None
    assert "nginx" in res.lower()  # Check case-insensitively

def test_codex_developer_with_coding_task():
    task = TestCodingTask()
    codex = CodexDeveloper(config=OpenAICodexConfig(model_name="gpt-4.1-mini"))
    res, _ = codex.gen(task)
    print(res)
    assert res is not None
    assert "gen_one_seed" in res  
    assert "Hello, World!" in res  
    assert "```python" in res  

def test_codex_developer_with_coding_task2():
    task = TestCodingTask2()
    codex = CodexDeveloper(config=OpenAICodexConfig(model_name="gpt-4.1-mini"))
    res, _ = codex.gen(task)
    print(res)
    assert res is not None
    assert "```python" not in res  
    assert "gen_one_seed" in res  
    assert "Hello, World!" in res  
