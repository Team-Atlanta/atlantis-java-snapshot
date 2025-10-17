#!/usr/bin/env python3
import argparse
import json
import os
import re
import signal
import sys
from typing import Optional, Tuple

SANITIZERS = [
    "FuzzerSecurityIssueCritical: OS Command Injection",
    "FuzzerSecurityIssueCritical: Integer Overflow",
    "FuzzerSecurityIssueMedium: Server Side Request Forgery (SSRF)",
    "FuzzerSecurityIssueHigh: Remote Code Execution",
    "FuzzerSecurityIssueHigh: SQL Injection",
    "FuzzerSecurityIssueCritical: Remote JNDI Lookup",
    "FuzzerSecurityIssueCritical: LDAP Injection",
    "FuzzerSecurityIssueHigh: XPath Injection",
    "FuzzerSecurityIssueHigh: load arbitrary library",
    "FuzzerSecurityIssueLow: Regular Expression Injection",
    "FuzzerSecurityIssueCritical: Script Engine Injection",
    "FuzzerSecurityIssueCritical: File read/write hook path",
]

FUZZ_START_LINE_PTRN = re.compile(
    r"^(\d+)\sOpenJDK 64-Bit Server VM warning: Option CriticalJNINatives was deprecated in version 16.0 and will likely be removed in a future release."
)

OLD_LIBFUZZER_COV_LINE_PTRN = re.compile(r"^#(\d+).*cov: (\d+) ft: (\d+)")
LIBFUZZER_COV_LINE_PTRN = re.compile(r"^(\d+)\s#(\d+).*cov: (\d+) ft: (\d+)")

OLD_LIBFUZZER_CRASH_LINE_PTRN = re.compile(r"^(== Java Exception:.*)")
LIBFUZZER_CRASH_LINE_PTRN = re.compile(r"^(\d+)\s(== Java Exception:.*)")

OLD_CRASH_ARTIFACT_LINE_PTRN = re.compile(
    r"^artifact_prefix=.*; Test unit written to .*/artifacts/(crash-[a-z0-9]+)"
)
CRASH_ARTIFACT_LINE_PTRN = re.compile(
    r"^(\d+)\sartifact_prefix=.*; Test unit written to .*/artifacts/(crash-[a-z0-9]+)"
)

JAZZER_EXIT_LOG = "@@@@@ exit code of Jazzer"


def is_of_jazzer_sink(crash: str) -> bool:
    return os.environ.get("JAZZER_SINK_MODE", '') != '' and "BEEP BEEP, sink point" in crash


def is_known_sanitizer(sanitizer: str) -> bool:
    return sanitizer in SANITIZERS


def is_interesting_crash(crash: str) -> bool:
    """
    Check if crash is interesting.
    """
    checkers = [
        # Filter for crashes that contain "code_intelligence"
        lambda c: "code_intelligence" in c.split(":")[1],
        # Filter out "Stack overflow" crashes
        lambda c: "Stack overflow (use " not in c,
        # Filter out "Out of memory" crashes
        lambda c: "Out of memory" not in c,
    ]

    for checker in checkers:
        if not checker(crash):
            # Not interesting crash
            return False
    return True


def crash_2_sanitizer(crash: str) -> Optional[str]:
    if is_of_jazzer_sink(crash):
        return "SINKPOINT"

    if not is_interesting_crash(crash):
        return None
    
    for sanitizer in SANITIZERS:
        if sanitizer in crash:
            return sanitizer
        elif sanitizer.replace(" ", "") in crash:
            # This is to be compatible with the old crash info
            return sanitizer

    return "UNKNOWN SANITIZER"


def _parse_cov_line(line: str, initial_timestamp: Optional[int]) -> Optional[Tuple]:
    match = LIBFUZZER_COV_LINE_PTRN.match(line)
    if match:
        timestamp, roundno, cov, ft = (
            int(match.group(1)),
            int(match.group(2)),
            int(match.group(3)),
            int(match.group(4)),
        )
        elapsed_time = (
            timestamp - initial_timestamp if initial_timestamp is not None else None
        )
        return roundno, elapsed_time, cov, ft
    else:
        match = OLD_LIBFUZZER_COV_LINE_PTRN.match(line)
        if match:
            roundno, cov, ft = (
                int(match.group(1)),
                int(match.group(2)),
                int(match.group(3)),
            )
            return roundno, None, cov, ft
    return None


def _parse_crash_line(line: str, initial_timestamp: Optional[int]) -> Optional[Tuple]:
    match = LIBFUZZER_CRASH_LINE_PTRN.match(line)
    if match:
        timestamp, crash = int(match.group(1)), match.group(2)
        elapsed_time = (
            timestamp - initial_timestamp if initial_timestamp is not None else None
        )
        return elapsed_time, crash
    else:
        match = OLD_LIBFUZZER_CRASH_LINE_PTRN.match(line)
        if match:
            crash = match.group(1)
            return None, crash
    return None


def _parse_artifact_line(
    line: str, initial_timestamp: Optional[int]
) -> Optional[Tuple]:
    match = CRASH_ARTIFACT_LINE_PTRN.match(line)
    if match:
        timestamp, artifact = int(match.group(1)), match.group(2)
        elapsed_time = (
            timestamp - initial_timestamp if initial_timestamp is not None else None
        )
        return elapsed_time, artifact
    else:
        match = OLD_CRASH_ARTIFACT_LINE_PTRN.match(line)
        if match:
            artifact = match.group(1)
            return None, artifact
    return None


def parse_log_in_stream(file_obj, fuzz_data: dict, no_tee=False):
    """
    Parses all fuzz status lines from libfuzzer logs using streaming.
    - fuzz_data is a dict that will be updated with the parsed data.
    - if no_tee is True, do not output the stdin line to stdout.
    """
    cov_over_time = []
    ft_over_time = []
    log_crash_over_time = []
    artifact_over_time = []
    log_triage_crash_over_time = []

    pending_crashes = []
    seen_sanitizers = set()

    ttl_round = 0
    last_cov, last_ft = 0, 0
    max_cov, max_ft = 0, 0

    need_dump = False

    def sync_result(data: dict):
        data.update(
            {
                "cov_over_time": cov_over_time,
                "ft_over_time": ft_over_time,
                "log_crash_over_time": log_crash_over_time,
                "artifact_over_time": artifact_over_time,
                "log_triage_crash_over_time": log_triage_crash_over_time,
                "ttl_round": ttl_round,
                "last_cov": last_cov,
                "last_ft": last_ft,
                "max_cov": max_cov,
                "max_ft": max_ft,
            }
        )

    try:
        initial_timestamp = None
        ttl_roundno_base = 0

        # fuzz_statuses & all_fuzz_statuses are kept for potential future use
        all_fuzz_statuses = []
        fuzz_statuses = []

        for line in file_obj:
            # Behave like "tee", output the stdin line to stdout if no_tee is False
            if not no_tee:
                sys.stdout.buffer.write(line)

            try:
                # Skip the line which we cannot decode
                line = line.decode("utf-8", errors="ignore").strip()
            except UnicodeDecodeError as e:
                print(f"[JAZZER_LOG_PARSER] Error decoding line {line}: {e}")
                continue

            # Only one of the following case will match for each line

            # 1. fuzzer start line: initial timestamp
            if initial_timestamp is None:
                match = FUZZ_START_LINE_PTRN.match(line)
                if match:
                    initial_timestamp = int(match.group(1))
                    need_dump = True  # We need to dump data when start line is found

            # 2. cov line: cov, ft, roundno, timestamp
            rslt = _parse_cov_line(line, initial_timestamp)
            if rslt:
                roundno, elapsed_time, cov, ft = rslt
                last_cov, max_cov = cov, max(max_cov, cov)
                last_ft, max_ft = ft, max(max_ft, ft)
                cov_over_time.append((elapsed_time, cov))
                ft_over_time.append((elapsed_time, ft))
                ttl_round = ttl_roundno_base + roundno

                fuzz_statuses.append((roundno, elapsed_time, cov, ft))

            # 3. crash line: crash, timestamp
            rslt = _parse_crash_line(line, initial_timestamp)
            if rslt:
                elapsed_time, crash = rslt
                log_crash_over_time.append((elapsed_time, crash))

                # Crash triage logic
                sanitizer = crash_2_sanitizer(crash)
                if sanitizer is not None and (sanitizer not in seen_sanitizers or sanitizer == "SINKPOINT"):
                    pending_crashes.append((elapsed_time, crash, sanitizer))

            # 4. artifact line: artifact, timestamp
            rslt = _parse_artifact_line(line, initial_timestamp)
            if rslt:
                elapsed_time, artifact = rslt
                artifact_over_time.append((elapsed_time, artifact))

                # Check pending_crashes
                i = 0
                while i < len(pending_crashes):
                    crash_time, crash, sanitizer = pending_crashes[i]
                    if (
                        elapsed_time is None
                        or crash_time is None
                        or elapsed_time >= crash_time
                    ):
                        if sanitizer not in seen_sanitizers or sanitizer == "SINKPOINT":
                            log_triage_crash_over_time.append(
                                (crash_time, sanitizer, crash, artifact)
                            )
                            seen_sanitizers.add(sanitizer)
                            need_dump = True  # We need to dump data when new artifact is triaged
                        pending_crashes.pop(i)
                    else:
                        i += 1

            # 5. exit line: exit log
            if JAZZER_EXIT_LOG in line:
                ttl_roundno_base = ttl_round

                if len(fuzz_statuses) > 0:
                    all_fuzz_statuses.append(fuzz_statuses)
                    fuzz_statuses = []

            # Sync the result
            sync_result(fuzz_data)

            if need_dump:
                dump_fuzz_data()
                need_dump = False

        if len(fuzz_statuses) > 0:
            all_fuzz_statuses.append(fuzz_statuses)

    except Exception as e:
        # We've already synced the result at the end of line parsing
        print(f"[JAZZER_LOG_PARSER] Error parsing libFuzzer logs: {e}")


def parse_libfuzzer_log(log_file: str, fuzz_data: dict = None, no_tee=False) -> dict:
    """
    Parse fuzz_data from libFuzzer log file.
    - if fuzz_data is provided, it will be updated with the parsed data.
    - if fuzz_data is None, a new dict will be created and returned.
    - if no_tee is True, do not output the stdin line to stdout.
    """
    _fuzz_data = fuzz_data if fuzz_data is not None else {}

    try:
        with open(log_file, "rb") as file_obj:
            parse_log_in_stream(file_obj, fuzz_data=_fuzz_data, no_tee=no_tee)

    except Exception as e:
        print(f"[JAZZER_LOG_PARSER] Error parsing libFuzzer log file {log_file}: {e}")

    return _fuzz_data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Analyze fuzzing data and output JSON results."
    )
    parser.add_argument(
        "fuzz_log_file",
        nargs="?",
        help="Path to the file containing fuzz data (fuzz.log).",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Path to the output file where JSON results will be saved.",
        default=None,
    )
    parser.add_argument(
        "--no-tee",
        action="store_true",
        help="Do not output the stdin line to stdout (disable tee behavior).",
    )

    args = parser.parse_args()

    out_obj = {}
    if os.path.exists(args.output):
        with open(args.output) as f:
            out_obj = json.load(f)

    fuzz_data = {}

    def dump_fuzz_data():
        global fuzz_data

        if args.output:
            out_obj["fuzz_data"] = fuzz_data
            with open(args.output, "w") as f:
                json.dump(out_obj, f, indent=2)
        else:
            print(json.dumps({"fuzz_data": fuzz_data}, indent=2))

    def signal_handler(sig, frame):
        """
        Gracefully exit the script.
        """
        print("[JAZZER_LOG_PARSER] Exiting...")
        dump_fuzz_data()
        sys.exit(0)

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGPIPE, signal_handler)

    # Determine if input is from stdin or a file
    if not sys.stdin.isatty():
        # Input is from stdin (piped input)
        print("[JAZZER_LOG_PARSER] Analyzing fuzz data from stream...")
        parse_log_in_stream(sys.stdin.buffer, fuzz_data=fuzz_data, no_tee=args.no_tee)
        dump_fuzz_data()

    elif args.fuzz_log_file:
        # Input is a fuzz log file
        parse_libfuzzer_log(args.fuzz_log_file, fuzz_data=fuzz_data, no_tee=args.no_tee)
        dump_fuzz_data()

    else:
        print("[JAZZER_LOG_PARSER] Usage:")
        print(
            "[JAZZER_LOG_PARSER]   python this_script.py [fuzz_log_file] [-o output_file]"
        )
        print("[JAZZER_LOG_PARSER] Or pipe the log data to the script:")
        print(
            "[JAZZER_LOG_PARSER]   fuzz_command | python this_script.py [-o output_file]"
        )
        sys.exit(1)
