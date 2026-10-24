from datetime import datetime, timedelta, timezone

import pytest

from loadmark import (
    Checkpoint, InvalidLookbackError, LocalFileStore, RunInProgressError,
    SQLiteStore, apply_lookback, dedupe_latest,
)
from loadmark.models import FAILED, RUNNING, SUCCESS, RunRecord


@pytest.fixture(params=["file", "sqlite"])
def store(request, tmp_path):
    if request.param == "file":
        return LocalFileStore(str(tmp_path / "state.json"))
    return SQLiteStore(str(tmp_path / "audit.db"))


def test_first_run_is_full_load(store):
    cp = Checkpoint("src/a", store)
    with cp.run() as run:
        assert run.since is None
        assert run.load_type == "full"


def test_success_moves_the_bookmark(store):
    cp = Checkpoint("src/a", store, lookback=None)
    with cp.run() as first:
        first.rows = 10
    with cp.run() as second:
        assert second.since == first.start
        assert second.load_type == "incremental"


def test_failure_does_not_move_the_bookmark(store):
    cp = Checkpoint("src/a", store, lookback=None)
    with cp.run() as good:
        pass
    with pytest.raises(ValueError):
        with cp.run():
            raise ValueError("S3 write failed")
    with cp.run() as after_failure:
        # still starts from the last SUCCESS, not from the failed run
        assert after_failure.since == good.start
    statuses = [r.status for r in cp.history()]
    assert FAILED in statuses


def test_failed_run_saves_error_message(store):
    cp = Checkpoint("src/a", store)
    with pytest.raises(RuntimeError):
        with cp.run():
            raise RuntimeError("boom")
    latest = cp.history(1)[0]
    assert latest.status == FAILED
    assert "boom" in latest.message


def test_rows_and_message_are_saved(store):
    cp = Checkpoint("src/a", store)
    with cp.run() as run:
        run.rows = 42
        run.message = "all good"
    latest = cp.history(1)[0]
    assert latest.status == SUCCESS
    assert latest.rows == 42
    assert latest.message == "all good"
    assert latest.end_time is not None


def test_names_are_independent(store):
    a = Checkpoint("src/a", store, lookback=None)
    b = Checkpoint("src/b", store, lookback=None)
    with a.run():
        pass
    with b.run() as run_b:
        assert run_b.since is None      # b has never succeeded


def test_second_run_is_blocked_while_first_is_running(store):
    cp = Checkpoint("src/a", store)
    with cp.run():
        with pytest.raises(RunInProgressError):
            with cp.run():
                pass


def test_stale_running_run_is_cleaned_up(store):
    cp = Checkpoint("src/a", store, stale_after=timedelta(hours=1))
    old = RunRecord(
        run_id="old1", name="src/a",
        start_time=datetime.now(timezone.utc) - timedelta(hours=5),
        status=RUNNING,
    )
    store.save(old)
    with cp.run():
        pass                              # allowed, the old one is stale
    statuses = {r.run_id: r.status for r in cp.history(10)}
    assert statuses["old1"] == FAILED


def test_backfill_overrides_the_bookmark(store):
    cp = Checkpoint("src/a", store)
    with cp.run():
        pass
    with cp.run(since="2026-09-01") as run:
        assert run.load_type == "backfill"
        assert run.since == datetime(2026, 9, 1, tzinfo=timezone.utc)


def test_reset_makes_next_run_full(store):
    cp = Checkpoint("src/a", store)
    with cp.run():
        pass
    cp.reset()
    with cp.run() as run:
        assert run.load_type == "full"


def test_next_since_applies_start_of_day_lookback(store):
    cp = Checkpoint("src/a", store, lookback="start_of_day", tz="UTC")
    store.save(RunRecord(
        run_id="r1", name="src/a",
        start_time=datetime(2026, 10, 20, 2, 15, tzinfo=timezone.utc),
        status=SUCCESS,
    ))
    assert cp.next_since() == datetime(2026, 10, 20, 0, 0, tzinfo=timezone.utc)


def test_start_of_day_respects_time_zone():
    moment = datetime(2026, 10, 20, 2, 15, tzinfo=timezone.utc)   # 07:45 in India
    result = apply_lookback(moment, "start_of_day", tz="Asia/Kolkata")
    # India midnight of 20 Oct = 19 Oct 18:30 UTC
    assert result == datetime(2026, 10, 19, 18, 30, tzinfo=timezone.utc)


@pytest.mark.parametrize("text,delta", [
    ("30m", timedelta(minutes=30)), ("2h", timedelta(hours=2)),
    ("1d", timedelta(days=1)), ("1w", timedelta(weeks=1)),
])
def test_duration_lookback(text, delta):
    moment = datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc)
    assert apply_lookback(moment, text) == moment - delta


def test_no_lookback_returns_same_time():
    moment = datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc)
    assert apply_lookback(moment, None) == moment


def test_bad_lookback_raises():
    with pytest.raises(InvalidLookbackError):
        apply_lookback(datetime.now(timezone.utc), "yesterday-ish")


def test_dedupe_keeps_latest_per_key():
    rows = [
        {"id": 1, "v": "old", "updated_at": 1},
        {"id": 1, "v": "new", "updated_at": 2},
        {"id": 2, "v": "x", "updated_at": 1},
    ]
    result = dedupe_latest(rows, key="id", order_by="updated_at")
    by_id = {r["id"]: r["v"] for r in result}
    assert by_id == {1: "new", 2: "x"}


def test_dedupe_with_composite_key():
    rows = [
        {"id": 1, "region": "A", "updated_at": 1},
        {"id": 1, "region": "B", "updated_at": 1},
        {"id": 1, "region": "A", "updated_at": 5},
    ]
    result = dedupe_latest(rows, key=("id", "region"), order_by="updated_at")
    assert len(result) == 2


def test_file_store_survives_empty_or_missing_file(tmp_path):
    path = tmp_path / "state.json"
    path.write_text("")
    cp = Checkpoint("src/a", LocalFileStore(str(path)))
    with cp.run() as run:
        assert run.since is None
