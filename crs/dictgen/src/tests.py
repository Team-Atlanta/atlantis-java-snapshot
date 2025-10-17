import concurrent.futures
import logging
import json
import os
import re
import yaml
import copy
import io

from redis_client import *
from utility.log import get_logger
from utility.llm import InferenceException

from decimal import Decimal

from contextlib import redirect_stdout
from pathlib import Path

current_directory = Path(__file__).parent.resolve()
test_directory = (current_directory / ".." / "tests").resolve()
BasicTests = {
    "c": {
        "directory": test_directory / "c",
        "functions": ["foo"],
        "answers": {"42", "66", "67", "token", "token2"},
    },
    "java": {
        "directory": test_directory / "java",
        "functions": ["foo"],
        "answers": {"42", "66", "67", "token", "token2", "magic"},
    },
    "python": {
        "directory": test_directory / "python",
        "functions": ["foo"],
        "answers": {"0xbeaf", "token1", "token2", "token3"},
    },
    "go": {
        "directory": test_directory / "go",
        "functions": ["foo"],
        "answers": {"42", "43", "token", "token2", "token3", "t", "66", "67"},
    },
}

# NOTE: "all" and "all-strict" runs all enabled tests (ie, "basic" +
# "oss-fuzz"). "all" checks whether all necessary toknes are generated
# or not, and "all-strict" additionally checks whether there are too
# many false positives or not. "basic" runs all tests in BasicTests.

AllTests = [
    "all",
    "all-strict",
    "basic",
    "oss-fuzz",
    "oss-fuzz-all",
    "stdout",
    "runner-docker",
    "redis-in-docker",
]


def load_oss_fuzz_test(test_dict):
    json_file_path = test_dict
    if not os.path.isfile(json_file_path):
        raise FileNotFoundError(f"The file {json_file_path} does not exist.")

    with open(json_file_path, "r") as file:
        lines = [
            line.partition("#")[0].strip()
            for line in file
            if line.partition("#")[0].strip()
        ]
        content = "\n".join(lines)
        test_info = json.loads(content)

    return test_info


def load_test_info(args, test_name, oss_fuzz):
    if oss_fuzz:
        assert args.path, "Path is required for OSS-Fuzz tests."
        assert (
            not args.funcs
        ), "Functions will be automatically loaded for OSS-Fuzz tests."

        test_info = load_oss_fuzz_test(args.test_dict)
        test_info["directory"] = args.path
    else:
        test_info = BasicTests[test_name]

    for key in ("harness", "cpv"):
        if test_info.get(key):
            test_name = f"{test_name}-{test_info[key]}"
    test_info["name"] = test_name
    return test_info


def run_test(args):
    # Do not write the output to a file if it is a test
    args.output = "/dev/null"
    test_name = args.test

    # XXX: super ugly. don't use global
    global tests, total_input_token_cost, total_output_token_cost
    tests, total_input_token_cost, total_output_token_cost = [], Decimal(0), Decimal(0)

    test_functions = {
        "basic": run_basic_tests,
        "oss-fuzz": run_oss_fuzz_test,
        "oss-fuzz-all": run_oss_fuzz_test_all,
        "stdout": run_stdout_test,
        "runner-docker": run_test_in_runner_docker,
        "all": run_all_tests,
        "diff": run_diff_tests,
        "all-strict": run_all_tests,
        "redis-in-docker": run_redis_in_docker,
    }
    for t in BasicTests.keys():
        test_functions[t] = run_basic_tests

    if test_name in ["oss-fuzz-all", "all"] and not args.path:
        # If path is not given, use the submodules directory
        args.path = (current_directory / ".." / ".." / "benchmarks").resolve()

    if test_name in test_functions:
        test_functions[test_name](args, test_name == "all-strict")

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=args.test_threads
    ) as executor:
        futures = {executor.submit(test): test for test in tests}
        failed = False
        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()
            except Exception as e:
                logging.error(f"Test failed with exception: {e}")
                failed = True
        if failed:
            raise AssertionError("Test failed.")

    logging.info("All tests passed.")
    logging.info(f"Total input token cost: {total_input_token_cost}")
    logging.info(f"Total output token cost: {total_output_token_cost}")


def run_basic_tests(args, strict=False):
    # basic tests do not run projects in oss-fuzz
    test_names = BasicTests.keys() if args.test == "basic" else [args.test]
    for test_name in test_names:
        test_info = load_test_info(args, test_name=test_name, oss_fuzz=False)
        do_run_test(
            args,
            test_info,
            strict,
        )


def run_oss_fuzz_test_all(args, strict=False):
    __run_oss_fuzz_test_all(args, strict)


def __run_oss_fuzz_test_all(args, strict=False, diff_only=False):
    # step1: collect projects that have test_info.json
    test_infos = []
    for root, _, files in os.walk(os.path.join(args.path, "projects", "aixcc")):
        for file in files:
            if file.startswith("test_info.json"):
                path = os.path.join(root, file)
                path = Path(path)
                if diff_only:
                    with open(path, "r") as f:
                        try:
                            test_info = json.load(f)
                            if test_info.get("diff") == True:
                                test_infos.append(path)
                        except json.JSONDecodeError:
                            logging.warning(f"Could not decode JSON from {path}")
                else:
                    test_infos.append(path)

    for test_info in test_infos:
        args0 = copy.copy(args)
        args0.test_dict = str(test_info)
        run_oss_fuzz_test(args0, strict)


def run_diff_tests(args, strict=False):
    __run_oss_fuzz_test_all(args, strict, True)


def run_stdout_test(args, strict=False):
    args.output = "STDOUT"
    test_name = "c"
    test_info = load_test_info(args, test_name=test_name, oss_fuzz=False)
    do_run_test(
        args,
        test_info,
        strict,
        stdout=True,
    )


def run_oss_fuzz_test(args, strict=False):
    assert args.workdir or os.environ.get(
        "WORKDIR"
    ), "WORKDIR is required for OSS-Fuzz tests."
    workdir = str(args.workdir or os.environ.get("WORKDIR"))
    assert args.test_dict

    project, test_info_path = None, Path(args.test_dict)
    for parent in test_info_path.parents:
        if parent.name == ".aixcc":
            project_path = parent.parent
            project = project_path
            logging.info(f"Found test {project_path}, {test_info_path.name}")
    assert project, f"Failed to find project for {test_info_path}"

    yaml_path = os.path.join(project, "project.yaml")
    main_repo = None
    try:
        with open(yaml_path, "r") as file:
            main_repo = yaml.safe_load(file).get("main_repo")
    except Exception as e:
        logging.error(f"Failed to load {yaml_path}: {e}")
        return

    clone_dir = os.path.join(workdir, "dictgen", "oss-fuzz", project.name)
    if not os.path.exists(clone_dir):
        os.system(f"git clone {main_repo} {clone_dir}")
    if not os.path.exists(clone_dir):
        logging.error(f"Failed to clone {main_repo} to {clone_dir}")
        return

    args.path = clone_dir
    match = re.search(r"/projects/aixcc/([^/]+/[^/]+)/", args.test_dict)
    test_name = match.group(1) if match else None
    assert test_name is not None, "Failed to extract project name from path."
    test_info = load_test_info(args, test_name=test_name, oss_fuzz=True)

    if "diff" in test_info:
        args.delta = True
        args.refdiff = test_info_path.parent.parent / "ref.diff"

    do_run_test(args, test_info, strict)


def do_run_test(args, test_info, strict, stdout=False):
    from dictgen import run_dictgen

    if "optional" in test_info and not os.environ.get("RUN_OPTIONAL"):
        logging.info(f"Skipping optional test {test_info['name']}.")
        return

    def test_worker():
        logging.info(f"Running test {test_info}...")
        required_fields = ["directory", "answers", "name"]
        assert all(field in test_info for field in required_fields) and (
            "functions" in test_info or "diff" in test_info
        )

        def _run_dictgen():
            result = run_dictgen(
                args,
                path=(
                    test_info["directory"]
                    if "subdirectory" not in test_info
                    else os.path.join(test_info["directory"], test_info["subdirectory"])
                ),
                funcs=test_info["functions"] if "functions" in test_info else None,
            )
            # TODO: ugly
            global total_input_token_cost, total_output_token_cost
            total_input_token_cost += result.input_token_cost
            total_output_token_cost += result.output_token_cost
            return result.dict

        def _run_dictgen_and_check_result():
            if stdout:
                f = io.StringIO()
                with redirect_stdout(f):
                    _run_dictgen()
                captured_output = f.getvalue()
                dict = {
                    json.loads(value)
                    for line in captured_output.splitlines()
                    if "=" in line
                    for _, value in [line.split("=", 1)]
                }
            else:
                dict = _run_dictgen()
            check_result(test_info["answers"], dict, test_info["name"], strict)

        try:
            _run_dictgen_and_check_result()
        except Exception as e:
            if not args.retry_test_on_failure:
                raise e
            logging.warning(f"Test {test_info['name']} failed on first attempt: {e}")
            logging.warning(f"Retrying test {test_info['name']}...")
            _run_dictgen_and_check_result()

    # XXX: this is also ugly
    global tests
    tests.append(test_worker)


def run_test_in_runner_docker(args, strict=False):
    test_name = os.environ.get("TARGET_CP", "Test")
    test_info = load_test_info(args, test_name, True)
    from dictgen import run_dictgen  # Import run_dictgen at the top of the file

    os.environ["RUNNING_TESTS"] = "true"

    try:
        result = run_dictgen(
            args,
            path=(
                test_info["directory"]
                if "subdirectory" not in test_info
                else os.path.join(test_info["directory"], test_info["subdirectory"])
            ),
            funcs=test_info["functions"],
        )
        check_result(test_info["answers"], result.dict, test_info["name"], strict)
    except InferenceException as e:
        logging.error(f"Test {test_info['name']} failed with inference exception: {e}")


def run_all_tests(args, strict=False):
    # check arguments early to avoid assertion failure during tests
    assert args.workdir or os.environ.get(
        "WORKDIR"
    ), "WORKDIR is required for OSS-Fuzz tests."

    args0 = copy.copy(args)
    args0.test = "basic"
    run_basic_tests(args0, strict)
    args0 = copy.copy(args)
    args0.test = "oss-fuzz-all"
    run_oss_fuzz_test_all(args0, strict)
    args0 = copy.copy(args)
    args0.test = "stdout"
    run_stdout_test(args0, strict)


def run_redis_in_docker(args, strict=False):
    sample_dict = {"foo": {"token": {"0x42", "0x43", "42", "token2", "token"}}}
    redis_client = RedisClient(os.environ.get("DICTGEN_REDIS_URL"), get_logger(None))
    redis_client.set("test", "test", "test", sample_dict)
    sample_dict2 = redis_client.get("test", "test", "test")
    assert sample_dict == sample_dict2, "Redis test failed."
    exit(0)


def check_result(expected: set, actual: set, test_name: str, strict: bool):
    # TODO: Implement strict mode
    LOG_INFO = "\033[94m"  # Blue
    LOG_RESET = "\033[0m"  # Reset to default
    logging.info(f"{LOG_INFO}Checking test {test_name}...{LOG_RESET}")
    logging.info(f"{LOG_INFO}Expected: {expected}{LOG_RESET}")
    logging.info(f"{LOG_INFO}Actual: {actual}{LOG_RESET}")
    actual = {convert_to_decimal_string(act) for act in actual}
    for token in expected:
        if check_token_in_actual(token, actual):
            continue
        raise AssertionError(f"Token {token} not found in {actual} for {test_name}")
    logging.info(f"{LOG_INFO}Test {test_name} passed.{LOG_RESET}")


def check_token_in_actual(token, actual):
    if token in actual:
        return True
    # Check if token is a hex or oct integer and convert it to decimal string
    decimal_string = is_hex(token)
    if decimal_string and decimal_string in actual:
        return True
    # Check if token is a regex pattern and search for it in actual
    pattern = re.compile(token)
    for act in actual:
        if pattern.search(act):
            return True
    return False


def convert_to_decimal_string(token):
    try:
        # Convert hex or octal to decimal string
        if token.startswith("0x") or token.startswith("0X"):
            return str(int(token, 16))
        return str(int(token))  # Convert to int and back to string
    except ValueError:
        return token  # Return the original token if conversion fails


def is_hex(token):
    try:
        # Try to interpret the token as a hexadecimal integer
        if token.startswith("0x") or token.startswith("0X"):
            int_value = int(token, 16)
            return str(int_value)
    except ValueError:
        pass
    return None
