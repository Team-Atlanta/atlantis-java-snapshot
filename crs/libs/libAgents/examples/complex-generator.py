# A simple seeds generator for oss-fuzz project

import asyncio
import logging
from pathlib import Path

from libAgents.agents import DeepSearchAgent
from libAgents.plugins import (
    AnswerPlugin,
    ReflectPlugin,
    CoderPlugin,
    CodeBrowserPlugin,
    FsReaderPlugin,
    RipGrepPlugin,
    ListDirPlugin,
    AskCodebasePlugin,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logging.getLogger("libAgents").setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)

SEEDS_GEN_PROMPT = """[Advanced Coding Task] Fuzzing Testing Research: High Code Coverage and Seed Generation

OBJECTIVE:
We are conducting fuzzing testing research aimed at achieving maximum code coverage for a specific project and its fuzzing harness. 
As an expert in fuzzing, you will generate an optimal set of fuzzing test cases and develop a corpus that targets the designated fuzzing harness effectively.

TASK:
1. Analyze the codebase build configurations.
2. Identify enabled modules.
3. Examine the fuzzing harness—specifically the function `LLVMFuzzerTestOneInput()`.
4. Craft an elegant, self-contained Python script that generates high-quality fuzzing test cases.

PROJECT INFORMATION:
- Project Name: {project_name}
- OSS-Fuzz Project Path (includes the fuzzer harness and build configurations): {ossfuzz_project_path}
- Fuzzing Harness Path (the main harness containing the `LLVMFuzzerTestOneInput()` function to be analyzed): {fuzzing_harness_path}
- Source Code Repository Path (contains the actual project source code): {source_code_repository_path}

HARNESS ANALYSIS GUIDANCE:
- Thoroughly read the source code to fully understand the `LLVMFuzzerTestOneInput()` function and the surrounding harness.
- Pay close attention to the expected input structure and format required by the harness.
- Focus on generating seeds that significantly boost testing coverage and have the potential to trigger crashes in vulnerable targets.
- Tailor your analysis and approach specifically for this harness.

SCRIPT USAGE GUIDE:
- Write elegant, precise, and error-free code (ensure proper Python syntax and indentation).
- Integrate your analysis insights directly into the script.
- The script must serve as a security expert-level fuzzing test generator.
- It should generate multiple, unique `.bin` files, each containing a distinct fuzzing test case.

CRITICAL REQUIREMENTS:
- Support execution from the command line with the following format:

  $ python3 seeds_generator.py --nblobs <number_of_blobs> --output_dir <output_directory>

OUTPUT FORMAT:

Show me the generated script in the format of:

<script_content>
# the python script content
</script_content>
"""

SRC_REPO_PATH = Path("./cloned-repos/aixcc/c/asc-nginx").resolve()
OSS_FUZZ_PATH = SRC_REPO_PATH / "oss-fuzz"
NGINX_OSS_FUZZ_PATH = OSS_FUZZ_PATH / "projects" / "aixcc" / "c" / "asc-nginx"
HARNESS_PATH = NGINX_OSS_FUZZ_PATH / "fuzz" / "pov_harness.cc"

plugins = [
    AnswerPlugin(),
    ReflectPlugin(),
    CoderPlugin(
        project_name="nginx-seeds-gen",
        main_repo=SRC_REPO_PATH,
        ro_fnames=[HARNESS_PATH],
    ),
    CodeBrowserPlugin(
        project_name="nginx",
        src_path=SRC_REPO_PATH,
    ),
    FsReaderPlugin(),
    RipGrepPlugin(),
    ListDirPlugin(),
    AskCodebasePlugin(
        project_name="nginx",
        src_path=SRC_REPO_PATH,
    ),
]

agent = DeepSearchAgent(plugins=plugins, enable_context_saving=True)

PROMPT = SEEDS_GEN_PROMPT.format(
    project_name="nginx",
    ossfuzz_project_path=NGINX_OSS_FUZZ_PATH,
    fuzzing_harness_path=HARNESS_PATH,
    source_code_repository_path=SRC_REPO_PATH,
)

print(PROMPT)

result = asyncio.run(agent.query(PROMPT, override_model="claude-opus-4-20250514"))

print(result)
