import logging
import traceback
import sys
import os
from contextlib import asynccontextmanager

# Ensure the repository's `backend` directory is on sys.path so `app` is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import configure_logging
from app.api.v1.router import api_router
from app.core.logging_middleware import StructuredLoggingMiddleware

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

configure_logging()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize database engine first, then migrate/seed
    from app.db.session import init_db_engine, init_db
    try:
        init_db_engine()  # Create engine and SessionLocal
        init_db()         # Create tables and seed data
        logger.info("Database initialized successfully.")
    except Exception as exc:
        logger.warning(f"Database initialization skipped or failed: {exc}")
    
    # AI Provider Validation
    providers = []
    if settings.gemini_api_key and settings.gemini_api_key != "change-me":
        providers.append(f"Gemini ({settings.gemini_default_model})")
    if settings.groq_api_key and settings.groq_api_key != "change-me":
        providers.append(f"Groq ({settings.groq_default_model})")
    
    if providers:
        logger.info(f"AI Strategy Service initializing with: {', '.join(providers)}")
        # Simple non-blocking connectivity check could be added here if needed
    else:
        logger.critical("AI Strategy Service: No LLM providers configured! Strategy features will fail.")
    
    yield
    # Shutdown
    logger.info("Application shutting down...")

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

app.include_router(api_router, prefix=settings.api_prefix)

@app.get("/health")
def root_health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=getattr(settings, "debug", False),
    )
