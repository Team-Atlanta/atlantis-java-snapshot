#!/usr/bin/env python3
import asyncio
import logging
import traceback

import atomics
from kubernetes_asyncio import config
from kubernetes_asyncio.client import api_client
from kubernetes_asyncio.leaderelection import electionconfig, leaderelection
from kubernetes_asyncio.leaderelection.resourcelock.leaselock import LeaseLock

from .utils import get_env_or_abort, get_env_or_empty

logger = logging.getLogger(__name__)
CRS_JAVA_TEST_ENV_ROLE = get_env_or_empty("CRS_JAVA_TEST_ENV_ROLE")
K8S_AVAILABLE = not CRS_JAVA_TEST_ENV_ROLE  # We are in k8s env if no test env is set
CRS_JAVA_POD_NAME = get_env_or_abort("CRS_JAVA_POD_NAME")
CRS_JAVA_POD_NAMESPACE = get_env_or_abort("CRS_JAVA_POD_NAMESPACE")


class LeaderElectionManager:
    """Manager for k8s leader election in CRS-Java"""

    def __init__(self):
        global logger, CRS_JAVA_POD_NAME, CRS_JAVA_POD_NAMESPACE

        self.logger = logger
        self.lock_name = "crs-java-leader-node-lock"
        self.lock_namespace = CRS_JAVA_POD_NAMESPACE
        self.candidate_id = CRS_JAVA_POD_NAME
        self._is_leader_atomic = atomics.atomic(width=4, atype=atomics.INT)
        self._is_leader_atomic.store(0)

        self.logger.info(
            f"LeaderElectionManager initialized with lock_name: {self.lock_name}, lock_namespace: {self.lock_namespace}, candidate_id: {self.candidate_id}"
        )

    def is_leader(self) -> bool:
        return self._is_leader_atomic.load() != 0

    async def _leader_start_func(self):
        """Callback when this instance becomes the leader"""
        self.logger.info("This instance became the leader")
        self._is_leader_atomic.store(1)

    async def _leader_end_func(self):
        """Callback when this instance is no longer the leader"""
        self.logger.info("This instance is no longer the leader")
        self._is_leader_atomic.store(0)

    async def run_leader_election(self, should_continue_fn):
        """Keep run the leader election process until cancelled."""
        global CRS_JAVA_TEST_ENV_ROLE, K8S_AVAILABLE

        if not K8S_AVAILABLE:
            # test env
            self._is_leader_atomic.store(1 if CRS_JAVA_TEST_ENV_ROLE == "leader" else 0)
            self.logger.info(f"Running in test env with role: {CRS_JAVA_TEST_ENV_ROLE}")
            return

        # k8s env
        try:
            config.load_incluster_config()
            self.logger.info("Loaded in-cluster config successfully")
        except Exception as e:
            self.logger.error(
                f"Failed to load in-cluster config: {e} {traceback.format_exc()}"
            )

        while should_continue_fn():
            try:
                async with api_client.ApiClient() as apic:
                    leader_election_config = electionconfig.Config(
                        LeaseLock(
                            self.lock_name,
                            self.lock_namespace,
                            self.candidate_id,
                            apic,
                        ),
                        lease_duration=30,
                        renew_deadline=25,
                        retry_period=5,
                        onstarted_leading=self._leader_start_func,
                        onstopped_leading=self._leader_end_func,
                    )

                    await leaderelection.LeaderElection(leader_election_config).run()

                    self.logger.info(
                        "Lost leadership or failed to acquire it, retrying..."
                    )
                    await asyncio.sleep(5)
            except Exception as e:
                self.logger.error(
                    f"Leader election failed with error: {e} {traceback.format_exc()}"
                )
                # NOTE: When network isolation issue happens, the last lock holder keeps being the leader. There can have multiple leader election instances running at the same time due to the isolation. We didn't do anything to the _is_leader_atomic flag to keep it simple.
                # self._is_leader_atomic.store(1)
                await asyncio.sleep(10)
