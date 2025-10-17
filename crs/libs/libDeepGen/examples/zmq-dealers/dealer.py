#!/usr/bin/env python3
"""
Seed-Consumer (DEALER, asyncio)
"""
import asyncio
import uuid
import zmq.asyncio as azmq
import zmq
import json
import logging

from dataclasses import dataclass, asdict
from typing import List


@dataclass(frozen=True, slots=True)
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


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('dealer')

ROUTER_ADDR   = "ipc:///tmp/haha"
#ROUTER_ADDR   = "tcp://localhost:5555"
HB_INTERVAL   = 5
HARNESS = "Rdf4jOne"

ctx    = azmq.Context.instance()
dealer = ctx.socket(zmq.DEALER)
dealer_id = f"SC-{uuid.uuid4().hex[:4]}"
dealer.setsockopt_string(zmq.IDENTITY, dealer_id)
logger.info(f"Dealer created with identity: {dealer_id}")

dealer.connect(ROUTER_ADDR)
logger.info(f"Connected to router at {ROUTER_ADDR}")

async def heartbeat_loop():
    logger.info(f"Starting heartbeat loop (interval: {HB_INTERVAL}s)")
    heartbeat_count = 0
    try:
        while True:
            logger.info(f"Sending HEARTBEAT {heartbeat_count}")
            await dealer.send_multipart([b"HEARTBEAT", HARNESS.encode()])
            heartbeat_count += 1
            if heartbeat_count % 10 == 0:
                logger.info(f"Sent {heartbeat_count} heartbeats so far")
            await asyncio.sleep(HB_INTERVAL)
    except asyncio.CancelledError:
        logger.info("Heartbeat loop cancelled")
    except Exception as e:
        logger.error(f"Error in heartbeat loop: {e}", exc_info=True)

async def main():
    logger.info("Starting dealer main loop")
    hb_task = asyncio.create_task(heartbeat_loop())
    
    seed_count = 0
    last_printed_count = 0
    try:
        while True:
            logger.debug("Waiting for message from router")
            cmd, *frames = await dealer.recv_multipart()
            logger.debug(f"Received command: {cmd}")
            
            if cmd == b"SEED":
                msg_id, bundle_b = frames
                logger.debug(f"Received SEED BATCH msg: msg_id={msg_id}")
                
                bundle = SubmitBundle.deserialize(bundle_b)
                seed_count += len(bundle.seed_ids)
                
                # Send ack
                logger.debug(f"Sending ACK for seed {msg_id}")
                await dealer.send_multipart([b"ACK", msg_id, bundle_b])
                logger.debug(f"ACK sent for seed {msg_id}")

                if seed_count - last_printed_count >= 1000:
                    logger.info(f"Processed {seed_count} seeds so far")
                    last_printed_count = seed_count
            else:
                logger.warning(f"Received unknown command: {cmd}")
    except asyncio.CancelledError:
        logger.info("Dealer main loop cancelled")
    except Exception as e:
        logger.error(f"Error in dealer main loop: {e}", exc_info=True)
    finally:
        logger.info("Cleaning up tasks and connections")
        hb_task.cancel()
        dealer.close()
        logger.info("Dealer shutdown complete")

if __name__ == "__main__":
    logger.info("Starting ZeroMQ dealer example")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Dealer stopped by user")
    except Exception as e:
        logger.error(f"Dealer failed with error: {e}", exc_info=True)