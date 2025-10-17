# Module for getting the reasons why execution is stuck.
from typing import List, Optional
from pathlib import Path
from dataclasses import dataclass
from pydantic import BaseModel
import logging
import subprocess
import re
import os


logger = logging.getLogger(__name__)

module_folder = Path(__file__).resolve().parent  # Folder for this file.
execution_tracer_folder = module_folder / ".." / "ProgramExecutionTracer"


class_path_seperator = ';' if os.name == 'nt' else ':'


def get_jar_program_execution_tracer_jar(tracer_folder=execution_tracer_folder):
    tracer_jar = (
        tracer_folder
        / "target"
        / "ProgramExecutionTracer-1.0-SNAPSHOT-jar-with-dependencies.jar"
    )
    if not tracer_jar.exists():
        raise ValueError("ProgramExecutionTracer jar does not exist")

    return tracer_jar


def compile_fuzzer_runner(fuzzing_class: str, class_path: str, output_dir: Path):
    """Compile a stub class that just calls the fuzzer based on input passed
    on the command line."""

    # Output this and then attempt to compile with `javac`
    class_name = "StuckReasonFuzzerRunner"
    main_method_class_code = f"""\
import java.util.*;
import java.io.*;
import java.nio.*;
import java.nio.file.Files;
import java.nio.file.Path;

public class {class_name} {{
    public static void main(String[] args) throws Throwable, Exception {{
        Path path = Path.of(args[0]);
        byte[] data = Files.readAllBytes(path);
        {fuzzing_class}.fuzzerTestOneInput(data);
    }}
}}
"""
    source_file = output_dir / f"{class_name}.java"
    with source_file.open("w") as f:
        f.write(main_method_class_code)

    logging.info("Compiling StuckReasonFuzzerRunner.java at %s", source_file)
    try:
        subprocess.check_call(
            ["javac", "-cp", class_path, source_file.name], cwd=output_dir
        )
    except:
        logging.critical("Failed to compile fuzzer runner")
        raise


def run_program_execution_tracer(
    tracer_jar: Path, stub_location: Path, class_path: str, corpus: Path
):
    # Add the directory of the stub to the classpath.
    class_path += f"{class_path_seperator}{stub_location.resolve()}"
    p = subprocess.run(
        [
            "java",
            "-jar",
            str(tracer_jar.resolve()),
            class_path,
            "StuckReasonFuzzerRunner",
            str(corpus.resolve()),
        ],
        capture_output=True,
        text=True,
        timeout=120
    )
    if p.returncode != 0:
        logger.critical("ProgramExecutionTracer failed command=%s", p.args)
        logger.critical("---- stdout ----")
        logger.critical(p.stdout)
        logger.critical("---- stderr ----")
        logger.critical(p.stderr)
        p.check_returncode()
    return p



class ExecutionFrame(BaseModel):
    sourceFileName: str
    lineNumber: int
    methodName: str
    qualifiedClassName: str

class StackTrace(BaseModel):
    frames: List[ExecutionFrame]

class StuckExecutionTrace(BaseModel):
    stuckCandidateTrace: StackTrace
    candidateFromException: bool
    exceptionMessage: Optional[str] = None
    leafFunctions: List[ExecutionFrame]


def parse_execution_trace(output: str) -> StuckExecutionTrace:
    """Takes the output from ProgramExecutionTracer and parses it."""
    output = output.rsplit("==== Stuck Frame ====", maxsplit=1)
    if len(output) != 2:
        raise ValueError("Execution trace does not have stuck frame separator")
    
    print(output[1])

    return StuckExecutionTrace.model_validate_json(output[1])
