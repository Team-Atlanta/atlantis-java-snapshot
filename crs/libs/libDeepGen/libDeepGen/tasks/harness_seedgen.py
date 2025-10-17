import logging
import sys

from libAgents.agents import AgentBase, DeepSearchAgent
from libAgents.utils import Project, get_model_by_weights
from libAgents.plugins import (
    AnswerPlugin,
    ReflectPlugin,
    CodeBrowserPlugin,
    CoderPlugin,
    ListDirPlugin,
    FsReaderPlugin,
    RipGrepPlugin,
    SedPlugin,
)

from .task_base import Task


logger = logging.getLogger(__name__)


class HarnessAgent(AgentBase):
    """
    An agent with full plugins support and agent flow support.
    """
    def __init__(self, model: str, project_bundle: Project, is_jvm: bool, timeout: int = 300):
        plugins=[
                AnswerPlugin(),
                ReflectPlugin(),
                RipGrepPlugin(),
                SedPlugin(),
                CoderPlugin(
                    project_name=project_bundle.name,
                    main_repo=project_bundle.repo_path,
                ),
                ListDirPlugin(),
            FsReaderPlugin(),
        ]
        if not is_jvm:
            plugins.append(
                CodeBrowserPlugin(
                    project_name=project_bundle.name,
                    src_path=project_bundle.repo_path,
                ),
            )
        self.deep_search_agent = DeepSearchAgent(plugins=plugins)
        self.model = model
        self.timeout = timeout

    async def run(self, input_data):
        return await self.deep_search_agent.query(input_data, self.model, timeout=self.timeout)


class AnyHarnessSeedGen(Task):
    """Seed generation task for any type of harness."""
    
    def __init__(self, 
                 project_bundle: Project,
                 harness_name: str,
                 harness_entrypoint_func: str,
                 is_jvm: bool,
                 weighted_models: list[tuple[str, int]] = None,
                 priority: int = 1,
                 dev_attempts: int = 10,
                 dev_cost: float = 100.0,
                 num_repeat: int = 1,
                 max_exec: int = sys.maxsize):
        super().__init__(
            harness_name=harness_name,
            priority=priority,
            dev_attempts=dev_attempts,
            dev_cost=dev_cost,
            num_repeat=num_repeat,
            max_exec=max_exec,
        )
        self.project_bundle = project_bundle
        self.harness_name = harness_name
        self.harness_entrypoint_func = harness_entrypoint_func
        self.weighted_models = weighted_models
        self.token_cost = 0
        
        self.harness_src = project_bundle.harness_path_by_name(harness_name)
        model = get_model_by_weights(weighted_models)
        logger.info(f"Initializing AnyHarnessSeedGen with model: {model}")
        self.coder = HarnessAgent(
            model=model,
            project_bundle=project_bundle,
            is_jvm=is_jvm,
        )

    def get_label(self) -> str:
        return f"Any:{self.harness_name}"
    
    def _get_prompt(self) -> str:
        PROMPT = """\
Advanced Coding Task:
Fuzzing Testing Research: High Code Coverage and Seed Generation

OBJECTIVE:
- We are conducting fuzzing testing research aimed at achieving maximum code coverage for a specific project and its fuzzing harness. 
- As an expert in fuzzing, you will write a seed generator script that targets the designated fuzzing harness effectively.
- Our ultimate goal is to call the generator to generate quality seed to trigger as many crashes as possible.

TASK:
1. Analyze the codebase build configurations.
2. Identify enabled modules.
3. Examine the fuzzing harness—specifically the function `{harness_entrypoint_func}`.
4. Craft an elegant, self-contained Python script that generates high-quality fuzzing test cases.

PROJECT INFORMATION:
- Project Name: {project_name}
- OSS-Fuzz Project Path (includes the fuzzer harness and build configurations): {ossfuzz_project_path}
- The specific fuzzing harness to be analyzed: {fuzzing_harness_name}
- Fuzzing Harness Path (the main harness containing the `{harness_entrypoint_func}` function to be analyzed): {fuzzing_harness_path}
- Source Code Repository Path (contains the actual project source code): {source_code_repository_path}
- Feel free to browse the relevant codes you need, using the code-browser plugin.

HARNESS ANALYSIS GUIDANCE:
- Thoroughly read the source code to fully understand the `{harness_entrypoint_func}` function and the surrounding harness.
- Pay close attention to the expected input structure, i.e., structure-aware and format required by the harness, i.e., semantic-aware.
- Focus on generating seeds that significantly boost testing coverage and have the potential to trigger crashes in vulnerable targets.
- Tailor your analysis and approach specifically for this harness.
- Read and Understand more codes to help your analysis.

SCRIPT USAGE GUIDE:
- Write elegant, precise, and error-free code (ensure proper Python syntax and indentation).
- Integrate your analysis insights directly into the script.
- The script must serve as a security expert-level fuzzing test generator.

CRITICAL REQUIREMENTS:
- There can be multiple fuzzing harnesses in the project, you only need to focus on the one provided in {fuzzing_harness_path}.
- After the analysis we mentioned in <HARNESS ANALYSIS GUIDANCE>, use the AI coder to generate the script.
- The script must implement a function named `gen_one_seed` that returns a seed for the fuzzing harness in bytes. An example is shown below.

<example>
def gen_one_seed() -> bytes: # for real usage
    # TODO: implement this
    pass

if __name__ == "__main__":
    gen_one_seed() # for testing
</example>

OUTPUT FORMAT:
- Show me the generate script enclosed within `<script>` and `</script>` tags:
<script>
# other codes ...
def gen_one_seed() -> bytes: # for real usage
    # TODO: implement this
    pass

if __name__ == "__main__":
    for _ in range(10): # for robust testing due to inner randomness
        gen_one_seed() # for testing
</script>"""
        return PROMPT.format(
            project_name=self.project_bundle.name,
            ossfuzz_project_path=str(self.project_bundle.project_path.resolve()),
            fuzzing_harness_path=str(self.harness_src.resolve()),
            source_code_repository_path=str(self.project_bundle.repo_path.resolve()),
            fuzzing_harness_name=self.harness_name,
            harness_entrypoint_func=self.harness_entrypoint_func
        )

    async def _post_process(self, input_text) -> str:
        script_start = input_text.find("<script>")
        script_end = input_text.find("</script>")
        if script_start != -1 and script_end != -1:
            # Return the extracted script content directly
            return input_text[script_start + len("<script>"):script_end].strip()
        return None

    async def _run_impl(self) -> (str, int):
        prompt = self._get_prompt()
        final_result = await self.coder.run(prompt)
        # TODO: add cost calculation when supported
        token_cost = 0
        processed_result = await self._post_process(final_result)
        return processed_result, token_cost
