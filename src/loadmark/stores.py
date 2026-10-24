import json
import os
import sqlite3
import tempfile
from abc import ABC, abstractmethod
from typing import List, Optional

from .models import RUNNING, SUCCESS, RunRecord, from_iso, to_iso


class Store(ABC):
    """Where run history is kept. Subclass this to use your own database."""

    @abstractmethod
    def save(self, record: RunRecord) -> None:
        """Insert the record, or update it if its run_id already exists."""

    @abstractmethod
    def last_success(self, name: str) -> Optional[RunRecord]:
        """Most recent SUCCESS run for this name (by start_time), or None."""

    @abstractmethod
    def running(self, name: str) -> List[RunRecord]:
        """All runs of this name that are still marked RUNNING."""

    @abstractmethod
    def history(self, name: str, limit: int = 10) -> List[RunRecord]:
        """Latest runs first."""

    @abstractmethod
    def clear(self, name: str) -> None:
        """Delete all history for this name (next run becomes a full load)."""


class LocalFileStore(Store):
    """Keeps history in one JSON file. Good for learning and small jobs."""

    def __init__(self, path: str = "loadmark_state.json"):
        self.path = path

    def _read(self) -> List[RunRecord]:
        if not os.path.exists(self.path):
            return []
        with open(self.path, "r", encoding="utf-8") as f:
            content = f.read().strip()
        if not content:
            return []
        data = json.loads(content)
        return [RunRecord.from_dict(item) for item in data.get("runs", [])]

    def _write(self, records: List[RunRecord]) -> None:
        folder = os.path.dirname(os.path.abspath(self.path))
        os.makedirs(folder, exist_ok=True)
        # write to a temp file first, then rename: a crash can't corrupt the file
        fd, tmp_path = tempfile.mkstemp(dir=folder, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump({"runs": [r.to_dict() for r in records]}, f, indent=2)
            os.replace(tmp_path, self.path)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def save(self, record: RunRecord) -> None:
        records = [r for r in self._read() if r.run_id != record.run_id]
        records.append(record)
        self._write(records)

    def last_success(self, name: str) -> Optional[RunRecord]:
        done = [r for r in self._read() if r.name == name and r.status == SUCCESS]
        return max(done, key=lambda r: r.start_time) if done else None

    def running(self, name: str) -> List[RunRecord]:
        return [r for r in self._read() if r.name == name and r.status == RUNNING]

    def history(self, name: str, limit: int = 10) -> List[RunRecord]:
        mine = [r for r in self._read() if r.name == name]
        return sorted(mine, key=lambda r: r.start_time, reverse=True)[:limit]

    def clear(self, name: str) -> None:
        self._write([r for r in self._read() if r.name != name])


class SQLiteStore(Store):
    """Keeps history in a SQLite table, like an audit table in a warehouse."""

    def __init__(self, path: str = "loadmark.db", table: str = "loadmark_runs"):
        if not table.replace("_", "").isalnum():
            raise ValueError("table name may only contain letters, digits and _")
        self.path = path
        self.table = table
        with self._connect() as conn:
            conn.execute(
                f"""CREATE TABLE IF NOT EXISTS {self.table} (
                    run_id     TEXT PRIMARY KEY,
                    name       TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    status     TEXT NOT NULL,
                    load_type  TEXT,
                    since      TEXT,
                    end_time   TEXT,
                    rows       INTEGER,
                    message    TEXT
                )"""
            )

    def _connect(self):
        return sqlite3.connect(self.path)

    @staticmethod
    def _to_record(row) -> RunRecord:
        return RunRecord(
            run_id=row[0], name=row[1], start_time=from_iso(row[2]),
            status=row[3], load_type=row[4], since=from_iso(row[5]),
            end_time=from_iso(row[6]), rows=row[7], message=row[8],
        )

    def save(self, record: RunRecord) -> None:
        with self._connect() as conn:
            conn.execute(
                f"""INSERT OR REPLACE INTO {self.table}
                    (run_id, name, start_time, status, load_type, since,
                     end_time, rows, message)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (record.run_id, record.name, to_iso(record.start_time),
                 record.status, record.load_type, to_iso(record.since),
                 to_iso(record.end_time), record.rows, record.message),
            )

    def _query(self, sql: str, params: tuple) -> List[RunRecord]:
        with self._connect() as conn:
            return [self._to_record(r) for r in conn.execute(sql, params).fetchall()]

    def last_success(self, name: str) -> Optional[RunRecord]:
        found = self._query(
            f"SELECT * FROM {self.table} WHERE name = ? AND status = ? "
            "ORDER BY start_time DESC LIMIT 1",
            (name, SUCCESS),
        )
        return found[0] if found else None

    def running(self, name: str) -> List[RunRecord]:
        return self._query(
            f"SELECT * FROM {self.table} WHERE name = ? AND status = ?",
            (name, RUNNING),
        )

    def history(self, name: str, limit: int = 10) -> List[RunRecord]:
        return self._query(
            f"SELECT * FROM {self.table} WHERE name = ? "
            "ORDER BY start_time DESC LIMIT ?",
            (name, limit),
        )

    def clear(self, name: str) -> None:
        with self._connect() as conn:
            conn.execute(f"DELETE FROM {self.table} WHERE name = ?", (name,))
