"""loadmark - a safe bookmark (checkpoint) for incremental data loads."""

from .core import Checkpoint, Run
from .dedupe import dedupe_latest
from .errors import InvalidLookbackError, LoadmarkError, RunInProgressError
from .lookback import apply_lookback
from .models import FAILED, RUNNING, SUCCESS, RunRecord
from .stores import LocalFileStore, SQLiteStore, Store

__version__ = "0.1.0"

__all__ = [
    "Checkpoint", "Run", "Store", "LocalFileStore", "SQLiteStore",
    "RunRecord", "dedupe_latest", "apply_lookback",
    "LoadmarkError", "RunInProgressError", "InvalidLookbackError",
    "RUNNING", "SUCCESS", "FAILED", "__version__",
]
