import logging
import re
from collections.abc import Awaitable, Callable
from time import perf_counter

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("api")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable]):
        start = perf_counter()
        response = await call_next(request)
        elapsed_ms = (perf_counter() - start) * 1000
        role = "anonymous"
        auth = request.headers.get("authorization", "")
        if auth.startswith("Bearer "):
            role = "token_user"

        logger.info(
            "request",
            extra={
                "endpoint": request.url.path,
                "method": request.method,
                "response_time_ms": round(elapsed_ms, 2),
                "status_code": response.status_code,
                "user_role": role,
            },
        )
        response.headers["X-Response-Time-ms"] = str(round(elapsed_ms, 2))
        return response


def mask_pii(text: str) -> str:
    text = re.sub(r"[\w\.-]+@[\w\.-]+", "[MASKED_EMAIL]", text)
    text = re.sub(r"\b\+?\d{10,15}\b", "[MASKED_PHONE]", text)
    return text


def sanitize_input_text(text: str) -> str:
    # Keep printable characters and trim to protect downstream prompts.
    safe = "".join(ch for ch in text if ch.isprintable())
    return safe.strip()
