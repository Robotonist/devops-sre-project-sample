# Poll more frequently than the minimum 10-second target interval so scheduler phase
# drift cannot turn a 10-second target cadence into an approximately 20-second cadence.
BEAT_SCHEDULE: dict[str, dict[str, str | float]] = {
    "dispatch-due-targets": {
        "task": "app.worker.tasks.dispatch_due_targets",
        "schedule": 1.0,
    }
}
