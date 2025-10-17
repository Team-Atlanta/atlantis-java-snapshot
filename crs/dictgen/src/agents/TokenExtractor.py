import asyncio
import ast
import logging
import ast
import re
from enum import Enum
from agents.BaseAgent import BaseAgent

from utility.llm import *


class TokenExtractor(BaseAgent):
    class TokenType(Enum):
        STRING = "String"
        INTEGER = "Integer"
        INVALID = "Invalid"

    def __init__(
        self,
        prompt_config_file_path,
        online_model_name: str,
        openai_url: str,
        openai_key: str,
        timeout: int,
        temp: float,
        logger: logging.Logger,
        calculate_token_cost: bool,
        replacement: dict,
        delimiter: str = "#",
        expand_token: bool = True,
        sanitize_token: bool = True,
        label: str | None = None,
        constant_map: dict | None = None,
        no_space: bool = False,
    ) -> None:
        super().__init__()
        self.calculate_token_cost = calculate_token_cost
        self.logger = logger
        self.logger.debug(f"Delimiter: {delimiter}")
        self.prompt_config_file_path = prompt_config_file_path
        self.openai_url = openai_url
        self.openai_key = openai_key
        replacement["<DELIMITER>"] = delimiter
        system_role, prompt = self.construct_general_prompt(
            self.prompt_config_file_path,
            replacement,
        )
        self.model = LLM(
            online_model_name,
            self.openai_url,
            self.openai_key,
            timeout,
            temp,
            self.calculate_token_cost,
            system_role,
        )
        self.prompt = prompt
        self.expand_token = expand_token
        self.sanitize_token = sanitize_token
        self.no_space = no_space
        self.label = label
        self.delimiter = delimiter
        self.constant_map = constant_map
        pass

    def is_token_simple(
        token: str | int, token_type: "TokenExtractor.TokenType", no_space: bool = False
    ) -> bool:
        if token_type == TokenExtractor.TokenType.STRING:
            token = str(token)
            if len(token) >= 3 and (token.startswith('"') and token.endswith('"')):
                token = token[1:-1]
            return len(token) == 0 or (no_space and token.find(" ") != -1)
        elif token_type == TokenExtractor.TokenType.INTEGER:
            token = int(token)
            return -0x10 < token and token < 0x10
        else:
            # Shouldn't happen, but just in case.
            return True

    def do_sanitize_token(self, token: str) -> "TokenExtractor.TokenType":
        # XXX: I assume that libafl prioritizes trivial values.
        TRIVIAL_TOKENS = {
            "0xFFFFFFFF",
            "0xFFFFFFFE",
            "0x7FFFFFFF",
            '"null"',
            '"NULL"',
        }
        if token == '"UNKNOWN"' or token in TRIVIAL_TOKENS or len(token) == 0:
            self.logger.debug(f"Token {token} is trivial.")
            return TokenExtractor.TokenType.INVALID
        try:
            # ast.literal_eval safely evaluates only literal structures
            value = ast.literal_eval(token)
        except (ValueError, SyntaxError):
            # If evaluation fails, the expression is not a valid literal.
            self.logger.debug(f"Could not evaluate token: {token}")
            return TokenExtractor.TokenType.INVALID
        if isinstance(value, str):
            return (
                TokenExtractor.TokenType.STRING
                if not TokenExtractor.is_token_simple(
                    value, TokenExtractor.TokenType.STRING, no_space=self.no_space
                )
                else TokenExtractor.TokenType.INVALID
            )
        elif isinstance(value, int):
            return (
                TokenExtractor.TokenType.INTEGER
                if not TokenExtractor.is_token_simple(
                    value, TokenExtractor.TokenType.INTEGER
                )
                else TokenExtractor.TokenType.INVALID
            )
        else:
            return TokenExtractor.TokenType.INVALID

    def do_expand_token(self, token_expr: str) -> str:
        MAX_TOKEN_LENGTH = 1024 * 1024
        try:
            node = ast.parse(token_expr, mode="eval")
            result = self._eval_node(node.body)
            if len(result) > MAX_TOKEN_LENGTH:
                result = result[:MAX_TOKEN_LENGTH]
            if isinstance(result, str):
                return f'"{result}"'
            return token_expr
        except Exception:
            return token_expr

    def _eval_node(self, node):
        if isinstance(node, ast.Constant):
            if isinstance(node.value, str):
                return node.value
            elif isinstance(node.value, int):
                return node.value
            else:
                raise ValueError(
                    "Unsupported constant type: only strings and integers are allowed"
                )
        elif isinstance(node, ast.BinOp):
            if isinstance(node.op, ast.Add):
                left = self._eval_node(node.left)
                right = self._eval_node(node.right)
                if isinstance(left, str) and isinstance(right, str):
                    return left + right
                else:
                    raise ValueError("Both operands must be strings for concatenation")
            elif isinstance(node.op, ast.Mult):
                left = self._eval_node(node.left)
                right = self._eval_node(node.right)
                if isinstance(left, str) and isinstance(right, int):
                    return left * right
                elif isinstance(left, int) and isinstance(right, str):
                    return left * right
                else:
                    raise ValueError(
                        "Multiplication must be between a string and an integer"
                    )
        else:
            raise ValueError("Unsupported expression")

    def parse_response(self, response):
        lines = response.splitlines()
        answers = []
        prev = ""
        for line in lines:
            if (
                line.strip().startswith("- Answer:")
                or line.strip().startswith("- **Answer**:")
            ) and not prev.strip().startswith("UNKNOWN"):
                answers.append(line)
            prev = line
        tokens = {}
        for answer in answers:
            try:
                token_part, sep, description_part = answer.partition(self.delimiter)
                if not sep:
                    token_part = answer
                token_part = token_part.replace("- **Answer**:", "- Answer:")
                token = token_part.split("- Answer:")[1].strip().strip("")
                token = self.do_expand_token(token) if self.expand_token else token
                token_typ = (
                    self.do_sanitize_token(token)
                    if self.sanitize_token
                    else TokenExtractor.TokenType.STRING
                )
                if token_typ == TokenExtractor.TokenType.INVALID:
                    continue
                elif token_typ == TokenExtractor.TokenType.STRING:
                    token = token.strip('"')
                description = (
                    description_part.strip().strip("`")
                    if not self.label
                    else self.label
                )
                tokens.setdefault(description, []).append(token)
            except ValueError:
                self.logger.warning(f"Could not parse line: {answer}")
        return tokens

    async def apply(self, source_content, prefix=""):
        message = prefix + self.prompt + "\n```\n" + source_content + "\n```\n"
        self.logger.debug(f"Message: {message}")
        response, input_token_cost, output_token_cost = await self.model.infer(message)
        self.total_input_token_cost += input_token_cost
        self.total_output_token_cost += output_token_cost
        self.logger.debug(f"Response: {response}")
        return self.parse_response(response)

    async def apply_repeatedly(self, source_content):
        def canonicalize(token):
            try:
                token_int = int(token, 0)
                return token_int
            except ValueError:
                return token

        REPEAT_COUNT = 2
        tasks = []
        for i in range(REPEAT_COUNT):
            task = asyncio.create_task(
                self.apply(
                    source_content, f"Attempt {i+1} to filter out flaky tokens:\n"
                )
            )
            tasks.append(task)

        tokens0 = {}
        token_counts = {}
        results = await asyncio.gather(*tasks)
        for i, tokens in enumerate(results):
            if i == 0:
                tokens0 = tokens
            self.logger.debug(f"The {i+1}-th tokens: {tokens}")

            for key, token_list in list(tokens.items()):
                for token in token_list:
                    token0 = canonicalize(token)
                    token_counts[token0] = token_counts.get(token0, 0) + 1

        for key, token_list in list(tokens0.items()):
            for token in token_list[:]:
                if token_counts[canonicalize(token)] < (REPEAT_COUNT + 1) / 2:
                    token_list.remove(token)
                    self.logger.debug(f"Removed {token} from {key}")
            if not token_list:
                del tokens0[key]

        return tokens0

    import re

    def augmenting_constant_map(self, source_content: str, constant_map: dict) -> str:
        if not constant_map:
            return source_content

        import_pattern = re.compile(r"^\s*import\s+[\w\.]+\s*;\s*$")
        last_import_idx = -1
        for idx, line in enumerate(source_content):
            if import_pattern.match(line):
                last_import_idx = idx

        if last_import_idx == -1:
            return source_content

        decl_lines = []
        for fn, consts in constant_map.items():
            if not consts:
                continue
            for k in consts:
                const = consts[k]
                name = const.get("name")
                exp = const.get("expression")
                if not name or not exp:
                    self.logger.warning(
                        f"Skipping constant {const} due to missing name or expression."
                    )
                    continue
                decl_lines.append(f"public static final {name} = {exp};\n")

        if len(decl_lines) == 0:
            return source_content

        insert_pos = last_import_idx + 1
        new_lines = (
            source_content[:insert_pos]
            + ["\n"]
            + decl_lines
            + source_content[insert_pos:]
        )
        return new_lines

    async def extract_tokens(
        self, source_content, source_file, func, filter_flaky_tokens
    ):
        self.logger.debug(f"Extracting tokensfrom {func} in {source_file}")
        source_content = self.augmenting_constant_map(source_content, self.constant_map)
        numbered_content = self.annotating_line_numbers(source_content)
        if filter_flaky_tokens:
            tokens = await self.apply_repeatedly(numbered_content)
        else:
            tokens = await self.apply(numbered_content)

        self.logger.debug(f"Tokens: {tokens}")
        return tokens
