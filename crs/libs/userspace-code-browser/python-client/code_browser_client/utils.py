import hashlib
import tarfile
from pathlib import Path

def deterministic_tarball_hash(tar_path: Path, hash_alg="sha256") -> str:
    hasher = hashlib.new(hash_alg)

    with tarfile.open(tar_path, "r:*") as tar:
        members = sorted(tar.getmembers(), key=lambda m: m.name)
        for m in members:
            hasher.update(f"name:{m.name}\n".encode())
            hasher.update(f"type:{m.type}\n".encode())
            hasher.update(f"linkname:{m.linkname or ''}\n".encode())
            hasher.update(f"size:{m.size}\n".encode())

            # Normalize file content if applicable
            if m.isfile():
                with tar.extractfile(m) as f:
                    hasher.update(b"data:")
                    while chunk := f.read(8192):
                        hasher.update(chunk)
                    hasher.update(b"\n")

    return hasher.hexdigest()
