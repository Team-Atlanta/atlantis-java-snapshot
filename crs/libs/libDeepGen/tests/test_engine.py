import time
import pytest
from libDeepGen.developers.developer_base import Developer
from libDeepGen.engine import DeepGenEngine
from libDeepGen.submit import MockEnsemblerSubmit, SubmitBundle
from libDeepGen.developers import LibAgentsDeveloper, ClaudeDeveloper
from libDeepGen.tasks import Task
from libDeepGen.ipc_utils.shm_pool import SeedShmemPoolConsumer
from libAgents.tools import ClaudeConfig
from pathlib import Path
from typing import Dict, Tuple
import threading

class TestTask(Task):
    return_value = "Hello, World!"

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
        return f"""
Write a python function (gen_one_seed) that returns b"{self.return_value}" (in bytes).

You need to put the script inside the <script></script> tag.

For example:
<script>
def gen_one_seed():
    return xxx
</script>
"""

    def post_process(self, script: str) -> str:
        # Extract content between <script> and </script> tags
        # print("script: ", script)
        script_start = script.find("<script>")
        script_end = script.find("</script>")
        if script_start != -1 and script_end != -1:
            # Return the extracted script content directly
            return script[script_start + len("<script>"):script_end].strip()
        return None

class TestTaskClaude(TestTask):
    return_value = "Hello, Claude!"

class TestTaskLibAgents(TestTask):
    return_value = "Hello, LibAgents!"


class MockDeveloper(Developer):
    def gen(self, task: Task) -> tuple[str, float]:
        content = """
<script>
def gen_one_seed():
    return b"mock_seed"
</script>
"""
        # Extract the script content directly
        processed_content = task.post_process(content)
        # TODO: Calculate actual token cost
        token_cost = 0.0
        return processed_content, token_cost


class AssertSubmit(MockEnsemblerSubmit):
    assert_value = b"mock_seed"

    def __init__(self, proc_map: Dict[str, Tuple[str, str]], workdir: Path, ensembler_submit_rb_name: str, ensembler_processed_rb_name: str):
        super().__init__(proc_map, workdir, ensembler_submit_rb_name, ensembler_processed_rb_name)
        self.seed_pool_consumers = {}
        self.exception = None
        self.exception_event = threading.Event()
        for _, (_, seed_pool_shm_name) in proc_map.items():
            if seed_pool_shm_name not in self.seed_pool_consumers:
                self.seed_pool_consumers[seed_pool_shm_name] = SeedShmemPoolConsumer(
                    shm_name=seed_pool_shm_name, create=False)

    def close(self):
        """Clean up resources including cached shared memory consumers."""
        if hasattr(self, 'seed_pool_consumers'):
            for pool in self.seed_pool_consumers.values():
                pool.close()
            self.seed_pool_consumers.clear()

        super().close()

    def mock_ensembler_loop_fn(self, should_continue_fn):
        """Thread fn for the Engine's thread pool that simulates Ensembler behavior."""
        try:
            while should_continue_fn():
                bundle = self.mock_submit_consumer.try_get(cls=SubmitBundle, deserialize_fn=SubmitBundle.deserialize)
                if bundle:
                    for _, pool_dict in bundle.seeds.items():
                        for seed_pool_shm_name, seed_ids in pool_dict.items():
                            # Use cached seed pool consumer
                            pool = self.seed_pool_consumers.get(seed_pool_shm_name)
                            if not pool:
                                continue
                            
                            for seed_id in seed_ids:
                                seed_data = pool.get_seed_content(seed_id)
                                assert seed_data is not None
                                assert seed_data == self.assert_value

                    self.mock_processed_producer.put(bundle, serialize_fn=SubmitBundle.serialize)
                else:
                    time.sleep(0.01)
        except Exception as e:
            # Store the exception and set the event
            self.exception = e
            self.exception_event.set()
            # Re-raise to stop the thread
            raise

    def check_for_exceptions(self):
        """Check if any exceptions occurred in the background thread."""
        if self.exception_event.is_set():
            raise self.exception

class PrintingSubmit(MockEnsemblerSubmit):
    def request_seed_submit(self, proc_id, script_id, script, seed_ids):
        if seed_ids:
            print(f"Script {script.sha256} has {len(seed_ids)} seeds: {seed_ids}")
        super().request_seed_submit(proc_id, script_id, script, seed_ids)

class AssertMockSubmit(AssertSubmit):
    assert_value = b"mock_seed"

class AssertHelloWorldSubmit(AssertSubmit):
    assert_value = b"Hello, World!"

class AssertClaudeSubmit(AssertSubmit):
    assert_value = b"Hello, Claude!"

class AssertLibAgentsSubmit(AssertSubmit):
    assert_value = b"Hello, LibAgents!"


#
# test functions
#

@pytest.mark.asyncio
async def test_mock_developer():
    tasks = [TestTask()]
    
    try:
        with DeepGenEngine(core_ids=[0, 1, 2, 3], model="gpt-4.1-nano", submit_class=AssertMockSubmit) as engine:
            engine.add_developer(MockDeveloper(model="gpt-4.1-nano"))
            await engine.run(
                tasks,
                time_limit=10,
            )
    except Exception as e:
        assert False, f"Exception: {e}"
    finally:
        engine.submit.check_for_exceptions()


@pytest.mark.asyncio
async def test_claude_developer_print():
    tasks = [TestTaskClaude()]
    
    with DeepGenEngine(core_ids=[0, 1, 2, 3], model="gpt-4.1-nano", submit_class=PrintingSubmit) as engine:
        engine.add_developer(ClaudeDeveloper(ClaudeConfig(provider="openai")))
        await engine.run(
            tasks,
            time_limit=10,
        )

@pytest.mark.asyncio
async def test_claude_developers_assert_print():
    tasks = [TestTaskClaude()]
    
    with DeepGenEngine(core_ids=[0, 1, 2, 3], model="gpt-4.1-nano", submit_class=AssertClaudeSubmit) as engine:
        engine.add_developer(ClaudeDeveloper(ClaudeConfig(provider="openai")))
        await engine.run(
            tasks,
            time_limit=10,
        )
        engine.submit.check_for_exceptions()

    with DeepGenEngine(core_ids=[0, 1, 2, 3], model="gpt-4.1-nano", submit_class=PrintingSubmit) as engine:
        engine.add_developer(ClaudeDeveloper(ClaudeConfig(provider="openai")))
        await engine.run(
            tasks,
            time_limit=10,
        )

@pytest.mark.asyncio
async def test_libagents_developer_print():
    task = TestTaskLibAgents()
    tasks = [task]

    with DeepGenEngine(core_ids=[0, 1, 2, 3], model="gpt-4.1-nano", submit_class=PrintingSubmit) as engine:
        engine.add_developer(LibAgentsDeveloper(model="gpt-4.1-nano", task=task))
        await engine.run(
            tasks,
            time_limit=10,
        )

@pytest.mark.asyncio
async def test_libagents_developer_assert_print():
    task = TestTaskLibAgents()
    tasks = [task]
    
    with DeepGenEngine(core_ids=[0, 1, 2, 3], model="gpt-4.1-nano", submit_class=AssertLibAgentsSubmit) as engine:
        engine.add_developer(LibAgentsDeveloper(model="gpt-4.1-nano", task=task))
        await engine.run(
            tasks,
            time_limit=10,
        )
        engine.submit.check_for_exceptions()

    with DeepGenEngine(core_ids=[0, 1, 2, 3], model="gpt-4.1-nano", submit_class=PrintingSubmit) as engine:
        engine.add_developer(LibAgentsDeveloper(model="gpt-4.1-nano", task=task))
        await engine.run(
            tasks,
            time_limit=10,
        )