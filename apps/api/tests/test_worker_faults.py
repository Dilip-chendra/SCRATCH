import pytest
from app.workers.tasks import simulated_fault_task


def test_simulated_fault_task_success():
    """Verify standard non-failing task execution."""
    result = simulated_fault_task.apply(args=[False]).get()
    assert result == "success"


def test_simulated_fault_triggers_retry():
    """Verify that an unhandled exception inside worker triggers Celery retry logic."""
    from celery.exceptions import Retry

    # When should_fail=True, the task calls self.retry() which raises Retry with throw=True
    with pytest.raises(Retry):
        simulated_fault_task.apply(args=[True], throw=True)
