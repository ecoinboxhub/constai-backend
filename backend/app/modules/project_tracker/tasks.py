import logging
from app.core.celery_app import celery_app
from app.services.redis_service import redis_cache
import httpx
import time

logger = logging.getLogger(__name__)

from app.services.weather import get_live_weather

@celery_app.task(name="fetch_weather_data")
def fetch_weather_data(city: str):
    cache_key = f"weather:{city.lower()}"
    
    # Check cache first
    cached_data = redis_cache.get(cache_key)
    if cached_data:
        return cached_data

    logger.info(f"Fetching live weather for {city}...")
    result = get_live_weather(city)
    
    # Cache for 30 minutes
    redis_cache.set(cache_key, result, expire=1800)
    
    return result

@celery_app.task(name="process_project_document")
def process_project_document(document_id: int):
    # This will handle OCR/Parsing and Vector indexing in the background
    logger.info(f"Processing document {document_id}...")
    # Implementation will follow in RAG refactor
    return {"status": "completed", "document_id": document_id}
