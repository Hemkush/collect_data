from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "scraper",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "app.tasks.execute_scraping_job": {"queue": "scraping"},
        "app.tasks.process_bulk_urls": {"queue": "bulk"},
    },
    task_default_queue="default",
    task_create_missing_queues=True,
)