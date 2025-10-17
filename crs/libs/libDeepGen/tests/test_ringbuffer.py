import os
import time
import uuid
import json
import pytest
import multiprocessing
from dataclasses import dataclass
from libDeepGen.ipc_utils.ringbuffer import RingBufferProducer, RingBufferConsumer


@pytest.fixture(scope="function")
def unique_name():
    """Generate a unique name for each test."""
    return f"test_rb_{uuid.uuid4().hex[:8]}"


def test_initialization(unique_name):
    size = 128
    with RingBufferProducer(name=unique_name, create=True, size=size) as rb:
        assert rb.sz == size
        assert rb.nm == unique_name
        assert rb.is_creator is True
        assert rb.ctrl_shm.name == unique_name
        assert rb.ctrl_shm.size == 12  # 12 bytes for size, read index, write index
        assert rb.data_nm == f"{unique_name}_data"
        assert len(rb.data_list) == size + 1  # size+1 slots for the data
        # Verify r/w indices are init to 0
        assert rb.ri.load() == 0
        assert rb.wi.load() == 0
        assert rb.length() == 0
        # Verify that the buffer is not full or empty on initialization
        assert rb.is_full() is False
        assert rb.is_empty() is True


def test_empty_state(unique_name):
    # Test with RingBufferProducer and RingBufferConsumer
    with RingBufferProducer(name=unique_name, create=True, size=16) as producer:
        with RingBufferConsumer(name=unique_name, create=False) as consumer:
            assert producer.is_empty() is True
            assert consumer.is_empty() is True
            
            producer.try_put(42)
            assert producer.is_empty() is False
            assert consumer.is_empty() is False
            assert producer.length() == 1
            assert consumer.length() == 1
            
            consumer.try_get()
            assert producer.is_empty() is True
            assert consumer.is_empty() is True
            assert producer.length() == 0
            assert consumer.length() == 0


def test_full_state(unique_name):
    with RingBufferProducer(name=unique_name, create=True, size=4) as producer:
        with RingBufferConsumer(name=unique_name, create=False) as consumer:
            assert producer.is_empty() is True
            assert producer.is_full() is False
            
            assert producer.try_put(1) is True
            assert producer.try_put(2) is True
            assert producer.is_full() is False
            
            assert producer.try_put(3) is True
            assert producer.try_put(4) is True
            assert producer.length() == 4
            assert producer.is_full() is True

            assert producer.try_put(5) is False

            assert consumer.try_get() == 1
            assert producer.is_full() is False
            assert consumer.try_get() == 2
            assert consumer.try_get() == 3
            assert consumer.try_get() == 4
            assert consumer.length() == 0
            assert consumer.is_empty() is True


def test_put_get_operations(unique_name):
    """Test basic put and get operations."""
    with RingBufferProducer(name=unique_name, create=True, size=8) as producer:
        with RingBufferConsumer(name=unique_name, create=False) as consumer:
            assert consumer.try_get() is None
            
            assert producer.try_put(1) is True
            assert producer.try_put(2) is True
            assert producer.try_put(3) is True
            
            assert consumer.try_get() == 1
            assert consumer.try_get() == 2
            assert consumer.try_get() == 3
            assert consumer.try_get() is None  # Buffer is now empty


def test_blocking_put_get(unique_name):
    with RingBufferProducer(name=unique_name, create=True, size=4) as producer:
        with RingBufferConsumer(name=unique_name, create=False) as consumer:
            # Test get with timeout on empty buffer
            start_time = time.time()
            result = consumer.get(timeout=0.1)
            assert result is None
            elapsed = time.time() - start_time
            assert 0.09 <= elapsed <= 0.2  # Allowing for slight timing variations
            
            # Test put with no timeout
            assert producer.put(42, timeout=0) is True
            assert consumer.get(timeout=0) == 42


def test_non_creator_ringbuffer(unique_name):
    with RingBufferProducer(name=unique_name, create=True, size=10) as producer:
        with RingBufferConsumer(name=unique_name, create=False) as consumer:
            # Verify that the is_creator flag is correctly set
            assert producer.is_creator is True
            assert consumer.is_creator is False

            assert producer.sz == consumer.sz
            
            # Test that both can access the same data
            producer.try_put(42)
            assert consumer.try_get() == 42


def test_serialization_deserialization():
    @dataclass
    class TestDataClass:
        id: int
        name: str
        values: list
        flag: bool
    
    class CustomClass:
        def __init__(self, id, data):
            self.id = id
            self.data = data
            
        def to_json(self):
            return json.dumps({"id": self.id, "data": self.data})
            
        @staticmethod
        def from_json(json_str):
            data = json.loads(json_str)
            return CustomClass(data["id"], data["data"])
            
        def __eq__(self, other):
            if not isinstance(other, CustomClass):
                return False
            return self.id == other.id and self.data == other.data

    buffer_name = f"test_serde_{uuid.uuid4().hex[:8]}"
    
    # Create the RingBuffer with a size big enough for all our tests
    with RingBufferProducer(name=buffer_name, create=True, size=20) as producer:
        with RingBufferConsumer(name=buffer_name, create=False) as consumer:
            # Test 1: Native types
            native_types = [
                42,                                # int
                3.14159,                           # float
                True,                              # bool
                "hello",                           # str
                b"binary",                         # bytes
                None,                              # None
                "nall\x00char",                    # str with null byte
                b"nall\x00byte",                   # bytes with null bytes
            ]
            
            # Put and get native types
            for item in native_types:
                assert producer.try_put(item), f"Failed to put {item}"
                retrieved = consumer.try_get()
                assert retrieved == item, f"Retrieved {retrieved} != original {item}"
            
            # Test 2: Dataclass serialization/deserialization
            data_obj = TestDataClass(
                id=123,
                name="test",
                values=[1, 2, 3],
                flag=True
            )
            
            # Put and get dataclass
            assert producer.try_put(data_obj), "Failed to put dataclass"
            retrieved_data = consumer.try_get(cls=TestDataClass)
            assert isinstance(retrieved_data, TestDataClass), f"Retrieved wrong type: {type(retrieved_data)}"
            assert retrieved_data == data_obj, f"Retrieved {retrieved_data} != original {data_obj}"
            
            # Test 3: Custom class with to_json/from_json
            custom_obj = CustomClass(id=456, data={"key": "value"})
            
            # Put and get custom class
            assert producer.try_put(custom_obj, serialize_fn=lambda x: x.to_json()), "Failed to put custom class"
            retrieved_custom = consumer.try_get(cls=CustomClass, deserialize_fn=CustomClass.from_json)
            assert isinstance(retrieved_custom, CustomClass), f"Retrieved wrong type: {type(retrieved_custom)}"
            assert retrieved_custom == custom_obj, f"Retrieved {retrieved_custom} != original {custom_obj}"
            
            # Test 4: Error cases
            class UnserializableClass:
                def __init__(self):
                    self.circular_ref = self  # Creates circular reference
            
            # Should raise exception when trying to serialize without serialize_fn
            try:
                producer.try_put(UnserializableClass())
                assert False, "Expected ValueError when serializing without serialize_fn"
            except ValueError:
                pass  # Expected behavior
    

def producer_process(buffer_name, num_items):
    """Process that produces items and puts them into the buffer."""
    with RingBufferProducer(name=buffer_name, create=False) as rb:
        print(f"producer, pid {os.getpid()}, buffer_name {buffer_name}, length: {rb.length()}")

        for i in range(num_items):
            # Keep trying until we succeed (the buffer might be full)
            rb.put(i)


def consumer_process(buffer_name, num_items, match_result):
    """Process that consumes items from the buffer."""
    with RingBufferConsumer(name=buffer_name, create=False) as rb:
        print(f"consumer, pid {os.getpid()}, buffer_name {buffer_name}, length: {rb.length()}")
        
        match, mismatch = 0, 0
        for i in range(num_items):
            item = rb.get()
            if item != i:
                mismatch += 1
            else:
                match += 1
        
        match_result.extend([ match, mismatch ])


def test_pre_alloc_high_load():
    """Test RingBuffer under high load across processes."""
    # Use a unique name for this test
    buffer_name = f"test_prealloc_highload_{uuid.uuid4().hex[:8]}"

    # Create the shared buffer and fill it with data
    buffer_size = 40000
    print(f"test func buffer_name {buffer_name}")
    
    with RingBufferProducer(name=buffer_name, size=buffer_size, create=True) as producer:
        with RingBufferConsumer(name=buffer_name, create=False) as consumer:
            # Number of items to exchange (higher load)
            num_items = buffer_size
            for i in range(num_items):
                producer.put(i)
            print(f"test func, pid {os.getpid()}, buffer_name {buffer_name}, length: {producer.length()}")

            # Create a shared list to store results from the consumer
            manager = multiprocessing.Manager()
            match_result = manager.list()
            
            start_time = time.time()
            # Create and start the consumer process
            consumer_proc = multiprocessing.Process(
                target=consumer_process,
                args=(buffer_name, num_items, match_result)
            )
            consumer_proc.start()
            
            # Wait for both processes to finish
            consumer_proc.join(timeout=20)

            end_time = time.time()
            print(f"Time taken for pre_alloc consumer: {end_time - start_time:.2f} seconds for {num_items} items")
            
            # Check that both processes completed successfully
            assert not consumer_proc.is_alive(), "Consumer process timed out"
            assert consumer_proc.exitcode == 0, f"Consumer process failed with exit code {consumer_proc.exitcode}"
            
            # Verify the results
            assert len(match_result) == 2, f"Invalid match result length: {match_result}"
            assert match_result[0] == num_items, f"Match count mismatch: {match_result[0]} != {num_items}"
            assert match_result[1] == 0, f"Mismatch count should be 0: {match_result[1]} != 0"
            assert producer.length() == 0, f"Buffer should be empty after all items are processed: {producer.length()}"
    

def test_1p1c_high_load():
    """Test RingBuffer under high load across processes."""
    # Use a unique name for this test
    buffer_name = f"test_1p1c_highload_{uuid.uuid4().hex[:8]}"

    # Create the shared buffer in the main process - larger size for better throughput
    buffer_size = 40000
    print(f"test func buffer_name {buffer_name}")
    
    with RingBufferProducer(name=buffer_name, size=buffer_size, create=True) as producer:
        # Number of items to exchange (higher load)
        num_items = buffer_size
        print(f"test func, pid {os.getpid()}, buffer_name {buffer_name}, length: {producer.length()}")

        # Create a shared list to store results from the consumer
        manager = multiprocessing.Manager()
        match_result = manager.list()
        
        start_time = time.time()

        # Create and start the producer process
        producer_proc = multiprocessing.Process(
            target=producer_process,
            args=(buffer_name, num_items)
        )
        producer_proc.start()

        # Create and start the consumer process
        consumer_proc = multiprocessing.Process(
            target=consumer_process,
            args=(buffer_name, num_items, match_result)
        )
        consumer_proc.start()
        
        # Wait for both processes to finish
        consumer_proc.join(timeout=20)
        producer_proc.join(timeout=20)

        end_time = time.time()

        print(f"Time taken for producer & consumer: {end_time - start_time:.2f} seconds for {num_items} items")

        # Check that both processes completed successfully
        assert not producer_proc.is_alive(), "Producer process timed out"
        assert not consumer_proc.is_alive(), "Consumer process timed out"
        assert producer_proc.exitcode == 0, f"Producer process failed with exit code {producer_proc.exitcode}"
        assert consumer_proc.exitcode == 0, f"Consumer process failed with exit code {consumer_proc.exitcode}"