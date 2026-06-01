import logging
from celery import Celery
from app.core.config import settings

logger = logging.getLogger(__name__)

# Global celery instance (lazy loaded)
_celery_instance = None


def get_celery_app() -> Celery:
    """
    Get or create Celery app instance.
    Lazy initialization to avoid blocking startup.
    """
    global _celery_instance
    
    if _celery_instance is not None:
        return _celery_instance
    
    try:
        logger.info("Initializing Celery app...")
        _celery_instance = Celery(
            "const_ai_worker",
            broker=settings.redis_url,
            backend=settings.redis_url
        )

        _celery_instance.conf.update(
            task_serializer="json",
            accept_content=["json"],
            result_serializer="json",
            timezone="UTC",
            enable_utc=True,
            task_track_started=True,
            task_time_limit=3600,
        )

        # Auto-discover tasks in modules - DEFERRED until get_celery_app() called
        try:
            _celery_instance.autodiscover_tasks([
                "app.modules.project_tracker.tasks",
                "app.services.rag.tasks",
            ])
        except Exception as e:
            logger.warning(f"Failed to autodiscover Celery tasks: {e}")
        
        logger.info("Celery app initialized successfully")
        return _celery_instance
    except Exception as e:
        logger.error(f"Failed to initialize Celery: {e}")
        # Return a non-functional celery app so imports don't fail
        _celery_instance = Celery("const_ai_worker")
        return _celery_instance


# DO NOT initialize celery_app here - use get_celery_app() instead
# For imports that expect "celery_app", create a lazy proxy
class LazyCeleryProxy:
    """Lazy proxy that initializes Celery only when accessed."""
    def __getattr__(self, name):
        return getattr(get_celery_app(), name)
    
    def __call__(self, *args, **kwargs):
        return get_celery_app()(*args, **kwargs)


# Export as celery_app for backward compatibility
celery_app = LazyCeleryProxy()
