import time
import json
import logging

from redis import Redis, RedisError
from typing import Optional, Dict, List, Any


REDIS_DEFAULT_HOST = "localhost"
REDIS_DEFAULT_PORT = 6379


class SetEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        if isinstance(obj, set):
            return {"__set__": list(obj)}
        return super().default(obj)


def _set_decoder(obj: Dict) -> Any:
    if "__set__" in obj:
        return set(obj["__set__"])
    return obj


class RedisClient:
    def __init__(self, url, logger):
        if url is None:
            logger.info("Redis URL is None, Redis client will not be initialized.")
            self.redis = None
            self.logger = None
        else:
            logger.info(f"Connecting to Redis at {url}")
            self.redis = RedisClient.init_redis_with_retry(url, logger=logger)
            self.logger = logger

    @staticmethod
    def serialize(tokens: Dict[str, List[str]]) -> str:
        return json.dumps(
            tokens, cls=SetEncoder, ensure_ascii=False, separators=(",", ":")
        )

    @staticmethod
    def deserialize(blob: str) -> Dict[str, List[str]]:
        return json.loads(blob, object_hook=_set_decoder)

    @staticmethod
    def get_key(typ, source, func):
        PREFIX = "dictgen"
        return f"{PREFIX}:{typ}:{source}:{func}"

    def set(self, typ, source, func, lst):
        if self.redis is None:
            return
        key = RedisClient.get_key(typ, source, func)
        value = RedisClient.serialize(lst)
        self.redis.set(key, value)

    def get(self, typ, source, func):
        if self.redis is None:
            return None
        key = RedisClient.get_key(typ, source, func)
        raw = self.redis.get(key)
        if raw is None:
            return None
        text = raw.decode("utf-8", errors="strict")
        return RedisClient.deserialize(text)

    def delete(self, key):
        if self.redis is None:
            return
        self.redis.delete(key)

    def exists(self, key):
        if self.redis is None:
            return False
        return bool(self.redis.exists(key))

    # -------- copied&pasted from codeindexer

    @staticmethod
    def parse_redis_host(redis_host: str) -> tuple[str, int]:
        """Parse Redis host string into host and port components.

        Handles various formats:
        - host:port (e.g., "localhost:6379", "127.0.0.1:6379")
        - redis://host:port (e.g., "redis://localhost:6379")
        - redis:host:port (treats redis: as part of hostname)
        - host (uses default port)

        Returns:
            tuple: (host, port)
        """
        port = REDIS_DEFAULT_PORT

        # Remove scheme if present (e.g., redis://)
        if "://" in redis_host:
            redis_host = redis_host.split("://", 1)[1]

        # Handle empty port case
        if redis_host.endswith(":"):
            redis_host = redis_host[:-1]

        # Parse host and port
        if ":" in redis_host:
            host, port_str = redis_host.rsplit(":", 1)
            if port_str:  # Only try to parse if port string is not empty
                try:
                    port_num = int(port_str)
                    if 1 <= port_num <= 65535:  # Valid port range
                        port = port_num
                    else:
                        logger.warning(
                            f"Port number {port_str} out of range (1-65535), using default"
                            f" port {port}"
                        )
                except ValueError:
                    logger.warning(
                        f"Invalid port number '{port_str}', using default port {port}"
                    )
        else:
            host = redis_host

        return host, port

    @staticmethod
    def init_redis_with_retry(
        redis_host: Optional[str] = None,
        retry_interval: int = 1,
        max_retries: Optional[int] = None,
        socket_timeout: int = 10,
        db: int = 0,
        logger: Optional[logging.Logger] = None,
    ) -> Redis | None:
        if redis_host is None:
            return None

        host, port = RedisClient.parse_redis_host(redis_host)
        redis_addr = f"{host}:{port}"
        retry_count = 0

        while max_retries is None or retry_count < max_retries:
            try:
                logger.info(f"Attempting to connect to Redis at: {redis_addr}")
                redis_client = Redis(
                    host=host, port=port, db=db, socket_connect_timeout=socket_timeout
                )
                if not redis_client.ping():
                    raise RedisError("Redis ping failed")
                logger.info(f"Successfully connected to Redis at: {redis_addr}")
                return redis_client
            except Exception as e:
                retry_count += 1
                error_msg = f"Failed to connect to Redis at {redis_addr}: {str(e)}"
                if max_retries is None or retry_count < max_retries:
                    logger.warning(
                        f"{error_msg}. Retrying in {retry_interval} seconds..."
                    )
                    time.sleep(retry_interval)
                else:
                    logger.error(error_msg)
                    raise RuntimeError(error_msg) from e

        error_msg = (
            f"Failed to connect to Redis at {redis_addr} in {max_retries} trials"
        )
        raise RuntimeError(error_msg)
