import asyncio
import anyio
import subprocess
import yaml
import logging
import argparse
from pathlib import Path
import traceback
import sys

# Agents
from libAgents.agents.fuzzer_analyzer import FuzzerAnalysisAgent, ImprovedFuzzerAgent
from libAgents.agents.fuzzer_analyzer import save_analysis_report, save_improved_script, format_report_for_display
from libAgents.utils import Project, get_model_by_weights

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
# You can set libAgents to DEBUG for more verbose output from the agents
logging.getLogger("libAgents").setLevel(logging.DEBUG)
logging.getLogger("litellm").setLevel(logging.WARNING)
logging.getLogger("LiteLLM").setLevel(logging.WARNING)
# import litellm
# litellm._turn_on_debug()

# Assuming root_dir is the parent of the 'examples' directory, so ../ from this file's location
root_dir = Path(__file__).parent.parent


# Helper functions adapted from other examples
def load_config(oss_fuzz_path: Path, project_name: str) -> dict:
    project_yaml = oss_fuzz_path / "projects" / project_name / "project.yaml"
    if not project_yaml.exists():
        logger.error(f"Could not find project.yaml at: {project_yaml}")
        raise ValueError(f"Could not find {project_yaml}")

    with open(project_yaml) as f:
        project_dict = yaml.safe_load(f)

    if "main_repo" not in project_dict:
        logger.error(f"Unable to find main_repo key in {project_yaml}")
        raise ValueError(f"Unable to find main_repo key in {project_yaml}")

    return project_dict


def get_src_dir(
    oss_fuzz_path: Path, project_name: str, cloned_repos_parent_dir: Path
) -> Path:
    """Fetch or clone the repository for the given project name into the cloned_repos_parent_dir."""
    logger.info(
        f"Attempting to load config for project: {project_name} from OSS-Fuzz path: {oss_fuzz_path}"
    )
    project_dict = load_config(oss_fuzz_path, project_name)
    main_repo_url = project_dict["main_repo"]

    # The target directory for the clone will be cloned_repos_parent_dir / project_name
    repo_clone_path = cloned_repos_parent_dir / project_name

    if not repo_clone_path.exists():
        logger.info(
            f"Repository not found at {repo_clone_path}. Cloning {main_repo_url}..."
        )
        # Ensure parent directories exist for repo_clone_path before cloning
        repo_clone_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.run(
                ["git", "clone", main_repo_url, str(repo_clone_path)],
                check=True,
                capture_output=True,
                text=True,
            )
            logger.info(f"Successfully cloned to {repo_clone_path}")
        except subprocess.CalledProcessError as e:
            logger.error(
                f"Failed to clone repository: {main_repo_url} into {repo_clone_path}"
            )
            logger.error(f"Git command stdout: {e.stdout}")
            logger.error(f"Git command stderr: {e.stderr}")
            raise
    else:
        logger.info(f"Repository already exists at {repo_clone_path}")

    return repo_clone_path


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Analyze an ineffective fuzzer script and generate an improved version."
    )
    parser.add_argument(
        "--project",
        type=str,
        default="aixcc/c/r2-freerdp-diff-1",
        help="Project name to analyze (default: r2-freerdp-diff-1)",
    )
    parser.add_argument(
        "--harness_id",
        type=str,
        default="TestFuzzCryptoCertificateDataSetPEM",
        help="The ID of the fuzzing harness to target (default: TestFuzzCryptoCertificateDataSetPEM)",
    )
    parser.add_argument(
        "--fuzzer_script",
        type=str,
        help="Path to the ineffective fuzzer script to analyze (if not provided, uses example)",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        help="Directory to save analysis report and improved script (default: workdir/fuzzer_analysis)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode for agents (e.g., context saving)",
    )
    return parser.parse_args()


# Example ineffective fuzzer script
EXAMPLE_INEFFECTIVE_SCRIPT = '''
import random

def gen_one_seed() -> bytes:
    # Simple random bytes - not structure-aware
    size = random.randint(1, 100)
    return bytes([random.randint(0, 255) for _ in range(size)])

if __name__ == "__main__":
    for _ in range(20):
        print(gen_one_seed())
'''


async def main():
    args = parse_arguments()

    workdir = root_dir / "workdir"
    workdir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Using working directory: {workdir.resolve()}")

    # Set up output directory
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = workdir / "fuzzer_analysis"
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Using output directory: {output_dir.resolve()}")

    cloned_repos_dir = root_dir / "cloned-repos"
    cloned_repos_dir.mkdir(parents=True, exist_ok=True)
    logger.info(
        f"Using cloned repositories base directory: {cloned_repos_dir.resolve()}"
    )

    oss_fuzz_home = root_dir / "oss-fuzz"
    if not oss_fuzz_home.exists():
        logger.error(f"OSS-Fuzz home directory not found at: {oss_fuzz_home}")
        logger.error(
            "Please ensure OSS-Fuzz is cloned/placed at the root of the libAgents workspace."
        )
        sys.exit(1)

    try:
        # Determine the local repository path and clone if necessary
        logger.info(f"Getting source directory for project: {args.project}")
        local_repo_clone_path = get_src_dir(
            oss_fuzz_path=oss_fuzz_home,
            project_name=args.project,
            cloned_repos_parent_dir=cloned_repos_dir,
        )
        logger.info(f"Local repository path set to: {local_repo_clone_path}")

        # Initialize the project
        project_instance = Project(
            project_name=args.project,
            oss_fuzz_home=oss_fuzz_home,
            local_repo_path=local_repo_clone_path,
        )

        # Prepare the project bundle
        logger.info(f"Preparing project bundle for: {args.project}")
        project_bundle = project_instance.prepare_project_bundle(workdir)

        # Load the ineffective fuzzer script
        if args.fuzzer_script:
            with open(args.fuzzer_script, 'r') as f:
                ineffective_script = f.read()
            logger.info(f"Loaded fuzzer script from: {args.fuzzer_script}")
        else:
            ineffective_script = EXAMPLE_INEFFECTIVE_SCRIPT
            logger.info("Using example ineffective fuzzer script")

        # Set up model
        weighted_models = {
            "claude-opus-4-20250514": 100,
            # "claude-sonnet-4-20250514": 100,
            # "o3": 100,
            # "gemini-2.5-pro": 100,
        }
        model = get_model_by_weights(weighted_models)

        # Step 1: Analyze the ineffective fuzzer
        logger.info("=" * 60)
        logger.info("STEP 1: Analyzing ineffective fuzzer script...")
        logger.info("=" * 60)
        
        analyzer = FuzzerAnalysisAgent(
            model=model,
            project_bundle=project_bundle,
            script_content=ineffective_script,
            harness_id=args.harness_id,
            timeout=1500,
            cache_type="disk",
            cache_expire_time=100000000,
        )

        analysis_report = await analyzer.run()
        
        # Save and display the analysis report
        report_path = output_dir / "analysis_report.md"
        save_analysis_report(analysis_report, str(report_path))
        
        print("\n" + "=" * 30 + " ANALYSIS REPORT " + "=" * 30)
        print(format_report_for_display(analysis_report, max_width=100))
        print("=" * 77 + "\n")

        # Step 2: Generate improved fuzzer based on analysis
        logger.info("=" * 60)
        logger.info("STEP 2: Generating improved fuzzer script...")
        logger.info("=" * 60)
        
        improver = ImprovedFuzzerAgent(
            model=model,
            project_bundle=project_bundle,
            analysis_report=analysis_report,
            harness_id=args.harness_id,
            timeout=1500,
        )

        improved_script = await improver.run()

        print("====================Final Improved Script=====================")
        
        print(improved_script)


    except Exception as e:
        logger.error(f"An error occurred during agent execution: {e}")
        print("\nTraceback:")
        traceback.print_exc()


if __name__ == "__main__":
    anyio.run(main) 
    # asyncio.run(main())