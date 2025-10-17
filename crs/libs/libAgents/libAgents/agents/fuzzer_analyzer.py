import os
from libAgents.agents import AgentBase, DeepThinkAgent
from libAgents.utils import Project, extract_script_from_response, cd
from libAgents.config import get_model
from libAgents.model import generate_text
from libAgents.tools import OpenAICodex, OpenAICodexConfig, ClaudeCode
from typing import Optional


FUZZER_ANALYSIS_PROMPT = """
INSTRUCTIONS:
- You are the world's leading program analysis and fuzzing expert, specializing in vulnerability discovery and fuzzer optimization.
- Your task is to analyze an existing fuzzer script that has been ineffective at finding vulnerabilities or achieving high coverage.
- You will provide a comprehensive analysis report and detailed improvement plan for the next iteration.

OBJECTIVE:
- Identify weaknesses in the current fuzzer script's approach
- Analyze why it failed to achieve high coverage or trigger crashes
- Propose specific, actionable improvements for the next agent to implement
- Create a detailed report that guides the next iteration toward better results

FUZZER SCRIPT CONVENTION:
- The script MUST contain a `gen_one_seed() -> bytes` function
- This function will be called millions of times during fuzzing
- Each call should return a different, high-quality seed
- Seed diversity is CRITICAL - the function must be capable of generating millions of unique inputs
- Performance matters - generation should be fast enough for high-throughput fuzzing

ANALYSIS TASKS:
1. **Script Analysis**:
   - Review the current `gen_one_seed()` implementation
   - Assess seed diversity - can it generate millions of unique seeds?
   - Evaluate generation performance and efficiency
   - Identify missing input patterns or structures
   - Check for proper randomization and state management

2. **Diversity Analysis**:
   - Evaluate if the script can generate sufficient variety
   - Check for patterns that might limit diversity
   - Assess randomization strategies
   - Identify if seeds are too similar or predictable
   - Analyze coverage of the input space

3. **Harness Understanding**:
   - Re-analyze the fuzzing harness (LLVMFuzzerTestOneInput)
   - Identify code paths not being exercised
   - Find input constraints or formats the script missed
   - Detect complex state machines or protocols not properly handled

4. **Coverage Gap Analysis**:
   - Determine which parts of the code are likely not being reached
   - Identify input structures needed to reach deeper code paths
   - Find conditional branches that require specific input patterns

5. **Vulnerability Pattern Recognition**:
   - Identify common vulnerability patterns in the target code
   - Suggest input patterns likely to trigger these vulnerabilities
   - Focus on memory corruption, integer overflows, format string bugs, etc.

CHALLENGE PROJECT DETAILS:
- Project Name: {project_name}
- OSS-Fuzz Project Path: {ossfuzz_project_path}
- Fuzzing Harness Name: {fuzzing_harness_name}
- Fuzzing Harness Path: {fuzzing_harness_path}
- Source Repository Path: {source_code_repository_path}

CURRENT FUZZER SCRIPT:
<current_script>
{script_content}
</current_script>

ANALYSIS REPORT FORMAT:
Your response should be a comprehensive analysis report with the following sections:

## FUZZER SCRIPT ANALYSIS REPORT

### 1. Executive Summary
- Brief overview of the script's main weaknesses
- Key findings about why it's ineffective
- High-level recommendations

### 2. Current Script Analysis
- **gen_one_seed() Implementation**: Analysis of the current function
- **Diversity Assessment**: Can it generate millions of unique seeds?
- **Performance**: Is generation fast enough for high-throughput fuzzing?
- **Strengths**: What the script does well
- **Weaknesses**: Critical flaws in the approach
- **Missing Coverage**: Input patterns or structures not generated

### 3. Seed Diversity Analysis
- **Current Diversity Level**: Rate the diversity (Low/Medium/High)
- **Diversity Limitations**: What limits the variety of generated seeds
- **Randomization Issues**: Problems with random state or generation
- **Input Space Coverage**: What percentage of valid inputs can be generated
- **Recommendations**: Specific techniques to improve diversity

### 4. Target Code Analysis
- **Entry Points**: Analysis of LLVMFuzzerTestOneInput
- **Code Paths**: Important paths not being reached
- **Input Constraints**: Formats, structures, or protocols expected
- **Vulnerability Surfaces**: Areas likely to contain bugs

### 5. Detailed Improvement Plan
- **Diversity Improvements**:
  - Techniques to ensure millions of unique seeds
  - Better randomization strategies
  - State management for variety
  
- **Input Structure Improvements**:
  - Specific formats or protocols to implement
  - Data structures that need proper generation
  - Edge cases and boundary values to include
  
- **Generation Strategy Improvements**:
  - Multiple generation modes for diversity
  - Mutation strategies for better coverage
  - Grammar-based or structure-aware approaches needed
  
- **Performance Optimizations**:
  - Make generation faster if needed
  - Reduce unnecessary computations
  - Efficient data structure usage

### 6. Implementation Recommendations
- **Priority 1 (Critical)**: Must-have improvements for diversity and coverage
- **Priority 2 (Important)**: Significant coverage gains
- **Priority 3 (Nice-to-have)**: Additional optimizations

### 7. Example Seed Patterns
Provide concrete examples showing the diversity of seeds that should be generated:
```python
# Example showing different generation strategies
def gen_one_seed() -> bytes:
    strategy = random.choice(['strategy1', 'strategy2', 'strategy3'])
    if strategy == 'strategy1':
        # Generate type 1 seeds
        return b"..."
    elif strategy == 'strategy2':
        # Generate type 2 seeds
        return b"..."
    # etc...
```

### 8. Next Steps
- Specific implementation guidance for improving gen_one_seed()
- Testing strategies to validate diversity
- Metrics to measure success (unique seeds per million calls, coverage achieved)

Remember: Focus heavily on seed diversity and the ability to generate millions of unique, high-quality inputs efficiently.
"""


class FuzzerAnalysisAgent(AgentBase):
    def __init__(
        self,
        model: str,
        project_bundle: Project,
        script_content: str,
        harness_id: str,
        timeout: int = 1500,
        cache_type: Optional[str] = None,
        cache_expire_time: int = 1800,
    ):
        super().__init__(project_bundle)
        self.project_bundle = project_bundle
        self.harness_id = harness_id
        self.model = model
        self.script_content = script_content
        self.deep_think_agent = DeepThinkAgent(
            model,
            project_bundle,
            timeout=timeout,
            cache_type=cache_type,
            cache_expire_time=cache_expire_time,
        )

    def __prompt(self):
        PROMPT = FUZZER_ANALYSIS_PROMPT.format(
            project_name=self.project_bundle.name,
            ossfuzz_project_path=self.project_bundle.project_path,
            fuzzing_harness_name=self.harness_id,
            fuzzing_harness_path=self.project_bundle.harness_path_by_name(
                self.harness_id
            ),
            source_code_repository_path=self.project_bundle.repo_path,
            script_content=self.script_content,
        )
        return PROMPT

    async def run(self, _input=None):
        response = await self.deep_think_agent.run(self.__prompt())
        # Return the analysis report directly instead of extracting a script
        return response


IMPROVED_FUZZER_PROMPT = """
INSTRUCTIONS:
- You are an expert fuzzer developer tasked with implementing an improved seed generator based on a detailed analysis report.
- The previous fuzzer script was ineffective, and you have been provided with specific recommendations for improvement.
- Your goal is to create a new, highly effective seed generator that addresses all identified weaknesses.

OBJECTIVE:
- Implement all critical improvements from the analysis report
- Create a seed generator that achieves high code coverage
- Generate inputs likely to trigger vulnerabilities
- Produce diverse, structure-aware seeds
- Ensure the generator can produce MILLIONS of unique seeds efficiently

FUZZER SCRIPT REQUIREMENTS:
- MUST implement a `gen_one_seed() -> bytes` function
- This function will be called millions of times
- Each call should return a different, high-quality seed
- Focus heavily on DIVERSITY - avoid generating similar or duplicate seeds
- Optimize for performance - generation must be fast

PREVIOUS ANALYSIS REPORT:
<analysis_report>
{analysis_report}
</analysis_report>

CHALLENGE PROJECT DETAILS:
- Project Name: {project_name}
- OSS-Fuzz Project Path: {ossfuzz_project_path}
- Fuzzing Harness Name: {fuzzing_harness_name}
- Fuzzing Harness Path: {fuzzing_harness_path}
- Source Repository Path: {source_code_repository_path}

IMPLEMENTATION REQUIREMENTS:
1. **Address All Critical Issues**: Implement all Priority 1 recommendations from the analysis
2. **Maximize Diversity**: Ensure millions of unique seeds can be generated
3. **Improve Input Generation**: Use the suggested patterns and structures
4. **Multiple Strategies**: Implement various generation modes for diversity
5. **Target Specific Paths**: Focus on reaching the identified uncovered code paths
6. **Edge Cases**: Include all suggested boundary conditions and edge cases
7. **Performance**: Ensure fast generation for high-throughput fuzzing

OUTPUT FORMAT:
Wrap the full script between <script> and </script> tags:

<script>
import os
import random
import struct
# ... other necessary imports ...

# Global state for diversity (if needed)
# generation_counter = 0
# seen_patterns = set()

def gen_one_seed() -> bytes:
    '''Generate a single fuzz input seed.
    
    This function will be called millions of times and must:
    - Return different seeds on each call
    - Cover various input structures and patterns
    - Be fast enough for high-throughput fuzzing
    '''
    # Implementation based on analysis recommendations
    # Use multiple strategies, randomization, mutations, etc.
    return b""

# Optional: Helper functions for different generation strategies
def generate_type_a() -> bytes:
    pass

def generate_type_b() -> bytes:
    pass

# Optional: Mutation functions
def mutate_seed(seed: bytes) -> bytes:
    pass

if __name__ == "__main__":
    for _ in range(20): # for local testing
        gen_one_seed() # don't print to make the stdout clean
</script>

KEY IMPLEMENTATION GUIDELINES:
1. **Diversity Techniques**:
   - Use multiple generation strategies selected randomly
   - Implement proper randomization with good entropy
   - Consider using counters, timestamps, or other varying state
   - Avoid patterns that limit the output space

2. **Performance Optimization**:
   - Avoid expensive operations in gen_one_seed()
   - Pre-compute data structures if needed
   - Use efficient random number generation
   - Cache reusable components

3. **Structure-Aware Generation**:
   - Implement the input formats identified in the analysis
   - Use proper encoding for protocols or file formats
   - Include valid headers, magic bytes, etc.

4. **Testing for Diversity**:
   - Include code to verify uniqueness over many calls
   - Test that seeds cover the expected input space
   - Ensure no obvious patterns or biases

Remember: 
1. The success of this fuzzer depends on its ability to generate millions of diverse, high-quality seeds that explore different code paths and trigger vulnerabilities.
2. Avoid overanalyzing — just give the copy/pasteable/runnable fuzzer script based on the analysis report.
"""


class ImprovedFuzzerAgent(AgentBase):
    def __init__(
        self,
        model: str,
        project_bundle: Project,
        analysis_report: str,
        harness_id: str,
        timeout: int = 1500,
        cache_type: Optional[str] = None,
        cache_expire_time: int = 1800,
    ):
        super().__init__(project_bundle)
        self.project_bundle = project_bundle
        self.harness_id = harness_id
        self.use_codex = False
        self.use_claude = False
        self.use_deep_think = False

        self.model = model

        if "claude" in model:
            self.use_claude = True
        else:
            self.use_deep_think = True

        self.analysis_report = analysis_report

        self.deep_think_agent = DeepThinkAgent(
            model,
            project_bundle,
            timeout=timeout,
            cache_type=cache_type,
            cache_expire_time=cache_expire_time,
            enable_aider=False,
            enable_codebrowser=False,
        )

    async def __query_codex(self, prompt: str) -> str:
        config = OpenAICodexConfig(
                model_name=self.model,
                quiet=True,
                use_json=True,
                verbose=False,
                full_auto=True,
                skip_permissions=False,
                cwd=self.project_bundle.repo_path,
            )
        codex = OpenAICodex(config)
        with cd(self.project_bundle.repo_path):
            response = await codex.async_query(prompt)
        return response

    async def __query_claude(self, prompt: str) -> str:
        claude = ClaudeCode(self.project_bundle.repo_path)
        response = await claude.async_query(prompt)
        return response

    def __prompt(self):
        PROMPT = IMPROVED_FUZZER_PROMPT.format(
            analysis_report=self.analysis_report,
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
        if self.use_codex:
            response = await self.__query_codex(self.__prompt())
            return await extract_script_from_response(response, self.model)
        elif self.use_claude:
            response = await self.__query_claude(self.__prompt())
            script = await extract_script_from_response(response, self.model)
            if script is None:
                response = await self.deep_think_agent.run(self.__prompt())
                script = await extract_script_from_response(response, self.model)
            return script
        elif self.use_deep_think:
            response = await self.deep_think_agent.run(self.__prompt())
            return await extract_script_from_response(response, self.model, use_model=True)
        else:
            # simply rely on the model
            model = get_model("deep-evolve", override_model=self.model)
            response = await generate_text(
                model,
                self.__prompt(),
            )
            return await extract_script_from_response(response.object, self.model)


# Utility functions for report handling
def save_analysis_report(report: str, output_path: str) -> None:
    """Save the analysis report to a file."""
    with open(output_path, 'w') as f:
        f.write(report)
    print(f"Analysis report saved to: {output_path}")


def save_improved_script(script: str, output_path: str) -> None:
    """Save the improved fuzzer script to a file."""
    with open(output_path, 'w') as f:
        f.write(script)
    print(f"Improved script saved to: {output_path}")


def format_report_for_display(report: str, max_width: int = 100) -> str:
    """Format the report for better console display."""
    import textwrap
    
    lines = report.split('\n')
    formatted_lines = []
    
    for line in lines:
        if line.strip():
            if line.startswith('#'):  # Headers
                formatted_lines.append(line)
            elif line.startswith('- ') or line.startswith('  '):  # Lists
                wrapped = textwrap.fill(line, width=max_width, 
                                      initial_indent='', 
                                      subsequent_indent='  ')
                formatted_lines.append(wrapped)
            else:  # Regular text
                wrapped = textwrap.fill(line, width=max_width)
                formatted_lines.append(wrapped)
        else:
            formatted_lines.append('')
    
    return '\n'.join(formatted_lines)