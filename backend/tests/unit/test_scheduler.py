import pytest

from app.services.scheduler import start_scheduler, shutdown_scheduler


@pytest.fixture
def scheduler():
    start_scheduler(interval_minutes=1, runnable=lambda: None)
    yield
    shutdown_scheduler()


def test_scheduler_starts(scheduler):
    from app.services.scheduler import _scheduler

    assert _scheduler is not None
    assert _scheduler.running is True
