#!/usr/bin/env python3

import argparse
import sqlite3
import sys
from tabulate import tabulate


def is_nonsec_finding(sanitizer_output):
    """Check if a finding is non-security related."""
    sanitizer_parts = sanitizer_output.split(',')
    if len(sanitizer_parts) < 3:
        return False
    
    third_part = sanitizer_parts[2].strip()
    nonsec_prefixes = ['NONSEC-', 'OOM-', 'timeout', 'StackOverflow-']
    
    return any(third_part.startswith(prefix) for prefix in nonsec_prefixes)


def selective_output(data, verbose=False, full_finding=False):
    """Extract only needed columns: Harness, sanitizer output, Time."""
    processed_data = []
    for row in data:
        uuid, harness, pov, status, sanitizer_output, finder, time = row
        
        # Filter out non-security findings unless full_finding is True
        if not full_finding and is_nonsec_finding(sanitizer_output):
            continue
        
        # Extract sanitizer output parts
        sanitizer_parts = sanitizer_output.split(',')
        
        if verbose:
            # From 3rd part till end, each part on separate line
            sanitizer_verbose = "\n".join(part.strip() for part in sanitizer_parts[2:] if part.strip())
            sanitizer_part = sanitizer_verbose
        else:
            # Only 3rd part
            sanitizer_part = sanitizer_parts[2].strip() if len(sanitizer_parts) > 2 else ""
        
        processed_data.append([harness, sanitizer_part, time])
    
    header_label = "Sanitizer Output (verbose)" if verbose else "Sanitizer Output (3rd part)"
    return processed_data, ["Harness", header_label, "Time (s)"]


def full_output(data):
    """Show all columns."""
    headers = [
        "UUID",
        "Harness", 
        "PoV",
        "Status",
        "Sanitizer Output",
        "Finder",
        "Time (s)"
    ]
    return data, headers


def analyze_db(db_path, verbose=False, full_finding=False):
    """Analyze the submit database and print columns."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Query all data from vd table
        cursor.execute("SELECT * FROM vd")
        data = cursor.fetchall()
        
        # Use selective output function
        processed_data, headers = selective_output(data, verbose, full_finding)
        
        # Print results
        if processed_data:
            print(tabulate(processed_data, headers=headers, tablefmt="grid"))
        else:
            print("No data found in the database.")
            
        conn.close()
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Analyze submit database")
    parser.add_argument("db_file", help="Path to the submit.db file")
    parser.add_argument("-v", "--verbose", action="store_true", 
                        help="Show verbose sanitizer output (3rd part till end, multiline)")
    parser.add_argument("-f", "--full-finding", action="store_true",
                        help="Show all findings including non-security ones (NONSEC-, OOM-, timeout, StackOverflow-)")
    
    args = parser.parse_args()
    analyze_db(args.db_file, args.verbose, args.full_finding)


if __name__ == "__main__":
    main()