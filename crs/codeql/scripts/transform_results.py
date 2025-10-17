#!/usr/bin/env python3
"""
Transform CodeQL JSON results from the current format to coordinate format.
"""

import json
import sys
import os
import re
from pathlib import Path


def extract_filename_from_path(file_path):
    """Extract just the filename from a full file path."""
    return os.path.basename(file_path)


def convert_class_name_to_jvm_format(class_name):
    """Convert class name from dot notation to JVM slash notation."""
    return class_name.replace('.', '/')


def transform_codeql_results(input_file, output_file):
    """Transform CodeQL JSON results to coordinate format."""

    # Read the input JSON
    with open(input_file, 'r') as f:
        data = json.load(f)

    # Extract the tuples from the CodeQL result format
    if '#select' not in data or 'tuples' not in data['#select']:
        raise ValueError("Invalid CodeQL JSON format - missing #select.tuples")

    tuples = data['#select']['tuples']
    columns = data['#select']['columns']

    # Create column index mapping
    col_map = {col['name']: idx for idx, col in enumerate(columns) if 'name' in col}
    col_map['entity'] = 0  # Entity is always first column

    # Transform each tuple to coordinate format
    coordinates = []

    for tuple_data in tuples:
        try:
            # Extract data from tuple
            entity = tuple_data[col_map['entity']]
            sink_type = tuple_data[col_map['sink_type']]
            has_non_constant_args = tuple_data[col_map['has_non_constant_args']]
            class_name = tuple_data[col_map['class_name']]
            method_name = tuple_data[col_map['method_name']]
            method_signature = tuple_data[col_map['method_signature']]
            method_descriptor = tuple_data[col_map['method_descriptor']]
            file_path = tuple_data[col_map['file_path']]
            line_number = tuple_data[col_map['line_number']]
            model_info = tuple_data[col_map['model_info']]

            if not has_non_constant_args:
                continue

            # Extract filename from path
            file_name = file_path  # extract_filename_from_path(file_path)

            # Convert class name to JVM format
            jvm_class_name = convert_class_name_to_jvm_format(class_name)

            # Map sink type to mark description
            mark_desc = sink_type

            # Create coordinate entry
            coord_entry = {
                "coord": {
                    "line_num": line_number,
                    "method_name": method_name,
                    "file_name": file_name,
                    "bytecode_offset": -1,
                    "method_desc": method_descriptor,
                    "mark_desc": mark_desc,
                    "method_signature": method_signature,
                    "class_name": jvm_class_name
                },
                "id": model_info
            }

            coordinates.append(coord_entry)

        except (KeyError, IndexError) as e:
            print(f"Warning: Skipping malformed tuple: {e}", file=sys.stderr)
            continue

    # Write the transformed results
    with open(output_file, 'w') as f:
        json.dump(coordinates, f, indent=2)

    print(f"Transformed {len(coordinates)} entries from {input_file} to {output_file}")


def main():
    if len(sys.argv) != 3:
        print("Usage: python3 transform_results.py <input_json> <output_json>")
        print("Example: python3 transform_results.py out.json transformed_results.json")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' does not exist")
        sys.exit(1)

    try:
        transform_codeql_results(input_file, output_file)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
