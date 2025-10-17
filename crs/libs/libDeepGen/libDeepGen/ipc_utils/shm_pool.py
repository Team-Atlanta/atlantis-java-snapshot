import struct
import traceback

from abc import ABC
from typing import Union

from multiprocessing.shared_memory import SharedMemory

from ..script import Script


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


class ScriptShmemPoolBase(ShmemPoolBase):
    """Base class for script shared memory pool."""
    # Pool size is 1GB -> 32K scripts X avg file size 32KB
    SCRIPT_SIZE = 64 * 1024  # 64KB (4b for length field)
    SCRIPT_NUM = 32768  # 32K scripts
    
    def __init__(self, shm_name: str, item_num: int = SCRIPT_NUM, 
                 item_size: int = SCRIPT_SIZE, create: bool = False):
        """Initialize script shared memory pool base.
        
        Args:
            shm_name: Name of the shared memory segment
            item_num: Number of items in the pool
            item_size: Maximum size of each item in bytes/chars
            create: Whether to create (True) or attach to (False) shared memory
        """
        super().__init__(shm_name, item_num, item_size, create)


class ScriptShmemPoolProducer(ScriptShmemPoolBase):
    """Producer for the script shared memory pool that manages adding and retrieving scripts."""
    
    def __init__(self, shm_name: str, 
                 item_num: int = ScriptShmemPoolBase.SCRIPT_NUM,
                 item_size: int = ScriptShmemPoolBase.SCRIPT_SIZE, create: bool = False):
        """Initialize script shared memory pool producer.
        
        Args:
            shm_name: Name of the shared memory segment
            item_num: Number of items in the pool
            item_size: Maximum size of each item in bytes/chars
            create: Whether to create (True) or attach to (False) shared memory
        """
        super().__init__(shm_name, item_num, item_size, create)
        self.idx2script = {}
        self.hash2idx = {}
    
    def add_script(self, script: Script) -> Union[int, None]:
        """Add a script to the pool and return its index (script_id)."""
        idx = len(self.idx2script)
        if idx >= self.item_num:
            # Pool is full
            return None
        if script.sha256 in self.hash2idx:
            return -1
        # Add script to the pool
        payload = script.content.encode("utf-8")
        try:
            self._write_item(idx, payload)
        except AssertionError:
            return -2
        self.idx2script[idx] = script
        self.hash2idx[script.sha256] = idx
        return idx

    def get_script_by_id(self, script_id: int) -> Union[Script, None]:
        """Get a script from the pool by script_id."""
        return self.idx2script.get(script_id)

    def get_script_by_hash(self, sha256: str) -> Union[Script, None]:
        """Get a script from the pool by its hash."""
        return self.idx2script.get(self.hash2idx.get(sha256, -1))

    def get_script_content(self, script_id: int) -> Union[str, None]:
        """Get the script content from the pool by script_id."""
        try:
            if 0 <= script_id < self.item_num:
                data = self._read_item(script_id)
                return data.decode("utf-8") if data else None
        except Exception:
            pass
        return None


class ScriptShmemPoolConsumer(ScriptShmemPoolBase):
    """Consumer for the script shared memory pool that only reads scripts."""
    
    def get_script_content(self, script_id: int) -> Union[str, None]:
        """Get the script content from the pool by script_id."""
        try:
            if 0 <= script_id < self.item_num:
                data = self._read_item(script_id)
                return data.decode("utf-8") if data else None
        except Exception:
            pass
        return None


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
