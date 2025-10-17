#!/usr/bin/env python3
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

"""
Minimal Router Implementation
"""
import asyncio
import json
import logging
import os
import time
import uuid
import zmq
import zmq.asyncio as azmq

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Set

from shm_pool import SeedShmemPoolProducer


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('minimal-router')


@dataclass(frozen=True)
class SubmitBundle:
    """A bundle of seed IDs organized by harness name and seed pool shared memory name."""
    script_id: int
    harness_name: str
    shm_name: str
    seed_ids: List[int]

    @staticmethod
    def serialize(bundle: 'SubmitBundle') -> bytes:
        """Serialize list of seed IDs"""
        return json.dumps(asdict(bundle)).encode()
        
    @staticmethod
    def deserialize(data: bytes) -> 'SubmitBundle':
        """Deserialize to list of seed IDs"""
        obj = json.loads(data.decode())
        return SubmitBundle(**obj)


class DirMonitor:
    """Monitors a directory for new seed files and adds them to shared memory pool."""
    
    def __init__(self, watch_dir: Path, shm_producer: SeedShmemPoolProducer):
        """Initialize the directory monitor.
        
        Args:
            watch_dir: Directory to monitor for seed files
            shm_producer: Shared memory pool producer
        """
        self.watch_dir = watch_dir
        self.shm_producer = shm_producer
        self.processed_files: Set[str] = set()
        
    async def scan_directory(self) -> List[int]:
        """Scan the directory for new files and add them to shared memory.
        
        Returns:
            List of seed IDs for newly added seeds
        """
        if not self.watch_dir.exists():
            logger.warning(f"Watch directory {self.watch_dir} does not exist")
            return []
            
        new_seed_ids = []
        for file_path in self.watch_dir.glob("*"):
            if not file_path.is_file():
                continue
                
            file_path_str = str(file_path)
            if file_path_str in self.processed_files:
                continue
                
            try:
                seed_data = file_path.read_bytes()
                seed_id = self.shm_producer.add_seed(seed_data)
                
                if seed_id is not None and seed_id >= 0:
                    new_seed_ids.append(seed_id)
                    self.processed_files.add(file_path_str)
                    logger.info(f"Added seed from {file_path.name} with ID {seed_id}")
                else:
                    if seed_id == -1:
                        logger.warning(f"Shared memory pool is full - cannot add {file_path.name}")
                    else:
                        logger.warning(f"Seed from {file_path.name} is invalid or too large")
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {e}")
                
        return new_seed_ids


class MinimalRouter:
    """A minimal router implementation that communicates with dealers."""
    
    def __init__(self, 
                 shm_name: str, 
                 harness_name: str,
                 watch_dir: Path,
                 bind_addr: str = "ipc:///tmp/haha",
                 script_id: int = 1,
                 dealer_timeout: int = 10):
        """Initialize the minimal router.
        
        Args:
            shm_name: Name of the shared memory segment
            harness_name: Name of the harness
            watch_dir: Directory to monitor for seed files
            bind_addr: Address to bind the ZMQ router socket
            script_id: ID for the script
            dealer_timeout: Timeout for dealers in seconds
        """
        self.shm_name = shm_name
        self.harness_name = harness_name
        self.script_id = script_id
        self.dealer_timeout = dealer_timeout
        
        # Create shared memory pool
        self.shm_producer = SeedShmemPoolProducer(shm_name, item_num=10, create=True)
        logger.info(f"Created shared memory pool '{shm_name}'")
        
        # Set up directory monitor
        self.dir_monitor = DirMonitor(watch_dir, self.shm_producer)
        
        # Set up ZeroMQ
        self.ctx = azmq.Context.instance()
        self.router = self.ctx.socket(zmq.ROUTER)
        self.router.bind(bind_addr)
        logger.info(f"Router bound to {bind_addr}")
        
        # Dealer tracking (identity -> timestamp)
        self.dealers = {}
        
        # Queue to store seeds when no dealers are available
        self.pending_seeds = []
        
    async def close(self):
        """Clean up resources."""
        self.router.close()
        self.shm_producer.close()
        logger.info("Router closed")
        
    async def directory_monitor_loop(self):
        """Loop that periodically checks the directory for new seeds."""
        logger.info(f"Starting directory monitor loop for {self.dir_monitor.watch_dir}")
        
        while True:
            try:
                new_seed_ids = await self.dir_monitor.scan_directory()
                
                # Send each new seed individually to the dealer
                for seed_id in new_seed_ids:
                    # Create a bundle with just 1 seed_id as per requirements
                    bundle = SubmitBundle(
                        script_id=self.script_id,
                        harness_name=self.harness_name,
                        shm_name=self.shm_name,
                        seed_ids=[seed_id]
                    )
                    
                    await self.send_seed(bundle)
                    
                await asyncio.sleep(1)  # Check once per second
            except asyncio.CancelledError:
                logger.info("Directory monitor loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in directory monitor loop: {e}")
                await asyncio.sleep(1)
                
    async def send_seed(self, bundle: SubmitBundle):
        """Send a SEED message to a dealer.
        
        Args:
            bundle: The SubmitBundle to send
        """
        # Check if we have any active dealers
        if not self.dealers:
            # Queue the seed instead of dropping it
            self.pending_seeds.append(bundle)
            logger.info(f"No active dealers - queued seed id={bundle.seed_ids[0]} for later delivery")
            return
            
        # Select a dealer (just use the first one for simplicity)
        dealer_id = next(iter(self.dealers))
        
        # Generate a unique message ID
        msg_id = uuid.uuid4().hex.encode()
        
        try:
            # Send the SEED message
            await self.router.send_multipart([
                dealer_id,
                b"SEED",
                msg_id,
                SubmitBundle.serialize(bundle)
            ])
            logger.info(f"Sent SEED message to dealer {dealer_id.hex()}, seed_id={bundle.seed_ids[0]}")
        except Exception as e:
            logger.error(f"Error sending SEED message: {e}")
            
    async def message_handling_loop(self):
        """Loop that handles messages from dealers."""
        logger.info("Starting message handling loop")
        
        while True:
            try:
                # Check for expired dealers
                now = time.time()
                expired = [ident for ident, ts in self.dealers.items() 
                          if now - ts > self.dealer_timeout]
                for ident in expired:
                    logger.info(f"Dealer {ident.hex()} timed out and was removed")
                    del self.dealers[ident]
                
                # Receive and process messages
                try:
                    dealer_id, cmd, *frames = await self.router.recv_multipart(flags=zmq.NOBLOCK)
                    
                    if cmd == b"HEARTBEAT":
                        # Update dealer's last seen time
                        harness_name = frames[0].decode() if frames else self.harness_name
                        self.dealers[dealer_id] = time.time()
                        logger.info(f"Received HEARTBEAT from dealer {dealer_id.hex()} for harness {harness_name}")
                        
                        # If we have pending seeds and this is a new dealer, send them now
                        if dealer_id not in self.dealers and self.pending_seeds:
                            logger.info(f"New dealer connected - processing {len(self.pending_seeds)} pending seeds")
                            # Process all pending seeds
                            for pending_bundle in self.pending_seeds:
                                await self.send_seed(pending_bundle)
                            # Clear the queue after attempting to send all seeds
                            self.pending_seeds = []
                        
                    elif cmd == b"ACK":
                        # Just echo the ACK message as required
                        msg_id, bundle_data = frames
                        logger.info(f"Received ACK from dealer {dealer_id.hex()} for message {msg_id.decode()}")
                        
                except zmq.Again:
                    # No messages available
                    await asyncio.sleep(0.1)
                    
                # Check if we have pending seeds and dealers are now available
                if self.pending_seeds and self.dealers:
                    logger.info(f"Dealers now available - processing {len(self.pending_seeds)} pending seeds")
                    # Process all pending seeds
                    pending_seeds = self.pending_seeds
                    self.pending_seeds = []
                    for pending_bundle in pending_seeds:
                        await self.send_seed(pending_bundle)
                    
            except asyncio.CancelledError:
                logger.info("Message handling loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in message handling loop: {e}")
                await asyncio.sleep(1)
                
    async def run(self):
        """Run the minimal router."""
        tasks = []
        try:
            tasks.append(asyncio.create_task(self.directory_monitor_loop()))
            tasks.append(asyncio.create_task(self.message_handling_loop()))
            
            # Wait for all tasks to complete
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            logger.info("Router operation cancelled")
        except Exception as e:
            logger.error(f"Error in router operation: {e}")
        finally:
            # Cancel all running tasks
            for task in tasks:
                task.cancel()
                
            await self.close()
            logger.info("Router shutdown complete")
            

async def main():
    """Main entry point for the minimal router."""
    # Configuration
    SHM_NAME = "minimal-router-shm"
    HARNESS_NAME = "oof_mutate_test"
    WATCH_DIR = Path("./seeds")  # Directory to monitor for seeds
    BIND_ADDR = "ipc:///tmp/haha"   # Address to bind the ZMQ router socket
    
    # Create watch directory if it doesn't exist
    WATCH_DIR.mkdir(exist_ok=True)
    
    # Create and run the minimal router
    router = MinimalRouter(
        shm_name=SHM_NAME,
        harness_name=HARNESS_NAME,
        watch_dir=WATCH_DIR,
        bind_addr=BIND_ADDR
    )
    
    try:
        await router.run()
    except KeyboardInterrupt:
        logger.info("Router stopped by user")
    finally:
        await router.close()
        
        
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Router stopped by user")
    except Exception as e:
        logger.error(f"Router failed with error: {e}", exc_info=True)