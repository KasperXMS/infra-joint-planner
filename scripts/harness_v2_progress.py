"""Show only batch count and timing, without reading model traces."""

from __future__ import annotations

import json
import time
from pathlib import Path
from statistics import median

ROOT = Path("/home/super/xiaoming/harness-v2-baseline-requalification/run-001/stage2")
finished_files = list((ROOT / "cells").glob("*/cell-finished.json"))
rows = [json.loads(path.read_text()) for path in finished_files]
times = [row["wall_ms"] / 1000 for row in rows]
active = next(
    (
        claim
        for claim in sorted((ROOT / "cells").glob("*/claim.json"))
        if not (claim.parent / "cell-finished.json").exists()
    ),
    None,
)
print(
    json.dumps(
        {
            "finished": len(rows),
            "claimed": len(list((ROOT / "cells").glob("*/claim.json"))),
            "remaining": 36 - len(rows),
            "median_finished_cell_seconds": round(median(times), 1) if times else None,
            "finished_cell_seconds": round(sum(times), 1),
            "current_network": json.loads(active.read_text())["cell"]["network"]
            if active is not None
            else json.loads(max(finished_files, key=lambda path: path.stat().st_mtime).read_text())[
                "cell"
            ]["network"]
            if finished_files
            else None,
            "active_cell": active.parent.name if active is not None else None,
            "active_age_seconds": round(time.time() - active.stat().st_mtime)
            if active is not None
            else None,
            "complete": (ROOT / "complete.json").exists(),
        }
    )
)
