import os
import argparse
import logging
from pathlib import Path
from typing import Tuple

from tests import AllTests, BasicTests

from dataclasses import dataclass


@dataclass
class ModelConfig:
    model_name: str
    url: str
    key: str
    timeout: int
    temp: float
    calculate_token_cost: bool


@dataclass
class PromptConfig:
    constant_extractor: str
    token_extractor: str
    diff_token_extractor: str
    trigger_extractor: str
    trigger_verifier: str
    parsing_function_detector: str
    parsable_string_extractor: str


@dataclass
class AnalysisConfig:
    repo: Path
    delta: bool
    refdiff: Path
    keep_arg_funcs: bool
    funcs: list
    extract_token: bool
    filter_flaky_tokens: bool
    extract_trigger: bool
    verify_trigger: bool
    extract_parsable_string: bool
    exact_match: bool
    num_analysis: int
    enable_inter_file_analysis: bool
    inter_file_analysis_using_llm: bool
    output: str


def get_model_name(name):
    if name == "gemini-1.5":
        return "gemini-1.5-flash"
    elif name == "claude-3-5-sonnet":
        return "claude-3-5-sonnet-20241022"
    elif name == "claude-3-5-opus":
        return "claude-3-5-opus"
    elif name == "claude-3-5-haiku":
        return "claude-3-5-haiku-20241022"
    else:
        return name


def get_path(args):
    if not args.path:
        raise ValueError("Path is not provided.")

    return Path(args.path)


def get_funcs(args):
    if not args.funcs and not args.delta:
        raise ValueError("Functions are not provided.")
    return args.funcs if args.funcs else []


def init_config(args) -> Tuple[ModelConfig, PromptConfig, AnalysisConfig]:
    return (
        ModelConfig(
            get_model_name(args.model_name),
            str(os.environ.get("LITELLM_URL")),
            str(os.environ.get("LITELLM_KEY")).split(":")[0],
            args.timeout,
            args.temp,
            args.calculate_token_cost,
        ),
        PromptConfig(
            "constant_extractor.json",
            "token_extractor.json",
            "diff_token_extractor.json",
            "trigger_extractor.json",
            "trigger_verifier.json",
            "parsing_function_detector.json",
            "parsable_string_extractor.json",
        ),
        AnalysisConfig(
            get_path(args),
            args.delta,
            Path(args.refdiff).resolve() if args.refdiff else None,
            args.keep_arg_funcs,
            get_funcs(args),
            args.extract_token,
            args.filter_flaky_tokens,
            args.extract_trigger,
            args.verify_trigger,
            args.extract_parsable_string,
            args.exact_match,
            args.num_analysis,
            args.enable_inter_file_analysis,
            args.inter_file_analysis_using_llm,
            args.output,
        ),
    )


def reinit_analysis_config(analysis_config: AnalysisConfig, workdir) -> AnalysisConfig:
    if not analysis_config.delta:
        return analysis_config

    analysis_config.repo = workdir.get_repo()

    funcs_from_refdiff = workdir.extract_functions_in_ref_diff()
    if not analysis_config.keep_arg_funcs and funcs_from_refdiff:
        analysis_config.funcs.clear()
    analysis_config.funcs.extend(funcs_from_refdiff)
    return analysis_config


def add_model_arguments(parser):
    models = [
        "gpt-4o",
        "o1",
        "gemini-1.5",
        "claude-3-5-sonnet",
        "claude-3-5-opus",
        "claude-3-5-haiku",
    ]
    parser.add_argument(
        "--model-name",
        choices=models,
        default="gpt-4o",
        help="The model name to use for analysis.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Timeout value of a single inference in seconds.",
    )
    parser.add_argument(
        "--temp",
        type=float,
        default=0,
        help="Temperature value.",
    )
    parser.add_argument(
        "--calculate-token-cost",
        default=False,
        action="store_true",
        help="Calculate token cost for the inference.",
    )


def add_mutually_exclusive_group(parser, name, dest, help, default=True):
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        f"--{name}",
        dest=dest,
        action="store_true",
        help=f"Enable {help}.",
    )
    group.add_argument(
        f"--no-{name}",
        dest=dest,
        action="store_false",
        help=f"Disable {help}.",
    )
    parser.set_defaults(**{dest: default})


def add_analysis_arguments(parser):
    parser.add_argument(
        "--path",
        type=str,
        help="Path of a repository or a file to analyze.",
    )
    parser.add_argument(
        "--workdir",
        type=str,
        help="Working directory to store the analysis results.",
    )
    add_mutually_exclusive_group(
        parser,
        "extract-token",
        "extract_token",
        "Extract tokens from source code",
        True,
    )
    add_mutually_exclusive_group(
        parser,
        "extract-trigger",
        "extract_trigger",
        "Extract trigger from source code",
        True,
    )
    add_mutually_exclusive_group(
        parser,
        "extract-parsable-string",
        "extract_parsable_string",
        "Extract parsable strings from source code",
        True,
    )
    add_mutually_exclusive_group(
        parser,
        "verify-trigger",
        "verify_trigger",
        "verification of triggers for vulnerabilities",
        True,
    )
    add_mutually_exclusive_group(
        parser, "exact-match", "exact_match", "exact match for function names", False
    )
    add_mutually_exclusive_group(
        parser,
        "filter-flaky-tokens",
        "filter_flaky_tokens",
        "filter flaky tokens",
        True,
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output file to store the results",
    )
    parser.add_argument(
        "--num-analysis",
        type=int,
        default=5,
        help="Number of functions to analyze concurrently",
    )
    parser.add_argument(
        "--delta",
        default=False,
        action="store_true",
    )
    parser.add_argument(
        "--refdiff",
        type=str,
        help="Path to the reference diff file.",
    )
    parser.add_argument(
        "--keep-arg-funcs",
        default=False,
        action="store_true",
        help="Keep argument functions in the analysis.",
    )
    parser.add_argument(
        "--enable-inter-file-analysis",
        default=False,
        action="store_true",
        help="Enable inter-file analysis.",
    )
    parser.add_argument(
        "--inter-file-analysis-using-llm",
        default=False,
        action="store_true",
        help="Enable inter-file analysis using LLM.",
    )


def add_test_arguments(parser):
    test_names = list(BasicTests.keys()) + AllTests
    parser.add_argument("--test", type=str, choices=test_names, help="Name of a test")

    parser.add_argument(
        "--funcs",
        type=lambda x: x.split(","),
        help="Functions separated by comma to analyze. It is assumed that functions were called in order.",
    )

    parser.add_argument(
        "--test-dict",
        type=str,
        help="Path to the test directory for a oss-fuzz project.",
    )

    parser.add_argument(
        "--test-threads",
        type=int,
        default=1,
        help="Number of threads to use when running tests. Maximum is 5.",
    )

    add_mutually_exclusive_group(
        parser,
        "retry-test-on-failure",
        "retry_test_on_failure",
        "retry-test-on-failure",
        True,
    )


def validate_args(parser, args):
    if args.test_threads > 5:
        parser.error("The number of test threads cannot exceed 5.")

    if args.delta and not args.refdiff:
        parser.error("Delta mode requires a reference diff file.")

    if args.delta:
        args.extract_trigger = False
        args.extract_parsable_string = True


def parse_arguments():
    parser = argparse.ArgumentParser(description="Generate dictionary.")
    add_model_arguments(parser)
    add_analysis_arguments(parser)
    add_test_arguments(parser)

    args = parser.parse_args()
    validate_args(parser, args)
    logging.info(f"Arguments: {args}")
    return args
