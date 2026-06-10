import logging

from app.core.celery_app import celery
from app.services.weather import get_live_weather

logger = logging.getLogger(__name__)


@celery.task(name="fetch_weather_data")
def fetch_weather_data(city: str):
    from app.services.redis_service import get_redis
    redis_cache = get_redis()

    cache_key = f"weather:{city.lower()}"

    cached_data = redis_cache.get(cache_key)
    if cached_data:
        return cached_data

    logger.info(f"Fetching live weather for {city}...")
    result = get_live_weather(city)

    redis_cache.set(cache_key, result, expire=1800)

    return result


@celery.task(name="process_project_document")
def process_project_document(document_id: int):
    logger.info(f"Processing document {document_id}...")
    return {"status": "completed", "document_id": document_id}
