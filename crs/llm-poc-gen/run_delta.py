import asyncio
import logging
import os
from argparse import ArgumentParser
from pathlib import Path
from typing import Optional

import coloredlogs
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from vuli.blackboard import Blackboard
from vuli.common.setting import Setting
from vuli.cp import CP
from vuli.delta import DeltaManager, LLMDeltaHandler, SinkManagerDeltaHandler
from vuli.dev import Dev
from vuli.joern import Joern
from vuli.model_manager import ModelManager
from vuli.runner import Runner


class Delta(Runner):
    def __init__(self):
        self._logger = logging.getLogger("Delta")

    async def run(self) -> None:
        try:
            self._initialize_joern()
            self._scan()
            self._update_from_delta()
        finally:
            Joern().close_server()

    async def _run(self) -> None:
        pass


class UserConfiguration(BaseModel):
    cp_meta_file: Path
    joern_dir: Path
    log_level: str
    model_cache_file: Optional[Path]
    output_dir: Path


def handle_command_line_option() -> UserConfiguration:
    parser = ArgumentParser(description="llm-poc-gen delta")
    parser.add_argument(
        "--cp_meta",
        required=True,
        type=str,
        help="CP metadata file (required)",
    )
    parser.add_argument(
        "--joern_dir",
        required=True,
        type=str,
        help="The path to the Joern directory",
    )
    parser.add_argument(
        "--log_level",
        choices=["DEBUG", "INFO", "WARN", "ERROR"],
        default="INFO",
        type=str,
        help="Log Level[DEBUG/INFO/WARN/ERROR](default: INFO)",
    )
    parser.add_argument(
        "--model_cache", type=str, help="The path to cache for model interaction"
    )
    parser.add_argument(
        "--output_dir",
        default=str(Path("output").absolute()),
        type=str,
        help="The path to the output directory",
    )
    args = parser.parse_args()
    return UserConfiguration(
        cp_meta_file=Path(args.cp_meta),
        joern_dir=Path(args.joern_dir),
        log_level=args.log_level,
        model_cache_file=Path(args.model_cache) if args.model_cache else None,
        output_dir=Path(args.output_dir),
    )


def initialize_logger(log_level: str) -> None:
    level = getattr(logging, log_level, None)
    if level is None:
        level = logging.INFO

    logging.basicConfig(
        level=level,
        format="[%(asctime)s] [%(name)s] (%(levelname)s) %(message)s",
        handlers=[logging.StreamHandler()],
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    coloredlogs.install(
        level=log_level, fmt="[%(asctime)s] [%(name)s] (%(levelname)s) %(message)s"
    )
    logging.getLogger("anthropic._base_client").setLevel(logging.CRITICAL)
    logging.getLogger("asyncio").setLevel(logging.CRITICAL)
    logging.getLogger("openai._base_client").setLevel(logging.CRITICAL)
    logging.getLogger("httpcore.connection").setLevel(logging.CRITICAL)
    logging.getLogger("httpcore.http11").setLevel(logging.CRITICAL)
    logging.getLogger("httpx").setLevel(logging.CRITICAL)
    logging.getLogger("urllib3.connection").setLevel(logging.CRITICAL)
    logging.getLogger("urllib3.connectionpool").setLevel(logging.CRITICAL)


def initialize_system(user_config: UserConfiguration):
    root_dir: Path = Path(__file__).parent.absolute()

    Setting().load(
        Path(__file__).absolute(),
        user_config.joern_dir,
        user_config.output_dir,
        root_dir,
        False,
    )
    Blackboard().set_path(Setting().blackboard_path)
    CP().load(user_config.cp_meta_file, [])
    api_key: str = os.getenv("LITELLM_KEY", "tmp")
    base_url: str = os.getenv(
        "AIXCC_LITELLM_HOSTNAME",
        "https://litellm-proxy-153298433405.us-east1.run.app",
    )
    temperature: float = 1.0
    if user_config.model_cache_file:
        ModelManager().set_cache(user_config.model_cache_file)
    ModelManager().set_max_retries(3)
    ModelManager().set_worker(1)
    ModelManager().add_model(
        lambda input, output: input * 0.0000025 + output * 0.00001,
        "gpt-4o",
        ChatOpenAI(
            api_key=api_key, base_url=base_url, model="gpt-4o", temperature=temperature
        ),
    )
    ModelManager().add_model(
        lambda input, output: input * 0.000003 + output * 0.000015,
        "claude-3.7-sonnet",
        ChatAnthropic(
            api_key=api_key,
            base_url=base_url,
            model="claude-3-7-sonnet-20250219",
            temperature=temperature,
            max_tokens=12800,
        ),
    )
    ModelManager().add_model(
        lambda input, output: (
            input * 0.00000125 + output * 0.000005
            if input > 128000
            else input * 0.0000025 + output * 0.00001
        ),
        "gemini-1.5-pro",
        ChatOpenAI(
            api_key=api_key,
            base_url=base_url,
            model="gemini-1.5-pro",
            temperature=temperature,
        ),
    )

    DeltaManager().add(SinkManagerDeltaHandler(), LLMDeltaHandler())

    if Setting().dev is True:
        Dev().load(Setting().root_dir / "dev" / "cpv.toml")


def main():
    user_config = handle_command_line_option()
    initialize_logger(user_config.log_level)
    initialize_system(user_config)
    asyncio.run(Delta().run())


if __name__ == "__main__":
    main()
