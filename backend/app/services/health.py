from fastapi import APIRouter
from datetime import UTC, datetime

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check():
    return {
        "status": "ok",
        "timestamp": datetime.now(UTC).isoformat()
    }


@router.get("/ready")
async def readiness_check():
    try:
        from app.services.llm import get_ai_health
        ai = await get_ai_health()
    except Exception:
        ai = {}

    from app.main import _db_initialized
    return {
        "status": "ready" if _db_initialized else "starting",
        "db_initialized": _db_initialized,
        "ai_providers": ai
    }
