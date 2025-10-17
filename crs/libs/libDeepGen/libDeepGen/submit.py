import aiofiles
import asyncio
import collections
import hashlib
import itertools
import json
import logging
import os
import time
import uuid
import zmq
import zmq.asyncio as azmq

from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Tuple

from .ipc_utils.ringbuffer import RingBufferProducer
from .ipc_utils.shm_pool import SeedShmemPoolConsumer
from .script import Script


logger = logging.getLogger(__name__)


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


class SubmitBase(ABC):
    """Base class for submitting seeds to the Ensembler."""

    def __init__(self, proc_map: Dict[str, Tuple[str, str]], workdir: Path):
        """
        Args:
            proc_map: A dict: { proc_id : (recycle_rb_name, seed_pool_shm_name) }
            workdir: ..
        """
        self.proc_map = proc_map
        self.workdir = workdir
        self.recycle_rbs = {}

        # Create a reverse mapping for faster lookups
        self.pool_to_proc_map = {}
        for proc_id, (_, pool_name) in self.proc_map.items():
            self.pool_to_proc_map[pool_name] = proc_id

        # Recycle rbs for notifying ExecProc instances when seeds can be recycled
        for proc_id, (recycle_rb_name, _) in proc_map.items():
            self.recycle_rbs[proc_id] = RingBufferProducer(recycle_rb_name, create=False)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.aclose()

    async def aclose(self):
        """Clean up resources."""
        for rb in self.recycle_rbs.values():
            rb.close()

    async def request_seed_submit(self, proc_id: str, script_id: int, script: Script, seed_ids: List[int]):
        """Launch seeds submission reqeust to Submit, called by Engine."""
        if not seed_ids:
            return
        if proc_id not in self.proc_map:
            logger.error(f"Unknown proc_id: {proc_id}")
            return

        _, seed_pool_shm_name = self.proc_map[proc_id]
        await self.do_submit(
            SubmitBundle(
                script_id=script_id,
                harness_name=script.harness_name,
                shm_name=seed_pool_shm_name,
                seed_ids=seed_ids,
            )
        )

    @abstractmethod
    async def do_submit(self, submit_bundle: SubmitBundle):
        """Submit the bundle to the seed consumer, i.e., fuzzer."""
        pass

    @abstractmethod
    async def recycle_loop(self, should_continue_fn):
        """Recycle the seeds in the bundle."""
        pass


class MockSubmit(SubmitBase):
    """Submit implementation with a mock seed processor for testing."""

    def __init__(self, proc_map: Dict[str, Tuple[str, str]], workdir: Path):
        super().__init__(proc_map, workdir)

        self.mock_process_queue = asyncio.Queue()

    async def aclose(self):
        """Clean up resources."""
        self.mock_process_queue = None
        await super().aclose()

    async def do_submit(self, submit_bundle: SubmitBundle):
        """Submit the bundle to the seed consumer, i.e., fuzzer."""
        try:
            self.mock_process_queue.put_nowait(submit_bundle)
            #logger.info(f"MockSubmit submitted bundle: {submit_bundle}")
        except Exception as e:
            logger.error(f"Error submitting bundle: {e} {traceback.format_exc()}")

    async def _get_submit_ack(self) -> SubmitBundle:
        """Receive the ack from the seed consumer, i.e., fuzzer."""
        bundle =  None
        try:
            bundle = self.mock_process_queue.get_nowait()
            #logger.info(f"MockSubmit received ack: {bundle}")
        except Exception as e:
            logger.error(f"Error receiving ack: {e} {traceback.format_exc()}")
        finally:
            if bundle:
                self.mock_process_queue.task_done()
            return bundle

    async def recycle_loop(self, should_continue_fn):
        """Recycle the seeds in the bundle."""
        logger.info("Seed id recycle loop started")

        while should_continue_fn():
            bundle = await self._get_submit_ack()
            if bundle:
                #logger.info(f"Submit recycle loop received bundle: {bundle}")
                proc_id = self.pool_to_proc_map.get(bundle.shm_name)
                self.recycle_rbs[proc_id].put_until(json.dumps(bundle.seed_ids), should_continue_fn)
            else:
                await asyncio.sleep(0.1)
        logger.info("Seed id recycle loop terminated")


class LocalFSSubmit(SubmitBase):
    """Mock submit that stores seeds to local filesystem."""
    
    def __init__(self, proc_map: Dict[str, Tuple[str, str]], workdir: Path):
        super().__init__(proc_map, workdir)

        self.mock_process_queue = asyncio.Queue()

        self.local_dir = workdir / "seeds"
        self.local_dir.mkdir(parents=True, exist_ok=True)

        self.seed_pool_consumers = {}
        for _, (_, seed_pool_shm_name) in proc_map.items():
            if seed_pool_shm_name not in self.seed_pool_consumers:
                self.seed_pool_consumers[seed_pool_shm_name] = SeedShmemPoolConsumer(
                    shm_name=seed_pool_shm_name, create=False)

    async def aclose(self):
        """Clean up resources including cached shared memory consumers."""
        self.mock_process_queue = None
        for pool in self.seed_pool_consumers.values():
            pool.close()
        self.seed_pool_consumers.clear()
        await super().aclose()

    async def do_submit(self, submit_bundle: SubmitBundle):
        """Submit the bundle to the seed consumer, i.e., fuzzer."""
        try:
            self.mock_process_queue.put_nowait(submit_bundle)
            #logger.info(f"MockSubmit submitted bundle: {submit_bundle}")
        except Exception as e:
            logger.error(f"Error submitting bundle: {e} {traceback.format_exc()}")

    async def _process_seed(self, bundle: SubmitBundle):
        """Thread fn for the Engine's thread pool that simulates a file-saving Ensembler."""
        if not bundle:
            return

        logger.debug(f"LocalFSSubmit received bundle: {bundle}")
        # Use cached seed pool consumer
        pool = self.seed_pool_consumers.get(bundle.shm_name)
        if not pool:
            logger.error(f"No cached pool consumer for {bundle.shm_name}")
            return
        
        for seed_id in bundle.seed_ids:
            try:
                seed_data = pool.get_seed_content(seed_id)
                if seed_data:
                    harness_dir = self.local_dir / os.path.basename(bundle.harness_name)
                    harness_dir.mkdir(exist_ok=True)
                    
                    seed_file = harness_dir / f"seed_{seed_id}.bin"
                    async with aiofiles.open(seed_file, "wb") as f:
                        await f.write(seed_data)
                    os.remove(seed_file)
                    # print(str(seed_file.resolve()))
            except Exception as e:
                logger.error(f"Error processing seed {seed_id} from {bundle.shm_name}: {e}")
                continue

        logger.debug(f"LocalFSSubmit processed bundle: {bundle}")

    async def _get_submit_ack(self) -> SubmitBundle:
        """Receive the ack from the seed consumer, i.e., fuzzer."""
        bundle =  None
        try:
            bundle = self.mock_process_queue.get_nowait()
            #logger.info(f"MockSubmit received ack: {bundle}")

            # NOTE: mock a seed processer logic here, storing to local fs
            #     in real case, this should be processed before _get_submit_ack is invoked
            await self._process_seed(bundle)
        except Exception as e:
            logger.error(f"Error receiving ack: {e} {traceback.format_exc()}")
        finally:
            if bundle:
                self.mock_process_queue.task_done()
            return bundle

    async def recycle_loop(self, should_continue_fn):
        """Recycle the seeds in the bundle."""
        logger.info("Seed id recycle loop started")

        while should_continue_fn():
            bundle = await self._get_submit_ack()
            if bundle:
                #logger.info(f"Submit recycle loop received bundle: {bundle}")
                proc_id = self.pool_to_proc_map.get(bundle.shm_name)
                # Notify the recycle ringbuffer, seed_ids => int list, just use json.dumps
                self.recycle_rbs[proc_id].put_until(json.dumps(bundle.seed_ids), should_continue_fn)
            else:
                await asyncio.sleep(0.1)
        logger.info("Seed id recycle loop terminated")


class ZeroMQSubmit(SubmitBase):
    """Submit implementation using ZeroMQ ROUTER-DEALER pattern for distributed seed processing."""

    def __init__(self, proc_map: Dict[str, Tuple[str, str]], workdir: Path, 
                 bind_addr: str = "ipc:///tmp/haha", dealer_timeout: int = 15, 
                 seed_timeout: int = 60):
        super().__init__(proc_map, workdir)

        self.bind_addr = bind_addr
        self.dealer_timeout = dealer_timeout
        self.seed_timeout = seed_timeout

        # ZeroMQ setup
        self.ctx = azmq.Context.instance()
        self.router = self.ctx.socket(zmq.ROUTER)
        self.router.bind(bind_addr)
        logger.info(f"ZeroMQSubmit bound to {bind_addr}")

        # ident -> {"ts": last_seen_timestamp, "harness": str}
        self.dealers = collections.OrderedDict()
        # harness_name -> (dealer_cycle, dealer_count)
        self.dealer_cycles: Dict[str, (itertools.cycle, int)] = {}

        self.pending_seeds = {}  # msg_id(bytes) -> (ts_send, dealer ident, bundle)
        self.act_queue = asyncio.Queue()  # for internal use

        self.deep_check = False  # whether to check the seed content
        #self.deep_check = True  # whether to check the seed content

        # content check purpose
        if self.deep_check:
            self.seed_pool_consumers = {}
            for _, (_, seed_pool_shm_name) in proc_map.items():
                if seed_pool_shm_name not in self.seed_pool_consumers:
                    self.seed_pool_consumers[seed_pool_shm_name] = SeedShmemPoolConsumer(
                        shm_name=seed_pool_shm_name, create=False)
                    
    def print_seed_info_for_check(self, msg_id: str, bundle: SubmitBundle):
        """Print seed information for verification checks."""
        if not bundle or not bundle.seed_ids:
            logger.warning(f"Empty bundle or seed IDs for msg_id: {msg_id}")
            return
            
        pool = self.seed_pool_consumers.get(bundle.shm_name)
        if not pool:
            logger.warning(f"No cached pool consumer for {bundle.shm_name}")
            return
            
        for seed_id in bundle.seed_ids:
            try:
                seed_data = pool.get_seed_content(seed_id)
                if not seed_data:
                    logger.warning(f"Seed data not found for seed_id: {seed_id} in {bundle.shm_name}")
                    return
                    
                sha256 = hashlib.sha256(seed_data).hexdigest()
                #logger.info(f"CHECK {msg_id}, {bundle.shm_name}, {seed_id}, {sha256}")
                logger.info(f"CHECK {sha256}")
            except Exception as e:
                logger.error(f"Error processing seed {seed_id} from {bundle.shm_name}: {e}")

    async def aclose(self):
        """Clean up resources."""
        if self.deep_check:
            for pool in self.seed_pool_consumers.values():
                pool.close()
            self.seed_pool_consumers.clear()
        self.router.close()
        self.ctx.term()
        await super().aclose()

    def _rebuild_cycles(self):
        """Rebuild the dealer cycles based on the current dealer list."""
        self.dealer_cycles.clear()

        groups = collections.defaultdict(list)
        for ident, info in self.dealers.items():
            groups[info["harness"]].append(ident)

        wildcard = groups.pop("*", [])

        if wildcard:
            self.dealer_cycles["*"] = (itertools.cycle(wildcard), len(wildcard))

        for harness, dealers in groups.items():
            merged = dealers + [w for w in wildcard if w not in dealers]
            self.dealer_cycles[harness] = (itertools.cycle(merged), len(merged))

    def _handle_act_heartbeat(self, cnt):
        """Handle heartbeat from dealer."""
        ident, harness_name = cnt
        new_dealer = ident not in self.dealers
        harness_changed = (not new_dealer) and (self.dealers[ident]["harness"] != harness_name)
        self.dealers[ident] = {"ts": time.time(), "harness": harness_name}

        if new_dealer:
            logger.info(f"New dealer connected: {ident}, harness={harness_name}")
            self._rebuild_cycles()
        elif harness_changed:
            logger.info(f"Dealer {ident} updated harness to {harness_name}")
            self._rebuild_cycles()
        else:
            logger.debug(f"Received HEARTBEAT from dealer: {ident}")

    def _handle_act_ack(self, should_continue_fn, cnt):
        """Handle ACK from dealer."""
        msg_id = None
        try:
            ident, msg_id, msg = cnt
            if msg_id not in self.pending_seeds:
                logger.warning(f"Expired or unknown ACK from dealer: {ident}, msg_id={msg_id}")
                return
            bundle = msg
            proc_id = self.pool_to_proc_map.get(bundle.shm_name)
            # Notify the recycle ringbuffer, seed_ids => int list, just use json.dumps
            self.recycle_rbs[proc_id].put_until(json.dumps(bundle.seed_ids), should_continue_fn)
        except Exception as e:
            logger.error(f"Error handling ACK from dealer: {e}", exc_info=True)
        finally:
            if msg_id is not None:
                self.pending_seeds.pop(msg_id, None)

    def _handle_act_seed(self, cnt):
        """Handle SEED submit request from engine."""
        msg_id, bundle = str(uuid.uuid4()), cnt
        self.pending_seeds[msg_id] = (None, None, bundle)

    def _handle_acts(self, should_continue_fn) -> bool:
        """Handle internal actions."""
        act, cnt = None, None
        try:
            act, cnt = self.act_queue.get_nowait()
            if act == "ACT-HEARTBEAT":
                # Recv heartbeat msg
                self._handle_act_heartbeat(cnt)
            elif act == "ACT-ACK":
                # Recv ack msg
                self._handle_act_ack(should_continue_fn, cnt)
            elif act == "ACT-SEED":
                # Recv seed submit request
                self._handle_act_seed(cnt)
            else:
                logger.error(f"Unknown internal action: {act}")
        except asyncio.QueueEmpty:
            pass
        except Exception as e:
            logger.error(f"Error handling internal action {act}/{cnt}: {e}", exc_info=True)
        finally:
            if act is None and cnt is None:
                # No action to handle, not busy
                return False
            else:
                # Action handled, mark as done, return busy
                self.act_queue.task_done()
                return True

    def _refresh_dealer_list(self) -> bool:
        """Refresh the dealer list and remove expired dealers."""
        now = time.time()
        expired_dealers = [ident for ident, info in self.dealers.items()
                           if now - info["ts"] > self.dealer_timeout]
        for ident in expired_dealers:
            logger.debug(f"Dealer {ident} timed out after {now - self.dealers[ident]['ts']:.1f}s")
            del self.dealers[ident]
        if expired_dealers:
            self._rebuild_cycles()
            return True
        return False

    def _ack_expired_seeds(self, should_continue_fn) -> bool:
        """Check for expired seeds and send ACK to dealers."""
        now = time.time()
        expired_seeds = [(msg_id, ts_send, ident, bundle)
                         for msg_id, (ts_send, ident, bundle) in self.pending_seeds.items()
                         if (ts_send is not None) and (now - ts_send > self.seed_timeout)]
        for msg_id, ts_send, ident, bundle in expired_seeds:
            if not should_continue_fn():
                logger.warning("ZeroMQSubmit loop cancelled, fast exit")
                break
            logger.warning(f"Seed {msg_id} from dealer {ident} timed out after {now - ts_send:.1f}s")
            try:
                self.act_queue.put_nowait(("ACT-ACK", ("EXPIRE", msg_id, bundle)))
            except Exception as e:
                logger.error(f"Error sending ACK for expired seed {msg_id}: {e}", exc_info=True)
        return bool(expired_seeds)

    def _send_new_seeds(self) -> bool:
        """Send new seeds to dealers."""
        for msg_id, (ts_send, _, bundle) in list(self.pending_seeds.items()):
            if ts_send is not None:
                continue  # Already sent, skip
            cycle, period = self.dealer_cycles.get(bundle.harness_name) or self.dealer_cycles.get("*") or (None, 0)
            for _ in range(period):
                try:
                    ident = next(cycle)
                    if self.deep_check:
                        self.print_seed_info_for_check(msg_id, bundle)
                    self.router.send_multipart(
                        [ident, b"SEED", msg_id.encode(), SubmitBundle.serialize(bundle)],
                        flags=zmq.NOBLOCK)
                    self.pending_seeds[msg_id] = (time.time(), ident, bundle)
                    return True
                except zmq.Again:
                    logger.error(f"Failed to send SEED to {ident}: {msg_id}")
                    continue
                except Exception as e:
                    logger.error(f"Error sending SEED to {ident}: {e}", exc_info=True)
                    continue
        # No new seeds/available dealers to send
        return False

    async def _internal_loop(self, should_continue_fn):
        """Internal loop for processing messages from the router."""
        logger.info("ZeroMQSubmit internal loop started")
        while should_continue_fn():
            busy = self._handle_acts(should_continue_fn)
            busy |= self._refresh_dealer_list()
            busy |= self._ack_expired_seeds(should_continue_fn)
            # NOTE: do not count send new seeds as busy
            self._send_new_seeds()
            if not busy:
                await asyncio.sleep(1)
            else:
                await asyncio.sleep(0)
        logger.info("ZeroMQSubmit internal loop terminated")

    async def _msg_recv_loop(self, should_continue_fn):
        """Message receiving loop for the router."""
        logger.info("ZeroMQSubmit message receiving loop started")

        while should_continue_fn():
            try:
                ident, *frames = await self.router.recv_multipart(flags=zmq.NOBLOCK)
                cmd = frames[0]
                if cmd == b"HEARTBEAT":
                    harness_name = frames[1].decode()
                    self.act_queue.put_nowait(("ACT-HEARTBEAT", (ident, harness_name)))
                elif cmd == b"ACK":
                    msg_id = frames[1].decode()
                    msg = SubmitBundle.deserialize(frames[2])
                    self.act_queue.put_nowait(("ACT-ACK", (ident, msg_id, msg)))
                else:
                    logger.warning(f"Unknown command received: {cmd} from {ident}")
            except zmq.Again:
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Error receiving message: {e}", exc_info=True)
                await asyncio.sleep(1)
            finally:
                await asyncio.sleep(0)

        logger.info("ZeroMQSubmit message receiving loop terminated")

    async def recycle_loop(self, should_continue_fn):
        tasks = []
        try:
            tasks.append(asyncio.create_task(self._internal_loop(should_continue_fn)))
            tasks.append(asyncio.create_task(self._msg_recv_loop(should_continue_fn)))
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            logger.info("ZeroMQSubmit recycle loop cancelled")
        except Exception as e:
            logger.error(f"Error in ZeroMQSubmit recycle loop: {e}", exc_info=True)
        finally:
            for task in tasks:
                task.cancel()
            logger.info("ZeroMQSubmit recycle loop terminated")

    async def do_submit(self, bundle: SubmitBundle):
        """Submit the bundle to the seed consumer, i.e., fuzzer."""
        try:
            self.act_queue.put_nowait(("ACT-SEED", bundle))
        except Exception as e:
            logger.error(f"Error submitting bundle: {e}", exc_info=True)
