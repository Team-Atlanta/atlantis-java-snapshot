import atomics
import json
import time
from abc import ABC
from dataclasses import is_dataclass, asdict
from multiprocessing import shared_memory
from multiprocessing.shared_memory import ShareableList
from typing import Any


class RingBufferBase(ABC):
    """
    Base class for shared memory ring buffer implementation.
    Provides common functionality for both producer and consumer.
    
    This ringbuffer has two segments of shmem:
    1. Control segment: SharedMemory for metadata (size, read/write indices)
    2. Data segment: ShareableList for storing the actual data items (any POD python type)
    """
    DEFAULT_POLL_INTERVAL = 0.0001
    _SHAREABLE_SUPP_TYPES = (int, float, bool, str, bytes, type(None))

    def __init__(self, name: str, create: bool, size: int = -1, bytes_per_slot: int = 4096):
        """Initialize the ring buffer.
        
        Args:
            name: Name of the shared memory segment
            create: Whether to create (True) or attach to (False) shared memory
            size: Number of usable slots in the ring buffer (required when create=True)
            bytes_per_slot: Maximum size in bytes for each slot
        """
        self.nm = name
        self.is_creator = create
        self.data_nm = f"{name}_data"
        
        if create:
            # creator (create/destroy shmem)
            assert size > 0, "Size must be greater than 0 when creating a new ring buffer."
            # ctrl segment: size + read index + write index
            self.ctrl_shm = shared_memory.SharedMemory(create=True, size=12, name=name)
            self._write_int(self.ctrl_shm.buf, 0, size)
            self._write_int(self.ctrl_shm.buf, 4, 0)  # read index
            self._write_int(self.ctrl_shm.buf, 8, 0)  # write index
            
            # data segment: ShareableList for any data type, size+1 slots for storing 'size' elements
            self.data_list = ShareableList(["A" * bytes_per_slot] * (size + 1), name=self.data_nm)
        else:
            # user (attach to existing shmem, not manage)
            self.ctrl_shm = shared_memory.SharedMemory(name=name, create=False)
            size = self._read_int(self.ctrl_shm.buf, 0)  # read size info from the first 4 bytes
            self.data_list = ShareableList(name=self.data_nm)

        self.sz = size
        self.rctx = atomics.atomicview(buffer=self.ctrl_shm.buf[4:8], atype=atomics.UINT)
        self.ri = self.rctx.__enter__()

        self.wctx = atomics.atomicview(buffer=self.ctrl_shm.buf[8:12], atype=atomics.UINT)
        self.wi = self.wctx.__enter__()
    
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def close(self):
        """Clean up all resources."""
        if hasattr(self, 'rctx') and self.rctx:
            try:
                self.rctx.__exit__(None, None, None)
            except Exception:
                pass
                
        if hasattr(self, 'wctx') and self.wctx:
            try:
                self.wctx.__exit__(None, None, None)
            except Exception:
                pass
        
        self.sz, self.wctx, self.rctx = 0, None, None
        
        if hasattr(self, 'ctrl_shm'):
            try:
                self.ctrl_shm.close()
            except Exception:
                pass
            
            if self.is_creator:
                try:
                    self.ctrl_shm.unlink()
                except Exception:
                    pass
        
        if hasattr(self, 'data_list'):
            try:
                self.data_list.shm.close()
            except Exception:
                pass
                
            if self.is_creator:
                try:
                    # Unlink the ShareableList's shared memory
                    self.data_list.shm.unlink()
                except Exception:
                    pass

    def __del__(self):
        """Fallback cleanup."""
        self.close()

    def _read_int(self, buf, off: int) -> int:
        """Helper func to read an int32 from the buf."""
        return int.from_bytes(buf[off:off + 4], byteorder='little')

    def _write_int(self, buf, off: int, data: int):
        """Helper func to write an int32 from the buf."""
        data_bytes = data.to_bytes(4, byteorder='little')
        buf[off + 0] = data_bytes[0]
        buf[off + 1] = data_bytes[1]
        buf[off + 2] = data_bytes[2]
        buf[off + 3] = data_bytes[3]

    def length(self) -> int:
        """Return the number of items in the ring buffer."""
        return (self.wi.load() - self.ri.load()) % (self.sz + 1)

    def is_full(self) -> bool:
        """A ring buffer is full when the write index is one position behind the read index."""
        next_w = (self.wi.load() + 1) % (self.sz + 1)
        return next_w == self.ri.load()

    def is_empty(self) -> bool:
        """A ring buffer is empty when the read index equals the write index."""
        return self.wi.load() == self.ri.load()

    def guess_never_put(self) -> int:
        """NOTE: Not always accurate as it is ring buffer, call multiple times to get a better guess."""
        return self.wi.load() == 0

    def _pad_str_bytes(self, data):
        """Add padding byte to strings and bytes to work around ShareableList null stripping bug.
        Issue ref: https://docs.python.org/3/library/multiprocessing.shared_memory.html#multiprocessing.shared_memory.ShareableList
        """
        if isinstance(data, str):
            return data + "\xFF"
        elif isinstance(data, bytes):
            return data + b"\xFF"
        return data
        
    def _unpad_str_bytes(self, data):
        """Remove padding byte from strings and bytes to work around ShareableList null stripping bug."""
        if isinstance(data, str):
            assert data[-1] == "\xFF"
            return data[:-1]
        elif isinstance(data, bytes):
            assert data[-1] == 0xFF  # Compare with integer value 255
            return data[:-1]
        return data

    def _serialize_data(self, data: Any, serialize_fn = None) -> Any:
        """Serialize data if needed for storage in ShareableList."""
        # Handle serialization first
        if isinstance(data, self._SHAREABLE_SUPP_TYPES):
            result = data
        elif is_dataclass(data):
            result = json.dumps(asdict(data))
        elif serialize_fn is not None:
            result = serialize_fn(data)
        else:
            raise ValueError(f"Cannot serialize object of type {type(data)}. "
                           f"Provide a serialize_fn for non-native types.")
                           
        return self._pad_str_bytes(result)
    
    def _deserialize_data(self, data: Any, cls = None, deserialize_fn = None) -> Any:
        """Deserialize data based on target class and optional deserialization function."""
        data = self._unpad_str_bytes(data)
        
        if deserialize_fn:
            return deserialize_fn(data)
        if cls is None or cls in self._SHAREABLE_SUPP_TYPES:
            return data
        if is_dataclass(cls) and isinstance(data, str):
            parsed_data = json.loads(data)
            return cls(**parsed_data)
        raise ValueError(f"Cannot deserialize data of type {type(data)} to {cls.__name__}. Provide a deserialize_fn.")


class RingBufferProducer(RingBufferBase):
    """
    Producer implementation for the ring buffer.
    Responsible for adding items to the buffer.
    """
    
    def try_put(self, data: Any, serialize_fn = None) -> bool:
        """Try to put an item into the ring buffer, return False if full."""
        ridx, widx = self.ri.load(), self.wi.load()
        next_w = (widx + 1) % (self.sz + 1)
        if next_w == ridx:
            # buffer is full
            return False
        
        serialized_data = self._serialize_data(data, serialize_fn)
        self.data_list[widx] = serialized_data
        self.wi.store(next_w)
        return True

    def put(self, data: Any, timeout: float = -1, serialize_fn = None) -> bool:
        """Block until the item can be added to the buffer, or until timeout expires."""
        end_time = time.time() + timeout if timeout >= 0 else None
        while True:
            if self.try_put(data, serialize_fn=serialize_fn):
                return True
            if end_time is not None and time.time() > end_time:
                return False
            #time.sleep(self.DEFAULT_POLL_INTERVAL)
            
    def put_until(self, data: Any, condition_fn, serialize_fn = None) -> bool:
        """Block until the item can be added to the buffer, or until condition_fn returns False."""
        while condition_fn():
            if self.try_put(data, serialize_fn=serialize_fn):
                return True
            #time.sleep(self.DEFAULT_POLL_INTERVAL)
        return False


class RingBufferConsumer(RingBufferBase):
    """
    Consumer implementation for the ring buffer.
    Responsible for retrieving items from the buffer.
    """
    
    def try_get(self, cls = None, deserialize_fn = None) -> Any | None:
        """Try to get next item from the ring buffer, return None if empty."""
        ridx, widx = self.ri.load(), self.wi.load()
        if ridx == widx:
            # buffer is empty
            return None

        data = self.data_list[ridx]
        self.ri.store((ridx + 1) % (self.sz + 1))
        return self._deserialize_data(data, cls, deserialize_fn)

    def get(self, timeout: float = -1, cls = None, deserialize_fn = None) -> Any | None:
        """Block until an item can be retrieved from the buffer, or until timeout expires."""
        end_time = time.time() + timeout if timeout >= 0 else None

        while True:
            result = self.try_get(cls=cls, deserialize_fn=deserialize_fn)
            if result is not None:
                return result
            if end_time is not None and time.time() > end_time:
                return None
            #time.sleep(self.DEFAULT_POLL_INTERVAL)
            
    def get_until(self, condition_fn, cls = None, deserialize_fn = None) -> Any | None:
        """Block until an item can be retrieved from the buffer, or until condition_fn returns False."""
        while condition_fn():
            result = self.try_get(cls=cls, deserialize_fn=deserialize_fn)
            if result is not None:
                return result
            #time.sleep(self.DEFAULT_POLL_INTERVAL)
        return None