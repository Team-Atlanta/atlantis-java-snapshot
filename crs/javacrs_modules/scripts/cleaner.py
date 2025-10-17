#!/usr/bin/env python3
"""
Temporary File Cleaner

This script periodically scans the /tmp directory for files matching specified patterns
and removes them if they're not being used by any process.
"""

import glob
import logging
import os
import shutil
import sys
import time
import traceback
from datetime import datetime

import psutil

SCAN_INTERVAL = 60
PATTERNS = [
    "/tmp/byteBuddyAgent*.jar",
    "/tmp/rules_jni.*",
    "/tmp/jazzer-agent-*.jar",
]
CRS_ERR = "CRS-JAVA-ERR-cleaner"
CRS_WARN = "CRS-JAVA-WARN-cleaner"


def setup_logging():
    """Configure logging with console output"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def is_file_in_use(filepath):
    if not os.path.exists(filepath):
        return False

    # For directories, check all files inside
    if os.path.isdir(filepath):
        try:
            for root, dirs, files in os.walk(filepath):
                for file in files:
                    full_path = os.path.join(root, file)
                    if is_file_in_use(full_path):
                        return True
            return False
        except Exception:
            # If we can't access the directory to check, assume it's in use
            return True

    # Check if the file is being used by any process
    try:
        for proc in psutil.process_iter(["pid", "open_files"]):
            try:
                for file in proc.info["open_files"] or []:
                    if os.path.samefile(file.path, filepath):
                        return True
            except Exception:
                continue
        return False
    except Exception:
        # If we can't determine if the file is in use, assume it is to be safe
        return True


def remove_file(filepath):
    try:
        if os.path.isdir(filepath):
            shutil.rmtree(filepath)
        else:
            os.remove(filepath)
        return True
    except Exception as e:
        logging.warning(
            f"Failed to remove {filepath}: {str(e)} {traceback.format_exc()}"
        )
        return False


def get_human_readable_size(size_bytes):
    """
    Convert size in bytes to human-readable format
    """
    if size_bytes == 0:
        return "0B"
    size_names = ("B", "KB", "MB", "GB", "TB")
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024
        i += 1
    return f"{size_bytes:.2f}{size_names[i]}"


def get_file_size(filepath):
    """
    Get the size of a file or directory
    """
    try:
        if os.path.isdir(filepath):
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(filepath):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    if os.path.exists(fp):
                        total_size += os.path.getsize(fp)
            return total_size
        else:
            return os.path.getsize(filepath)
    except Exception:
        return 0


def clean_tmp_files():
    """
    Scan and clean unused temporary files matching the configured patterns
    """
    logging.info(f"Starting cleanup scan: {datetime.now()}")

    total_files_checked = 0
    total_files_removed = 0
    total_bytes_freed = 0

    try:
        for pattern in PATTERNS:
            matching_files = glob.glob(pattern)

            for filepath in matching_files:
                total_files_checked += 1
                try:
                    if not os.path.exists(filepath):
                        continue

                    file_size = get_file_size(filepath)

                    # Check if file is in use
                    if not is_file_in_use(filepath):
                        file_type = "directory" if os.path.isdir(filepath) else "file"
                        human_size = get_human_readable_size(file_size)

                        if remove_file(filepath):
                            total_files_removed += 1
                            total_bytes_freed += file_size
                            logging.info(
                                f"Removed unused {file_type}: {filepath} (Size: {human_size})"
                            )
                        else:
                            logging.warning(
                                f"{CRS_WARN} Failed to remove {file_type}: {filepath}"
                            )
                    else:
                        logging.info(f"File is in use, skipping: {filepath}")
                except Exception as e:
                    logging.error(f"{CRS_ERR} processing {filepath}: {str(e)}")
    except Exception as e:
        logging.error(f"{CRS_ERR} during cleanup scan: {str(e)}")

    # Log summary
    freed_space = get_human_readable_size(total_bytes_freed)
    logging.info(
        f"Cleanup summary: {total_files_checked} files checked, {total_files_removed} removed, {freed_space} freed"
    )


def main():
    """Main function: sets up logging and runs the cleaner in a loop"""
    setup_logging()

    logging.info("Temporary file cleaner service started")

    try:
        while True:
            try:
                clean_tmp_files()
                logging.info(
                    f"Cleanup complete, waiting {SCAN_INTERVAL} seconds until next scan"
                )
                time.sleep(SCAN_INTERVAL)
            except Exception as e:
                logging.error(f"{CRS_ERR} in cleanup cycle: {str(e)}")
                time.sleep(SCAN_INTERVAL)
    except KeyboardInterrupt:
        logging.info("Service interrupted by user")
    except Exception as e:
        logging.critical(f"{CRS_ERR} Critical error in main loop: {str(e)}")
    finally:
        logging.info("Temporary file cleaner service stopped")


if __name__ == "__main__":
    main()
