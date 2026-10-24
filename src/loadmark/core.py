import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Iterator, List, Optional, Union

from .errors import RunInProgressError
from .lookback import apply_lookback
from .models import FAILED, RUNNING, SUCCESS, RunRecord, from_iso, utcnow
from .stores import Store


class Run:
    """The object you get inside `with checkpoint.run() as run:`."""

    def __init__(self, record: RunRecord):
        self._record = record
        self.rows: Optional[int] = None      # set this to the number of rows loaded
        self.message: Optional[str] = None   # optional note saved with the run

    @property
    def run_id(self) -> str:
        return self._record.run_id

    @property
    def since(self) -> Optional[datetime]:
        """Fetch records changed at or after this time. None = first run (full load)."""
        return self._record.since

    @property
    def start(self) -> datetime:
        return self._record.start_time

    @property
    def load_type(self) -> str:
        return self._record.load_type


class Checkpoint:
    """A bookmark for incremental loads.

    The bookmark only moves forward when a run finishes successfully.
    """

    def __init__(
        self,
        name: str,
        store: Store,
        lookback: Optional[str] = "start_of_day",
        tz: str = "UTC",
        stale_after: timedelta = timedelta(hours=6),
    ):
        self.name = name
        self.store = store
        self.lookback = lookback
        self.tz = tz
        self.stale_after = stale_after

    # ------------------------------------------------------------------
    def next_since(self) -> Optional[datetime]:
        """Where the next incremental run would start from (None = full load)."""
        last = self.store.last_success(self.name)
        if last is None:
            return None
        return apply_lookback(last.start_time, self.lookback, self.tz)

    def _check_no_active_run(self) -> None:
        now = utcnow()
        for old in self.store.running(self.name):
            if now - old.start_time > self.stale_after:
                # a run that never finished (crashed machine, killed job)
                old.status = FAILED
                old.end_time = now
                old.message = "marked FAILED: run never finished (stale)"
                self.store.save(old)
            else:
                raise RunInProgressError(
                    f"{self.name!r} already has a run in progress "
                    f"(run_id={old.run_id}, started {old.start_time.isoformat()})."
                )

    # ------------------------------------------------------------------
    @contextmanager
    def run(self, since: Union[None, str, datetime] = None) -> Iterator[Run]:
        """Start a run.

        since=None      -> use the checkpoint (full load if there is none yet)
        since=<datetime or ISO text> -> manual backfill from that time
        """
        self._check_no_active_run()

        if since is not None:
            start_from = from_iso(since) if isinstance(since, str) else since
            if start_from.tzinfo is None:
                start_from = start_from.replace(tzinfo=timezone.utc)
            load_type = "backfill"
        else:
            start_from = self.next_since()
            load_type = "full" if start_from is None else "incremental"

        record = RunRecord(
            run_id=uuid.uuid4().hex,
            name=self.name,
            start_time=utcnow(),
            status=RUNNING,
            load_type=load_type,
            since=start_from,
        )
        self.store.save(record)
        run = Run(record)

        try:
            yield run
        except BaseException as error:       # also covers Ctrl+C
            record.status = FAILED
            record.end_time = utcnow()
            record.rows = run.rows
            record.message = f"{type(error).__name__}: {error}"
            self.store.save(record)
            raise
        else:
            record.status = SUCCESS
            record.end_time = utcnow()
            record.rows = run.rows
            record.message = run.message
            self.store.save(record)

    # ------------------------------------------------------------------
    def history(self, limit: int = 10) -> List[RunRecord]:
        return self.store.history(self.name, limit)

    def reset(self) -> None:
        """Forget all history. The next run will be a full load."""
        self.store.clear(self.name)
