import time
import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import json

logger = logging.getLogger("const_ai_audit")

class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        process_time = time.time() - start_time
        
        log_data = {
            "method": request.method,
            "url": str(request.url),
            "status_code": response.status_code,
            "duration_ms": round(process_time * 1000, 2),
            "client_ip": request.client.host if request.client else None,
        }
        
        # Log to audit stream
        logger.info(json.dumps(log_data))
        
        # Add timing header
        response.headers["X-Process-Time"] = str(log_data["duration_ms"])
        
        return response
