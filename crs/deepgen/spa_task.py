#!/usr/bin/env python3

import asyncio
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
import uuid
from pathlib import Path
from typing import List, Optional, Dict, Any

from libAgents.utils import Project
from libDeepGen.engine import DeepGenEngine
from libDeepGen.tasks.harness_seedgen import AnyHarnessSeedGen

logger = logging.getLogger(__name__)


class StuckPoint:
    """Represents a stuck point identified during SPA analysis."""
    
    def __init__(self, data: Dict[str, Any]):
        # These fields are required from our tool's output
        # If any are missing, it indicates a fatal error
        try:
            self.class_fqn = data["classFqn"]
            self.file_name = data["fileName"]
            self.line_number = data["lineNumber"]
            self.coverage_status = data["coverageStatus"]
            self.stuck_point_score = data["stuckPointScore"]
            self.instruction_coverage = data["instructionCoverage"]
            self.branch_coverage = data["branchCoverage"]
            self.summary = data["summary"]
            self.raw_data = data
            # Annotated source dir will be set after analysis
            self.annotated_source_dir = None
        except KeyError as e:
            raise ValueError(f"Missing required field in stuck point data: {e}")


class StuckPointAnaSeedGen(AnyHarnessSeedGen):
    """Seed generation task with stuck point analysis for fuzzing harnesses."""
    
    def __init__(self, 
                 project_bundle: Project,
                 harness_name: str,
                 harness_entrypoint_func: str,
                 stuck_point: StuckPoint,
                 is_jvm: bool,
                 weighted_models: list[tuple[str, int]] = None,
                 priority: int = 1,
                 dev_attempts: int = 5,
                 dev_cost: float = 10.0,
                 num_repeat: int = 1,
                 max_exec: int = sys.maxsize):
        super().__init__(
            project_bundle=project_bundle,
            harness_name=harness_name,
            harness_entrypoint_func=harness_entrypoint_func,
            is_jvm=is_jvm,
            weighted_models=weighted_models,
            priority=priority,
            dev_attempts=dev_attempts,
            dev_cost=dev_cost,
            num_repeat=num_repeat,
            max_exec=max_exec,
        )
        self.stuck_point = stuck_point
    
    def get_label(self) -> str:
        return f"StuckPointAna:{self.harness_name}"
    
    def _get_prompt(self) -> str:
        PROMPT = f"""\
Stuck Point Analysis-Driven Fuzzing Input Generation for Improving Fuzzing Coverage

OBJECTIVE:
You are a fuzzing expert specializing in breaking through coverage stuck points. Our fuzzing campaign has identified a critical stuck point where the fuzzer cannot progress further. Your mission is to write a sophisticated Python fuzzing input generator that specifically targets this stuck point to achieve deeper code coverage and potentially discover crashes in unexplored code paths.

STUCK POINT IDENTIFIED:
**Location:**
- **Class**: {self.stuck_point.class_fqn}
- **File**: {self.stuck_point.file_name}
- **Line Number**: {self.stuck_point.line_number}

**Source Code Preview:**
{self.stuck_point.summary}

ANNOTATED SOURCE CODE:
The source code has been specially annotated with coverage information. Each line is prefixed with:
- `[✓]` - Fully covered (all instructions executed)
- `[~]` - Partially covered (STUCK POINT - some instructions executed but not all)
- `[✗]` - Not covered (no instructions executed)
- `[ ]` - No executable code or no coverage data

The annotated source code is available at: {self.stuck_point.annotated_source_dir}

You should examine the annotated source code to understand:
1. The exact code context where fuzzing gets stuck (lines marked with `[~]`)
2. The surrounding covered code paths (lines marked with `[✓]`)
3. The uncovered code paths beyond the stuck point (lines marked with `[✗]`)
4. The control flow and data dependencies around the stuck point

SEMANTIC ANALYSIS REQUIREMENTS:
As a fuzzing expert, you must:
1. **Understand the Stuck Point Context**: Analyze why the fuzzer gets stuck at line {self.stuck_point.line_number}. What conditions or constraints are preventing progress?
2. **Identify Input Requirements**: Determine what specific input characteristics are needed to pass through the stuck point
3. **Consider Data Dependencies**: Trace back through the code to understand what values and states lead to the stuck point
4. **Format-Aware Generation**: Understand the expected input format and structure for the harness
5. **Branch Coverage Focus**: Pay special attention to uncovered branches at the stuck point - what values would take the unexplored paths?

HIGH-LEVEL STRATEGY:
1. Navigate to the annotated source directory and examine the coverage-annotated code
2. Analyze the stuck point in {self.stuck_point.file_name} at line {self.stuck_point.line_number} marked with `[~]`
3. Understand the fuzzing harness entry point: `{self.harness_entrypoint_func}`
4. Identify the specific constraints, conditions, or values needed to progress past the stuck point, trace the execution path from the harness entry to the stuck point if necessary
6. Write a sophisticated Python input generator that keeps producing inputs with randomness and specifically crafted to test the uncovered lines behind this stuck point

PROJECT INFORMATION:
- Project Name: {self.project_bundle.name}
- OSS-Fuzz Project Path: {self.project_bundle.project_path.resolve()}
- Fuzzing Harness: {self.harness_name}
- Harness Path: {self.harness_src.resolve() if self.harness_src else "N/A"}
- Annotated Source Repository Path: {self.project_bundle.repo_path.resolve()}
- Harness Entry Point: `{self.harness_entrypoint_func}`

SCRIPT REQUIREMENTS:
- The script MUST implement a function named `gen_one_seed()` that returns bytes
- The script should be sophisticated and targeted to test then uncovered lines behind the stuck point
- Each call should potentially generate different seeds (use appropriate randomization)
- Include detailed comments explaining your stuck point analysis and generation strategy

OUTPUT FORMAT:
Generate the Python script enclosed within `<script>` and `</script>` tags:

<script>
import random
import struct
# Add other necessary imports

# Stuck Point Analysis:
# Line {self.stuck_point.line_number} in {self.stuck_point.file_name} shows partial coverage because...
# To test uncovered lines behind this stuck point, we need inputs that...
# The uncovered branch requires...

def gen_one_seed() -> bytes:
    \"\"\"
    Generate a seed specifically targeting the uncovered lines behind the stuck point at {self.stuck_point.file_name}:{self.stuck_point.line_number}

    Strategy: [Explain your specific strategy for this targeted generation]
    \"\"\"
    # TODO: Implementation
    pass
</script>"""
        
        return PROMPT


def get_exec_files_to_merge(exec_files: List[str]) -> List[Path]:
    """
    Get list of JaCoCo execution files to merge.
    
    Args:
        exec_files: List of exec file paths from command line
    
    Returns:
        List of Path objects pointing to .exec files that exist
    """
    if not exec_files:
        logger.warning("No exec files provided via command line")
        return []
    
    existing_files = []
    for exec_file in exec_files:
        path = Path(exec_file)
        if path.exists():
            existing_files.append(path)
            logger.info(f"Found exec file: {path}")
        else:
            logger.warning(f"Exec file does not exist (yet): {path}")
    
    if not existing_files:
        logger.warning("No existing exec files found")
    else:
        logger.info(f"Found {len(existing_files)} existing exec files to merge")
    
    return existing_files


def merge_exec_files(exec_files: List[Path], output_file: Path) -> Optional[Path]:
    """
    Merge multiple JaCoCo execution files into a single file using JaCoCo CLI.
    
    Args:
        exec_files: List of exec files to merge
        output_file: Path where merged exec file should be written
    
    Returns:
        Path to merged exec file if successful, None otherwise
    """
    if not exec_files:
        logger.warning("No exec files to merge")
        return None
    
    if len(exec_files) == 1:
        # Only one file, just copy it
        logger.info(f"Only one exec file found, copying to {output_file}")
        try:
            import shutil
            shutil.copy2(exec_files[0], output_file)
            return output_file
        except Exception as e:
            logger.error(f"Failed to copy single exec file: {e}")
            return None
    
    # Multiple files, need to merge using JaCoCo CLI
    logger.info(f"Merging {len(exec_files)} exec files into {output_file}")
    
    # Path to JaCoCo CLI JAR from environment variable
    jacoco_cli_dir = os.environ.get("JACOCO_CLI_DIR")
    if not jacoco_cli_dir:
        logger.error("JACOCO_CLI_DIR environment variable is not set")
        return None
    jacoco_cli_jar = Path(jacoco_cli_dir) / "jacococli.jar"
    
    # Build command: java -jar jacococli.jar merge <execfiles> --destfile <path>
    cmd = ["java", "-jar", str(jacoco_cli_jar), "merge"]
    
    # Add all exec files to merge
    for exec_file in exec_files:
        cmd.append(str(exec_file))
    
    # Add destination file
    cmd.extend(["--destfile", str(output_file)])
    
    logger.debug(f"Running JaCoCo merge command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60  # 1 minute timeout
        )
        
        if result.returncode != 0:
            logger.error(f"JaCoCo merge failed with code {result.returncode}")
            logger.error(f"stderr: {result.stderr}")
            return None
        
        if not output_file.exists():
            logger.error(f"Merged exec file not created at {output_file}")
            return None
        
        logger.info(f"Successfully merged {len(exec_files)} exec files")
        return output_file
        
    except subprocess.TimeoutExpired:
        logger.error("JaCoCo merge command timed out")
        return None
    except FileNotFoundError:
        logger.error(f"JaCoCo CLI JAR not found at {jacoco_cli_jar}")
        logger.error("Please ensure jacococli.jar exists in crs/prebuilt/jacococli/")
        return None
    except Exception as e:
        logger.error(f"Error during JaCoCo merge: {e}")
        return None


async def spa_analyze(project_bundle: Project, harness_name: str, harness_info: Dict[str, Any], metadata_path: Path, cp_full_src: Path, exec_files: List[str], max_stuck_points: int = 10) -> List[StuckPoint]:
    """
    Perform SPA (Stuck Point Analysis) on a harness.
    
    Args:
        project_bundle: The project bundle containing harness information
        harness_name: Name of the harness to analyze
        harness_info: Harness metadata from cpmeta.json containing classpath, target_method, etc.
        metadata_path: Path to the cpmeta.json file
        cp_full_src: Path to the repository source from CPMetadata
        exec_files: List of exec file paths from command line
        max_stuck_points: Maximum number of stuck points to return
    
    Returns:
        List of StuckPoint objects identified during analysis
    """
    logger.info(f"Performing SPA analysis for harness: {harness_name}")
    
    try:
        # Step 1: Get exec files to merge
        exec_files_to_merge = get_exec_files_to_merge(exec_files)
        if not exec_files_to_merge:
            logger.warning("No exec files found for SPA analysis")
            return []
        
        # Step 2: Merge exec files into a single file
        with tempfile.NamedTemporaryFile(suffix=".exec", delete=False) as tmp_exec:
            merged_exec_path = Path(tmp_exec.name)
        
        merged_exec = merge_exec_files(exec_files_to_merge, merged_exec_path)
        if not merged_exec:
            logger.error("Failed to merge exec files")
            return []
        
        # Step 3: Prepare paths based on the README example
        # Based on real-world example from README:
        # -e /app/crs-cp-java/deepgen/jvm/stuck-point-analyzer/test/imaging/jacoco.exec
        # -j /cp_root/build/out/aixcc/jvm/imaging/jars/one/commons-imaging-1.0.0-alpha6-aixcc.jar
        # -j /cp_root/build/out/aixcc/jvm/imaging/jars/one/imaging-harness-one.jar
        # --entrypoint com.aixcc.imaging.harnesses.one.fuzzerTestOneInput
        # -m /crs-workdir/worker-0/metadata/aixcc/jvm/imaging/cpmeta.json
        # --source-dir /src-imaging
        # --annotated-output-dir /tmp/src-imaging
        
        # Path to stuck-point-analyzer JAR
        spa_jar_path = Path(__file__).parent / "jvm" / "stuck-point-analyzer" / "target" / "stuck-point-analyzer-1.0.0.jar"
        
        if not spa_jar_path.exists():
            logger.error(f"Stuck-point-analyzer JAR not found at: {spa_jar_path}")
            logger.error("Please build the stuck-point-analyzer first (cd stuck-point-analyzer && mvn clean package)")
            return []
        
        # Get harness info from project bundle
        cp_name = project_bundle.name  # e.g., "imaging"
        
        # Get classpath from harness metadata
        # The classpath field contains JAR files and directories (both are supported by the analyzer)
        classpath = harness_info.get("classpath", [])
        if not classpath:
            logger.error(f"No classpath found for harness {harness_name}")
            return []
        
        # Filter out non-existent classpath entries for fault tolerance
        valid_classpath = []
        for cp_entry in classpath:
            cp_path = Path(cp_entry)
            if cp_path.exists():
                valid_classpath.append(cp_entry)
            else:
                logger.warning(f"Classpath entry does not exist, skipping: {cp_entry}")
        
        if not valid_classpath:
            logger.error(f"No valid classpath entries found for harness {harness_name}")
            logger.error(f"All classpath entries were invalid: {classpath}")
            return []
        
        logger.info(f"Using {len(valid_classpath)} valid classpath entries out of {len(classpath)} total")
        
        # Get entry point from harness metadata
        # Format: {target_class}.{target_method}
        target_class = harness_info.get("target_class")
        target_method = harness_info.get("target_method")
        if not target_class or not target_method:
            logger.error(f"Missing target_class or target_method for harness {harness_name}")
            return []
        
        entry_point = f"{target_class}.{target_method}"
        
        # Use the provided metadata_path
        metadata_file = metadata_path
        if not metadata_file.exists():
            logger.error(f"Metadata file not found: {metadata_file}")
            return []
        
        # Use cp_full_src from CPMetadata as the source directory
        source_dir = cp_full_src
        if not source_dir.exists():
            logger.warning(f"Source directory does not exist: {source_dir}")
            logger.warning("Stuck-point-analyzer may fail to generate annotated source")
        
        # Annotated output directory (temporary)
        # Create a unique temp directory with timestamp
        temp_dir_name = f"spa-annotated-{uuid.uuid4().hex[:8]}"
        temp_base = Path("/tmp") / temp_dir_name
        temp_base.mkdir(parents=True, exist_ok=True)
        
        annotated_dir = temp_base
        
        # Output file for results
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp_output:
            output_file = Path(tmp_output.name)
        
        # Step 4: Build command line for stuck-point-analyzer
        cmd = [
            "java", "-jar", str(spa_jar_path),
            "-e", str(merged_exec),
        ]
        
        # Add all valid classpath entries as -j options
        # The analyzer supports both JAR files and directories
        for cp_entry in valid_classpath:
            cmd.extend(["-j", cp_entry])
        
        cmd.extend([
            "--entrypoint", entry_point,
            "-m", str(metadata_file),
            "--source-dir", str(source_dir),
            "--annotated-output-dir", str(annotated_dir),
            "-o", str(output_file),
            "-v"  # Verbose output
        ])
        
        logger.info(f"Running stuck-point-analyzer with command: {' '.join(cmd)}")
        
        # Step 5: Execute the analyzer
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )
        
        if result.returncode != 0:
            logger.error(f"Stuck-point-analyzer failed with code {result.returncode}")
            
            # Log full stderr output
            if result.stderr:
                logger.error("=== FULL STDERR OUTPUT ===")
                for line in result.stderr.splitlines():
                    logger.error(line)
                logger.error("=== END STDERR ===")
            
            # Log full stdout output
            if result.stdout:
                logger.error("=== FULL STDOUT OUTPUT ===")
                for line in result.stdout.splitlines():
                    logger.error(line)
                logger.error("=== END STDOUT ===")
            
            logger.info("Command was: " + " ".join(cmd))
            return []
        
        logger.info("Stuck-point-analyzer completed successfully")
        
        # Log full stdout for debugging (even on success)
        if result.stdout:
            logger.info("=== ANALYZER STDOUT ===")
            for line in result.stdout.splitlines():
                logger.info(line)
            logger.info("=== END STDOUT ===")
        
        # Also log stderr if any (even on success)
        if result.stderr:
            logger.warning("=== ANALYZER STDERR (success but with warnings) ===")
            for line in result.stderr.splitlines():
                logger.warning(line)
            logger.warning("=== END STDERR ===")
        
        # Check if annotated directory was created
        if not annotated_dir.exists():
            logger.warning(f"Annotated directory was not created at: {annotated_dir}")
            logger.warning("The analyzer may have failed to create annotated source files")
        else:
            # List what's in the annotated directory
            files = os.listdir(annotated_dir)
            logger.info(f"Annotated directory contains {len(files)} items: {files}")
        
        # Step 6: Parse the output JSON
        if not output_file.exists():
            logger.error(f"Output file not found: {output_file}")
            return []
        
        with open(output_file) as f:
            analysis_result = json.load(f)
        
        # Step 7: Extract stuck points from results
        stuck_points_data = analysis_result.get("stuckPoints", [])
        if not stuck_points_data:
            logger.warning(f"No stuck points found in analysis result for harness {harness_name}")
            return []
        
        stuck_points = []
        for i, sp_data in enumerate(stuck_points_data[:max_stuck_points]):
            try:
                stuck_point = StuckPoint(sp_data)
                # Set the annotated source directory for this stuck point
                stuck_point.annotated_source_dir = str(annotated_dir)
                stuck_points.append(stuck_point)
            except ValueError as e:
                logger.error(f"Failed to parse stuck point {i}: {e}")
                logger.error(f"Stuck point data: {sp_data}")
                # This is a fatal error - our tool should always produce valid data
                raise
        
        logger.info(f"Successfully parsed {len(stuck_points)} stuck points for harness {harness_name}")
        
        # Final check for annotated directory
        if not annotated_dir.exists():
            logger.warning(f"Annotated source directory does not exist: {annotated_dir}")
            logger.warning(f"Stuck points will be processed without annotated source")
            # Don't fail - we still have the stuck points data
        
        return stuck_points
            
    except subprocess.TimeoutExpired:
        logger.error("Stuck-point-analyzer timed out")
        return []
    except Exception as e:
        logger.error(f"Error during SPA analysis: {e}", exc_info=True)
        return []

async def add_spa_tasks(
    engine: DeepGenEngine,
    project_bundle: Project,
    harnesses: dict,
    weighted_models: dict,
    metadata_path: Path,           # Path to cpmeta.json
    cp_full_src: Path,         # Full source path from CPMetadata
    exec_files: List[str],         # List of exec file paths from command line
    run_time: int,                 # Total runtime limit in seconds
    workdir: Path,
    interval_seconds: int = 300,  # X seconds interval (default 5 minutes)
    max_stuck_points: int = 5,     # Y stuck points to process (default 5)
):
    """
    Periodically perform SPA analysis and add StuckPointAnaSeedGen tasks.
    
    Args:
        engine: The DeepGen engine to add tasks to
        project_bundle: Project information
        harnesses: Dictionary of harness configurations
        weighted_models: Model weights for task generation
        metadata_path: Path to cpmeta.json file
        cp_full_src: Full source path from CPMetadata
        exec_files: List of exec file paths from command line
        run_time: Total runtime limit in seconds
        interval_seconds: Interval between SPA analyses (X seconds)
        max_stuck_points: Maximum number of stuck points to process per analysis (Y)
    """
    logger.info(f"Starting SPA task monitor with interval={interval_seconds}s, max_stuck_points={max_stuck_points}, run_time={run_time}s")
    
    start_time = time.time()
    last_analysis_start = start_time
    
    while True:
        try:
            current_time = time.time()
            elapsed_time = current_time - start_time
            
            # Check if we've exceeded the total runtime
            if elapsed_time >= run_time:
                logger.info(f"SPA task monitor reached runtime limit ({run_time}s), shutting down")
                break
            
            # Check if enough time has passed since last analysis started
            if current_time - last_analysis_start >= interval_seconds:
                last_analysis_start = current_time
                logger.info(f"Starting SPA analysis cycle at {current_time}")
                
                # Analyze each harness
                for harness_name, harness_info in harnesses.items():
                    if "target_method" not in harness_info:
                        logger.warning(f"Skipping harness {harness_name}: missing target_method")
                        continue
                    
                    target_method = harness_info["target_method"]
                    
                    # Perform SPA analysis
                    stuck_points = await spa_analyze(project_bundle, harness_name, harness_info, metadata_path, cp_full_src, exec_files, max_stuck_points)
                    
                    if not stuck_points:
                        logger.info(f"No stuck points found for harness {harness_name}")
                        continue
                    
                    # Get annotated source directory from first stuck point
                    # All stuck points from same analysis share the same annotated source
                    annotated_source_dir = stuck_points[0].annotated_source_dir
                    logger.info(f"Annotated source directory from stuck point: {annotated_source_dir}")
                    
                    if not annotated_source_dir:
                        logger.error(f"Annotated source directory not set for stuck points in harness {harness_name}")
                        logger.error("Cannot proceed without annotated source - skipping this round of generation")
                        continue
                    
                    # Verify the annotated directory exists
                    if not Path(annotated_source_dir).exists():
                        logger.error(f"Annotated source directory does not exist: {annotated_source_dir}")
                        logger.error("Cannot proceed without annotated source - skipping this round of generation")
                        continue
                    
                    # Create a modified project bundle that uses the annotated source
                    try:
                        annotated_bundle = Project(
                            oss_fuzz_home=Path(annotated_source_dir) / "oss-fuzz",
                            project_name=project_bundle.name,
                            local_repo_path=Path(annotated_source_dir) / "repo",
                        )
                        # Prepare the bundle with the working directory
                        annotated_bundle = annotated_bundle.prepare_project_bundle(workdir)
                    except Exception as e:
                        logger.error(f"Failed to create annotated project bundle: {e} {traceback.format_exc()}")
                        logger.error("Skipping this round of generation")
                        continue
                    
                    # Process stuck points
                    for i, stuck_point in enumerate(stuck_points):
                        logger.info(f"Creating StuckPointAnaSeedGen task for harness {harness_name}, stuck point {i+1}/{len(stuck_points)}")
                        
                        task = StuckPointAnaSeedGen(
                            project_bundle=annotated_bundle,  # Use annotated bundle
                            harness_name=harness_name,
                            harness_entrypoint_func=target_method,
                            stuck_point=stuck_point,
                            is_jvm=True,
                            weighted_models=weighted_models,
                            priority=5,
                            dev_attempts=3,
                            dev_cost=6.0,
                            num_repeat=1,
                            max_exec=100000,
                        )
                        
                        task_id = await engine.add_task(task)
                        logger.info(f"Added StuckPointAnaSeedGen task with ID: {task_id}")
                
                logger.info(f"SPA analysis cycle completed, next cycle in {interval_seconds}s")
            
            # Sleep for a short time before checking again
            await asyncio.sleep(1)  # Check every 1 second
            
        except asyncio.CancelledError:
            logger.info("SPA task monitor cancelled")
            break
        except Exception as e:
            logger.error(f"Error in SPA task monitor: {e}", exc_info=True)
            # Continue monitoring even if there's an error
            await asyncio.sleep(1)