import asyncio
import re
from agents.TokenExtractor import TokenExtractor
from agents.TriggerVerifier import TriggerVerifier
from agents.ParsingFunctionDetector import ParsingFunctionDetector
from configs import *
from utility import log
from collections import Counter


class DictAnalyzer:
    def __init__(
        self,
        workdir,
        analysis_repo,
        source_file,
        source_code,
        func,
        constant_map,
        model_config,
        prompt_config,
        analysis_config,
        redis_client,
        calculate_token_cost,
        delta_mode,
        diff,
    ):
        self.analysis_repo = analysis_repo
        self.source_file = source_file
        self.source_code = source_code
        self.func = func

        self.constant_map = constant_map
        self.model_config = model_config

        self.analysis_config = analysis_config
        self.logger = log.get_logger(workdir, func)

        self.redis_client = redis_client
        self.calculate_token_cost = calculate_token_cost
        self.delta_mode = delta_mode
        self.diff = workdir.diff

        self.__init_agents(prompt_config)

    def __init_agents(self, prompt_config):
        common_replacement = {
            "<FUNCTION_NAME>": self.func,
            "<FILE_NAME>": self.source_file,
        }

        def make_agent(cls, prompt, **kwargs):
            return cls(
                prompt,
                self.model_config.model_name,
                self.model_config.url,
                self.model_config.key,
                self.model_config.timeout,
                self.model_config.temp,
                self.logger,
                self.calculate_token_cost,
                common_replacement,
                **kwargs,
            )

        self.agents = {
            "token_extractor": make_agent(
                TokenExtractor,
                prompt_config.token_extractor,
                constant_map=self.constant_map,
            ),
            "diff_mode_analyzer": make_agent(
                TokenExtractor,
                prompt_config.diff_token_extractor,
                constant_map=self.constant_map,
                no_space=True,
            ),
            "trigger_extractor": make_agent(
                TokenExtractor,
                prompt_config.trigger_extractor,
            ),
            "trigger_verifier": make_agent(
                TriggerVerifier, prompt_config.trigger_verifier
            ),
            # For the majority voting
            "parsing_function_detector": make_agent(
                ParsingFunctionDetector, prompt_config.parsing_function_detector
            ),
            "parsing_function_detector_second": make_agent(
                ParsingFunctionDetector, prompt_config.parsing_function_detector
            ),
            "parsable_string_extractor": make_agent(
                TokenExtractor,
                prompt_config.parsable_string_extractor,
                expand_token=False,
                sanitize_token=False,
                delimiter="<#>",
                label="parsable_string",
            ),
        }

    async def analyze(self):
        results = await asyncio.gather(
            self.analyze_tokens(),
            self.analyze_triggers(),
            self.analyze_parsable_string(),
        )

        tokens = {}
        for _tokens in results:
            for key, value in _tokens.items():
                tokens.setdefault(key, []).extend(value)

        return tokens

    def retrieve_tokens_from_redis(self, typ, source_file, func):
        if self.redis_client is None:
            return None
        tokens = self.redis_client.get(typ, source_file, func)
        if tokens is None:
            return None
        self.logger.debug(
            f"Retrieved {len(tokens)} tokens from Redis for {typ} in {source_file} - {func}"
        )
        return tokens

    def store_tokens_to_redis(self, typ, source_file, func, tokens):
        if self.redis_client is None:
            return None
        self.logger.debug(
            f"Storing {len(tokens)} tokens to Redis for {typ} in {source_file} - {func}"
        )
        return self.redis_client.set(typ, source_file, func, tokens)

    async def analyze_tokens(self):
        if not self.analysis_config.extract_token:
            return {}

        if not self.delta_mode:
            return await self.analyze_tokens_full_mode()
        else:
            return await self.analyze_tokens_delta_mode()

    async def analyze_tokens_full_mode(self):
        results = self.retrieve_tokens_from_redis("tokens", self.source_file, self.func)
        if results is not None:
            return results

        tokens = await self.agents["token_extractor"].extract_tokens(
            self.source_code,
            self.source_file,
            self.func,
            self.analysis_config.filter_flaky_tokens,
        )
        self.store_tokens_to_redis("tokens", self.source_file, self.func, tokens)
        return tokens

    def iter_hunks(self, diff_text: str):
        def _is_valid_extension(file_path: str) -> bool:
            # Check if the file has a valid extension
            valid_extensions = {".c", ".java", ".h", ".cpp", ".inc", ".pm"}
            return any(file_path.endswith(ext) for ext in valid_extensions)

        header = None
        body: List[str] = []
        current_file = None
        file_regex = re.compile(r"^\+\+\+ b/(.*)")

        lines = diff_text.splitlines()
        for line in lines:
            if line.startswith("+++"):
                match = file_regex.match(line)
                if match:
                    current_file = match.group(1)
            if line.startswith("@@"):
                if (
                    header is not None
                    and current_file
                    and _is_valid_extension(current_file)
                ):
                    yield header, body
                header = line
                body = [header]
            elif header is not None:
                if line.startswith((" ", "+", "-", "\\")):
                    body.append(line)

        if header is not None and current_file and _is_valid_extension(current_file):
            yield header, body

    async def analyze_tokens_delta_mode(self):
        results = self.retrieve_tokens_from_redis(
            "tokens_delta", self.source_file, self.func
        )
        if results is not None:
            return results

        tokens = {}

        for idx, (hdr, lines) in enumerate(self.iter_hunks(self.diff), start=1):
            tokens0 = (
                await self.agents["diff_mode_analyzer"].extract_tokens(
                    lines, self.source_file, self.func, False
                )
                if self.diff
                else {}
            )
            for key, value in tokens0.items():
                if key not in tokens:
                    tokens[key] = []
                tokens[key].extend(value)
        self.store_tokens_to_redis("tokens_delta", self.source_file, self.func, tokens)
        return tokens

    async def analyze_triggers(self):
        if not self.analysis_config.extract_trigger or self.delta_mode:
            return {}

        results = self.retrieve_tokens_from_redis(
            "triggers", self.source_file, self.func
        )
        if results is not None:
            return results

        triggers = await self.agents["trigger_extractor"].extract_tokens(
            self.source_code,
            self.source_file,
            self.func,
            # Do not use self.filter_flaky_tokens here
            False,
        )
        if self.analysis_config.verify_trigger:
            triggers = await self.agents["trigger_verifier"].verify(
                self.source_code, self.source_file, self.func, triggers
            )
        self.store_tokens_to_redis("triggers", self.source_file, self.func, triggers)
        return triggers

    async def analyze_parsable_string(self):
        if not self.analysis_config.extract_parsable_string:
            return {}

        results = self.retrieve_tokens_from_redis(
            "parsable_string", self.source_file, self.func
        )
        if results is not None:
            return results

        is_parsing_function = await self.detect_parsing_function()

        if not is_parsing_function:
            return {}

        tokens = await self.agents["parsable_string_extractor"].extract_tokens(
            self.source_code,
            self.source_file,
            self.func,
            False,
        )
        self.store_tokens_to_redis(
            "parsable_string", self.source_file, self.func, tokens
        )
        return tokens

    async def detect_parsing_function(self):
        results = await asyncio.gather(
            self.agents["parsing_function_detector"].detect_parsing_function(
                self.source_code
            ),
            self.agents["parsing_function_detector_second"].detect_parsing_function(
                self.source_code
            ),
        )

        result_counts = Counter(results)
        majority_result = result_counts.most_common(1)[0][0]
        return majority_result
