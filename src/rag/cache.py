"""
Feature 18/20: Redis Caching
Caches full RAG responses keyed by a normalized query hash, giving
sub-second responses for repeated/similar queries without hitting
OpenSearch or Gemini again.
"""
import hashlib
import json
from typing import Optional

import redis

from config.settings import settings
from src.utils.logging_config import logger
from src.utils.metrics import CACHE_HITS, CACHE_MISSES

_redis_client = redis.from_url(settings.redis_url, decode_responses=True)


def _cache_key(query: str, mode: str) -> str:
    normalized = query.strip().lower()
    digest = hashlib.sha256(f"{mode}:{normalized}".encode()).hexdigest()
    return f"rag:response:{digest}"


def get_cached_response(query: str, mode: str = "hybrid") -> Optional[dict]:
    key = _cache_key(query, mode)
    try:
        raw = _redis_client.get(key)
    except redis.RedisError as e:
        logger.warning(f"Redis unavailable, skipping cache read: {e}")
        return None

    if raw:
        CACHE_HITS.inc()
        return json.loads(raw)
    CACHE_MISSES.inc()
    return None


def set_cached_response(query: str, mode: str, response: dict, ttl: int = None) -> None:
    key = _cache_key(query, mode)
    ttl = ttl or settings.redis_cache_ttl_seconds
    try:
        _redis_client.setex(key, ttl, json.dumps(response))
    except redis.RedisError as e:
        logger.warning(f"Redis unavailable, skipping cache write: {e}")
