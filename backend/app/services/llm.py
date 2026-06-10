import logging
import asyncio
import time
import functools
from typing import Any, Dict, Callable
import httpx

from app.core.config import settings
from app.services.ai_optimizer import ai_cache, token_tracker

logger = logging.getLogger(__name__)


class AIServiceError(Exception):
    def __init__(self, message: str, details: str = None):
        super().__init__(message)
        self.details = details


def with_retry(retries: int = 2, delay: float = 1.0):
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exc = None
            for i in range(retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exc = e
                    if i < retries:
                        wait = delay * (2 ** i)
                        logger.warning(f"Retry {i+1}/{retries} for {func.__name__} after {wait}s. Error: {e}")
                        await asyncio.sleep(wait)
            raise last_exc
        return wrapper
    return decorator


async def _http_post(url: str, json_data: dict, headers: dict, timeout: float = 30.0) -> dict:
    async with httpx.AsyncClient(timeout=timeout, verify=True) as client:
        response = await client.post(url, json=json_data, headers=headers)
        if response.status_code != 200:
            logger.error(f"HTTP {response.status_code}: {response.text[:500]}")
            response.raise_for_status()
        return response.json()


@ai_cache(expire=86400)
@with_retry(retries=1)
async def ask_gemini(prompt: str) -> str:
    if not settings.gemini_api_key or settings.gemini_api_key == "change-me":
        raise AIServiceError("Gemini API key is not configured.")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_default_model}:generateContent?key={settings.gemini_api_key}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 2048,
            "topP": 0.95,
        }
    }

    result = await _http_post(url, payload, headers)
    candidates = result.get("candidates", [])
    if candidates and candidates[0].get("content", {}).get("parts"):
        text = candidates[0]["content"]["parts"][0].get("text", "")
        token_tracker.track(settings.gemini_default_model, len(prompt) // 4, len(text) // 4)
        return text
    raise AIServiceError("Gemini returned empty response.")


@ai_cache(expire=86400)
@with_retry(retries=1)
async def ask_groq(prompt: str) -> str:
    if not settings.groq_api_key or settings.groq_api_key == "change-me":
        raise AIServiceError("Groq API key is not configured.")

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.groq_api_key.strip()}",
        "Content-Type": "application/json",
        "User-Agent": settings.user_agent
    }
    payload = {
        "model": settings.groq_default_model,
        "messages": [
            {"role": "system", "content": "You are a specialized construction assistant for ConstAI Nigeria."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 2048,
        "temperature": 0.7,
    }

    result = await _http_post(url, payload, headers)
    text = result.get("choices", [{}])[0].get("message", {}).get("content", "")
    usage = result.get("usage", {})
    token_tracker.track(settings.groq_default_model, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0))
    return text


@ai_cache(expire=86400)
@with_retry(retries=1)
async def ask_openrouter(prompt: str) -> str:
    if not settings.openrouter_api_key or settings.openrouter_api_key == "change-me":
        raise AIServiceError("OpenRouter API key is not configured.")

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key.strip()}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://constai.nigeria",
        "X-Title": "ConstAI Nigeria",
    }
    payload = {
        "model": settings.openrouter_default_model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 2048,
    }

    result = await _http_post(url, payload, headers, timeout=40.0)
    text = result.get("choices", [{}])[0].get("message", {}).get("content", "")
    return text


async def get_ai_health() -> Dict[str, bool]:
    return {
        "gemini": bool(settings.gemini_api_key and settings.gemini_api_key != "change-me"),
        "groq": bool(settings.groq_api_key and settings.groq_api_key != "change-me"),
        "openrouter": bool(settings.openrouter_api_key and settings.openrouter_api_key != "change-me")
    }


async def ask_ai(prompt: str) -> str:
    health = await get_ai_health()
    providers = []

    if health["gemini"]:
        providers.append(("Gemini", ask_gemini))
    if health["groq"]:
        providers.append(("Groq", ask_groq))
    if health["openrouter"]:
        providers.append(("OpenRouter", ask_openrouter))

    if not providers:
        raise AIServiceError("No AI providers configured. Connectivity is offline.")

    errors = []
    for name, provider_func in providers:
        try:
            logger.info(f"AI Orchestrator: Attempting {name}...")
            result = await provider_func(prompt)
            if result:
                logger.info(f"AI Orchestrator: {name} Success.")
                return result
        except Exception as e:
            err_msg = f"{name} failed: {str(e)}"
            logger.warning(f"AI Orchestrator: {err_msg}")
            errors.append(err_msg)

    error_summary = " | ".join(errors)
    logger.error(f"AI Orchestrator: All providers failed. {error_summary}")
    raise AIServiceError("AI Strategy Service encountered a complete outage.", details=error_summary)
