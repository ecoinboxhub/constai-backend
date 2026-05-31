import json
import logging
from typing import Any, Optional

import redis
from app.core.config import settings

logger = logging.getLogger(__name__)

class RedisService:
    def __init__(self):
        try:
            self.redis = redis.from_url(settings.redis_url, decode_responses=True)
            self.redis.ping()
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

redis_cache = RedisService()
