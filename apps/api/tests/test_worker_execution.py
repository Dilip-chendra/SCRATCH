from app.workers.celery_app import celery_app
from app.workers.tasks import health_check_ping


def test_celery_task_registration():
    """Verify that health_check_ping is properly registered with Celery."""
    assert "app.workers.tasks.health_check_ping" in celery_app.tasks


def test_health_check_ping_task_execution():
    """Verify that health_check_ping executes and returns a well-formed pong response."""
    result = health_check_ping.apply(args=["unit_test_ping_payload"]).get()
    
    assert result["status"] == "pong"
    assert result["message"] == "unit_test_ping_payload"
    assert "worker_timestamp" in result
    assert "task_id" in result
    assert result["retries"] == 0


def test_celery_configuration_parameters():
    """Verify Celery task serialization and queue configuration."""
    assert celery_app.conf.task_serializer == "json"
    assert celery_app.conf.result_serializer == "json"
    assert celery_app.conf.task_default_queue == "default"
    assert celery_app.conf.enable_utc is True
