import logging
import traceback
import sys
import os
import gc
from contextlib import asynccontextmanager

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import configure_logging
from app.core.logging_middleware import StructuredLoggingMiddleware

configure_logging()
logger = logging.getLogger(__name__)

_db_initialized = False
_db_init_attempted = False


def log_startup_diagnostics(stage: str):
    try:
        import psutil
        process = psutil.Process()
        mem = process.memory_info()
        percent = process.memory_percent()
        logger.info(f"[STARTUP] {stage} | Memory: {mem.rss / 1024 / 1024:.1f}MB ({percent:.1f}%)")
    except Exception:
        pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    log_startup_diagnostics("STARTUP_BEGIN")

    try:
        logger.info("Database initialization deferred to first request for faster startup")
        log_startup_diagnostics("STARTUP_DEFERRED_DB")
    except Exception as exc:
        logger.warning(f"Startup warning: {exc}")

    providers = []
    if settings.gemini_api_key and settings.gemini_api_key != "change-me":
        providers.append(f"Gemini ({settings.gemini_default_model})")
    if settings.groq_api_key and settings.groq_api_key != "change-me":
        providers.append(f"Groq ({settings.groq_default_model})")

    if providers:
        logger.info(f"AI Strategy Service initializing with: {', '.join(providers)}")
    else:
        logger.warning("AI Strategy Service: No LLM providers configured! Strategy features will fail.")

    try:
        from app.api.v1.router import build_api_router
        api_router = build_api_router()
        app.include_router(api_router, prefix=settings.api_prefix)
        logger.info("API routers built and included lazily during lifespan startup")
    except Exception as exc:
        logger.error(f"Failed to include API routers during startup: {exc}")
        raise

    log_startup_diagnostics("STARTUP_COMPLETE")
    logger.info("FastAPI application ready to accept requests")

    yield

    logger.info("Application shutting down...")
    gc.collect()
    log_startup_diagnostics("SHUTDOWN_COMPLETE")


def ensure_db_initialized():
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

origins = [
    "http://localhost:3000",
    "https://constai-frontend.vercel.app",
    "http://localhost:5173",
]
if settings.production_domain:
    origins.append(settings.production_domain)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://.*\.(netlify\.app|vercel\.app|onrender\.com)",
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


@app.middleware("http")
async def lazy_db_init_middleware(request: Request, call_next):
    if request.url.path in ("/", "/health", "/ready", "/diagnostics", "/docs", "/openapi.json"):
        response = await call_next(request)
        return response
    ensure_db_initialized()
    response = await call_next(request)
    return response


@app.get("/")
@app.get("/health")
def health_check():
    try:
        import psutil
        process = psutil.Process()
        mem_mb = process.memory_info().rss / 1024 / 1024
    except Exception:
        mem_mb = 0

    return {
        "name": "ConstAI",
        "tagline": "Building Africa's Future with Predictive Construction Intelligence",
        "status": "operational",
        "version": "0.1.0",
        "memory_mb": round(mem_mb, 2) if mem_mb else None,
        "region": "Nigeria & Africa",
        "overview": "An enterprise-grade AI platform for predictive risk management, cost optimization, compliance automation, and operational excellence across the construction lifecycle.",
        "key_outcomes": {
            "reduce_delays": True,
            "control_budget_overruns": True,
            "improve_regulatory_compliance": True,
            "enhance_site_productivity": True,
            "centralize_project_intelligence": True
        },
        "modules": [
            "Project Tracker",
            "Delay Predictor",
            "AI Copilot",
            "Document Analyzer",
            "Legal RAG Search",
            "Weather Intelligence",
            "Workforce Management",
            "Site Logs",
            "Analytics Dashboard",
            "Notifications"
        ],
        "docs": "/docs",
        "health": "/health",
        "ready": "/ready"
    }


@app.get("/ready")
async def readiness_check():
    try:
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
    try:
        import psutil
        p = psutil.Process()
        mem = p.memory_info().rss / 1024 / 1024
        return {"status": "ok", "memory_mb": round(mem, 2)}
    except Exception:
        return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8008))
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        workers=1,
        reload=settings.debug,
    )
