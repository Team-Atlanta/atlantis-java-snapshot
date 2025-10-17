from .utils import get_env_or_abort


def get_redis_sinkpoint_hash_key(sp_key: str) -> str:
    """Convert sp_key to sp_hash_key."""
    return f"sinkpoints:hash:{sp_key}"


def get_redis_sinkpoint_data_key(sp_key: str) -> str:
    """Convert sp_key to sp_data_key."""
    return f"sinkpoints:data:{sp_key}"


def extract_sp_key_from_hash_key(sp_hash_key: str) -> str:
    """Extract sp_key from sp_hash_key."""
    prefix = "sinkpoints:hash:"
    if sp_hash_key.startswith(prefix):
        return sp_hash_key[len(prefix) :]
    return sp_hash_key


def extract_sp_key_from_data_key(sp_data_key: str) -> str:
    """Extract sp_key from sp_data_key."""
    prefix = "sinkpoints:data:"
    if sp_data_key.startswith(prefix):
        return sp_data_key[len(prefix) :]
    return sp_data_key


def get_redis_sinkpoint_hash_pattern() -> str:
    """Get the Redis pattern for matching all sinkpoint hash keys."""
    return "sinkpoints:hash:*"


def get_redis_url() -> str:
    """Get the Redis URL."""
    return get_env_or_abort("CPMETA_REDIS_URL")


def get_redis_expkit_cache_key(beepseed_key: str, model_id: str) -> str:
    """Get the Redis key for the exploit kit."""
    return f"expkit:cache:{beepseed_key}:{model_id}"


def get_redis_concolic_cache_key(req_data_id: str) -> str:
    """Get the Redis key for the concolic cache."""
    return f"concolic:cache:{req_data_id}"
