"""Look up what the system stored about one decision (for the demo page's "typed vs kept" view).

Only the two records the system writes anyway are read: the audit entry and the prompt journal
entry. Both are in registered Leak Audit sinks and hold no personal data by construction, so
showing them adds no new exposure. Recent decisions sit at the end of the files, so only the tail is
read unless the decision is older.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

TAIL_BYTES = 512 * 1024


def find_record(
    path: Path, decision_id: str, tail_bytes: int = TAIL_BYTES
) -> dict[str, Any] | None:
    """The newest JSON line of `path` whose `decision_id` matches, or None."""
    if not path.exists():
        return None
    size = path.stat().st_size
    for window in [size] if size <= tail_bytes else [tail_bytes, size]:
        with open(path, "rb") as fh:
            fh.seek(max(0, size - window))
            chunk = fh.read().decode("utf-8", errors="replace")
        for line in reversed(chunk.splitlines()):
            if decision_id not in line:
                continue
            try:
                record = json.loads(line)
            except ValueError:  # the first line of a tail window may be cut in half
                continue
            if record.get("decision_id") == decision_id:
                return record
    return None
