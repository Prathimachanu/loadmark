from typing import Iterable, List, Sequence, Union


def dedupe_latest(
    records: Iterable[dict],
    key: Union[str, Sequence[str]],
    order_by: str,
) -> List[dict]:
    """Keep only the newest record for each key.

    A lookback window re-reads some rows you already loaded, so duplicates are
    expected. Use this (or a MERGE in your database) to remove them.

        dedupe_latest(rows, key="id", order_by="updated_at")
        dedupe_latest(rows, key=("id", "region"), order_by="updated_at")
    """
    keys = (key,) if isinstance(key, str) else tuple(key)
    best = {}
    for record in records:
        k = tuple(record.get(name) for name in keys)
        current = best.get(k)
        if current is None or record.get(order_by) >= current.get(order_by):
            best[k] = record
    return list(best.values())
