from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Optional

RUNNING = "RUNNING"
SUCCESS = "SUCCESS"
FAILED = "FAILED"


def utcnow() -> datetime:
    """Current time as a timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def to_iso(value: Optional[datetime]) -> Optional[str]:
    return value.isoformat() if value else None


def from_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


@dataclass
class RunRecord:
    """One row of the audit trail (like a row in an audit table)."""

    run_id: str
    name: str
    start_time: datetime
    status: str = RUNNING
    load_type: str = "incremental"      # full / incremental / backfill
    since: Optional[datetime] = None    # the window start used by this run
    end_time: Optional[datetime] = None
    rows: Optional[int] = None
    message: Optional[str] = None

    def to_dict(self) -> dict:
        data = asdict(self)
        for key in ("start_time", "since", "end_time"):
            data[key] = to_iso(data[key])
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "RunRecord":
        return cls(
            run_id=data["run_id"],
            name=data["name"],
            start_time=from_iso(data["start_time"]),
            status=data["status"],
            load_type=data.get("load_type") or "incremental",
            since=from_iso(data.get("since")),
            end_time=from_iso(data.get("end_time")),
            rows=data.get("rows"),
            message=data.get("message"),
        )
