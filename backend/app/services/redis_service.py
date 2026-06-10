import json
import logging
from typing import Any, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

_redis_instance = None


class RedisService:
    def __init__(self):
        self.redis = None
        if not settings.redis_url or settings.redis_url == "redis://localhost:6379/0":
            logger.info("Redis not configured. Cache disabled.")
            return
        try:
            import redis as redis_module
            self.redis = redis_module.from_url(settings.redis_url, decode_responses=True, socket_timeout=2)
            self.redis.ping()
            logger.info("Redis connection established.")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}. Cache disabled.")
            self.redis = None

    def get(self, key: str) -> Optional[Any]:
        if not self.redis:
            return None
        try:
            data = self.redis.get(key)
            if data:
                try:
                    return json.loads(data)
                except (json.JSONDecodeError, TypeError):
                    return data
            return None
        except Exception:
            return None

    def set(self, key: str, value: Any, expire: int = 3600):
        if not self.redis:
            return
        try:
            if not isinstance(value, str):
                value = json.dumps(value)
            self.redis.setex(key, expire, value)
        except Exception:
            pass

    def delete(self, key: str):
        if not self.redis:
            return
        try:
            self.redis.delete(key)
        except Exception:
            pass

    def exists(self, key: str) -> bool:
        if not self.redis:
            return False
        try:
            return self.redis.exists(key) > 0
        except Exception:
            return False


def get_redis() -> RedisService:
    global _redis_instance
    if _redis_instance is None:
        _redis_instance = RedisService()
    return _redis_instance


redis_cache = None
