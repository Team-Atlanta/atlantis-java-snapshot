import re
import sys
from typing import List, Optional

# (Assuming EXIT_SUCCESS, EXIT_FAILURE_ARGS, etc. are defined as before)
# Define standard exit codes (if not already defined elsewhere)
EXIT_SUCCESS = 0
EXIT_FAILURE_ARGS = 1
EXIT_FAILURE_FILE_IO = 2
EXIT_FAILURE_HASH_MISMATCH = 3


# (Assuming extract_hashes_from_file is defined as before)
def extract_hashes_from_file(filepath: str, pattern: str, encoding: str = 'utf-8') -> Optional[List[str]]:
    """
    Extracts hashes from a file based on a regex pattern.
    (Implementation from the previous detailed answer)
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
                            f"⚠️ Warning: Regex matched on line {line_number} in '{filepath}' but "
                            f"capturing group 1 was not found. Line: '{line.strip()}'",
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


def compare_hash_sequences(prod_hashes: List[str], cons_hashes: List[str]) -> bool:
    """
    Compares two lists of hashes and prints differences, including original indices.

    Args:
        prod_hashes: A list of hashes from the producer.
        cons_hashes: A list of hashes from the consumer.

    Returns:
        True if hashes are identical and in the same order, False otherwise.
    """
    print(f"Producer hash count: {len(prod_hashes)}")
    print(f"Consumer hash count: {len(cons_hashes)}")

    if prod_hashes == cons_hashes:
        print("✅ Hashes are identical and in the same order.")
        return True

    overall_match = True # Assume match until a discrepancy is found
    prod_set = set(prod_hashes)
    cons_set = set(cons_hashes)

    # Hashes in producer but not found in consumer's set of hashes
    hashes_in_prod_missing_from_cons_set = prod_set - cons_set
    if hashes_in_prod_missing_from_cons_set:
        overall_match = False
        print("\n❌ Hashes in producer log but not found in consumer log (showing original producer indices):")
        found_count = 0
        for idx, p_hash in enumerate(prod_hashes):
            if p_hash in hashes_in_prod_missing_from_cons_set:
                found_count +=1
                print(f"  - Hash '{p_hash}' (Producer index: {idx})")
        if found_count == 0: # Should not happen if hashes_in_prod_missing_from_cons_set is non-empty
             print("  (Error in logic: set difference non-empty but no elements found in list iteration)")


    # Hashes in consumer but not found in producer's set of hashes
    hashes_in_cons_extra_to_prod_set = cons_set - prod_set
    if hashes_in_cons_extra_to_prod_set:
        overall_match = False
        print("\n❌ Hashes in consumer log but not found in producer log (showing original consumer indices):")
        found_count = 0
        for idx, c_hash in enumerate(cons_hashes):
            if c_hash in hashes_in_cons_extra_to_prod_set:
                found_count +=1
                print(f"  - Hash '{c_hash}' (Consumer index: {idx})")
        if found_count == 0: # Should not happen
            print("  (Error in logic: set difference non-empty but no elements found in list iteration)")


    # If the sets of unique hashes are identical, but the lists are not,
    # it implies order differences or different counts of duplicate hashes.
    if not hashes_in_prod_missing_from_cons_set and not hashes_in_cons_extra_to_prod_set:
        if len(prod_hashes) != len(cons_hashes):
            overall_match = False
            print("\n⚠️ Hash sets are identical, but overall counts differ (implies different numbers of duplicates).")
            # Further detailed comparison of order for the common length
            print("   Comparing sequences up to the length of the shorter list for order issues:")
            mismatches_found = 0
            for i, (p_hash, c_hash) in enumerate(zip(prod_hashes, cons_hashes)): # zip stops at shortest
                if p_hash != c_hash:
                    mismatches_found +=1
                    print(f"     Order mismatch at index {i}: producer='{p_hash}', consumer='{c_hash}'")
                    if mismatches_found >= 10:
                        print("     ... (and potentially more order mismatches)")
                        break
            if mismatches_found == 0:
                print("     No order mismatches in the common part of the sequence.")

        else: # Sets are identical, lengths are identical, but lists are not -> pure order issue
            overall_match = False
            print("\n⚠️ Hashes match as sets and counts, but order is different!")
            mismatches_found = 0
            for i, (p_hash, c_hash) in enumerate(zip(prod_hashes, cons_hashes)):
                if p_hash != c_hash:
                    mismatches_found +=1
                    print(f"  Order mismatch at index {i}: producer='{p_hash}', consumer='{c_hash}'")
                    if mismatches_found >= 10: # Limit number of printed mismatches
                        print("  ... (and potentially more order mismatches)")
                        break
    elif overall_match : # If we haven't found any set differences, but the first check (prod_hashes == cons_hashes) failed
        # This case might be hit if overall_match was not properly set to False by other conditions.
        # This implies a subtle difference, likely already covered, but as a fallback:
        if prod_hashes != cons_hashes: # Re-ensure they are not identical
             print("\nℹ️ Sequences differ, but set-based differences were not the primary issue. Checking common prefix order.")
             mismatches_found = 0
             for i, (p_hash, c_hash) in enumerate(zip(prod_hashes, cons_hashes)):
                 if p_hash != c_hash:
                     overall_match = False
                     mismatches_found +=1
                     print(f"  Order mismatch at index {i} (within common sequence): producer='{p_hash}', consumer='{c_hash}'")
                     if mismatches_found >= 10:
                         print("  ... (and potentially more order mismatches in common prefix)")
                         break
             if mismatches_found == 0 and len(prod_hashes) != len(cons_hashes):
                  print("  No order mismatches in the common prefix, differences are due to length or items beyond common prefix.")


    if overall_match and prod_hashes == cons_hashes: # Should have been caught by the very first if
        # This should ideally not be reached if the first check for equality was done.
        # If it is, it implies the 'overall_match' flag logic might need review for some edge cases.
        # However, given the first check, this is more of a safeguard.
        # print("\n✅ No discrepancies found.") # Redundant due to first check
        return True
    elif overall_match and prod_hashes != cons_hashes:
        # This state means initial lists were not equal, but no specific differences were flagged by subsequent checks.
        # This is an unlikely state and might indicate an edge case not handled or a flaw in overall_match logic.
        print("\n❌ Summary: Hash sequences do not fully match (unspecified difference or edge case).")
        return False
    else: # overall_match is False
        print("\n❌ Summary: Hash sequences do not fully match.")
        return False

def main():
    """
    Main function to parse arguments and run the hash comparison.
    (Implementation from the previous detailed answer)
    """
    if len(sys.argv) != 3:
        print(f"Usage: python {sys.argv[0]} <producer_log_file> <consumer_log_file>")
        sys.exit(EXIT_FAILURE_ARGS)

    producer_log_file = sys.argv[1]
    consumer_log_file = sys.argv[2]

    producer_pattern = r"CHECK ([0-9a-f]{64})"
    consumer_pattern = r"MAIN CHECK ([0-9a-f]{64})"

    print(f"--- Analyzing Producer Log: {producer_log_file} ---")
    prod_hashes = extract_hashes_from_file(producer_log_file, producer_pattern)
    if prod_hashes is None:
        sys.exit(EXIT_FAILURE_FILE_IO)

    print(f"\n--- Analyzing Consumer Log: {consumer_log_file} ---")
    cons_hashes = extract_hashes_from_file(consumer_log_file, consumer_pattern)
    if cons_hashes is None:
        sys.exit(EXIT_FAILURE_FILE_IO)

    print("\n--- Comparison Results ---")
    if compare_hash_sequences(prod_hashes, cons_hashes):
        sys.exit(EXIT_SUCCESS)
    else:
        sys.exit(EXIT_FAILURE_HASH_MISMATCH)

if __name__ == "__main__":
    main()
