import argparse
import asyncio
import logging
import sys
import subprocess
import yaml
from pathlib import Path
from typing import Set, Tuple, Dict, List

from libAgents.agents import HarnessFormatAnalyzerAgent, CorpusMatcherAgent
from libAgents.agents.corpus_relevance_agent import analyze_corpus_relevance, fast_analyze_corpus_relevance
from libAgents.utils import Project

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Enable debug logging for deep agent components
logging.getLogger("libAgents.agents.deep_search_agent").setLevel(logging.DEBUG)
logging.getLogger("libAgents.agents.deep_think_agent").setLevel(logging.DEBUG)
logging.getLogger("libAgents.session").setLevel(logging.DEBUG)

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

def extract_categories_from_directory(categories_dir: Path) -> list[str]:
    """Extract category names from the categories directory structure."""
    category_names = []
    if not categories_dir.exists():
        logger.error(f"Categories directory not found: {categories_dir}")
        return category_names
    
    for item in categories_dir.iterdir():
        if item.is_dir():
            # Each subdirectory is a category
            category_names.append(item.name)
    
    return sorted(category_names)

def parse_arguments():
    parser = argparse.ArgumentParser(
        description="""
Analyze which corpus categories could be useful for a given repository.

Required Directory Structure:
    libAgents/
    ├── oss-fuzz/                  # OSS-Fuzz repository (required)
    ├── workdir/                   # Created automatically
    ├── cloned-repos/             # Created automatically
    └── examples/
        └── corpus_relevance.py   # This script

Setup Steps:
1. Clone OSS-Fuzz:
   cd libAgents
   git clone https://github.com/google/oss-fuzz.git

2. Run the script:
   python corpus_relevance.py --project <project_name> --categories_dir <path_to_categories> --mode <mode>

The script will automatically:
- Clone the project repository if needed
- Extract available categories from the categories directory
- Perform analysis based on selected mode

Categories Directory Structure:
    categories/
    ├── archive-format/
    │   ├── corpus/
    │   │   └── archive-format.tar.zst
    │   └── dictionaries/
    │       ├── libzip_zip_read_file_fuzzer.dict
    │       └── ...
    └── sql/
        ├── corpus/
        │   └── sql.tar.zst
        └── dictionaries/
            ├── mysql-server_burmesedict.dict
            └── ...

Analysis Modes:
- llm: Use LLM-based corpus relevance analysis (returns categories, default)
- fast_llm: Use fast LLM backup mode

Backup Options:
- --use_backup_format_analyzer: Use faster backup mode for format analysis
- --use_backup_corpus_matcher: Use faster backup mode for corpus matching
- These options can be used independently to mix normal and backup modes

Examples:
  # Use normal mode (default)
  python corpus_relevance.py --project openssl --categories_dir /path/to/categories --mode llm
  
  # Use backup mode for both agents
  python corpus_relevance.py --project openssl --categories_dir /path/to/categories --mode llm --use_backup_format_analyzer --use_backup_corpus_matcher
  
  # Use backup mode only for format analyzer
  python corpus_relevance.py --project openssl --categories_dir /path/to/categories --mode llm --use_backup_format_analyzer
  
  # Use fast LLM mode
  python corpus_relevance.py --project openssl --categories_dir /path/to/categories --mode fast_llm
"""
    )
    parser.add_argument(
        "--project",
        type=str,
        required=True,
        help="Project name as it appears in OSS-Fuzz (e.g., 'openssl', 'sqlite3')",
    )
    parser.add_argument(
        "--categories_dir",
        type=str,
        required=True,
        help="Directory containing corpus categories (e.g., large_data/osv_analyzer/fuzz-corpus/categories/)",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["llm", "fast_llm"],
        default="llm",
        help="Analysis mode: llm (LLM analysis only, default), fast_llm (fast LLM backup mode). Use --use_backup_format_analyzer and --use_backup_corpus_matcher to control which agents use backup mode.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode for agents (e.g., context saving)",
    )
    parser.add_argument(
        "--use_backup_format_analyzer",
        action="store_true",
        help="Use run_backup() for HarnessFormatAnalyzerAgent instead of run() (faster but less comprehensive analysis)",
    )
    parser.add_argument(
        "--use_backup_corpus_matcher",
        action="store_true",
        help="Use run_backup() for CorpusMatcherAgent instead of run() (faster but less comprehensive analysis)",
    )
    return parser.parse_args()

async def run_llm_analysis(project_bundle: Project, available_categories: list[str], model: str, use_backup_format_analyzer: bool = False, use_backup_corpus_matcher: bool = False) -> Dict[str, List[str]]:
    """Run LLM-based corpus relevance analysis."""
    logger.info("Running corpus relevance analysis...")
    
    if use_backup_format_analyzer:
        logger.info("Using backup mode for HarnessFormatAnalyzerAgent")
    if use_backup_corpus_matcher:
        logger.info("Using backup mode for CorpusMatcherAgent")
    
    try:
        # Run both format analysis and corpus matching
        format_analysis, corpus_matches = await analyze_corpus_relevance(
            model=model,
            project_bundle=project_bundle,
            available_categories=available_categories,
            cache_type="disk",
            cache_expire_time=1,
            use_backup_format_analyzer=use_backup_format_analyzer,
            use_backup_corpus_matcher=use_backup_corpus_matcher,
        )
        
        # Print format analysis results
        print("\n" + "=" * 30 + " HARNESS FORMAT ANALYSIS " + "=" * 30)
        if format_analysis:
            print("\nFormat Analysis Results:")
            for harness, data in format_analysis.get("harness_mappings", {}).items():
                print(f"\nHarness: {harness}")
                print(f"Input Formats: {', '.join(data.get('input_formats', []))}")
                print(f"Project Category: {data.get('project_category', 'Unknown')}")
                print(f"Format Requirements: {', '.join(data.get('format_requirements', []))}")
        else:
            print("No format analysis results available")
        print("=" * 74 + "\n")

        # Print corpus matching results
        print("\n" + "=" * 30 + " CORPUS MATCHING ANALYSIS " + "=" * 30)
        if corpus_matches:
            for harness, relevant_categories in corpus_matches.items():
                print(f"\nHarness: {harness}")
                if relevant_categories:
                    print("Relevant Corpus Categories:")
                    for category in relevant_categories:
                        print(f"  - {category}")
                else:
                    print("No relevant corpus categories found")
        else:
            print("No matching results available")
        print("=" * 74 + "\n")

        return corpus_matches

    except Exception as e:
        logger.error(f"Error during LLM analysis: {e}")
        print("\nError during LLM analysis. Please try again.")
        return {}

async def main():
    args = parse_arguments()

    # Set up working directories
    root_dir = Path(__file__).parent.parent
    workdir = root_dir / "workdir"
    workdir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Using working directory: {workdir.resolve()}")

    cloned_repos_dir = root_dir / "cloned-repos"
    cloned_repos_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Using cloned repositories base directory: {cloned_repos_dir.resolve()}")

    # Check for OSS-Fuzz home directory
    oss_fuzz_home = root_dir / "oss-fuzz"
    if not oss_fuzz_home.exists():
        logger.error(f"OSS-Fuzz home directory not found at: {oss_fuzz_home}")
        logger.error(
            "Please ensure OSS-Fuzz is cloned at the root of the libAgents workspace:\n"
            "cd libAgents\n"
            "git clone https://github.com/google/oss-fuzz.git"
        )
        sys.exit(1)

    # Validate OSS-Fuzz project exists
    project_yaml = oss_fuzz_home / "projects" / args.project / "project.yaml"
    if not project_yaml.exists():
        logger.error(f"Project {args.project} not found in OSS-Fuzz")
        logger.error(f"Expected project.yaml at: {project_yaml}")
        logger.error("Please ensure the project name matches exactly as it appears in OSS-Fuzz")
        sys.exit(1)

    try:
        # Get source directory for the project
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

        # Extract available categories from categories directory
        categories_dir = Path(args.categories_dir)
        if not categories_dir.exists():
            logger.error(f"Categories directory not found: {categories_dir}")
            sys.exit(1)

        available_categories = extract_categories_from_directory(categories_dir)
        logger.info(f"Found {len(available_categories)} available categories in categories directory")

        # Set up model
        # model = "o4-mini"
        # model = "gpt-4.1"
        model = "o3"
        model = "gemini-2.5-pro"

        # Run analyses based on mode
        llm_results = {}
        fast_llm_results = {}

        if args.mode == "llm":
            llm_results = await run_llm_analysis(
                project_bundle,
                available_categories,
                model,
                args.use_backup_format_analyzer,
                args.use_backup_corpus_matcher
            )

        if args.mode == "fast_llm":
            model = "gemini-2.5-pro"
            print("\n" + "=" * 30 + " FAST LLM CORPUS RELEVANCE " + "=" * 30)
            fast_format_analysis, fast_llm_results = await fast_analyze_corpus_relevance(
                model,
                args.project,
                available_categories,
            )
            print("\nFast LLM Format Analysis:")
            print(fast_format_analysis)
            print("\nFast LLM Corpus Matches:")
            print(fast_llm_results)
            print("=" * 74 + "\n")

    except Exception as e:
        logger.error(f"An error occurred during analysis: {e}")
        print("\nTraceback:")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main()) 
