from fastapi import APIRouter

from app.services.health import router as health_router
from app.modules.project_tracker.router import router as project_tracker_router
from app.modules.auth.router import router as auth_router
from app.modules.document_analyzer.router import router as document_analyzer_router
from app.modules.logs.router import router as logs_router
from app.modules.analytics.router import router as analytics_router
from app.modules.dashboard.router import router as dashboard_router
from app.modules.search.router import router as search_router
from app.modules.workforce.router import router as workforce_router
from app.modules.sync.router import router as sync_router
from app.modules.notifications.router import router as notifications_router

api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(project_tracker_router, prefix="/project-tracker", tags=["project-tracker"])
api_router.include_router(document_analyzer_router, prefix="/document-analyzer", tags=["document-analyzer"])
api_router.include_router(logs_router, prefix="/logs", tags=["logs"])
api_router.include_router(analytics_router, prefix="/analytics", tags=["analytics"])
api_router.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(search_router, prefix="/search", tags=["search"])
api_router.include_router(workforce_router, prefix="/workforce", tags=["workforce"])
api_router.include_router(sync_router, prefix="/sync", tags=["sync"])
api_router.include_router(notifications_router, prefix="/notifications", tags=["notifications"])
