import logging
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

_celery_instance: Any = None


def get_celery_app() -> Any:
    global _celery_instance

    if _celery_instance is not None:
        return _celery_instance

    if not settings.redis_url or settings.redis_url == "redis://localhost:6379/0":
        logger.warning("Redis not configured. Celery will be unavailable.")
        _celery_instance = None
        return None

    try:
        from celery import Celery

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
            task_always_eager=bool(settings.debug),
        )

        try:
            _celery_instance.autodiscover_tasks([
                "app.modules.project_tracker.tasks",
                "app.services.rag.tasks",
            ])
        except Exception as e:
            logger.warning(f"Failed to autodiscover Celery tasks: {e}")

        logger.info("Celery app initialized successfully")
        return _celery_instance
    except ModuleNotFoundError:
        logger.warning("Celery package not installed. Background tasks disabled.")
        _celery_instance = None
        return None
    except Exception as e:
        logger.error(f"Failed to initialize Celery: {e}")
        _celery_instance = None
        return None


def get_celery():
    return get_celery_app()


class LazyCeleryProxy:
    def __getattr__(self, name):
        app = get_celery_app()
        if app is None:
            raise RuntimeError("Celery is not available. Check Redis configuration.")
        return getattr(app, name)

    def __call__(self, *args, **kwargs):
        app = get_celery_app()
        if app is None:
            logger.warning("Celery task called but Celery is unavailable. Running synchronously.")
            return None
        return app(*args, **kwargs)

    def task(self, *args, **kwargs):
        app = get_celery_app()
        if app is None:
            def noop_decorator(f):
                return f
            return noop_decorator
        return app.task(*args, **kwargs)


celery = LazyCeleryProxy()
