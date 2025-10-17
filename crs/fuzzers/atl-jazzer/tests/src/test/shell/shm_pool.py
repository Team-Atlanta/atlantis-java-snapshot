# Copyright 2025 Code Intelligence GmbH
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import struct
import traceback

from abc import ABC
from typing import Union

from multiprocessing.shared_memory import SharedMemory


class ShmemPoolBase(ABC):
    """
    Common base class for all shared memory pools.
    Layout:
        Header(8B) :  <item_size:uint32><item_num:uint32>
        Item[n]    :  <data_len:uint32><payload bytes..>
    """

    HEADER_FMT  = "<II"
    HEADER_SIZE = struct.calcsize(HEADER_FMT)    # 8

    def __init__(self, shm_name: str, item_num: int, item_size: int, create: bool = False):
        """Create or attach to shared memory.

        Args:
            shm_name: Name of the shared memory segment
            item_num: Number of items in the pool
            item_size: Maximum size of each item in bytes/chars
            create: Whether to create (True) or attach to (False) shared memory
        """
        assert shm_name, "shm_name must be provided for shared memory operations"

        self.shm_name  = shm_name
        self.create    = create
        try:
            if create:
                assert item_num > 0 and item_size > 4
                self.item_size = item_size
                self.item_num  = item_num

                total_size = self.HEADER_SIZE + item_num * item_size
                self.shm = SharedMemory(name=shm_name, create=True, size=total_size)

                # write header info
                self.shm.buf[:self.HEADER_SIZE] = struct.pack(self.HEADER_FMT,
                                                              item_size,
                                                              item_num)
                # set all length items to zero
                for i in range(item_num):
                    off = self._item_offset(i)
                    self.shm.buf[off:off+4] = b"\x00\x00\x00\x00"
            else:
                self.shm = SharedMemory(name=shm_name, create=False)
                # read header info
                self.item_size, self.item_num = struct.unpack(
                    self.HEADER_FMT,
                    self.shm.buf[:self.HEADER_SIZE]
                )

        except Exception as e:
            raise RuntimeError(f"Failed to {'create' if create else 'attach'} "
                               f"shared memory: {e}\n{traceback.format_exc()}")

    def _item_offset(self, idx: int) -> int:
        """Get the byte offset of the item at index idx."""
        return self.HEADER_SIZE + idx * self.item_size

    def _write_item(self, idx: int, payload: bytes):
        assert 0 <= idx < self.item_num, "idx out of range"
        assert payload is not None
        max_payload = self.item_size - 4
        assert len(payload) <= max_payload, "payload too large"

        off = self._item_offset(idx)
        self.shm.buf[off      : off+4]           = struct.pack("<I", len(payload))
        self.shm.buf[off+4    : off+4+len(payload)] = payload

    def _read_item(self, idx: int) -> bytes:
        assert 0 <= idx < self.item_num, "idx out of range"
        off   = self._item_offset(idx)
        size  = struct.unpack("<I", self.shm.buf[off:off+4])[0]
        if size == 0:
            return b""
        return bytes(self.shm.buf[off+4 : off+4+size])

    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        
    def close(self):
        """Release or detach from shared memory."""
        if hasattr(self, "shm"):
            try:
                self.shm.close()
                if self.create:
                    self.shm.unlink()
            except Exception:
                pass

    def __del__(self):
        """Fallback cleanup."""
        self.close()


class SeedShmemPoolBase(ShmemPoolBase):
    """Base class for seed shared memory pool."""
    # Pool size is 0.5GB
    SEED_SIZE = 8 * 1024  # 8KB
    SEED_NUM = 65536  # 
    
    def __init__(self, shm_name: str, item_num: int = SEED_NUM, 
                 item_size: int = SEED_SIZE, create: bool = False):
        """Initialize seed shared memory pool base.
        
        Args:
            shm_name: Name of the shared memory segment
            item_num: Number of items in the pool
            item_size: Maximum size of each item in bytes/chars
            create: Whether to create (True) or attach to (False) shared memory
        """
        super().__init__(shm_name, item_num, item_size, create)


class SeedShmemPoolProducer(SeedShmemPoolBase):
    """Producer for the seed shared memory pool that manages adding and releasing seeds."""
    
    def __init__(self, shm_name: str, 
                 item_num: int = SeedShmemPoolBase.SEED_NUM,
                 item_size: int = SeedShmemPoolBase.SEED_SIZE, create: bool = False):
        """Initialize seed shared memory pool producer.
        
        Args:
            shm_name: Name of the shared memory segment
            item_num: Number of items in the pool
            item_size: Maximum size of each item in bytes/chars
            create: Whether to create (True) or attach to (False) shared memory
        """
        super().__init__(shm_name, item_num, item_size, create)
        self.unassigned = set(range(self.item_num))
    
    def add_seed(self, seed: bytes) -> Union[int, None]:
        """Add a seed to the pool and return its index (seed_id)."""
        if seed is None:
            # Invalid seed
            return None
        if len(seed) > (self.item_size - 4):
            # Seed is too large
            return None
        if not self.unassigned:
            # Pool is full
            return -1
        idx = self.unassigned.pop()
        self._write_item(idx, seed)
        return idx

    def release_seed(self, seed_id: int):
        """Release a seed from the pool by seed_id."""
        self.unassigned.add(seed_id)
    
    def get_seed_content(self, seed_id: int) -> Union[bytes, None]:
        """Get the seed content from the pool by seed_id."""
        if 0 <= seed_id < self.item_num:
            return self._read_item(seed_id)
        return None
    
    def is_full(self) -> bool:
        """Check if the pool is full."""
        return len(self.unassigned) == 0


class SeedShmemPoolConsumer(SeedShmemPoolBase):
    """Consumer for the seed shared memory pool that only reads seeds."""
    
    def get_seed_content(self, seed_id: int) -> Union[bytes, None]:
        """Get the seed content from the pool by seed_id."""
        if 0 <= seed_id < self.item_num:
            return self._read_item(seed_id)
        return None