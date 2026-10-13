"""Show only batch count and timing, without reading model traces."""

from __future__ import annotations

import json
from pathlib import Path
from statistics import median

ROOT = Path("/home/super/xiaoming/harness-v2-baseline-requalification/run-001/stage2")
rows = [
    json.loads(path.read_text()) for path in sorted((ROOT / "cells").glob("*/cell-finished.json"))
]
times = [row["wall_ms"] / 1000 for row in rows]
print(
    json.dumps(
        {
            "finished": len(rows),
            "claimed": len(list((ROOT / "cells").glob("*/claim.json"))),
            "remaining": 36 - len(rows),
            "median_finished_cell_seconds": round(median(times), 1) if times else None,
            "finished_cell_seconds": round(sum(times), 1),
            "current_network": rows[-1]["cell"]["network"] if rows else None,
            "complete": (ROOT / "complete.json").exists(),
        }
    )
)
