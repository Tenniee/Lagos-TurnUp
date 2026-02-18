from datetime import datetime, timedelta, timezone

FEATURING_TIMELINE_OPTIONS = {"3d", "1w", "2w", "1m"}

def compute_featured_until(timeline: str) -> datetime:
    now = datetime.now(timezone.utc)
    mapping = {
        "3d": timedelta(days=3),
        "1w": timedelta(weeks=1),
        "2w": timedelta(weeks=2),
        "1m": timedelta(days=30),
    }
    delta = mapping.get(timeline)
    if not delta:
        raise ValueError(f"Invalid featuring_timeline: '{timeline}'. Must be one of: {FEATURING_TIMELINE_OPTIONS}")
    return now + delta