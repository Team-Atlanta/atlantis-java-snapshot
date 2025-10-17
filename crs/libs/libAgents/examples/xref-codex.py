#! /usr/bin/env python3
import argparse
import asyncio
import logging
import os
from pathlib import Path

from libAgents.agents import DeepSearchAgent
from libAgents.plugins import AnswerPlugin, AskCodebasePlugin, ReflectPlugin

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logging.getLogger("libAgents").setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)


def expand_path(path: str) -> Path:
    """Expand user path (with ~) to absolute path."""
    return Path(os.path.expanduser(path))


def main():
    print("[!] This example hardcoded a local nginx source code repository.\n")
    print(
        f">> uv run {__file__} --src-repo=./cloned-repos/aixcc/c/asc-nginx --query 'What functions call ngx_decode_base64 in nginx?'\n"
    )
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Deep Research Query Tool")
    parser.add_argument(
        "--query",
        type=str,
        help="The question you want to ask",
        default="What functions call ngx_decode_base64 in nginx?",
    )
    parser.add_argument(
        "--src-repo",
        type=str,  # Changed from Path to str to handle ~ expansion
        help="The path to the source repository",
        default=Path("./cloned-repos/aixcc/c/asc-nginx").resolve(),
    )

    args = parser.parse_args()

    src_repo_path = expand_path(args.src_repo)
    if not src_repo_path.exists():
        logger.error(f"Source repository path does not exist: {src_repo_path}")
        return

    plugins = [
        AnswerPlugin(),
        ReflectPlugin(),
        AskCodebasePlugin(
            project_name="nginx",
            src_path=src_repo_path,
        ),
    ]

    agent = DeepSearchAgent(plugins=plugins)
    res = asyncio.run(agent.query(args.query))
    print(res)


if __name__ == "__main__":
    main()
