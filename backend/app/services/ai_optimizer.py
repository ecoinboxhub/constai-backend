import functools
import hashlib
import json
import logging
import time
from typing import Any, Callable

from app.services.redis_service import redis_cache

logger = logging.getLogger(__name__)

import asyncio

def ai_cache(expire: int = 86400):
    """
    Decorator to cache AI responses based on prompt hash.
    Supports both sync and async functions.
    Default expiry is 24 hours.
    """
    def decorator(func: Callable):
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(prompt: str, *args, **kwargs):
                cache_input = f"{func.__name__}:{prompt}:{json.dumps(kwargs, sort_keys=True)}"
                cache_key = f"ai_cache:{hashlib.md5(cache_input.encode()).hexdigest()}"
                
                cached_res = redis_cache.get(cache_key)
                if cached_res:
                    logger.info("AI Cache Hit (Async)")
                    return cached_res
                
                start_time = time.time()
                result = await func(prompt, *args, **kwargs)
                duration = time.time() - start_time
                
                logger.info(f"AI Inference (Async): {func.__name__} took {duration:.2f}s")
                
                if result:
                    redis_cache.set(cache_key, result, expire=expire)
                return result
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(prompt: str, *args, **kwargs):
                cache_input = f"{func.__name__}:{prompt}:{json.dumps(kwargs, sort_keys=True)}"
                cache_key = f"ai_cache:{hashlib.md5(cache_input.encode()).hexdigest()}"
                
                cached_res = redis_cache.get(cache_key)
                if cached_res:
                    logger.info("AI Cache Hit (Sync)")
                    return cached_res
                
                start_time = time.time()
                result = func(prompt, *args, **kwargs)
                duration = time.time() - start_time
                
                logger.info(f"AI Inference (Sync): {func.__name__} took {duration:.2f}s")
                
                if result:
                    redis_cache.set(cache_key, result, expire=expire)
                return result
            return sync_wrapper
    return decorator

class TokenTracker:
    def __init__(self):
        self.usage_key = "ai_token_usage:global"

    def track(self, model: str, prompt_tokens: int, completion_tokens: int):
        data = {
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "timestamp": time.time()
        }
        # In a real app, we'd use Redis INCR or push to a time-series DB
        # For MVP, we'll just log it structured
        logger.info(f"TOKEN_USAGE: {json.dumps(data)}")

token_tracker = TokenTracker()
