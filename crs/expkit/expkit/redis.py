import logging
import traceback
from typing import Optional

import redis

from .beepobjs import BeepSeed
from .utils import CRS_ERR_LOG, CRS_WARN_LOG, get_env_or_abort

logger = logging.getLogger(__name__)


CRS_ERR = CRS_ERR_LOG("redis")
CRS_WARN = CRS_WARN_LOG("redis")


def get_redis_url() -> str:
    """Get the Redis URL."""
    return get_env_or_abort("CPMETA_REDIS_URL")


def get_redis_expkit_cache_key(beepseed_key: str, model_id: str, stage: str) -> str:
    """Get the Redis key for the exploit kit."""
    return f"expkit:cache:{beepseed_key}:{model_id}:{stage}"


class RedisCacheClient:
    """Redis client for caching operations in expkit."""

    def __init__(self):
        """Initialize the Redis client."""
        self._redis_cli = None
        self._init_redis_client()

    def _init_redis_client(self) -> bool:
        try:
            if self._redis_cli is None:
                redis_url = get_redis_url()
                self._redis_cli = redis.from_url(redis_url)
            else:
                # Check if connection is alive
                self._redis_cli.ping()
            return True
        except Exception as e:
            logger.warning(
                f"{CRS_WARN} Redis connection error: {e} {traceback.format_exc()}"
            )
            self._redis_cli = None
            return False

    def get(self, beepseed: BeepSeed, model: str, stage: str) -> Optional[str]:
        if not self._init_redis_client():
            return None

        try:
            key = get_redis_expkit_cache_key(beepseed.redis_key(), model, stage)
            value = self._redis_cli.get(key)
            if value is None:
                logger.info(f"Cache miss for {key}")
                return None
            logger.info(f"Cache hit for {key}")
            return value.decode("utf-8")
        except Exception as e:
            logger.warning(
                f"{CRS_WARN} Error getting cache for BeepSeed {beepseed.redis_key()} stage {stage}: {e} {traceback.format_exc()}"
            )
            return None

    def set(self, beepseed: BeepSeed, model: str, stage: str, data: str):
        if not self._init_redis_client():
            return

        try:
            key = get_redis_expkit_cache_key(beepseed.redis_key(), model, stage)
            succ = self._redis_cli.set(key, data)
            if not succ:
                logger.error(f"{CRS_ERR} Failed to set cache for {key}")
            else:
                logger.info(f"Cache set for {key}")
            return succ
        except Exception as e:
            logger.error(
                f"{CRS_ERR} Error setting cache for BeepSeed {beepseed.redis_key()} stage {stage}: {e} {traceback.format_exc()}"
            )
