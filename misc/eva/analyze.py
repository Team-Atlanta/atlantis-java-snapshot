#!/usr/bin/env python3

import argparse
import json
import yaml
import os
import glob
import re
from collections import defaultdict
from tabulate import tabulate
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class HarnessFuzzerStatus:
    harness: str
    fuzzer_type: str
    fuzzer_instance: str
    status: str  # "exploited", "reached", "in-the-wild"

@dataclass
class CPVResult:
    cpv_type: str
    harness_fuzzer_statuses: List[HarnessFuzzerStatus]

CPVResults = Dict[str, CPVResult]

def is_security_bug(vuln_type):
    """Check if a vulnerability type is security-related"""
    non_security_prefixes = ["NONSEC", "timeout", "OOM", "StackOverflow"]
    return not any(vuln_type.startswith(prefix) for prefix in non_security_prefixes)


def match_cpv_to_crash(cpv_sinkpoints, crash_frames):
    """Check if CPV sinkpoints match any crash stack frames"""
    # Get trigger sinkpoints only
    trigger_sinkpoints = [sp for sp in cpv_sinkpoints if sp.get("comment") == "trigger"]
    
    for sinkpoint in trigger_sinkpoints:
        sp_class = sinkpoint["class_name"]
        sp_method = sinkpoint["method_name"]
        sp_line = sinkpoint["line_num"]
        
        # Create search patterns
        class_method_pattern = f"{sp_class}.{sp_method}"
        line_pattern = f":{sp_line})"
        
        for frame in crash_frames:
            if class_method_pattern in frame and line_pattern in frame:
                return True
    
    return False

def match_cpv_to_beep(cpv_sinkpoints, beep_coordinate):
    """Check if CPV sinkpoints match beep coordinate"""
    # Get trigger sinkpoints only
    trigger_sinkpoints = [sp for sp in cpv_sinkpoints if sp.get("comment") == "trigger"]
    
    for sinkpoint in trigger_sinkpoints:
        sp_class = sinkpoint["class_name"].replace(".", "/")  # Convert to beep format
        sp_method = sinkpoint["method_name"]
        sp_line = sinkpoint["line_num"]
        
        beep_class = beep_coordinate["class_name"]
        beep_method = beep_coordinate["method_name"]
        beep_line = beep_coordinate["line_num"]
        
        if (beep_class == sp_class and 
            beep_method == sp_method and 
            beep_line == sp_line):
            return True
    
    return False

def load_project_cpvs(benchmarks_file, project_name):
    """Load CPV information for a project from benchmarks.yaml"""
    with open(benchmarks_file, 'r') as f:
        data = yaml.safe_load(f)
    
    project_data = data.get("cps", {}).get(project_name, {})
    if not project_data:
        raise ValueError(f"Project {project_name} not found in benchmarks.yaml")
    
    harnesses = project_data.get("harnesses", {})
    return harnesses

def load_crash_data(result_file):
    """Load crash data from result.json"""
    # One crash data json example: crs-workdir/aixcc/jvm/activemq/HarnessRunner/ActivemqOne/fuzz/atljazzer-r16/result.json
    if not os.path.exists(result_file):
        return []
    
    with open(result_file, 'r') as f:
        data = json.load(f)
    
    crashes = data.get("fuzz_data", {}).get("log_dedup_crash_over_time", [])
    security_crashes = []
    
    for crash in crashes:
        if len(crash) >= 4:
            vuln_type = crash[1]
            stack_frames = crash[3]
            
            if is_security_bug(vuln_type):
                security_crashes.append({
                    "vuln_type": vuln_type,
                    "stack_frames": stack_frames
                })
    
    return security_crashes

def load_beep_data(beeps_dir):
    """Load beep coordinate data from beeps directory"""
    # One beepseed example: crs-workdir/aixcc/jvm/activemq/HarnessRunner/ActivemqOne/fuzz/atljazzer-r0/beeps/sink-9c8897d3e68e2ecc-2808489792223418751.json
    beep_coordinates = []
    
    if not os.path.exists(beeps_dir):
        return beep_coordinates
    
    # Find all JSON files except xcode.json
    json_files = glob.glob(os.path.join(beeps_dir, "*.json"))
    
    for json_file in json_files:
        if os.path.basename(json_file) == "xcode.json":
            continue
        
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            coordinate = data.get("coordinate", {})
            if coordinate:
                beep_coordinates.append(coordinate)
        except:
            continue
    
    return beep_coordinates

def analyze_project(project_name, base_dir="crs-workdir") -> CPVResults:
    """Analyze CVE status for a project"""
    benchmarks_file = "misc/eva/benchmarks.yaml"
    
    # Load project CPVs
    try:
        harnesses = load_project_cpvs(benchmarks_file, project_name)
    except ValueError as e:
        print(f"Error: {e}")
        return {}
    
    # Dictionary to store CPV info
    cpv_results: CPVResults = {}
    
    for harness_name, harness_data in harnesses.items():
        cpvs = harness_data.get("cpvs", {})
        
        # Get simple harness name (e.g., "ActivemqOne" from "com.aixcc.activemq.harnesses.one.ActivemqOne")
        simple_harness = harness_name.split(".")[-1]
        
        # Find all fuzz results for this harness
        harness_dir = os.path.join(base_dir, project_name, "HarnessRunner", simple_harness, "fuzz")
        
        if not os.path.exists(harness_dir):
            continue
        
        # Get all fuzz run directories
        fuzz_dirs = [d for d in os.listdir(harness_dir) if os.path.isdir(os.path.join(harness_dir, d))]
        
        # Analyze each CPV
        for cpv_id, cpv_data in cpvs.items():
            cpv_type = cpv_data.get("type", "Unknown")
            sinkpoints = cpv_data.get("sinkpoint_coords", [])
            
            # Initialize CPV entry if not exists
            if cpv_id not in cpv_results:
                cpv_results[cpv_id] = CPVResult(
                    cpv_type=cpv_type,
                    harness_fuzzer_statuses=[]
                )
            
            # Analyze each fuzzer instance
            for fuzz_dir in fuzz_dirs:
                fuzz_path = os.path.join(harness_dir, fuzz_dir)
                
                # Extract fuzzer type from directory name (e.g., "atljazzer-r0" -> "atljazzer")
                fuzzer_type = fuzz_dir.rsplit("-", 1)[0]
                
                # Load crash data for this instance
                result_file = os.path.join(fuzz_path, "result.json")
                crashes = load_crash_data(result_file)
                
                # Load beep data for this instance
                beeps_dir = os.path.join(fuzz_path, "beeps")
                beeps = load_beep_data(beeps_dir)
                
                # Check if exploited for this instance
                exploited = False
                for crash in crashes:
                    if match_cpv_to_crash(sinkpoints, crash["stack_frames"]):
                        exploited = True
                        break
                
                # Check if reached for this instance
                reached = False
                if not exploited:  # Only check reached if not exploited
                    for beep in beeps:
                        if match_cpv_to_beep(sinkpoints, beep):
                            reached = True
                            break
                
                # Determine status for this instance
                if exploited:
                    status = "exploited"
                elif reached:
                    status = "reached"
                else:
                    status = "in-the-wild"
                
                cpv_results[cpv_id].harness_fuzzer_statuses.append(
                    HarnessFuzzerStatus(
                        harness=simple_harness,
                        fuzzer_type=fuzzer_type,
                        fuzzer_instance=fuzz_dir,
                        status=status
                    )
                )
    
    return cpv_results

def print_table(project_name: str, cpv_results: CPVResults):
    """Print table output for CPV analysis results"""
    if not cpv_results:
        print(f"No results found for project: {project_name}")
        return
    
    # Prepare table data
    table_data = []
    for cpv_id, cpv_data in cpv_results.items():
        cpv_type = cpv_data.cpv_type
        
        # Group by harness, then by fuzzer_type
        harness_groups = {}
        for hfs in cpv_data.harness_fuzzer_statuses:
            harness = hfs.harness
            fuzzer_type = hfs.fuzzer_type
            status = hfs.status
            
            if harness not in harness_groups:
                harness_groups[harness] = {}
            if fuzzer_type not in harness_groups[harness]:
                harness_groups[harness][fuzzer_type] = {"exploited": 0, "reached": 0, "in-the-wild": 0}
            
            harness_groups[harness][fuzzer_type][status] += 1
        
        # Create separate status columns
        exploited_lines = []
        reached_lines = []
        in_the_wild_lines = []
        
        for harness, fuzzer_types in sorted(harness_groups.items()):
            exploited_lines.append(f"{harness}:")
            reached_lines.append(f"{harness}:")
            in_the_wild_lines.append(f"{harness}:")
            
            for fuzzer_type, counts in sorted(fuzzer_types.items()):
                total = counts["exploited"] + counts["reached"] + counts["in-the-wild"]
                
                # Add counts to respective columns
                exploited_lines.append(f"  {fuzzer_type}: {counts['exploited']}/{total}")
                reached_lines.append(f"  {fuzzer_type}: {counts['reached']}/{total}")
                in_the_wild_lines.append(f"  {fuzzer_type}: {counts['in-the-wild']}/{total}")
        
        exploited_multiline = "\n".join(exploited_lines)
        reached_multiline = "\n".join(reached_lines)
        in_the_wild_multiline = "\n".join(in_the_wild_lines)
        
        table_data.append([
            cpv_id,
            cpv_type,
            exploited_multiline,
            reached_multiline,
            in_the_wild_multiline
        ])
    
    # Sort by CPV ID
    table_data.sort(key=lambda x: x[0])
    
    # Print table
    headers = ["CPV ID", "CPV Type", "Exploited", "Reached", "In-the-wild"]
    print(f"\nCPV Analysis Results for {project_name}:")
    print("=" * 80)
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    # Print summary
    status_priority = {"exploited": 3, "reached": 2, "in-the-wild": 1}
    cpv_overall_status = {}
    cpv_harnesses = {}  # cpv_id -> set of harnesses that have this CPV
    
    for cpv_id, cpv_data in cpv_results.items():
        # Get best status across all harness+fuzzer combinations for this CPV
        best_status = "in-the-wild"
        best_priority = 0
        
        # Collect unique harnesses for this CPV
        harnesses = set()
        for hfs in cpv_data.harness_fuzzer_statuses:
            harnesses.add(hfs.harness)
            status = hfs.status
            priority = status_priority.get(status, 0)
            if priority > best_priority:
                best_priority = priority
                best_status = status
        
        cpv_overall_status[cpv_id] = best_status
        cpv_harnesses[cpv_id] = harnesses
    
    # Group CPVs by status and collect harnesses
    status_cpv_harnesses = defaultdict(set)
    for cpv_id, status in cpv_overall_status.items():
        status_cpv_harnesses[status].update(cpv_harnesses[cpv_id])
    
    # Count overall CPV statuses
    status_counts = defaultdict(int)
    for status in cpv_overall_status.values():
        status_counts[status] += 1
    
    print(f"\nSummary:")
    print(f"Total-CPVs: {len(cpv_results)}")
    for status in ["exploited", "reached", "in-the-wild"]:
        if status in status_counts:
            harnesses_list = sorted(list(status_cpv_harnesses[status]))
            harnesses_str = " ".join(harnesses_list)
            print(f"{status.capitalize()}: {status_counts[status]} {project_name} {harnesses_str}")

def beep_command(project_name, cpv_name, base_dir="crs-workdir"):
    """Find and print paths of matched beep seeds for a specific CPV"""
    benchmarks_file = "misc/eva/benchmarks.yaml"
    
    # Load project CPVs
    try:
        harnesses = load_project_cpvs(benchmarks_file, project_name)
    except ValueError as e:
        print(f"Error: {e}")
        return
    
    # Find the CPV across all harnesses
    target_cpv = None
    for harness_name, harness_data in harnesses.items():
        cpvs = harness_data.get("cpvs", {})
        if cpv_name in cpvs:
            target_cpv = cpvs[cpv_name]
            break
    
    if not target_cpv:
        print(f"Error: CPV {cpv_name} not found in project {project_name}")
        return
    
    sinkpoints = target_cpv.get("sinkpoint_coords", [])
    beep_paths = []
    
    # Search through all harnesses and fuzz directories
    for harness_name, harness_data in harnesses.items():
        simple_harness = harness_name.split(".")[-1]
        harness_dir = os.path.join(base_dir, project_name, "HarnessRunner", simple_harness, "fuzz")
        
        if not os.path.exists(harness_dir):
            continue
            
        # Get all fuzz run directories
        fuzz_dirs = [d for d in os.listdir(harness_dir) if os.path.isdir(os.path.join(harness_dir, d))]
        
        for fuzz_dir in fuzz_dirs:
            fuzz_path = os.path.join(harness_dir, fuzz_dir)
            beeps_dir = os.path.join(fuzz_path, "beeps")
            
            if not os.path.exists(beeps_dir):
                continue
                
            # Find all JSON files except xcode.json
            json_files = glob.glob(os.path.join(beeps_dir, "*.json"))
            
            for json_file in json_files:
                if os.path.basename(json_file) == "xcode.json":
                    continue
                    
                try:
                    with open(json_file, 'r') as f:
                        data = json.load(f)
                    
                    coordinate = data.get("coordinate", {})
                    if coordinate and match_cpv_to_beep(sinkpoints, coordinate):
                        beep_paths.append(json_file)
                except:
                    continue
    
    # Print all matched beep seed paths
    for path in sorted(beep_paths):
        print(path)

def get_cpv_status(full_project_name, cpv_id, base_dir="crs-workdir"):
    """Get the status of a specific CPV in a specific project"""
    # Load project CPVs
    try:
        harnesses = load_project_cpvs("misc/eva/benchmarks.yaml", full_project_name)
    except ValueError:
        return "in-the-wild"  # Default if project not found
    
    status_priority = {"exploited": 3, "reached": 2, "in-the-wild": 1}
    best_status = "in-the-wild"
    best_priority = 0
    
    for harness_name, harness_data in harnesses.items():
        cpvs = harness_data.get("cpvs", {})
        if cpv_id not in cpvs:
            continue
            
        cpv_data = cpvs[cpv_id]
        sinkpoints = cpv_data.get("sinkpoint_coords", [])
        
        # Get simple harness name
        simple_harness = harness_name.split(".")[-1]
        
        # Find all fuzz results for this harness
        harness_dir = os.path.join(base_dir, full_project_name, "HarnessRunner", simple_harness, "fuzz")
        
        if not os.path.exists(harness_dir):
            continue
            
        # Get all fuzz run directories
        fuzz_dirs = [d for d in os.listdir(harness_dir) if os.path.isdir(os.path.join(harness_dir, d))]
        
        # Analyze each fuzzer instance
        for fuzz_dir in fuzz_dirs:
            fuzz_path = os.path.join(harness_dir, fuzz_dir)
            
            # Load crash data for this instance
            result_file = os.path.join(fuzz_path, "result.json")
            crashes = load_crash_data(result_file)
            
            # Load beep data for this instance
            beeps_dir = os.path.join(fuzz_path, "beeps")
            beeps = load_beep_data(beeps_dir)
            
            # Check if exploited for this instance
            exploited = False
            for crash in crashes:
                if match_cpv_to_crash(sinkpoints, crash["stack_frames"]):
                    exploited = True
                    break
            
            # Check if reached for this instance
            reached = False
            if not exploited:  # Only check reached if not exploited
                for beep in beeps:
                    if match_cpv_to_beep(sinkpoints, beep):
                        reached = True
                        break
            
            # Determine status for this instance
            if exploited:
                status = "exploited"
            elif reached:
                status = "reached"
            else:
                status = "in-the-wild"
            
            # Update best status
            priority = status_priority.get(status, 0)
            if priority > best_priority:
                best_priority = priority
                best_status = status
    
    return best_status

def sinks_command(regex_pattern, filter_status=None, output_format="csv"):
    """Convert project CPV data to CSV or TOML format showing sinks with trigger comments that match regex"""
    benchmarks_file = "misc/eva/benchmarks.yaml"
    
    # Load all projects from benchmarks.yaml
    try:
        with open(benchmarks_file, 'r') as f:
            data = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Error: {benchmarks_file} not found")
        return
    
    # Compile regex pattern
    try:
        pattern = re.compile(regex_pattern)
    except re.error as e:
        print(f"Error: Invalid regex pattern: {e}")
        return
    
    # Collect all CPVs from all projects
    cpv_dict = {}  # key: (project_short_name, cpv_id), value: {path, line, harnesses, full_project_name}
    
    projects = data.get("cps", {})
    for project_name, project_data in projects.items():
        # Extract short project name (e.g., "aixcc/jvm/activemq" -> "activemq")
        project_short_name = project_name.split("/")[-1]
        
        harnesses = project_data.get("harnesses", {})
        for harness_name, harness_data in harnesses.items():
            cpvs = harness_data.get("cpvs", {})
            
            # Extract simple harness name
            simple_harness = harness_name.split(".")[-1]
            
            for cpv_id, cpv_data in cpvs.items():
                # Create CPV identifier
                cpv_identifier = f"{project_short_name}.{cpv_id}"
                
                # Check if this CPV matches the regex
                if pattern.search(cpv_identifier):
                    sinkpoints = cpv_data.get("sinkpoint_coords", [])
                    
                    # Find trigger sinkpoints
                    trigger_sinkpoints = [sp for sp in sinkpoints if sp.get("comment") == "trigger"]
                    
                    # TODO: Currently only using the first trigger sinkpoint when multiple exist
                    # Some CPVs have multiple trigger sinkpoints (e.g., activemq.cpv_0 has 12),
                    # but we only output the first one to keep section names simple
                    if trigger_sinkpoints:
                        sinkpoint = trigger_sinkpoints[0]  # Just take the first one
                        
                        # Convert class name to file path
                        class_name = sinkpoint["class_name"]
                        file_name = sinkpoint["file_name"]
                        
                        # Create path based on class name structure
                        class_path_parts = class_name.split(".")
                        path = f"repo/src/main/java/{'/'.join(class_path_parts[:-1])}/{file_name}"
                        
                        cpv_key = (project_short_name, cpv_id)
                        if cpv_key not in cpv_dict:
                            cpv_dict[cpv_key] = {
                                'path': path,
                                'line': sinkpoint["line_num"],
                                'class_name': class_name,
                                'harnesses': [],
                                'full_project_name': project_name
                            }
                        
                        cpv_dict[cpv_key]['harnesses'].append(simple_harness)
    
    # Filter by status if specified
    if filter_status:
        # Determine valid statuses based on filter_status
        if filter_status == "all":
            valid_statuses = {"exploited", "reached", "in-the-wild"}
        else:
            valid_statuses = {filter_status}
        
        # Filter CPVs by status
        filtered_cpvs = {}
        for cpv_key, cpv_data in cpv_dict.items():
            project_short_name, cpv_id = cpv_key
            full_project_name = cpv_data['full_project_name']
            
            # Get the status of this CPV
            status = get_cpv_status(full_project_name, cpv_id)
            
            # Only include if status matches filter
            if status in valid_statuses:
                filtered_cpvs[cpv_key] = cpv_data
        
        cpv_dict = filtered_cpvs
    
    # Sort by section name for consistent output
    sorted_cpvs = sorted(cpv_dict.items(), key=lambda x: f"{x[0][0]}.{x[0][1]}")
    
    if output_format == "toml":
        # Output TOML format (original lpg-format)
        for (project_short_name, cpv_id), cpv_data in sorted_cpvs:
            section_name = f"{project_short_name}.{cpv_id}"
            print(f"[{section_name}]")
            print(f'path = "{cpv_data["path"]}"')
            print(f'line = {cpv_data["line"]}')
            print(f'class_name = "{cpv_data["class_name"]}"')
            
            # Format harness as string or list
            harnesses = cpv_data['harnesses']
            if len(harnesses) == 1:
                print(f'harness = "{harnesses[0]}"')
            else:
                harness_list = ', '.join(f'"{h}"' for h in harnesses)
                print(f'harness = [{harness_list}]')
            print()
    else:  # csv format
        # Output CSV format (coordinate-based sinkpoints format)
        # Format: caller#className#methodName#methodDesc#fileName#lineNumber#bytecodeOffset#markDesc
        print("########")
        print("# Generated by misc/eva/analyze.py")
        print("# API-based sinkpoints (format: api#calleeClassName#methodName#methodDesc#markDesc)")
        print("# Coordinate-based sinkpoints (format: caller#className#methodName#methodDesc#fileName#lineNumber#bytecodeOffset#markDesc)")
        print("########")
        
        for (project_short_name, cpv_id), cpv_data in sorted_cpvs:
            # Convert path to class name and method name
            # Extract class name from path
            path = cpv_data["path"]
            line = cpv_data["line"]
            
            # Extract class name from path (e.g., "repo/src/main/java/org/apache/batik/util/ParsedURLData.java" -> "org.apache.batik.util.ParsedURLData")
            if path.startswith("repo/src/main/java/"):
                class_path = path[len("repo/src/main/java/"):]
                if class_path.endswith(".java"):
                    class_path = class_path[:-5]  # Remove .java extension
                class_name = class_path.replace("/", ".")
            else:
                # Fallback: try to extract from path
                class_name = path.split("/")[-1]
                if class_name.endswith(".java"):
                    class_name = class_name[:-5]
            
            # Extract file name
            file_name = path.split("/")[-1]
            
            # For CSV format, we need to generate coordinate-based sinkpoints
            # Format: caller#className#methodName#methodDesc#fileName#lineNumber#bytecodeOffset#markDesc
            # Since we don't have method information, we'll use placeholder values
            caller = "unknown"
            method_name = "unknown"
            method_desc = "unknown"
            bytecode_offset = "-1"
            mark_desc = f"sink-{project_short_name}-{cpv_id}"
            
            csv_line = f"{caller}#{class_name}#{method_name}#{method_desc}#{file_name}#{line}#{bytecode_offset}#{mark_desc}"
            print(csv_line)

def main():
    parser = argparse.ArgumentParser(description="Analyze project CPV status")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Stat/Sum subcommand (existing functionality)
    stat_parser = subparsers.add_parser("stat", aliases=["sum"], help="Generate CPV statistics table")
    stat_parser.add_argument("project_name", help="Project name (e.g., 'aixcc/jvm/activemq')")
    
    # Beep subcommand (new functionality)
    beep_parser = subparsers.add_parser("beep", help="Find paths of matched beep seeds")
    beep_parser.add_argument("project_name", help="Project name (e.g., 'aixcc/jvm/activemq')")
    beep_parser.add_argument("cpv_name", help="CPV name (e.g., 'cpv_0')")
    
    # Sinks subcommand (new functionality)
    sinks_parser = subparsers.add_parser("sinks", help="Convert project CPV data to CSV or TOML format")
    sinks_parser.add_argument("regex_pattern", help=r"Regex pattern to match CPV identifiers (e.g., 'activemq.*', 'batik\.cpv_0')")
    
    # Status filtering options (mutually exclusive)
    status_group = sinks_parser.add_mutually_exclusive_group()
    status_group.add_argument("--all", action="store_true", help="Show all CPVs (exploited, reached, in-the-wild)")
    status_group.add_argument("--exploited", action="store_true", help="Show only exploited CPVs")
    status_group.add_argument("--reached", action="store_true", help="Show only reached CPVs")
    status_group.add_argument("--in-the-wild", action="store_true", help="Show only in-the-wild CPVs")
    
    # Format options (mutually exclusive)
    format_group = sinks_parser.add_mutually_exclusive_group()
    format_group.add_argument("--csv-format", action="store_true", help="Output in CSV format (coordinate-based sinkpoints format) - default")
    format_group.add_argument("--lpg-format", action="store_true", help="Output in TOML format (original lpg format)")
    
    args = parser.parse_args()
    
    if args.command in ["stat", "sum"]:
        cpv_results = analyze_project(args.project_name)
        print_table(args.project_name, cpv_results)
    elif args.command == "beep":
        beep_command(args.project_name, args.cpv_name)
    elif args.command == "sinks":
        # Determine filter status based on arguments
        filter_status = None
        if args.all:
            filter_status = "all"
        elif args.exploited:
            filter_status = "exploited"
        elif args.reached:
            filter_status = "reached"
        elif args.in_the_wild:
            filter_status = "in-the-wild"
        
        # Determine output format (default to csv)
        output_format = "csv"
        if args.lpg_format:
            output_format = "toml"
        
        sinks_command(args.regex_pattern, filter_status, output_format)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()