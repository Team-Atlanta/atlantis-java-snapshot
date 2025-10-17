import logging
from libAgents.agents import AgentBase, DeepThinkAgent
from libAgents.utils import Project, extract_script_from_response
from typing import override, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class _BaseDiffProcessingAgent(AgentBase):
    """
    Base class for agents that process Git diffs.

    Handles common initialization tasks such as setting up project details,
    harness information, and ensuring the reference diff is available.
    """

    def __init__(self, model: str, project_bundle: Project, harness_id: str):
        super().__init__()
        self.model = model
        self.project_bundle = project_bundle
        self.harness_id = harness_id
        self.ref_diff: str | None = project_bundle.ref_diff
        self.ref_diff_total_lines: int = len(self.ref_diff.splitlines())

        harness_path_or_none: Path | None = project_bundle.harness_path_by_name(
            harness_id
        )
        if harness_path_or_none is None:
            error_msg = f"Fuzzing harness '{harness_id}' not found in project '{project_bundle.name}'."
            logger.error(error_msg)
            raise ValueError(error_msg)
        self.harness_path: Path = harness_path_or_none

        self._ensure_ref_diff_exists()

    def _ensure_ref_diff_exists(self):
        if self.ref_diff is None:
            error_msg = (
                f"No ref diff found for project {self.project_bundle.name}. "
                f"{self.__class__.__name__} requires a diff."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

    def _get_ref_diff_prompt(self, lines_limit: int = 300) -> str:
        if self.ref_diff_total_lines <= lines_limit:
            return f"""
- **Ref Diff File:**
<ref_diff>
{self.ref_diff}
</ref_diff>
"""

        ref_diff_snippet = "\n".join(self.ref_diff.splitlines()[:lines_limit])
        return f"""
- **Ref Diff File (Showing first {lines_limit} of {self.ref_diff_total_lines} lines):**
<first_{lines_limit}_lines_of_ref_diff>
{ref_diff_snippet}
</first_{lines_limit}_lines_of_ref_diff>
"""


class FullDiffAnalysisAgent(_BaseDiffProcessingAgent):
    """
    Agent responsible for analyzing a given diff to identify vulnerabilities
    and explain how they can be triggered via a fuzzing harness.
    """

    def __init__(
        self,
        model: str,
        project_bundle: Project,
        harness_id: str,
        timeout: int = 1000,
        cache_type: Optional[str] = None,
        cache_expire_time: int = 1800,
    ):
        super().__init__(model, project_bundle, harness_id)
        self.deep_think_agent = DeepThinkAgent(
            model=self.model,
            project_bundle=self.project_bundle,
            timeout=timeout,
            cache_type=cache_type,
            cache_expire_time=cache_expire_time,
        )

    def __prompt(self) -> str:
        """Generates the prompt for the DeepThinkAgent to perform diff analysis."""
        # self.ref_diff is guaranteed to be non-None by _ensure_ref_diff_exists
        ref_diff_prompt = self._get_ref_diff_prompt(lines_limit=300)

        return f"""
You are the world’s foremost expert in program analysis and vulnerability research, competing in the AI Cyber Challenge (AIxCC) Final Round (AFC).  
Your task is to analyze a provided diff or Pull Request, identify any vulnerabilities introduced by the changes, and explain how they can be triggered via the fuzzing harness entrypoint: `LLVMFuzzerTestOneInput()`.

Produce a comprehensive vulnerability analysis report that:
- Clearly describes the flaw(s)
- Explains how the vulnerability can be triggered
- Provides guidance on writing a fuzzer to reproduce the issue

## Critical Notes

- The diff **is guaranteed** to introduce at least one vulnerability.  
- If no issues are apparent in the diff itself, investigate interactions with the surrounding code, as the vulnerability may emerge only in context.

## Challenge Project Details

- **Project Name:** {self.project_bundle.name}  
- **Fuzzing Harness Name:** {self.harness_id}  
- **Fuzzing Harness Path:** {self.harness_path}  
- **Post-Patch Repository Path:** {self.project_bundle.repo_path}  
- **Reference Diff Path:** {self.project_bundle.ref_diff_path}  
- **Diff Line Count:** {self.ref_diff_total_lines}

{ref_diff_prompt}

## Important Reminders

- There may be multiple fuzzing harnesses in the project. Focus **only** on the one specified above.

## Output Format

Wrap your final vulnerability report in a `<report>` tag, for example:

<report>
...
</report>

Remember: If there are test or example testcases in the diff, remember to check and utilize them to guide the later seed generation. You can include your guide in the report.

"""

    @override
    async def run(self, input_data=None):
        logger.info("Running DiffAnalysisAgent...")
        return await self.deep_think_agent.run(self.__prompt())


class BasicDiffGen(_BaseDiffProcessingAgent):
    """
    Agent responsible for generating a Python script that creates fuzzing seeds
    targeted at changes introduced in a given diff.
    """

    def __init__(
        self,
        model: str,
        project_bundle: Project,
        harness_id: str,
        timeout: int = 1500,
        cache_type: Optional[str] = None,
        cache_expire_time: int = 1800,
    ):
        super().__init__(model, project_bundle, harness_id)
        self.ossfuzz_project_path: Path = self.harness_path.parent
        self.deep_think_agent = DeepThinkAgent(
            model=self.model,
            project_bundle=self.project_bundle,
            timeout=timeout,
            cache_type=cache_type,
            cache_expire_time=cache_expire_time,
        )

    def __prompt(self, vulnerability_analysis_report: str | None = None) -> str:
        analysis_context_prompt = ""
        if vulnerability_analysis_report:
            analysis_context_prompt = f"""

## ADDITIONAL CONTEXT FROM PREVIOUS ANALYSIS:
A prior analysis of this diff produced the following report. Use this to inform your seed generation strategy, focusing on areas identified as potentially problematic or interesting.
<vulnerability_report>
{vulnerability_analysis_report}
</vulnerability_report>
"""
        return f"""
You are the world's leading program analysis expert and security researcher competing in the AI Cyber Challenge (AIxCC) Final Round (AFC).  
You are an expert in fuzzing and vulnerability discovery, tasked with creating targeted fuzzing seeds based on specific code changes.
Given a diff, and potentially a vulnerability analysis report on that diff, your goal is to write a fuzzing test generator Python script that generates seeds to effectively test the modifications and uncover potential vulnerabilities.
Note that, due to the nature of the competition, the provided diff is guaranteed to contain one or more vulnerabilities.
We have put the diff in the file {self.project_bundle.ref_diff_path}.

## Challenge Project Information:
- **Project Name:** {self.project_bundle.name}
- **OSS-Fuzz Project Path:** {self.ossfuzz_project_path}
- **Fuzzing Harness Name:** {self.harness_id}
- **Fuzzing Harness Path:** {self.harness_path}
- **Source Code Repository Path (Post-Patch):** {self.project_bundle.repo_path}
- ** Ref Diff Path (This is the diff you need to analyze) **: {self.project_bundle.ref_diff_path}
- Ref Diff Total Lines: {self.ref_diff_total_lines}
{self._get_ref_diff_prompt(lines_limit=300)}
{analysis_context_prompt}

## !! Important Information !!:
<important_info>
- There may be multiple fuzzing harnesses in the project, but in this case, you only need to care about the one specified in the Fuzzing Harness Name ({self.harness_id}: {self.harness_path}).
</important_info>

TASK:
1. Analyze the provided `Ref Diff` to understand the code changes.
2. If provided, review the `ADDITIONAL CONTEXT FROM PREVIOUS ANALYSIS` to further guide your seed generation.
3. Consider how these changes (and any reported vulnerabilities) might introduce new execution paths or weaknesses.
4. Examine the specified fuzzing harness (`{self.harness_path}`), particularly `LLVMFuzzerTestOneInput()`, to understand how to provide input.
5. Craft an elegant, self-contained Python script (a fuzzer script) that generates high-quality fuzzing test cases (seeds) specifically designed to:
    a. Exercise the code paths modified in the `Ref Diff`.
    b. Probe for potential vulnerabilities related to the changes in the `Ref Diff`, informed by any prior analysis.
    c. Maximize the chance of triggering crashes related to the diff.
    d. Ensure the generator can be called millions of times without exhausting diversity.

## HARNESS ANALYSIS GUIDANCE (for context):
- Understand the `LLVMFuzzerTestOneInput()` function in `{self.harness_path}`.
- Pay attention to expected input structure and format.

## SCRIPT USAGE GUIDE:
- Write elegant, precise, and error-free Python code.
- Integrate your analysis of the `Ref Diff` (and any provided report) directly into the seed generation logic.
- The script must implement a function named `gen_one_seed` that returns a seed for the fuzzing harness in bytes.

## CRITICAL REQUIREMENTS:
- Focus your seed generation strategy on the changes highlighted in the `Ref Diff` and informed by any vulnerability report.
- The primary goal is to generate seeds that test the implications of the provided `Ref Diff`.
- After your analysis, use the AI coder to generate the script.
- The script must implement `gen_one_seed` as specified.
- Ensure the generator can be called millions of times without exhausting diversity.
- Include necessary comments for better understanding the strategies and your thoughts.
- We prefer self-contained scripts, but you can use third-party packages when you have to.
- If you use third-party packages, make sure you correctly use the APIs.
- Remember to do auto-testing by running the script to mitigate the import errors and syntax errors.

## OUTPUT FORMAT:
- Show me the generated script enclosed within `<script>` and `</script>` tags:
- We'll extract the runnable script from <script>...</script> tags.

For example:
<script>
# other codes ...
def gen_one_seed() -> bytes: # for real usage
    # Your diff-aware and analysis-informed seed generation logic here
    pass

if __name__ == "__main__": # for auto-testing
    for _ in range(30): # for local testing
        gen_one_seed() # do not print to make the stdout clean
</script>

Remember: Avoid overanalyzing — just give the fuzzer script based on the vulnerability analysis report.
If there are test or example testcases in the diff, remember to check and utilize them to generate seeds.
"""

    @override
    async def run(
        self, vulnerability_analysis_report: str | None = None
    ):  # Accepts report from previous agent
        logger.info("Running DiffFuzzerGeneratorAgent...")
        return await self.deep_think_agent.run(
            self.__prompt(vulnerability_analysis_report)
        )


class SeedsGenForDiff:
    def __init__(
        self,
        model: str,
        project_bundle: Project,
        harness_id: str,
        timeout: int = 1500,
        cache_type: Optional[str] = None,
        cache_expire_time: int = 1800,
    ):
        self.model = model
        self.project_bundle = project_bundle
        self.harness_id = harness_id
        self.timeout = timeout
        self.cache_type = cache_type
        self.cache_expire_time = cache_expire_time

    async def run(self):
        self.diff_analyzer = FullDiffAnalysisAgent(
            model=self.model,
            project_bundle=self.project_bundle,
            harness_id=self.harness_id,
            timeout=self.timeout,
            cache_type=self.cache_type,
            cache_expire_time=self.cache_expire_time,
        )

        diff_analysis_report = await self.diff_analyzer.run()

        if "<skip_harness>" in diff_analysis_report:
            logger.info("Skipping harness due to low chance to reach the target")
            return None

        if diff_analysis_report is None:
            logger.error("Diff analysis report is None")
            return None
        else:
            logger.info(diff_analysis_report)

        diff_fuzzer_generator = BasicDiffGen(
            model=self.model,
            project_bundle=self.project_bundle,
            harness_id=self.harness_id,
            timeout=self.timeout,
            cache_type=self.cache_type,
            cache_expire_time=self.cache_expire_time,
        )

        diff_fuzzer_script = await diff_fuzzer_generator.run(diff_analysis_report)

        logger.info(diff_fuzzer_script)

        return await extract_script_from_response(diff_fuzzer_script, self.model)
