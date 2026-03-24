from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

celery_app = Celery(
    "worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.tasks", "app.workers.email_tasks"]
)

celery_app.conf.task_routes = {
    "app.workers.tasks.*": "main-queue",
    "app.workers.email_tasks.*": "main-queue",
}

# Mission 10.13: Hardened Celery Configuration
celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_track_started=True,
)

celery_app.conf.beat_schedule = {
    "process_email_outbox_every_minute": {
        "task": "app.workers.email_tasks.process_email_outbox",
        "schedule": 60.0,
    },
    "purge_runtime_events_daily_0300": {
        "task": "app.workers.tasks.purge_runtime_events_task",
        "schedule": crontab(hour=3, minute=0),
    },
    "expire_plan_overrides_every_5min": {
        "task": "app.workers.tasks.expire_plan_overrides_task",
        "schedule": 300.0,
    },
    "export_to_hf_daily_0200": {
        "task": "app.workers.tasks.export_to_hf_task",
        "schedule": crontab(hour=2, minute=0),
    },
    # Mission M-D: resume WAITING ExecutionInstances after WAIT_DELAY expires
    "resume_waiting_instances_every_minute": {
        "task": "app.workers.tasks.resume_waiting_instances_task",
        "schedule": 60.0,
    },
}

celery_app.autodiscover_tasks(["app.workers"])
