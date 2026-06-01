import json
import logging
from typing import Any, Optional

import redis
from app.core.config import settings

logger = logging.getLogger(__name__)

# Global singleton cache instance
_redis_instance = None


class RedisService:
    def __init__(self):
        try:
            self.redis = redis.from_url(settings.redis_url, decode_responses=True)
            self.redis.ping()
            logger.info("Redis connection established.")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis = None

    def get(self, key: str) -> Optional[Any]:
        if not self.redis:
            return None
        data = self.redis.get(key)
        if data:
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                return data
        return None

    def set(self, key: str, value: Any, expire: int = 3600):
        if not self.redis:
            return
        if not isinstance(value, str):
            value = json.dumps(value)
        self.redis.setex(key, expire, value)

    def delete(self, key: str):
        if not self.redis:
            return
        self.redis.delete(key)

    def exists(self, key: str) -> bool:
        if not self.redis:
            return False
        return self.redis.exists(key) > 0


def get_redis() -> RedisService:
    """Lazy-load Redis singleton. Initialize only when first called."""
    global _redis_instance
    if _redis_instance is None:
        _redis_instance = RedisService()
    return _redis_instance


# For backwards compatibility, provide a default instance accessor
# (Note: this should NOT be used at import time)
@property
def redis_cache():
    return get_redis()
