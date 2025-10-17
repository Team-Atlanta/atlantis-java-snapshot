#!/usr/bin/env python3

import sys
from pathlib import Path
import yaml
from collections import defaultdict

# This script requires the PyYAML package.
# You can install it using: pip install pyyaml

def extract_harnesses_with_cpvs():
    """
    Finds all .aixcc/config.yaml files under cp_root/projects/aixcc/jvm,
    extracts project and harness names where the harness has a non-empty
    'cpvs' list, and returns the results grouped by project.
    """
    search_dir = Path("cp_root/projects/aixcc/jvm")
    projects_root = Path("cp_root/projects")
    # Use a defaultdict to easily group harnesses by project
    results = defaultdict(list)

    if not search_dir.is_dir():
        print(f"Error: Directory not found: {search_dir}", file=sys.stderr)
        sys.exit(1)

    config_files = search_dir.rglob("*/.aixcc/config.yaml")

    for config_file in config_files:
        try:
            # The project directory is one level above '.aixcc'.
            project_dir = config_file.parents[1]
            project_name = str(project_dir.relative_to(projects_root))

            with open(config_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            if not data:
                continue

            harness_list = data.get('harness_files')
            if not isinstance(harness_list, list):
                continue

            for harness_data in harness_list:
                if not isinstance(harness_data, dict) or 'name' not in harness_data:
                    continue

                if harness_data.get('cpvs'):
                    harness_name = harness_data['name']
                    # Append the harness to the list for this project
                    results[project_name].append(harness_name)

        except (IOError, yaml.YAMLError) as e:
            print(f"Warning: Could not process {config_file}: {e}", file=sys.stderr)
        except (IndexError, ValueError) as e:
            print(f"Warning: Could not determine project name for {config_file}: {e}", file=sys.stderr)

    # Convert defaultdict back to a regular dict for the return value
    return dict(results)

if __name__ == "__main__":
    grouped_harnesses = extract_harnesses_with_cpvs()
    if grouped_harnesses:
        print("Found the following projects and harnesses with non-empty 'cpvs':\n")
        # Sort projects by name for consistent output
        for project, harnesses in sorted(grouped_harnesses.items()):
            print(f"bash dev.sh test {project} {','.join(harnesses)} 7200 true")
    else:
        print("No harnesses with non-empty 'cpvs' found in the specified directory.")
