from app.worker.schedule import BEAT_SCHEDULE


def test_beat_schedule_dispatches_due_targets_every_ten_seconds() -> None:
    entry = BEAT_SCHEDULE["dispatch-due-targets"]

    assert entry["task"] == "app.worker.tasks.dispatch_due_targets"
    assert entry["schedule"] == 10.0
