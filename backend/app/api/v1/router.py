from fastapi import APIRouter


def build_api_router() -> APIRouter:
	"""Construct and return the API router, importing sub-routers lazily.

	Call this from application startup (lifespan) to avoid importing heavy
	modules at module import time.
	"""
	api_router = APIRouter()

	# Import sub-routers lazily
	from app.services.health import router as health_router
	api_router.include_router(health_router)

	from app.modules.auth.router import router as auth_router
	api_router.include_router(auth_router, prefix="/auth", tags=["auth"])

	from app.modules.project_tracker.router import router as project_tracker_router
	api_router.include_router(project_tracker_router, prefix="/project-tracker", tags=["project-tracker"])

	from app.modules.document_analyzer.router import router as document_analyzer_router
	api_router.include_router(document_analyzer_router, prefix="/document-analyzer", tags=["document-analyzer"])

	from app.modules.logs.router import router as logs_router
	api_router.include_router(logs_router, prefix="/logs", tags=["logs"])

	from app.modules.analytics.router import router as analytics_router
	api_router.include_router(analytics_router, prefix="/analytics", tags=["analytics"])

	from app.modules.dashboard.router import router as dashboard_router
	api_router.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])

	from app.modules.search.router import router as search_router
	api_router.include_router(search_router, prefix="/search", tags=["search"])

	from app.modules.workforce.router import router as workforce_router
	api_router.include_router(workforce_router, prefix="/workforce", tags=["workforce"])

	from app.modules.sync.router import router as sync_router
	api_router.include_router(sync_router, prefix="/sync", tags=["sync"])

	from app.modules.notifications.router import router as notifications_router
	api_router.include_router(notifications_router, prefix="/notifications", tags=["notifications"])

	from app.modules.ml.router import router as ml_router
	api_router.include_router(ml_router, prefix="/ml", tags=["ml"])

	from app.modules.blog.router import router as blog_router
	api_router.include_router(blog_router, prefix="/blog", tags=["blog"])

	from app.modules.news.router import router as news_router
	api_router.include_router(news_router, prefix="/news", tags=["news"])

	return api_router
