import asyncio
import subprocess
import yaml
import logging
import argparse
from pathlib import Path
import traceback
import sys

# Agents
from libAgents.agents import SeedsGenForDiff
from libAgents.utils import Project, get_model_by_weights

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
# You can set libAgents to DEBUG for more verbose output from the agents
# logging.getLogger("libAgents").setLevel(logging.DEBUG)

# Assuming root_dir is the parent of the 'examples' directory, so ../ from this file's location
root_dir = Path(__file__).parent.parent


# Helper functions adapted from step_analyze.py
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
    # Handles project_name like "aixcc/c/r2-sqlite3-diff-1" by creating nested dirs.
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
        description="Run DiffAnalysisAgent followed by DiffFuzzerGeneratorAgent for a project."
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
        default="TestFuzzCryptoCertificateDataSetPEM",  # Default harness ID, ensure this is valid for your project
        help="The ID of the fuzzing harness to target (default: TestFuzzCryptoCertificateDataSetPEM)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode for agents (e.g., context saving)",
    )
    return parser.parse_args()


async def main():
    args = parse_arguments()

    workdir = root_dir / "workdir"
    workdir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Using working directory: {workdir.resolve()}")

    cloned_repos_dir = (
        root_dir / "cloned-repos"
    )  # This is the parent directory for all clones
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

        # Initialize the project.
        project_instance = Project(
            project_name=args.project,
            oss_fuzz_home=oss_fuzz_home,
            local_repo_path=local_repo_clone_path,  # Now correctly provided
        )

        # Prepare the project bundle.
        # This typically involves preparing the diff file based on the local_repo_path.
        logger.info(f"Preparing project bundle for: {args.project}")
        project_bundle = project_instance.prepare_project_bundle(workdir)
        logger.info(
            f"Project bundle prepared. Ref diff available: {project_bundle.ref_diff is not None}"
        )
        if project_bundle.ref_diff is None:
            logger.warning(
                "Reference diff is not available in the project bundle. The agents might not work as expected."
            )

        # Instantiate the agents
        logger.info("Instantiating SeedsGenForDiff...")

        weighted_models = {
            "claude-opus-4-20250514": 100,
            # "gemini-2.5-flash-preview-05-20": 100,
        }
        model = get_model_by_weights(weighted_models)

        gen = SeedsGenForDiff(
            model=model,
            project_bundle=project_bundle,
            harness_id=args.harness_id,
            timeout=1000,
        )

        final_result = await gen.run()

        print("\\n" + "=" * 30 + " FINAL RESULT " + "=" * 30)
        if final_result:
            print("Successfully generated fuzzer script:")
            # The result from DiffFuzzerGeneratorAgent is expected to be a string
            # containing the Python script within <script> tags.
            print(final_result)
        else:
            print("The agent pipeline did not produce a result.")
        print("=" * 74 + "\\n")

    except Exception as e:
        logger.error(f"An error occurred during agent execution: {e}")
        print("\\nTraceback:")
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
