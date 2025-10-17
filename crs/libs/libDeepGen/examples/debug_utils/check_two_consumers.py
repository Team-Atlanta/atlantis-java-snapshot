import re
import sys
from typing import List, Optional, Dict
from collections import Counter

# Define standard exit codes
EXIT_SUCCESS = 0
EXIT_FAILURE_ARGS = 1
EXIT_FAILURE_FILE_IO = 2
EXIT_FAILURE_MISMATCH = 3

# --- Reusable Hash Extraction Function (same as before) ---
def extract_hashes_from_file(filepath: str, pattern: str, encoding: str = 'utf-8') -> Optional[List[str]]:
    """
    Extracts hashes from a file based on a regex pattern.
    The pattern should have one capturing group for the hash.
    """
    hashes: List[str] = []
    try:
        compiled_regex = re.compile(pattern)
        with open(filepath, 'r', encoding=encoding) as f:
            for line_number, line in enumerate(f, 1):
                match = compiled_regex.search(line)
                if match:
                    try:
                        hashes.append(match.group(1))
                    except IndexError:
                        print(
                            f"⚠️ Warning (File: {filepath}, Line: {line_number}): Regex matched but "
                            f"capturing group 1 not found. Line: '{line.strip()}'",
                            file=sys.stderr
                        )
    except FileNotFoundError:
        print(f"❌ Error: File not found: '{filepath}'", file=sys.stderr)
        return None
    except IOError as e:
        print(f"❌ Error: Could not read file '{filepath}': {e}", file=sys.stderr)
        return None
    except re.error as e:
        print(f"❌ Error: Invalid regex pattern '{pattern}': {e}", file=sys.stderr)
        return None
    return hashes

# --- Main Analysis Function for N Consumers ---
def analyze_multi_sum(
    producer_hashes: List[str],
    consumer_hashes_map: Dict[str, List[str]], # {filepath: [hashes]}
    producer_file: str
) -> bool:
    """
    Checks if producer_hashes multiset equals the multiset sum of all consumer hashes.
    """
    print("\n--- Multi-Consumer Sum Analysis ---")
    print(f"Producer ('{producer_file}') total hash instances: {len(producer_hashes)}")

    total_consumer_instances = 0
    if not consumer_hashes_map:
        print("No consumer logs provided for comparison.")
    else:
        print(f"{len(consumer_hashes_map)} consumer log(s) provided:")
        for cons_file, cons_hashes in consumer_hashes_map.items():
            print(f"  Consumer ('{cons_file}') total hash instances: {len(cons_hashes)}")
            total_consumer_instances += len(cons_hashes)
        print(f"Total hash instances across all consumers: {total_consumer_instances}")


    producer_counts = Counter(producer_hashes)
    
    # Combine all consumer counts
    combined_consumer_counts = Counter()
    for cons_file_path in consumer_hashes_map: # Iterate in order of processing from main
        hashes_for_this_consumer = consumer_hashes_map[cons_file_path]
        combined_consumer_counts.update(hashes_for_this_consumer) # .update adds counts from list

    if producer_counts == combined_consumer_counts:
        print("\n✅ SUCCESS: Producer hashes perfectly match the combined hashes of all Consumers.")
        print("   (This means no missing hashes, no new/unexpected hashes in consumers, and all counts match.)")
        return True
    else:
        print("\n❌ FAILURE: Producer hashes DO NOT perfectly match the combined hashes of all Consumers.")
        
        # Find all unique hashes across producer and all consumers for comprehensive comparison
        all_unique_hashes = set(producer_counts.keys()) | set(combined_consumer_counts.keys())

        print("\n  Detailed Mismatches (Hash: Producer_Count vs Sum_of_All_Consumer_Counts):")
        for h_val in sorted(list(all_unique_hashes)):
            p_count = producer_counts.get(h_val, 0)
            # Get individual consumer counts for this specific hash for detailed reporting
            
            # Re-calculate combined count for this hash from individual consumers for clarity,
            # or just use combined_consumer_counts.get(h_val,0)
            current_combined_c_count_for_hash = 0
            consumer_specific_counts_for_hash: Dict[str, int] = {}

            for cons_file_path, cons_hashes_list in consumer_hashes_map.items():
                # Count occurrences of h_val in this specific consumer's list
                count_in_this_consumer = Counter(cons_hashes_list).get(h_val,0)
                if count_in_this_consumer > 0 : # Store for reporting if relevant
                    consumer_specific_counts_for_hash[cons_file_path] = count_in_this_consumer
                current_combined_c_count_for_hash += count_in_this_consumer
            
            # This should be same as combined_consumer_counts.get(h_val, 0)
            # combined_c_val_from_master = combined_consumer_counts.get(h_val, 0)

            if p_count != current_combined_c_count_for_hash:
                print(f"  - Hash: {h_val}")
                print(f"    Producer Count: {p_count}")
                print(f"    Combined Consumer Count (Sum from all consumers): {current_combined_c_count_for_hash}")
                
                # Optional: Print individual consumer counts for this mismatched hash
                if consumer_specific_counts_for_hash:
                    print("      Individual Consumer Counts for this hash:")
                    for cons_f, c_count in consumer_specific_counts_for_hash.items():
                        print(f"        '{cons_f}': {c_count}")
                elif current_combined_c_count_for_hash > 0 : # Combined count is >0 but no individuals? Error in logic.
                     print("      (Note: Combined consumer count > 0 but no individual consumer counts found for this hash - check logic)")


                if p_count > current_combined_c_count_for_hash:
                    print(f"    Status: MISSING {p_count - current_combined_c_count_for_hash} instance(s) from consumers overall.")
                else: # current_combined_c_count_for_hash > p_count
                    print(f"    Status: EXTRA {current_combined_c_count_for_hash - p_count} instance(s) in consumers overall (or not from producer).")
        return False

# --- Main Script Execution ---
def main():
    script_name = sys.argv[0]
    if len(sys.argv) < 2: # Must have at least script_name and producer_log_file
        print(f"Usage: python {script_name} <producer_log_file> [<consumer1_log_file> <consumer2_log_file> ...]")
        sys.exit(EXIT_FAILURE_ARGS)

    producer_log_file = sys.argv[1]
    consumer_log_files = sys.argv[2:] # This will be an empty list if no consumers are provided

    # Define regex patterns
    producer_pattern = r"CHECK ([0-9a-f]{64})"
    consumer_pattern = r"MAIN CHECK ([0-9a-f]{64})" # Assuming all consumers use this pattern

    print("Starting multi-consumer sum hash analysis...")

    producer_hashes = extract_hashes_from_file(producer_log_file, producer_pattern)
    if producer_hashes is None:
        # Error message already printed by extract_hashes_from_file
        sys.exit(EXIT_FAILURE_FILE_IO)

    consumer_hashes_map: Dict[str, List[str]] = {}
    for cons_file in consumer_log_files:
        current_consumer_hashes = extract_hashes_from_file(cons_file, consumer_pattern)
        if current_consumer_hashes is None:
            # Error message already printed
            sys.exit(EXIT_FAILURE_FILE_IO)
        consumer_hashes_map[cons_file] = current_consumer_hashes
    
    if analyze_multi_sum(
        producer_hashes,
        consumer_hashes_map,
        producer_log_file
    ):
        sys.exit(EXIT_SUCCESS)
    else:
        sys.exit(EXIT_FAILURE_MISMATCH)

if __name__ == "__main__":
    main()
