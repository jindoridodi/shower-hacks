from datetime import datetime, timezone


def utc_now() -> str:
    # Microseconds keep same-second writes in creation order when sorted as text.
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")
