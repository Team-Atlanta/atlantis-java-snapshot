#!/usr/bin/env python3

import abc
import glob
import json
import os
import subprocess
import sys
from typing import Dict, List, Set, Tuple


class CheckerBase(abc.ABC):
    """Base class for all checkers that examine end-to-end test results"""

    CRS_ERR_SIG = "CRS-JAVA-ERR-"
    CRS_WARN_SIG = "CRS-JAVA-WARN-"

    def __init__(self, name: str, log_files: Dict[str, str]):
        """Initialize the checker."""
        self.name = name
        self.log_files: Dict[str, str] = log_files
        self.failed_files: List[str] = []
        self.all_fails: Dict[str, List[str]] = {}
        self.all_warns: Dict[str, List[str]] = {}
        self.deliverable_results: Dict[str, str] = {}
        self.deliverable_status: bool = True

    @abc.abstractmethod
    def check_deliverable(self) -> Tuple[bool, Dict[str, str]]:
        """Check if the expected deliverables are present and valid."""
        pass

    def parse_log_file(self, log_path: str) -> Tuple[List[str], List[str], bool]:
        """Parse a log file and extract lines containing FAIL or WARN signatures.
        Returns: (fail_lines, warn_lines, log_parse_error)."""
        fail_lines = []
        warn_lines = []
        parse_error = False

        try:
            # Read all lines to access context
            with open(log_path, encoding="utf-8", errors="replace") as f:
                all_lines = f.readlines()

            # Process each line to find errors and their context
            for i, line in enumerate(all_lines):
                line = line.strip()
                if self.CRS_ERR_SIG in line:
                    # Get context: 1 lines before and 9 lines after
                    start_idx = max(0, i - 1)
                    end_idx = min(len(all_lines), i + 9)

                    # Add all context lines to failures
                    fail_lines.append("-" * 50)
                    for j in range(start_idx, end_idx):
                        context_line = all_lines[j].strip()
                        # Mark the actual error line with ">" prefix
                        if j == i:
                            fail_lines.append(f"> {context_line}")
                        else:
                            fail_lines.append(f"  {context_line}")
                elif self.CRS_WARN_SIG in line:
                    # For warnings, just add the warning line without context
                    warn_lines.append(line)
        except FileNotFoundError:
            print(f"ERROR: Log file not found: {log_path}")
            parse_error = True
        except Exception as e:
            print(f"ERROR: Failed to read {log_path}: {e}")
            parse_error = True

        return fail_lines, warn_lines, parse_error

    def extract_tool_names(self, lines: List[str], prefix: str) -> Set[str]:
        tools = set()
        for line in lines:
            idx = line.find(prefix)
            if idx >= 0:
                rest = line[idx + len(prefix) :]
                tool = rest.split()[0] if " " in rest else rest
                tools.add(tool)
        return tools

    def check_log(self) -> bool:
        """Check log files for failures or warnings."""
        if not self.log_files:
            print(f"[{self.name}] WARNING: No log files configured for this checker.")
            return True

        self.all_fails.clear()
        self.all_warns.clear()
        self.failed_files.clear()

        not_found_log = []
        for log_name, log_files in self.log_files.items():
            if len(log_files) == 0:
                not_found_log.append(log_name)
            print("Found log file for", log_name, ":", log_files)
        if len(not_found_log) > 0:
            print(f"[{self.name}] ERROR: No log file configured for {not_found_log}.")

        for log_paths in self.log_files.values():
            for log_path in log_paths:
                print(f"[{self.name}] Checking {log_path}...")
                fails, warns, parse_error = self.parse_log_file(log_path)

                if parse_error:
                    self.failed_files.append(log_path)

                if fails:
                    self.all_fails[log_path] = fails
                if warns:
                    self.all_warns[log_path] = warns

        return not self.failed_files and not self.all_fails

    def check_summary(self) -> bool:
        """Print summary of checks and return overall status."""
        print(f"\n{'=' * 80}")
        print(f"SUMMARY FOR {self.name}")
        print(f"{'=' * 80}")

        if self.failed_files:
            print("\nFILE PROCESSING ERRORS:")
            for file_path in self.failed_files:
                print(f"  > {file_path}")

        if self.all_fails:
            print("\nFAILURES DETECTED IN LOGS:")
            for log_path, fails in self.all_fails.items():
                # Count actual errors (lines starting with ">")
                error_count = sum(1 for line in fails if line.startswith("> "))
                print(f"\n{log_path} ({error_count} failures):")
                # Extract tool names only from actual error lines (those with "> ")
                error_lines = [line[2:] for line in fails if line.startswith("> ")]
                tools = self.extract_tool_names(error_lines, self.CRS_ERR_SIG)
                print(f"  Tools with failures: {', '.join(sorted(tools))}")

                # Group the context lines by error
                print("\n".join(fails))
        else:
            print("\nNo failures detected in logs.")

        if self.all_warns:
            print("\nWARNINGS DETECTED IN LOGS:")
            for log_path, warns in self.all_warns.items():
                print(f"\n{log_path} ({len(warns)} warnings):")
                tools = self.extract_tool_names(warns, self.CRS_WARN_SIG)
                print(f"  Tools with warnings: {', '.join(sorted(tools))}")
                for line in warns:
                    print(f"  > {line}")
        else:
            print("\nNo warnings detected in logs.")

        if not self.deliverable_status:
            print("\nDELIVERABLE CHECK FAILED:")
            for check, result in self.deliverable_results.items():
                print(f"  > {check}: {result}")
        else:
            print("\nAll deliverable checks passed.")
            for check, result in self.deliverable_results.items():
                print(f"  > {check}: {result}")

        passed = (
            not self.failed_files and not self.all_fails and self.deliverable_status
        )
        if passed:
            print(f"\n✅ {self.name} PASSED")
        else:
            print(f"\n❌ {self.name} FAILED")

        return passed

    def check_all(self) -> bool:
        """Run all checks and return overall status."""
        log_status = self.check_log()
        deliverable_status, deliverable_results = self.check_deliverable()

        self.deliverable_status = deliverable_status
        self.deliverable_results = deliverable_results

        return log_status and deliverable_status


class CRSChecker(CheckerBase):
    """Checker for CRS Java deliverables"""

    def __init__(self):
        log_files = self._find_log_files()
        super().__init__("CRS Java Checker", log_files)

    def _find_files_by_glob(self, pattern: str) -> List[str]:
        """Find files matching a glob pattern."""
        found_files = []
        recursive = "**" in pattern
        for path in glob.glob(pattern, recursive=recursive):
            if os.path.isfile(path):
                found_files.append(path)
        return found_files

    def _find_file_by_glob(self, pattern: str) -> str:
        """Find a single file matching a glob pattern."""
        found_files = self._find_files_by_glob(pattern)
        if len(found_files) == 0:
            return ""
        return found_files[0]

    def _find_dirs_by_glob(self, pattern: str) -> List[str]:
        """Find directories matching a glob pattern."""
        found_dirs = []
        recursive = "**" in pattern
        for path in glob.glob(pattern, recursive=recursive):
            if os.path.isdir(path):
                found_dirs.append(path)
        return found_dirs

    def _find_dir_by_glob(self, pattern: str) -> str:
        """Find one dir matching a glob pattern."""
        found_dirs = self._find_dirs_by_glob(pattern)
        if len(found_dirs) == 0:
            return ""
        return found_dirs[0]

    def _find_log_files(self) -> List[str]:
        """Find log files in the CRS Java workdir."""
        log_files = {}

        crs_src = os.environ.get("JAVA_CRS_SRC", "")
        log_files["crs"] = [os.path.join(crs_src, "crs-java.log")]

        atljazzer_ptrn = (
            "/crs-workdir/worker-0/HarnessRunner/*/fuzz/atljazzer-*/fuzz.log"
        )
        log_files["atljazzer"] = self._find_files_by_glob(atljazzer_ptrn)

        atldirected_ptrn = (
            "/crs-workdir/worker-0/HarnessRunner/*/fuzz/atldirectedjazzer-*/fuzz.log"
        )
        log_files["atldirected"] = self._find_files_by_glob(atldirected_ptrn)

        libafljazzer_ptrn = (
            "/crs-workdir/worker-0/HarnessRunner/*/fuzz/atllibafljazzer-*/fuzz.log"
        )
        log_files["libafljazzer"] = self._find_files_by_glob(libafljazzer_ptrn)

        seedmerger_ptrn = (
            "/crs-workdir/worker-0/HarnessRunner/*/fuzz/seedmerger-*/fuzz.log"
        )
        log_files["seedmerger"] = self._find_files_by_glob(seedmerger_ptrn)

        concolic_ptrn = "/crs-workdir/worker-0/concolic/**/*.log"
        log_files["concolic"] = self._find_files_by_glob(concolic_ptrn)

        deepgen_ptrn = "/crs-workdir/worker-0/deepgen/**/*.log"
        log_files["deepgen"] = self._find_files_by_glob(deepgen_ptrn)

        dictgen_ptrn = "/crs-workdir/worker-0/dictgen/**/*.log"
        log_files["dictgen"] = self._find_files_by_glob(dictgen_ptrn)

        expkit_ptrn = "/crs-workdir/worker-0/expkit/**/*.log"
        log_files["expkit"] = self._find_files_by_glob(expkit_ptrn)

        llmpocgen_ptrn = "/crs-workdir/worker-0/llmpocgen/**/*.log"
        log_files["llmpocgen"] = self._find_files_by_glob(llmpocgen_ptrn)

        staticana_ptrn = "/crs-workdir/worker-0/staticanalysis/**/*.log"
        log_files["staticana"] = self._find_files_by_glob(staticana_ptrn)

        return log_files

    def _check_submitdb(self) -> Dict[str, str]:
        """Check if the submit database contains expected data."""
        results = {}

        try:
            cmd = ["python3.12", "-m", "libCRS.submit", "show"]
            proc = subprocess.run(cmd, capture_output=True, text=True, check=False)

            if proc.returncode != 0:
                results["submit_command"] = (
                    f"Command failed with return code {proc.returncode}"
                )
                if proc.stderr:
                    results["submit_stderr"] = proc.stderr.strip()

            if not proc.stdout or not proc.stdout.strip():
                results["submit_stdout"] = "Command output is empty"
            else:
                # TODO: @cen, add more specific pov check here
                output = proc.stdout.strip()

                if "aixcc/jvm/mock-java" in output and "OssFuzz1" in output:
                    required_elements = [
                        "aixcc/jvm/mock-java",
                        "OssFuzz1",
                        "crash",
                        "sink-OsCommandInjection",
                    ]

                    found_complete_line = False
                    for line in output.splitlines():
                        if all(element in line for element in required_elements):
                            print(f"Found Submitted POV: {line}")
                            found_complete_line = True
                            break

                    if not found_complete_line:
                        results["pov_check"] = (
                            "Missing expected POV data: Found 'aixcc/jvm/mock-java' and 'OssFuzz1', but no line contains all required elements: "
                            + ", ".join(required_elements)
                        )

        except Exception as e:
            results["submit_exception"] = f"Exception running submit command: {str(e)}"

        return results

    def _is_expected_file(self, path: str, min_size: int = -1) -> Dict[str, str]:
        """Check if a file exists and optionally has a minimum size."""
        results = {}
        if not os.path.exists(path):
            results[path] = "File does not exist"
        elif not os.path.isfile(path):
            results[path] = "Path is not a file"
        elif min_size >= 0 and os.path.getsize(path) < min_size:
            results[path] = f"File size is less than {min_size} bytes"
        return results

    def _is_nonempty_dir(self, path: str) -> Dict[str, str]:
        """Check if a directory exists and is not empty."""
        results = {}
        if not os.path.exists(path):
            results[path] = "Directory does not exist"
        elif not os.path.isdir(path):
            results[path] = "Path is not a directory"
        elif not os.listdir(path):
            results[path] = "Directory is empty"
        return results

    def _is_expected_json(self, path: str, non_empty_keys: List[str]) -> Dict[str, str]:
        """Check if a file exists, is a valid JSON, and contains a non-empty list for a specific key."""
        results = {}
        try:
            with open(path, encoding="utf-8") as f:
                data = f.read()
                if not data.strip():
                    results[path] = "File is empty"
                    return results
                json_data = json.loads(data)
                for key in non_empty_keys:
                    if key is not None and key not in json_data:
                        results[path] = f"Missing expected key: {key}"
                        return results
                    obj = json_data[key] if key is not None else json_data
                    if isinstance(obj, list):
                        if len(obj) == 0:
                            results[path] = f"Key '{key}' is an empty list"
                            return results
                    elif isinstance(obj, dict):
                        if not obj:
                            results[path] = f"Key '{key}' is an empty object"
                            return results
                    elif obj is None:
                        results[path] = f"Key '{key}' is null"
                        return results
        except json.JSONDecodeError:
            results[path] = "File is not valid JSON"
        except Exception as e:
            results[path] = f"Error reading JSON file: {str(e)}"
        return results

    def _check_llmpocgen(self) -> Dict[str, str]:
        """Check if llmpocgen generated files are present."""
        results = {}

        blackboard = "/crs-workdir/worker-0/llmpocgen/**/blackboard"
        cpg = "/crs-workdir/worker-0/llmpocgen/**/cpg"
        pocs_dir = "/crs-workdir/worker-0/llmpocgen/**/pocs"
        joern_cg = "/crs-workdir/worker-0/llmpocgen/**/joern-cg.json"
        model_cached = "/crs-workdir/worker-0/llmpocgen/**/model-cache.db"

        # blackboard => exist, valid json, contain non-empty "sinks" key (value is a list)
        blackboard = self._find_file_by_glob(blackboard)
        if not blackboard:
            results["blackboard"] = "Blackboard file not found"
        else:
            results.update(self._is_expected_json(blackboard, non_empty_keys=["sinks"]))
        # cpg => exist, file, > 1KB
        cpg = self._find_file_by_glob(cpg)
        if not cpg:
            results["cpg"] = "CPG file not found"
        else:
            results.update(self._is_expected_file(cpg, min_size=1024))
        # pocs => exist, dir, contain at least one file
        pocs_dir = self._find_dir_by_glob(pocs_dir)
        if not pocs_dir:
            results["pocs_dir"] = "POCs directory not found"
        else:
            results.update(self._is_nonempty_dir(pocs_dir))
        # joern-cg => exist, valid json, contain non-empty "nodes" key (value is a list)
        joern_cg = self._find_file_by_glob(joern_cg)
        if not joern_cg:
            results["joern_cg"] = "Joern CG file not found"
        else:
            results.update(self._is_expected_json(joern_cg, non_empty_keys=["nodes"]))
        # model-cache.db => exist, file, > 1KB
        # if LLM turned off, not check this (LITELLM_KEY=fake-key)
        llm_on = os.environ.get("LITELLM_KEY", "")
        if not llm_on or llm_on == "fake-key":
            results["model_cached"] = "LLM is turned off, skipping model cache check"
        else:
            model_cached = self._find_file_by_glob(model_cached)
            if not model_cached:
                results["model_cached"] = "Model cache file not found"
            else:
                results.update(self._is_expected_file(model_cached, min_size=1024))

        return results

    def _check_staticana(self) -> Dict[str, str]:
        """Check if static analysis results are present."""
        results = {}

        soot_cg = "/crs-workdir/worker-0/staticanalysis/**/soot-cg.json"
        static_ana_cfg = (
            "/crs-workdir/worker-0/staticanalysis/**/static-analysis-cfg.json"
        )
        static_ana_result = (
            "/crs-workdir/worker-0/staticanalysis/**/static-analysis-result.json"
        )

        # soot-cg => exist, valid json, contain non-empty "nodes" key (value is a list)
        soot_cg = self._find_file_by_glob(soot_cg)
        if not soot_cg:
            results["soot_cg"] = "Soot CG file not found"
        else:
            results.update(self._is_expected_json(soot_cg, non_empty_keys=["nodes"]))
        # static-analysis-config => exist, valid json, contain non-empty "classpath" (list) and "harnesses" keys (dict)
        static_ana_cfg = self._find_file_by_glob(static_ana_cfg)
        if not static_ana_cfg:
            results["static_ana_cfg"] = "Static analysis config file not found"
        else:
            results.update(
                self._is_expected_json(
                    static_ana_cfg, non_empty_keys=["classpath", "harnesses"]
                )
            )
        # static-analysis-result => exist, valid json, contain non-empty "target_data" key (list), "all_mapped_methods" key (list)
        static_ana_result = self._find_file_by_glob(static_ana_result)
        if not static_ana_result:
            results["static_ana_result"] = "Static analysis result file not found"
        else:
            results.update(
                self._is_expected_json(
                    static_ana_result,
                    non_empty_keys=["target_data", "all_mapped_methods"],
                )
            )

        return results

    def _check_deepgen(self) -> Dict[str, str]:
        results = {}

        summary = "/crs-workdir/worker-0/deepgen/**/summary.json"
        # summary => exist, valid json, contain non-empty "scripts" key (value is a dict)
        summary = self._find_file_by_glob(summary)
        if not summary:
            results["deepgen_summary"] = "DeepGen summary file not found"
        else:
            results.update(self._is_expected_json(summary, non_empty_keys=["scripts"]))

        return results

    def _check_dictgen(self) -> Dict[str, str]:
        """Check if dictgen generated files are present."""
        results = {}

        all_dicts = "/crs-workdir/worker-0/dictgen/**/all-dicts.json"
        # all-dicts.json => exist, valid json, root is non-empty dict
        all_dicts = self._find_file_by_glob(all_dicts)
        if not all_dicts:
            results["all_dicts"] = "All dicts file not found"
        else:
            results.update(self._is_expected_json(all_dicts, non_empty_keys=[None]))

        return results

    def _check_expkit(self) -> Dict[str, str]:
        """Check if expkit generated files are present."""
        results = {}

        exp_jsons = "/crs-workdir/worker-0/expkit/**/exp.json"
        # expkit directory => exist, directory, contain at least one file
        exp_jsons = self._find_files_by_glob(exp_jsons)
        if len(exp_jsons) == 0:
            results["expkit_jsons"] = "exp.json not found"
        else:
            for exp_json in exp_jsons:
                results.update(self._is_expected_json(exp_json, non_empty_keys=[None]))

        return results

    def _check_metadata(self) -> Dict[str, str]:
        """Check if metadata files are present."""
        results = {}

        cpmeta_json = "/crs-workdir/worker-0/metadata/**/cpmeta.json"
        sinkpoints_json = "/crs-workdir/worker-0/metadata/**/sinkpoints.json"
        # cpmeta.json => exist, valid json, harnesses is non-empty list
        cpmeta_json = self._find_file_by_glob(cpmeta_json)
        if not cpmeta_json:
            results["cpmeta_json"] = "cpmeta.json file not found"
        else:
            results.update(
                self._is_expected_json(cpmeta_json, non_empty_keys=["harnesses"])
            )
        # sinkpoints.json => exist, valid json, root is non-empty list
        sinkpoints_json = self._find_file_by_glob(sinkpoints_json)
        if not sinkpoints_json:
            results["sinkpoints_json"] = "sinkpoints.json file not found"
        else:
            results.update(
                self._is_expected_json(sinkpoints_json, non_empty_keys=[None])
            )

        return results

    def _check_sinkmanager(self) -> Dict[str, str]:
        """Check if sinkmanager generated files are present."""
        results = {}

        custom_sinks = "/crs-workdir/worker-0/sinkmanager/**/custom-sinkpoints.conf"
        # custom-sinkpoints.conf => exist, file, > 10 bytes
        custom_sinks = self._find_file_by_glob(custom_sinks)
        if not custom_sinks:
            results["custom_sinks"] = "Custom sinkpoints file not found"
        else:
            results.update(self._is_expected_file(custom_sinks, min_size=10))
        return results

    def _check_coordinates(self) -> Dict[str, str]:
        """Check if coordinates files are present."""
        results = {}

        tmp_jsons = "/crs-workdir/worker-0/coordinates/**/*.json"
        # >= 1 tmp jsons
        tmp_jsons = self._find_files_by_glob(tmp_jsons)
        if len(tmp_jsons) == 0:
            results["coordinates_jsons"] = "No coordinates JSON files found"
        else:
            for tmp_json in tmp_jsons:
                results.update(self._is_expected_json(tmp_json, non_empty_keys=[None]))

        return results

    def _check_concolic(self) -> Dict[str, str]:
        """Check if concolic files are present."""
        results = {}

        debug_runs = "/crs-workdir/worker-0/concolic/**/debug-seeds/runs"
        # concolic out dir => exist, directory, contain at least one file
        debug_runs = self._find_dir_by_glob(debug_runs)
        if not debug_runs:
            results["debug_runs"] = "Concolic directory not found"
        else:
            results.update(self._is_nonempty_dir(debug_runs))

        return results

    def _check_fuzzers(self) -> Dict[str, str]:
        """Check if fuzzers works."""
        results = {}

        # 1. find all corpus_dir
        corpus_dirs = self._find_dirs_by_glob(
            "/crs-workdir/worker-0/HarnessRunner/**/fuzz/*/corpus_dir"
        )
        if len(corpus_dirs) == 0:
            results["fuzzers_corpus"] = "No corpus directories found for fuzzers"
            return results
        # 2. infer result.json from corpus_dir path
        result_jsons = []
        for corpus_dir in corpus_dirs:
            result_json = os.path.join(os.path.dirname(corpus_dir), "result.json")
            if os.path.exists(result_json):
                result_jsons.append(result_json)
            else:
                results["result_json"] = f"{result_json} not found"

        # 3. check result.json files
        for result_json in result_jsons:
            # each result.json should be a valid JSON and "fuzz_data" is a non-empty dict
            results.update(
                self._is_expected_json(result_json, non_empty_keys=["fuzz_data"])
            )
            # parse and check result.json
            # obj["fuzz_data"]["max_cov"] > 0
            # obj["fuzz_data"]["ttl_round"] > 0
            with open(result_json, encoding="utf-8") as f:
                try:
                    obj = json.load(f)
                    max_cov = int(obj["fuzz_data"]["max_cov"])
                    ttl_round = int(obj["fuzz_data"]["ttl_round"])
                    if max_cov <= 0:
                        results[result_json] = (
                            "max_cov should be greater than 0, found: " + str(max_cov)
                        )
                    if ttl_round <= 0:
                        results[result_json] = (
                            "ttl_round should be greater than 0, found: "
                            + str(ttl_round)
                        )
                except Exception as e:
                    results[result_json] = "Invalid JSON format: " + str(e)
                    continue

        return results

    def check_deliverable(self) -> Tuple[bool, Dict[str, str]]:
        """Check CRS Java deliverables by running submit show command."""
        results = {}

        results.update(self._check_submitdb())
        results.update(self._check_llmpocgen())
        results.update(self._check_staticana())
        results.update(self._check_deepgen())
        results.update(self._check_dictgen())
        results.update(self._check_expkit())
        results.update(self._check_metadata())
        results.update(self._check_sinkmanager())
        results.update(self._check_coordinates())
        results.update(self._check_concolic())
        results.update(self._check_fuzzers())

        return len(results) == 0, results


CHECKERS: List[CheckerBase] = [
    CRSChecker(),
]


def main() -> int:
    """Returns 0 for success, non-zero if any check fails."""
    if not CHECKERS:
        print(
            "ERROR: No checkers configured. Please add checker instances to CHECKERS."
        )
        return 1

    overall_status = True
    for checker in CHECKERS:
        print(f"\nRunning checker: {checker.name}")
        status = checker.check_all()
        overall_status = overall_status and status

    print(f"\n{'=' * 80}")
    print("E2E RESULT SUMMARY")
    print(f"{'=' * 80}")

    for checker in CHECKERS:
        status = checker.check_summary()
        overall_status = overall_status and status

    print(f"\n{'=' * 80}")
    if overall_status:
        print("ALL CHECKS PASSED")
    else:
        print("SOME CHECKS FAILED")
    print(f"{'=' * 80}")

    return 0 if overall_status else 1


if __name__ == "__main__":
    sys.exit(main())
