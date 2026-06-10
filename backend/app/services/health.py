from fastapi import APIRouter
from datetime import UTC, datetime

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check():
    return {
        "status": "ok",
        "timestamp": datetime.now(UTC).isoformat()
    }
