from celery import Celery
from app.core.config import settings

# This creates a Celery instance and points it to your Redis broker
celery_app = Celery(
    "ai_service",
    broker=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0",
    backend=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/1"
)