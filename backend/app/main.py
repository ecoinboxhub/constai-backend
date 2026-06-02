import logging
import traceback
import sys
import os
import psutil
import gc
from contextlib import asynccontextmanager

# Ensure the repository's `backend` directory is on sys.path so `app` is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import configure_logging
from app.core.logging_middleware import StructuredLoggingMiddleware

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

configure_logging()
logger = logging.getLogger(__name__)

# Global flags to track initialization
_db_initialized = False
_db_init_attempted = False


def log_startup_diagnostics(stage: str):
    """Log memory usage and current state during startup."""
    try:
        process = psutil.Process()
        mem = process.memory_info()
        percent = process.memory_percent()
        logger.info(f"[STARTUP] {stage} | Memory: {mem.rss / 1024 / 1024:.1f}MB ({percent:.1f}%)")
    except Exception:
        pass


# Log immediate memory on module import to help profile import-time usage
try:
    process = psutil.Process()
    logger.info(f"[IMPORT] module app.main imported | PID={process.pid} | RSS={process.memory_info().rss / 1024 / 1024:.1f}MB")
except Exception:
    pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager with optimized startup."""
    log_startup_diagnostics("STARTUP_BEGIN")
    
    # Startup phase
    try:
        # Defer database initialization - do NOT block on startup
        # Database will be initialized lazily on first request
        logger.info("Database initialization deferred to first request for faster startup")
        log_startup_diagnostics("STARTUP_DEFERRED_DB")
    except Exception as exc:
        logger.warning(f"Startup warning: {exc}")
    
    # AI Provider Validation (non-blocking check)
    providers = []
    if settings.gemini_api_key and settings.gemini_api_key != "change-me":
        providers.append(f"Gemini ({settings.gemini_default_model})")
    if settings.groq_api_key and settings.groq_api_key != "change-me":
        providers.append(f"Groq ({settings.groq_default_model})")
    
    if providers:
        logger.info(f"AI Strategy Service initializing with: {', '.join(providers)}")
    else:
        logger.critical("AI Strategy Service: No LLM providers configured! Strategy features will fail.")
    
    # Include API routes lazily to avoid importing heavy modules at module import time
    try:
        from app.api.v1.router import api_router
        app.include_router(api_router, prefix=settings.api_prefix)
        logger.info("API routers included lazily during lifespan startup")
    except Exception as exc:
        logger.warning(f"Failed to include API routers during startup: {exc}")

    log_startup_diagnostics("STARTUP_COMPLETE")
    logger.info("✅ FastAPI application ready to accept requests")
    
    yield
    
    # Shutdown phase
    logger.info("Application shutting down...")
    gc.collect()
    log_startup_diagnostics("SHUTDOWN_COMPLETE")


def ensure_db_initialized():
    """Initialize database on first request if not already done."""
    global _db_initialized, _db_init_attempted
    
    if _db_initialized or _db_init_attempted:
        return
    
    _db_init_attempted = True
    try:
        from app.db.session import init_db_engine, init_db
        log_startup_diagnostics("DB_INIT_START")
        init_db_engine()
        init_db()
        _db_initialized = True
        log_startup_diagnostics("DB_INIT_COMPLETE")
        logger.info("Database initialized successfully.")
    except Exception as exc:
        logger.warning(f"Database initialization failed: {exc}")
        logger.info("Application will continue without database persistence.")


app = FastAPI(
    title=settings.app_name, 
    version="0.1.0",
    lifespan=lifespan
)

# CORS Configuration
origins = [
    "http://localhost:3000",
    "http://localhost:5173",
]
if settings.production_domain:
    origins.append(settings.production_domain)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://.*\.netlify\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(StructuredLoggingMiddleware)

from app.services.llm import AIServiceError

@app.exception_handler(AIServiceError)
async def ai_service_exception_handler(request: Request, exc: AIServiceError):
    logger.error(f"AI Service Error at {request.url.path}: {exc}")
    return JSONResponse(
        status_code=503,
        content={
            "detail": str(exc),
            "error_type": "AI_SERVICE_UNAVAILABLE",
            "provider_errors": exc.details
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception at {request.url.path}: {exc}")
    logger.error(traceback.format_exc())
    detail = "Internal Server Error"
    if settings.debug:
        detail = f"{str(exc)}\n{traceback.format_exc()}"
    return JSONResponse(status_code=500, content={"detail": detail})

# Include API router with lazy DB initialization
@app.middleware("http")
async def lazy_db_init_middleware(request: Request, call_next):
    """Ensure database is initialized before processing requests."""
    ensure_db_initialized()
    response = await call_next(request)
    return response

# API routers are included lazily during lifespan startup to avoid heavy imports at module import time

@app.get("/")
@app.get("/health")
def health_check():
    """Simple health check that responds immediately without waiting for DB."""
    try:
        import psutil
        process = psutil.Process()
        mem_mb = process.memory_info().rss / 1024 / 1024
        return {
            "status": "ok",
            "memory_mb": round(mem_mb, 2),
            "db_initialized": _db_initialized
        }
    except Exception:
        return {"status": "ok"}


@app.get("/ready")
async def readiness_check():
    """Readiness endpoint that does not initialize heavy models."""
    try:
        # Lazy import to avoid initializing providers
        from app.services.llm import get_ai_health
        ai = await get_ai_health()
    except Exception:
        ai = {}
    return {
        "status": "ready" if _db_initialized else "starting",
        "db_initialized": _db_initialized,
        "ai_providers": ai
    }


@app.get("/diagnostics")
def diagnostics():
    """Return lightweight diagnostics including current memory."""
    try:
        import psutil
        p = psutil.Process()
        mem = p.memory_info().rss / 1024 / 1024
        return {"status": "ok", "memory_mb": round(mem, 2)}
    except Exception:
        return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        workers=1,  # Single worker for memory efficiency
        reload=getattr(settings, "debug", False),
    )
