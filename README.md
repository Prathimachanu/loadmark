# loadmark

A safe **bookmark (checkpoint)** for incremental data loads.

Incremental loading means "fetch only what changed since last time". `loadmark` remembers
"since when" for you, and it follows three rules that are easy to get wrong by hand:

1. **The bookmark moves only when a run succeeds.** A crash never loses data.
2. **It uses the run's start time, with an optional lookback** (for example, back to midnight),
   so late-arriving records are not missed.
3. **Every run is recorded** (run id, start, end, status, load type, rows), like an audit table.

No dependencies. Python 3.9+.

## Install

```bash
pip install loadmark
```

## Quick start

```python
from loadmark import Checkpoint, SQLiteStore, dedupe_latest

cp = Checkpoint(
    name="crm/contacts",                 # one name per source/object
    store=SQLiteStore("audit.db"),       # where the history is kept
    lookback="start_of_day",             # re-read from midnight of the last good run
)

with cp.run() as run:
    rows = fetch_from_api(since=run.since)   # run.since is None on the first run (full load)
    rows = dedupe_latest(rows, key="id", order_by="updated_at")
    write_to_s3(rows)
    run.rows = len(rows)
# leaving the block normally  -> run is saved as SUCCESS and the bookmark moves
# an exception inside the block -> run is saved as FAILED and the bookmark stays
```

## Why a lookback?

Records can arrive late, and a job can start a little before the source finishes writing.
A lookback re-reads a small overlap so nothing is missed. The price is **duplicates**, so always
deduplicate by key afterwards (`dedupe_latest`, or a `MERGE` in your database).

| lookback | meaning |
|---|---|
| `None` | start exactly at the last successful run's start time |
| `"start_of_day"` | midnight of that day, in the time zone you set with `tz="Asia/Kolkata"` |
| `"30m"`, `"2h"`, `"1d"`, `"1w"` | go back that much |

## Features

- `cp.run()` - start a run (context manager)
- `cp.run(since="2026-09-01")` - manual **backfill** from a date
- `cp.next_since()` - see where the next run would start
- `cp.history(limit=10)` - latest runs, newest first
- `cp.reset()` - forget history, next run is a full load
- **Run lock:** a second run of the same name is refused (`RunInProgressError`) while one is running.
  A run stuck as RUNNING for more than `stale_after` (default 6 hours) is marked FAILED automatically.
- **Stores:** `LocalFileStore` (JSON file), `SQLiteStore`, or write your own.

## Use your own database (Snowflake, Postgres, ...)

Subclass `Store` and implement five methods: `save`, `last_success`, `running`, `history`, `clear`.

```python
from loadmark import Store

class MyWarehouseStore(Store):
    ...   # run SQL against your own audit table
```

## Limits (honest list)

- The run lock is a status check, not a database-level lock. For many parallel workers, use a store
  with real transactions.
- It remembers *when your job ran*, not the highest `updated_at` seen in the data.
- It does not fetch or write data. It only manages the bookmark.

## Develop

```bash
pip install -e ".[dev]"
pytest
python examples/basic_usage.py
```

## License

MIT
