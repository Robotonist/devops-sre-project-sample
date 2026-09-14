BEAT_SCHEDULE: dict[str, dict[str, str | float]] = {
    "dispatch-due-targets": {
        "task": "app.worker.tasks.dispatch_due_targets",
        "schedule": 10.0,
    }
}
