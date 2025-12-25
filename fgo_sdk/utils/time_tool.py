import math
from datetime import datetime, timedelta, timezone


def get_timestamp() -> int:
    """Get current UTC timestamp."""
    return int(datetime.now().timestamp())


def is_free_fp_draw_available(last_free_draw_timestamp_utc: int) -> bool:
    """Check if free friend point draw is available (resets at midnight JST)."""
    JST = timezone(timedelta(hours=+9))
    dt_utc = datetime.fromtimestamp(last_free_draw_timestamp_utc, timezone.utc)
    dt_japan = dt_utc.astimezone(JST)
    next_midnight = datetime(dt_japan.year, dt_japan.month, dt_japan.day, tzinfo=JST) + timedelta(days=1)

    next_midnight_utc = next_midnight.astimezone(timezone.utc)
    next_midnight_timestamp = next_midnight_utc.timestamp()

    return get_timestamp() >= next_midnight_timestamp


def get_used_act_amount(full_recover_at: int) -> int:
    """Calculate used AP based on recovery time."""
    return max(0, math.ceil((full_recover_at - get_timestamp()) / 300))
