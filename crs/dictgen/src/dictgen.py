import sys
import os
import json
import logging
import random
import asyncio

from utility.function_filter import extract_function_and_globals, shrink_context
from utility.workdir import Workdir
from utility.log import get_logger
from utility.java_util import *

from agents.ConstantExtractor import ConstantExtractor
from agents.DictAnalyzer import DictAnalyzer

from tests import *
from configs import *
from redis_client import *

from decimal import Decimal

from dataclasses import dataclass


# XXX: I'm skeptical about the following import. Without it, I
# encounter "RuntimeError: Event loop is closed". I have no idea why
# it occurs (possibly because AsyncOpenai?). Suppress it until I
# figure out the reason.
import nest_asyncio

nest_asyncio.apply()


@dataclass
class DictgenResult:
    dict: set
    input_token_cost: Decimal
    output_token_cost: Decimal


class DictionaryGenerator:
    def __init__(
        self,
        workdir: Workdir,
        prompt_configs: PromptConfig,
        model_config: ModelConfig,
        analysis_config: AnalysisConfig,
    ):
        self.model_config = model_config
        self.analysis_config = analysis_config
        self.prompt_configs = prompt_configs
        self.all_source_files = []
        self.workdir = workdir
        self.constant_map = {}
        self.result = {}
        self.output = (
            sys.stdout
            if analysis_config.output == "STDOUT"
            else open(analysis_config.output or self.workdir.get_output_file(), "w")
        )
        self.total_input_token_cost = Decimal(0)
        self.total_output_token_cost = Decimal(0)
        self.lock = asyncio.Lock()
        # RedisClient will handle non-existent redis url
        self.redis_client = RedisClient(
            os.environ.get("DICTGEN_REDIS_URL"), get_logger(workdir, "redis")
        )

        return

    def collect_source_files(self, exact_match):
        self.source_files_to_analyze = []
        COMMON_SOURCE_EXTENSIONS = {".java", ".c", ".cpp"}
        self.all_source_files = []
        for root, _, files in os.walk(self.analysis_config.repo):
            for file in files:
                _, ext = os.path.splitext(file)
                if ext.lower() in COMMON_SOURCE_EXTENSIONS:
                    self.all_source_files.append(os.path.join(root, file))

        for func in self.analysis_config.funcs:
            fnames = self.workdir.find_fname(func, exact_match)
            if not fnames:
                logging.debug(f"Function {func} not found in the index.")
                continue
            for fname in fnames:
                self.source_files_to_analyze.append((fname, func))
        if self.analysis_config.delta:
            self.source_files_to_analyze.append(
                (str(self.workdir.refdiff_path), "<diff>")
            )

    def get_name(self, file_path) -> str:
        return os.path.splitext(os.path.basename(file_path))[0]

    def preprocess_source_file(self) -> None:
        if self.workdir.language != "java":
            # TODO: support C
            return

        if self.analysis_config.inter_file_analysis_using_llm:
            # This is an outdated implementation from when we didn't
            # know what language we should support
            self.preprocess_source_file_with_llm()
        else:
            self.preprocess_source_file_static()

    def preprocess_source_file_with_llm(self) -> None:
        logging.warning("This is outdated, please use static analysis")
        constant_extractor = ConstantExtractor(
            self.prompt_configs.constant_extractor,
            self.model_config.model_name,
            self.model_config.url,
            self.model_config.key,
            self.model_config.timeout,
            self.model_config.temp,
        )
        for source_file, _ in self.source_files_to_analyze:
            if source_file in self.constant_map:
                continue
            if self.load_constant_map(source_file):
                continue
            self.constant_map[source_file] = constant_extractor.extract_constants(
                source_file
            )
            self.store_constant_map(source_file)

        logging.debug(f"constants: {json.dumps(self.constant_map, indent=4)}")

    def preprocess_source_file_static(self) -> None:
        def format_constants(raw_constants):
            if raw_constants is None:
                return None
            return {
                k: {"name": k, "expression": v, "value": v, "line": -1}
                for k, (v, _) in raw_constants.items()
            }

        fqn_to_path, package_to_classes = build_repo_metadata(self.workdir.repo_path)
        for source_file, func in self.source_files_to_analyze:
            if source_file in self.constant_map:
                continue
            if self.load_constant_map(source_file):
                continue
            if func == "<diff>":
                continue
            raw_constants = find_imported_constants_in_file(
                self.workdir.repo_path, source_file, fqn_to_path, package_to_classes
            )
            self.constant_map[source_file] = format_constants(raw_constants)
            self.store_constant_map(source_file)
        logging.debug(f"constants: {json.dumps(self.constant_map, indent=4)}")

    def load_constant_map(self, source_file):
        if self.workdir.check_constant_map(source_file):
            self.constant_map[source_file] = self.workdir.load_constant_map(source_file)
            logging.debug(
                f"Loaded constant map for {source_file}: {json.dumps(self.constant_map[source_file], indent=4)}"
            )
            return True
        else:
            logging.debug(f"No constant map found for {source_file}")
            return False

    def store_constant_map(self, source_file):
        self.workdir.store_constant_map(self.constant_map[source_file], source_file)

    async def analyze_source_file(self, source_file, func0, count, sem):
        async with sem:
            func = Workdir.canonicalize_function_name(func0)
            source_code = extract_function_and_globals(source_file, func)
            source_code = shrink_context(
                self.model_config.model_name, source_file, source_code, func
            )
            delta = func == "<diff>"
            DictEngine = DictAnalyzer(
                self.workdir,
                self.analysis_config.repo,
                source_file,
                source_code,
                func,
                self.constant_map,
                self.model_config,
                self.prompt_configs,
                self.analysis_config,
                self.redis_client,
                self.model_config.calculate_token_cost,
                delta,
                self.workdir.diff if self.workdir.diff else None,
            )

            DictEngine.logger.debug(
                f"Start to analyze ({count}/{len(self.source_files_to_analyze)})"
            )
            DictEngine.logger.debug(f"{func} in {source_file}")
            tokens = await DictEngine.analyze()
            if func in self.workdir.funcs_in_diff:
                self.workdir.write_tokens_from_diff(func, tokens)

            await self.merge_tokens(source_file, func, tokens)
            await self.accumulate_token_cost(DictEngine)

    async def analyze_source_files(self) -> set:
        sem = asyncio.Semaphore(self.analysis_config.num_analysis)
        tasks = [
            self.analyze_source_file(source_file, func, count, sem)
            for count, (source_file, func) in enumerate(self.source_files_to_analyze)
        ]
        await asyncio.gather(*tasks)
        return self.generate_dictionary()

    async def merge_tokens(self, source_file: str, func: str, tokens: dict) -> None:
        async with self.lock:
            if " - " in func:
                name, vuln = func.split(" - ", 1)
            else:
                name, vuln = func, None

            if vuln:
                self.result.setdefault(source_file, {}).setdefault(vuln, {}).update(
                    tokens
                )
                # Check if the tokens for this vulnerability exceed 3, and trim if necessary
                THRESHOLD_TABLE = {
                    "xpath injection": 2,
                    "default": 3,
                }
                threshold = THRESHOLD_TABLE.get(
                    vuln.lower(), THRESHOLD_TABLE["default"]
                )
                if len(self.result[source_file][vuln]) > threshold:
                    self.result[source_file][vuln] = self.result[source_file][vuln][
                        :threshold
                    ]
            else:
                self.result.setdefault(source_file, {}).setdefault(name, {}).update(
                    tokens
                )

            logging.debug(
                f"tokens for {func} in {source_file}: {json.dumps(tokens, indent=4)}"
            )

    async def accumulate_token_cost(self, DictEngine) -> None:
        async with self.lock:
            for name, agent in DictEngine.agents.items():
                logging.debug(
                    f"Input token cost for {name} is {agent.total_input_token_cost}"
                )
                self.total_input_token_cost += agent.total_input_token_cost
                logging.debug(
                    f"Output token cost for {name} is {agent.total_output_token_cost}"
                )
                self.total_output_token_cost += agent.total_output_token_cost

    def report_cost(self):
        logging.info(f"Total input token cost: {self.total_input_token_cost}")
        logging.info(f"Total output token cost: {self.total_output_token_cost}")
        self.workdir.write_cost(
            self.total_input_token_cost,
            self.total_output_token_cost,
            self.model_config.model_name,
        )

    def generate_dictionary(self) -> set:
        self.dict = {}
        for _, functions in self.result.items():
            # Iterate over each function in the file
            for func, names in functions.items():
                self.generate_dictionary_for_function(func, names)

        logging.info(f"dictionary: {self.dict}")

        res = set()
        for category, tokens in self.dict.items():
            selected = (
                random.sample(list(tokens), 2)
                if category != "token" and len(tokens) >= 2
                else tokens
            )
            for token in selected:
                res.add(token)

        logging.debug(f"dict: {res}")
        for index, item in enumerate(res):
            self.output.write(f"str{index}={json.dumps(item)}\n")
        logging.info(f"dictionary has been written to {self.output}")
        return res

    def generate_dictionary_for_function(self, func: str, names: dict) -> None:
        _ = func
        for name, tokens in names.items():
            category = "token"
            if " - " in name:
                # Split the name to get the vulnerability type
                _, vuln_type = name.split(" - ", 1)
                category = vuln_type.lower()

            self.dict.setdefault(category, set()).update(tokens)

    def startBatchRun(self):
        self.collect_source_files(self.analysis_config.exact_match)
        if (
            self.analysis_config.enable_inter_file_analysis
            or self.workdir.need_inter_file_analysis()
        ):
            self.preprocess_source_file()
        dict = asyncio.run(self.analyze_source_files())
        return dict


def run_dictgen(args, path=None, funcs=None) -> DictgenResult:
    # If a specific path or funcs is provided, override the args.path
    # or args.funcs. This is used for testing.
    if path is not None:
        args.path = path
    if funcs is not None:
        args.funcs = funcs

    model_config, prompt_config, analysis_config = init_config(args)

    workdir = Workdir(
        args.workdir,
        analysis_config.repo,
        analysis_config.refdiff if analysis_config.refdiff else None,
    )

    analysis_config = reinit_analysis_config(analysis_config, workdir)

    generator = DictionaryGenerator(
        workdir,
        prompt_config,
        model_config,
        analysis_config,
    )
    dict = generator.startBatchRun()
    generator.report_cost()
    return DictgenResult(
        dict, generator.total_input_token_cost, generator.total_output_token_cost
    )


def main():
    get_logger(None)
    args = parse_arguments()
    if not args.test:
        run_dictgen(args)
    else:
        run_test(args)


if __name__ == "__main__":
    main()
