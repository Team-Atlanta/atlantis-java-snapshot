#!/usr/bin/env python3
"""
Retrieve metadata for a sink definition given its ID.
"""

import yaml
import sys
from pathlib import Path


def get_sink_id(model_data):
    """Generate the ID string for a sink model."""
    subtypes_str = "true" if model_data['subtypes'] else "false"
    return f"Sink: {model_data['package']}; {model_data['type']}; {subtypes_str}; {model_data['name']}; {model_data['signature']}; {model_data['ext']}; {model_data['input']}; {model_data['kind']}; {model_data['provenance']}"


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 scripts/get_metadata.py <sink_id>", file=sys.stderr)
        sys.exit(1)

    target_id = sys.argv[1]

    # Setup paths
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent
    sink_defs_file = repo_root / "sink_definitions.yml"

    # Load sink definitions
    try:
        with open(sink_defs_file, 'r') as f:
            data = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Error: Sink definitions file '{sink_defs_file}' not found", file=sys.stderr)
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error parsing YAML file '{sink_defs_file}': {e}", file=sys.stderr)
        sys.exit(1)

    # Find matching sink definition
    for sink_def in data['sink_definitions']:
        sink_id = get_sink_id(sink_def['model'])
        if sink_id == target_id:
            # Output the metadata as YAML
            yaml.dump(sink_def['metadata'], sys.stdout, default_flow_style=False)
            return

    # If we get here, no matching sink was found
    print(f"Error: No sink definition found for ID: {target_id}", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
