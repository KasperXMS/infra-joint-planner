"""Read-only exact projection view over the same four execution epochs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import large_scale_resident_E_query_snapshot_v1 as core
import large_scale_resident_projection_review_v1 as reviewer

EXECUTIONS = core.EXECUTIONS
resident = core.resident


def collect(root: Path = core.resident.ROOT,
            predecessor: Path = core.resident.PREDECESSOR) -> dict[str, Any]:
    value = core.collect(root, predecessor, audit_view=reviewer)
    value["collector_source_sha256"][Path(__file__).name] = core.resident.sha256(Path(__file__))
    return value


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if (sys.platform != "linux" or args.output.is_symlink()
            or args.output.resolve().parent != core.resident.ROOT / "analysis"):
        raise RuntimeError("projection remains in the owned remote namespace")
    value = collect()
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
    print(json.dumps({k: v for k, v in value.items() if k != "rows"}))
