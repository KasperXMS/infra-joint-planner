"""New offline field/policy control over immutable compound control006."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import large_scale_compound_queue_v1 as parent
import large_scale_field_policy_review_v1 as review

from infra_joint.control.provenance import provenance_sha256

ROOT = review.ROOT
PARENT_CONTROL = "80129a3427d32f2026e1c6259460f58b3cf1d1ec1607ad32990d78042bbe41f3"


class FieldQueueView(review.FieldAttemptLedger):
    @property
    def completed_cells(self) -> tuple[str, ...]:
        folders = ("adjudications", review.previous.policy_review.POLICY_DIRECTORY,
                   review.previous.DIRECTORY, review.DIRECTORY)
        receipts = tuple((folder, p.name, review.sha256(p)) for folder in folders
                         for p in sorted((self.path.parent / folder).glob("*.json")))
        original = self.original_attempts
        evidence = tuple((a.run_id, str(p.relative_to(directory)), p.is_symlink(),
                          p.stat().st_size, p.stat().st_mtime_ns, p.stat().st_ctime_ns)
                         for a in original if any(
                             (self.path.parent / folder / (a.run_id + ".json")).exists()
                             for folder in folders)
                         for directory in [self.path.parent / "evidence" / a.cell_id /
                                           f"attempt{a.attempt_index}"]
                         for p in sorted(directory.rglob("*")) if p.is_file())
        prepared = []
        for p in sorted((self.path.parent / review.DIRECTORY).glob("*.json")):
            for row in json.loads(p.read_text())["initial_artifact_shapes"].values():
                f = Path(row["path"])
                prepared.append((str(f), f.is_symlink(), f.stat().st_size,
                                 f.stat().st_mtime_ns, f.stat().st_ctime_ns))
        source_paths = (*review.SOURCE_PATHS, "src/infra_joint/worker/server.py")
        execution = tuple((p, review.sha256(self.path.parent / "app" / p))
                          for p in source_paths)
        key = (original, receipts, evidence, tuple(prepared), execution, review.sources())
        if getattr(self, "_completion_key", None) != key:
            admitted = {a.cell_id for a in self.attempts if a.disposition == "valid"}
            self._completion_value = tuple(c for c in self.cells if c in admitted)
            self._completion_key = key
        return self._completion_value


def control_value() -> dict[str, Any]:
    saved = json.loads((ROOT / "queue-control-freeze-006.json").read_text())
    if provenance_sha256(saved) != PARENT_CONTROL or parent.control_value() != saved:
        raise RuntimeError("immutable compound parent control drift")
    return {"version": "offline-field-policy-control-v1",
            "parent_control_sha256": PARENT_CONTROL,
            "parent_control_source_sha256": review.sha256(Path(parent.__file__)),
            "queue_source_sha256": review.sha256(Path(__file__)),
            "reviewer_sources_sha256": review.sources(),
            "execution_sha256": saved["execution_sha256"],
            "field_review_receipts": {p.name: review.sha256(p)
                for p in sorted((ROOT / review.DIRECTORY).glob("*.json"))},
            "replacement_authorized": False, "formal_execution_changed": False,
            "schedule_unchanged": True}


def run(path: Path) -> None:
    import large_scale_queue_v1 as queue

    queue.require_remote(ROOT)
    if (path.is_symlink() or path.resolve().parent != ROOT
            or not path.name.startswith("queue-control-freeze-")):
        raise RuntimeError("field control must have a new owned namespace")
    value = control_value()
    if json.loads(path.read_text()) != value or not value["field_review_receipts"]:
        raise RuntimeError("field queue-control provenance drift")
    review.previous.require_stopped(ROOT, ignore_pid=os.getpid())
    queue.AttemptLedger = FieldQueueView
    queue.run_queue(ROOT / "execution-freeze-003.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--control-freeze", type=Path, required=True)
    args = parser.parse_args()
    if args.freeze:
        import large_scale_queue_v1 as queue

        queue.require_remote(ROOT)
        if (args.control_freeze.is_symlink() or args.control_freeze.resolve().parent != ROOT
                or not args.control_freeze.name.startswith("queue-control-freeze-")):
            raise RuntimeError("field freeze must remain in a new owned namespace")
        review.previous.require_stopped(ROOT, ignore_pid=os.getpid())
        value = control_value()
        queue.write_new(args.control_freeze, value)
        print(json.dumps({"control_sha256": provenance_sha256(value)}))
    else:
        run(args.control_freeze)
