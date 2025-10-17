from libAgents.agents import AgentBase, DeepThinkAgent
from libAgents.utils import Project, extract_script_from_response
from typing import Optional


BASIC_SEED_GENERATION_PROMPT = """
INSTRUCTIONS:
- You are the world's leading program analysis and security expert, competing in the AI Cyber Challenge (AIxCC) Final Round (AFC).
- Your expertise lies in fuzzing and vulnerability discovery. Your task is to create a targeted seed generator for a specified fuzzing harness.
- The challenge project is guaranteed to contain at least one vulnerability.

OBJECTIVE:
- Maximize code coverage and trigger as many crashes as possible for the given fuzzing harness.
- Deliver a self-contained, production-quality Python script that generates high-value, structure-aware seeds for the harness.

TASKS:
1. Analyze the build configuration of the project.
2. Identify which modules are enabled or compiled into the binary.
3. Study the fuzz entry point: LLVMFuzzerTestOneInput.
4. Review all reachable code paths invoked by the harness.
5. Write a robust and elegant Python script that emits semantically rich and diverse test inputs.

CHALLENGE PROJECT DETAILS:
- Project Name: {project_name}
- OSS-Fuzz Project Path: {ossfuzz_project_path}
- Fuzzing Harness Name: {fuzzing_harness_name}
- Fuzzing Harness Path: {fuzzing_harness_path}
- Source Repository Path: {source_code_repository_path}

IMPORTANT:
<important_info>
- The project may contain multiple fuzzing harnesses, but your task concerns only the one specified above ({fuzzing_harness_name}: {fuzzing_harness_path}).
</important_info>

HARNESS ANALYSIS GUIDANCE:
- Carefully read LLVMFuzzerTestOneInput and all functions it calls.
- Determine the expected input structure, formats, and any semantic constraints.
- Design seed generation logic to explore edge cases, uncover hidden paths, and trigger subtle bugs.
- Base your seed generation directly on your analysis of the code.

SCRIPT REQUIREMENTS:
- Use clean, idiomatic Python with proper style and structure.
- Encode your analysis insights directly into the generator logic.
- Include multiple generation strategies to ensure seed diversity.
- Implement a function: `gen_one_seed() -> bytes` that returns a single fuzz input.
- Ensure the generator is capable of producing millions of distinct, high-quality seeds.
- Include necessary comments for better understanding the codes.

OUTPUT FORMAT:
Wrap the full script between <script> and </script> tags, like this:

<script>
import os
import random
# ... other necessary imports ...

def gen_one_seed() -> bytes:
    # TODO: Implement seed generation logic based on code analysis
    return b""

if __name__ == "__main__":
    for _ in range(20): # local testing
        gen_one_seed() # don't print to make the stdout clean
</script>
"""


class OneShotSeedGenAgent(AgentBase):
    def __init__(
        self,
        model: str,
        project_bundle: Project,
        harness_id: str,
        timeout: int = 1500,
        cache_type: Optional[str] = None,
        cache_expire_time: int = 1800,
    ):
        super().__init__(project_bundle)
        self.project_bundle = project_bundle
        self.harness_id = harness_id
        self.model = model
        self.deep_think_agent = DeepThinkAgent(
            model,
            project_bundle,
            timeout=timeout,
            cache_type=cache_type,
            cache_expire_time=cache_expire_time,
        )

    def __prompt(self):
        PROMPT = BASIC_SEED_GENERATION_PROMPT.format(
            project_name=self.project_bundle.name,
            ossfuzz_project_path=self.project_bundle.project_path,
            fuzzing_harness_name=self.harness_id,
            fuzzing_harness_path=self.project_bundle.harness_path_by_name(
                self.harness_id
            ),
            source_code_repository_path=self.project_bundle.repo_path,
        )
        return PROMPT

    async def run(self, _input=None):
        response = await self.deep_think_agent.run(self.__prompt())
        return await extract_script_from_response(response, self.model)
