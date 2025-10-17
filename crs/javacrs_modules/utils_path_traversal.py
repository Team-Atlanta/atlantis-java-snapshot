import asyncio
import sys
import traceback
from pathlib import Path
from typing import List, Set, Tuple

import aiofiles


def match_ptrn(ptrns: Set[str], target: str) -> bool:
    for ptrn in ptrns:
        if target.startswith(ptrn):
            return True
    return False


async def extract_paths_from_binary(
    file_path: Path,
    target_string: str = "jazzer-traversal",
    min_length: int = 4,
    logger=None,
) -> List[Tuple[str, str]]:
    async with aiofiles.open(file_path, "rb") as f:
        data = await f.read()

    strings = []
    current = bytearray()

    for byte in data:
        if 0x20 <= byte <= 0x7E:
            current.append(byte)
        elif len(current) >= min_length:
            strings.append(bytes(current))
            current = bytearray()

    if len(current) >= min_length:
        strings.append(bytes(current))

    slash_patterns = {"/", "%2F", "%2f"}
    dot_ptrn1 = {"./", "%2E%2F", "%2e%2f"}
    dot_ptrn2 = {"../", "%2E%2E%2F", "%2e%2e%2f"}
    results = []

    try:
        for s in strings:
            decoded = s.decode("ascii", errors="ignore")

            # Find all occurrences of target_string
            idx = 0
            while True:
                target_idx = decoded.find(target_string, idx)
                if target_idx == -1:
                    break

                start_idx = idx
                category = "misc"

                for i in range(start_idx, target_idx):
                    part_str = decoded[i:]
                    if match_ptrn(slash_patterns, part_str):
                        start_idx = i
                        category = "abs"
                        break
                    elif match_ptrn(dot_ptrn1, part_str):
                        start_idx = i
                        category = "rel-1"
                        break
                    elif match_ptrn(dot_ptrn2, part_str):
                        start_idx = i
                        category = "rel-2"
                        break

                path = decoded[start_idx : target_idx + len(target_string)]
                results.append((category, path))

                idx = target_idx + len(target_string)
    except Exception as e:
        if logger:
            logger.error(
                f"Error processing file {file_path}: {e} {traceback.format_exc()}"
            )

    return results


async def main():
    if len(sys.argv) < 2:
        print("Usage: python script.py <binary_file>")
        sys.exit(1)

    file_path = Path(sys.argv[1])
    signatures = await extract_paths_from_binary(file_path)

    for category, path in signatures:
        print(f"{category}: {path}")


if __name__ == "__main__":
    asyncio.run(main())
