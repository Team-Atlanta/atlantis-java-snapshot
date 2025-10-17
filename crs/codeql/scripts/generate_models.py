#!/usr/bin/env python3
"""
Generate CodeQL model and query files from centralized sink definitions.
"""

import yaml
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
from collections import defaultdict
import sys
import os
from dataclasses import dataclass
from typing import List, Dict, Set


@dataclass
class Sink:
    """Represents a sink definition with all required properties."""
    package: str
    class_name: str
    subtypes: bool
    name: str
    signature: str
    ext: str
    input_arg: str
    kind: str
    provenance: str
    metadata: Dict

    @classmethod
    def from_dict(cls, data: Dict) -> 'Sink':
        """Create a Sink instance from a dictionary."""
        model_data = data['model']
        return cls(
            package=model_data['package'],
            class_name=model_data['type'],
            subtypes=model_data['subtypes'],
            name=model_data['name'],
            signature=model_data['signature'],
            ext=model_data['ext'],
            input_arg=model_data['input'],
            kind=model_data['kind'],
            provenance=model_data['provenance'],
            metadata=data['metadata']
        )

    def to_model_tuple(self) -> List:
        """Convert sink to model tuple format for CodeQL."""
        return [
            self.package,
            self.class_name,
            self.subtypes,
            self.name,
            self.signature,
            self.ext,
            self.input_arg,
            self.kind,
            self.provenance
        ]

    def get_id(self) -> str:
        """Generate the ID string for this sink definition."""
        subtypes_str = "true" if self.subtypes else "false"
        return f"Sink: {self.package}; {self.class_name}; {subtypes_str}; {self.name}; {self.signature}; {self.ext}; {self.input_arg}; {self.kind}; {self.provenance}"


def load_sink_definitions(file_path) -> List[Sink]:
    """Load sink definitions from YAML file and return list of Sink objects."""
    try:
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Error: Sink definitions file '{file_path}' not found", file=sys.stderr)
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error parsing YAML file '{file_path}': {e}", file=sys.stderr)
        sys.exit(1)

    if 'sink_definitions' not in data:
        print("Error: Invalid sink definitions format - missing 'sink_definitions' key", file=sys.stderr)
        sys.exit(1)

    # Convert dictionary data to Sink objects
    sinks = []
    for sink_data in data['sink_definitions']:
        try:
            sink = Sink.from_dict(sink_data)
            sinks.append(sink)
        except KeyError as e:
            print(f"Error: Missing required field {e} in sink definition: {sink_data}", file=sys.stderr)
            sys.exit(1)

    return sinks


def group_sinks_by_package(sinks: List[Sink]) -> Dict[str, List[Sink]]:
    """Group sink definitions by package for separate model files."""
    grouped = defaultdict(list)
    for sink in sinks:
        grouped[sink.package].append(sink)
    return grouped


def generate_model_files(grouped_sinks, template_env, output_dir):
    """Generate model files for each package."""
    model_template = template_env.get_template('model.yml.j2')

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    generated_files = []
    for package, sinks in grouped_sinks.items():
        # Convert package name to filename (e.g., java.io -> java.io.model.yml)
        output_file = output_dir / f"{package}.model.yml"
        content = model_template.render(sinks=sinks)

        with open(output_file, 'w') as f:
            f.write(content)

        generated_files.append(output_file)
        print(f"Generated model file: {output_file}")

    return generated_files


def generate_query_file(sinks: List[Sink], template_env, output_file):
    """Generate the sinks.ql file with all sink types."""
    query_template = template_env.get_template('sinks.ql.j2')

    # Extract unique sink kinds
    sink_kinds = set()
    for sink in sinks:
        sink_kinds.add(sink.kind)

    # Sort sink kinds for consistent output
    sorted_sink_kinds = sorted(sink_kinds)

    content = query_template.render(sink_types=sorted_sink_kinds)

    # Ensure output directory exists
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w') as f:
        f.write(content)

    print(f"Generated query file: {output_file}")
    print(f"Included sink kinds: {', '.join(sorted_sink_kinds)}")


def clean_old_model_files(models_dir, generated_files):
    """Remove old model files that are no longer generated."""
    if not models_dir.exists():
        return

    # Get all existing .model.yml files
    existing_files = list(models_dir.glob("*.model.yml"))
    generated_file_names = {f.name for f in generated_files}

    removed_count = 0
    for existing_file in existing_files:
        if existing_file.name not in generated_file_names:
            print(f"Removing old model file: {existing_file}")
            existing_file.unlink()
            removed_count += 1

    if removed_count > 0:
        print(f"Removed {removed_count} old model files")
    else:
        print("No old model files to remove")


def main():
    # Setup paths
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent
    sink_defs_file = repo_root / "sink_definitions.yml"
    templates_dir = repo_root / "templates"
    models_dir = repo_root / "sinks-pack" / "models"
    queries_dir = repo_root / "sinks-pack" / "queries"

    # Validate required directories and files
    if not templates_dir.exists():
        print(f"Error: Templates directory '{templates_dir}' does not exist", file=sys.stderr)
        sys.exit(1)

    if not (templates_dir / "model.yml.j2").exists():
        print(f"Error: Model template '{templates_dir / 'model.yml.j2'}' does not exist", file=sys.stderr)
        sys.exit(1)

    if not (templates_dir / "sinks.ql.j2").exists():
        print(f"Error: Query template '{templates_dir / 'sinks.ql.j2'}' does not exist", file=sys.stderr)
        sys.exit(1)

    # Load sink definitions
    print(f"Loading sink definitions from: {sink_defs_file}")
    sinks = load_sink_definitions(sink_defs_file)

    total_sinks = len(sinks)
    print(f"Loaded {total_sinks} sink definitions")

    # Setup Jinja2 environment
    template_env = Environment(
        loader=FileSystemLoader(templates_dir),
        trim_blocks=False,
        lstrip_blocks=True
    )

    # Generate files
    print("\nGenerating model files...")
    grouped_sinks = group_sinks_by_package(sinks)
    generated_files = generate_model_files(grouped_sinks, template_env, models_dir)

    print(f"\nGenerating query file...")
    generate_query_file(sinks, template_env, queries_dir / "sinks.ql")

    print(f"\nCleaning up old model files...")
    clean_old_model_files(models_dir, generated_files)

    print(f"\nGeneration complete!")
    print(f"- Generated {len(generated_files)} model files")
    print(f"- Generated 1 query file")
    print(f"- Total sink definitions processed: {total_sinks}")


if __name__ == "__main__":
    main()
