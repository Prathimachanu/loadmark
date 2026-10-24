"""A runnable demo. Run it twice and watch `since` change."""
from loadmark import Checkpoint, SQLiteStore, dedupe_latest

cp = Checkpoint(
    name="demo_source/contacts",
    store=SQLiteStore("demo_audit.db"),
    lookback="start_of_day",     # re-read from midnight of the last good run
)

with cp.run() as run:
    print("Load type :", run.load_type)
    print("Fetch since:", run.since)

    # pretend this came from an API
    rows = [
        {"id": 1, "email": "a@x.com", "updated_at": "2026-10-20T01:00:00"},
        {"id": 1, "email": "a@x.com", "updated_at": "2026-10-20T03:00:00"},  # duplicate key
        {"id": 2, "email": "b@x.com", "updated_at": "2026-10-20T02:00:00"},
    ]
    rows = dedupe_latest(rows, key="id", order_by="updated_at")
    run.rows = len(rows)
    print("Rows to load:", run.rows)

print("\nHistory:")
for r in cp.history():
    print(" ", r.status, r.load_type, r.since, "rows =", r.rows)
