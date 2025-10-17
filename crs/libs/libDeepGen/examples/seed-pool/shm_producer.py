#!/usr/bin/env python3
import hashlib
import traceback
from pathlib import Path

from libDeepGen.ipc_utils.shm_pool import SeedShmemPoolProducer

SHM_NAME = "test-seed-shm-pool"

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def main():
    create = False
    producer = SeedShmemPoolProducer(SHM_NAME, create=True)
    print(f"[+] created shared memory '{SHM_NAME}'")

    print("Enter file path to upload (blank / q to quit)")
    while True:
        try:
            line = input("path> ").strip()
        except EOFError:
            break
        if line in {"", "q", "quit", "exit"}:
            break
        p = Path(line)
        if not p.is_file():
            print("! not a file")
            continue
        data = p.read_bytes()
        seed_id = producer.add_seed(data)
        if seed_id is None or seed_id < 0:
            print("! pool full or seed too large")
            continue
        print(f"[OK] seed_id={seed_id}  shm_name={SHM_NAME}  sha256={sha256(data)}")
    producer.close()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
    except Exception:
        traceback.print_exc()