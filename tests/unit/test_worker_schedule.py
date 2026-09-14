from app.worker.schedule import BEAT_SCHEDULE


def test_beat_schedule_polls_due_targets_once_per_second() -> None:
    entry = BEAT_SCHEDULE["dispatch-due-targets"]

    assert entry["task"] == "app.worker.tasks.dispatch_due_targets"
    assert entry["schedule"] == 1.0
