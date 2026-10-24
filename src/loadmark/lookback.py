import re
from datetime import datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from .errors import InvalidLookbackError

_UNITS = {"m": "minutes", "h": "hours", "d": "days", "w": "weeks"}
_PATTERN = re.compile(r"^\s*(\d+)\s*([mhdw])\s*$", re.IGNORECASE)


def apply_lookback(moment: datetime, lookback: Optional[str], tz: str = "UTC") -> datetime:
    """Move a point in time backwards by the lookback rule.

    lookback can be:
      None            -> no change
      "start_of_day"  -> midnight of that day, in time zone `tz`
      "30m" "2h" "1d" "1w" -> subtract that amount of time
    """
    if lookback is None:
        return moment

    text = str(lookback).strip().lower()
    if text == "start_of_day":
        local = moment.astimezone(ZoneInfo(tz))
        midnight = local.replace(hour=0, minute=0, second=0, microsecond=0)
        return midnight.astimezone(timezone.utc)

    match = _PATTERN.match(text)
    if not match:
        raise InvalidLookbackError(
            f"Unknown lookback {lookback!r}. Use None, 'start_of_day', or "
            "something like '30m', '2h', '1d', '1w'."
        )
    amount, unit = int(match.group(1)), match.group(2)
    return moment - timedelta(**{_UNITS[unit]: amount})
