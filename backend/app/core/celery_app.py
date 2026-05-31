from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "const_ai_worker",
    broker=settings.redis_url,
    backend=settings.redis_url
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,
)

# Auto-discover tasks in modules
celery_app.autodiscover_tasks([
    "app.modules.project_tracker.tasks",
    "app.services.rag.tasks",
])
