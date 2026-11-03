import time
from datetime import datetime, timezone
from celery.utils.log import get_task_logger
from app.workers.celery_app import celery_app

logger = get_task_logger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=2, name="app.workers.tasks.health_check_ping")
def health_check_ping(self, message: str = "ping") -> dict:
    """
    Idempotent health check ping task.
    Verifies Celery worker connectivity, message serialization, and result backend persistence.
    """
    logger.info(f"Executing health_check_ping with message: {message}")
    
    return {
        "status": "pong",
        "message": message,
        "worker_timestamp": datetime.now(timezone.utc).isoformat(),
        "task_id": self.request.id,
        "retries": self.request.retries
    }


@celery_app.task(bind=True, max_retries=2, default_retry_delay=1, name="app.workers.tasks.simulated_fault_task")
def simulated_fault_task(self, should_fail: bool = False) -> str:
    """Task used in automated tests to verify retry and backoff error behavior."""
    if should_fail:
        try:
            raise ValueError("Simulated transient worker failure")
        except Exception as exc:
            logger.warning(f"Task fault occurred, triggering retry {self.request.retries + 1}")
            raise self.retry(exc=exc)
    return "success"
