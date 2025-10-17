import asyncio
import subprocess
import yaml
import logging
import signal
import traceback
import sys
import inspect
import argparse
from libAgents.agents import MapAgent
from libAgents.utils import Project, get_model_by_weights
from pathlib import Path


# Enhanced signal handler for SIGINT (Ctrl+C)
def sigint_handler(sig, frame):
    print("\n\nCaught SIGINT (Ctrl+C). Printing stack trace:")
    traceback.print_stack(frame)

    # Print asyncio task information
    print("\nActive asyncio tasks:")
    try:
        current_loop = asyncio.get_event_loop()
        tasks = asyncio.all_tasks(current_loop)
        for i, task in enumerate(tasks):
            print(f"\nTask {i + 1}/{len(tasks)}:")
            print(f"Name: {task.get_name()}")
            print(f"Done: {task.done()}")
            print(f"Cancelled: {task.cancelled()}")
            print(f"Task: {task}")
            print(f"Coroutine: {task.get_coro()}")

            # Print task state
            if not task.done():
                # Print the stack of the pending task directly
                print(f"\nStack for pending Task {i + 1} ({task.get_name()}):")
                task.print_stack(file=sys.stdout)

            # For _query method specifically
            print("\nChecking for deep_search_agent._query:")
            for module_frame in inspect.stack():
                if (
                    "stepwise_agent.py" in module_frame.filename
                    and "_query" in module_frame.function
                ):
                    print(
                        f"Found in {module_frame.filename}, line {module_frame.lineno}, in {module_frame.function}"
                    )
                    print(
                        f"  Code: {module_frame.code_context[0].strip() if module_frame.code_context else 'N/A'}"
                    )

    except Exception as e:
        print(f"Error getting task information: {e}")
        print(traceback.format_exc())

    raise KeyboardInterrupt


# Register the signal handler
signal.signal(signal.SIGINT, sigint_handler)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logging.getLogger("libAgents").setLevel(logging.DEBUG)

root_dir = Path(__file__).parent.parent


def load_config(oss_fuzz_path, project_name):
    project_yaml = oss_fuzz_path / "projects" / project_name / "project.yaml"
    if not project_yaml.exists():
        raise ValueError(f"Could not find {project_yaml}")

    with open(project_yaml) as f:
        project_dict = yaml.safe_load(f)

    if "main_repo" not in project_dict:
        raise ValueError(f"Unable to find main_repo key in {project_yaml}")

    return project_dict


def get_src_dir(oss_fuzz_path, project_name, dst_dir):
    """Fetch or clone the repository for the given project name."""

    project_dict = load_config(oss_fuzz_path, project_name)
    main_repo = project_dict["main_repo"]

    repo_path = Path(dst_dir) / project_name
    if not repo_path.exists():
        subprocess.run(["git", "clone", main_repo, repo_path], check=True)

    return repo_path


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Run differential analysis on a project"
    )
    parser.add_argument(
        "--project",
        type=str,
        default="aixcc/c/r2-sqlite3-diff-1",
        help="Project name to analyze (default: aixcc/c/r2-sqlite3-diff-1)",
    )
    return parser.parse_args()


QUERY = """
Advanced Coding Task:
Fuzzing Testing Research: High Code Coverage and Seed Generation

OBJECTIVE:
- We are conducting fuzzing testing research aimed at achieving maximum code coverage for a specific project and its fuzzing harness. 
- As an expert in fuzzing, you will write a seed generator script that targets the designated fuzzing harness effectively.
- Our ultimate goal is to call the generator to generate quality seed to trigger as many crashes as possible.

TASK:
1. Analyze the codebase build configurations.
2. Identify enabled modules.
3. Examine the fuzzing harness—specifically the function `LLVMFuzzerTestOneInput()`.
4. Craft an elegant, self-contained Python script that generates high-quality fuzzing test cases.

PROJECT INFORMATION:
- Project Name: {project_name}
- OSS-Fuzz Project Path (includes the fuzzer harness and build configurations): {ossfuzz_project_path}
- The specific fuzzing harness to be analyzed: {fuzzing_harness_name}
- Fuzzing Harness Path (the main harness containing the `LLVMFuzzerTestOneInput()` function to be analyzed): {fuzzing_harness_path}
- Source Code Repository Path (contains the actual project source code): {source_code_repository_path}
- Feel free to browse the relavant codes you need for C/C++ codes, using the code-browser plugin.

HARNESS ANALYSIS GUIDANCE:
- Thoroughly read the source code to fully understand the `LLVMFuzzerTestOneInput()` function and the surrounding harness.
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
def gen_on_seed() -> bytes: # for real usage
    # TODO: implement this
    pass

if __name__ == "__main__":
    gen_on_seed() # for testing
</example>

OUTPUT FORMAT:
- Show me the generate script enclosed within `<script>` and `</script>` tags:
<script>
# other codes ...
def gen_on_seed() -> bytes: # for real usage
    # TODO: implement this
    pass

if __name__ == "__main__":
    for _ in range(10): # for robust testing due to inner randomness
        gen_on_seed() # for testing
</script>"""


def main():
    args = parse_arguments()

    workdir = root_dir / "workdir"
    workdir.mkdir(parents=True, exist_ok=True)

    home_dir = root_dir / "oss-fuzz"
    project_name = args.project
    local_repo_dir = get_src_dir(home_dir, project_name, root_dir / "cloned-repos")

    project = Project(
        project_name=project_name,
        oss_fuzz_home=home_dir,
        local_repo_path=local_repo_dir,
    ).prepare_project_bundle(Path("./workdir").resolve())

    query = QUERY.format(
        project_name=project_name,
        ossfuzz_project_path=home_dir,
        fuzzing_harness_name="customfuzz3",
        fuzzing_harness_path=project.harness_path_by_name("customfuzz3"),
        source_code_repository_path=local_repo_dir,
    )

    weighted_models = {
        # "gemini-2.5-pro": 50,
        # "grok-3-mini-beta": 50,
        # "claude-3-7-sonnet-20250219": 50,
        # "claude-opus-4-20250514": 50,
        "o4-mini": 100,
    }
    model = get_model_by_weights(weighted_models)

    agent = MapAgent(model, project, "customfuzz3", query=query, debug=True)

    result = asyncio.run(agent.start())

    print(">>> Result:")
    print(result)


if __name__ == "__main__":
    main()
