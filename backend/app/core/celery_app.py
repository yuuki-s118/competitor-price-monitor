from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "competitor_price_monitor",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.price_collection"],
)

celery_app.conf.timezone = "Asia/Tokyo"
celery_app.conf.beat_schedule = {
    "collect-all-active-prices-hourly": {
        "task": "tasks.collect_all_active_prices",
        "schedule": crontab(minute=0),
    },
}
