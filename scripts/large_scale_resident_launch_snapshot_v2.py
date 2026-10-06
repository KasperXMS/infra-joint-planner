"""Stable current audit projection; preserve historical collectors and receipts.

Bind only dependencies actually referenced by the collector/reviewer closure,
not unrelated imported queue/gate modules. All source, admission, graph, residency
and journal checks remain the original implementation.
"""

from __future__ import annotations

import argparse
import inspect
import json
import sys
from pathlib import Path
from types import FunctionType, ModuleType, SimpleNamespace
from typing import Any

import large_scale_resident_launch_snapshot_v1 as previous
import large_scale_resident_sdk_argument_review_v1 as reviewer

resident, EXECUTIONS = previous.resident, previous.EXECUTIONS


def source_bindings() -> dict[str, str]:
    pending = [previous, reviewer]
    seen: set[str] = set()
    paths = {Path(__file__)}
    while pending:
        module = pending.pop()
        if module.__name__ in seen:
            continue
        seen.add(module.__name__)
        if module.__file__ is None:
            raise RuntimeError("audit dependencies require actual source files")
        paths.add(Path(module.__file__))
        for value in vars(module).values():
            dependency = value if isinstance(value, ModuleType) else (
                sys.modules.get(value.__module__)
                if inspect.isfunction(value) or inspect.isclass(value) else None)
            if isinstance(dependency, ModuleType) and dependency.__name__.startswith(
                    ("large_scale_", "cost_guidance_", "resident_model_")):
                pending.append(dependency)
    if len({p.name for p in paths}) != len(paths):
        raise RuntimeError("ambiguous actual collector source basenames")
    return {p.name: resident.sha256(p) for p in sorted(paths)}


def collect(root: Path = resident.ROOT, predecessor: Path = resident.PREDECESSOR) -> dict[str, Any]:
    # A copied function namespace selects the verified new admission view without
    # mutating old module globals or any runtime/Agent/Worker implementation.
    view = SimpleNamespace(**{**vars(previous.reviewer),
        "ProjectionAttemptLedger": reviewer.ProjectionAttemptLedger,
        "effective_admission": reviewer.effective_admission})
    namespace = {**previous.collect.__globals__, "reviewer": view}
    collect_current = FunctionType(previous.collect.__code__, namespace,
        previous.collect.__name__, previous.collect.__defaults__, previous.collect.__closure__)
    value = collect_current(root, predecessor)
    for row in value["rows"]:
        for attempt in row["attempts"]:
            path = root / reviewer.SEMANTIC_DIRECTORY / (attempt["run_id"] + ".json")
            attempt["native_specialist_argument_review_file_sha256"] = (
                resident.sha256(path) if path.exists() else None)
            if path.exists():
                attempt.update(original_rejection_preserved=True, benchmark_quality_unknown=True,
                    failure_class="workflow_composition_malformed_native_tool_json")
    value["version"] = "resident-stable-current-admission-projection-v2"
    value["collector_source_sha256"] = source_bindings()
    if resident.sha256(root / "phase1-attempts.jsonl") != value["journal_sha256"]:
        raise RuntimeError("journal advanced; never publish a stale current projection")
    return value


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if (sys.platform != "linux" or args.output.is_symlink()
            or args.output.resolve().parent != resident.ROOT / "analysis"):
        raise RuntimeError("audit projection remains in its owned remote namespace")
    value = collect()
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
    print(json.dumps({k: v for k, v in value.items() if k != "rows"}))
