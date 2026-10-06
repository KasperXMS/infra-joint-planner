"""Current metadata projection includes exact mixed provider operational audits.

Reuse all frozen collector guards. Historical collectors, original admissions
and evidence remain unchanged; this entrypoint does not read gold or run Agents.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from types import FunctionType, SimpleNamespace
from typing import Any

import large_scale_resident_launch_snapshot_v2 as previous
import large_scale_resident_rate_policy_review_v1 as reviewer

resident, EXECUTIONS = previous.resident, previous.EXECUTIONS


def source_bindings() -> dict[str, str]:
    original = previous.source_bindings
    namespace = {**original.__globals__, "reviewer": reviewer, "__file__": __file__}
    bound = FunctionType(original.__code__, namespace, original.__name__,
                         original.__defaults__, original.__closure__)
    sources = bound()
    path = Path(previous.__file__)
    sources[path.name] = resident.sha256(path)
    return sources


def collect(root: Path = resident.ROOT, predecessor: Path = resident.PREDECESSOR) -> dict[str, Any]:
    view = SimpleNamespace(**{**vars(reviewer),
        "SEMANTIC_DIRECTORY": reviewer.previous.SEMANTIC_DIRECTORY})
    original = previous.collect
    namespace = {**original.__globals__, "reviewer": view, "source_bindings": source_bindings}
    bound = FunctionType(original.__code__, namespace, original.__name__,
                         original.__defaults__, original.__closure__)
    value = bound(root, predecessor)
    for row in value["rows"]:
        for attempt in row["attempts"]:
            path = root / reviewer.RATE_DIRECTORY / (attempt["run_id"] + ".json")
            attempt["mixed_token_rate_policy_review_file_sha256"] = (
                resident.sha256(path) if path.exists() else None)
            if path.exists():
                if (attempt["disposition"] != "operational_excluded"
                        or attempt["reason"] != reviewer.REASON):
                    raise RuntimeError("mixed provider collector/admission identity drift")
                attempt.update(original_rejection_preserved=True, benchmark_quality_unknown=True,
                    failure_class="mixed_provider_token_rate_and_input_policy",
                    replacement_basis="independently_proven_HTTP429_token_rate_limit",
                    policy_only_replacement_authorized=False)
    value["version"] = "resident-exact-mixed-provider-admission-projection-v3"
    if resident.sha256(root / "phase1-attempts.jsonl") != value["journal_sha256"]:
        raise RuntimeError("journal advanced; never publish stale mixed provider projection")
    return value


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if (sys.platform != "linux" or args.output.is_symlink()
            or args.output.resolve().parent != resident.ROOT / "analysis"):
        raise RuntimeError("current projection remains in its owned remote namespace")
    value = collect()
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
    print(json.dumps({k: v for k, v in value.items() if k != "rows"}))
