"""Offline compound-review queue controller; frozen execution app stays unchanged."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import large_scale_compound_review_v1 as review

from infra_joint.control.provenance import provenance_sha256

ROOT = review.ROOT
PARENT_CONTROL = "f67ed3890442ec6c483cfb4a8c4c78b99dd067fa665147f91b5e26da9cd8b09e"


class CompoundQueueView(review.CompoundAttemptLedger):
    @property
    def completed_cells(self) -> tuple[str, ...]:
        folders = ("adjudications", review.policy_review.POLICY_DIRECTORY, review.DIRECTORY)
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
        worker = self.path.parent / "app/src/infra_joint/worker/server.py"
        worker_source = review.sha256(worker) if worker.is_file() else None
        key = (original, receipts, evidence, worker_source, review.reviewer_sources())
        if getattr(self, "_completion_key", None) != key:
            admitted = {a.cell_id for a in self.attempts if a.disposition == "valid"}
            self._completion_value = tuple(c for c in self.cells if c in admitted)
            self._completion_key = key
        return self._completion_value


def control_value() -> dict[str, Any]:
    import large_scale_transport_control_v1 as parent

    saved = json.loads((ROOT / "queue-control-freeze-005.json").read_text())
    if provenance_sha256(saved) != PARENT_CONTROL or parent.control_value() != saved:
        raise RuntimeError("immutable parent transport control drift")
    return {"version": "offline-compound-failure-control-v1",
            "parent_control_sha256": PARENT_CONTROL,
            "parent_control_source_sha256": review.sha256(Path(parent.__file__)),
            "queue_source_sha256": review.sha256(Path(__file__)),
            "reviewer_sources_sha256": review.reviewer_sources(),
            "execution_sha256": saved["execution_sha256"],
            "compound_review_receipts": {p.name: review.sha256(p)
                for p in sorted((ROOT / review.DIRECTORY).glob("*.json"))},
            "replacement_authorized": False, "formal_execution_changed": False,
            "schedule_unchanged": True}


def run(path: Path) -> None:
    import large_scale_queue_v1 as queue

    queue.require_remote(ROOT)
    if (path.is_symlink() or path.resolve().parent != ROOT
            or not path.name.startswith("queue-control-freeze-")):
        raise RuntimeError("compound control must have a new owned namespace")
    value = control_value()
    if json.loads(path.read_text()) != value or not value["compound_review_receipts"]:
        raise RuntimeError("compound queue-control provenance drift")
    review.require_stopped(ROOT, ignore_pid=os.getpid())
    queue.AttemptLedger = CompoundQueueView
    queue.run_queue(ROOT / "execution-freeze-003.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--control-freeze", type=Path, required=True)
    arguments = parser.parse_args()
    if arguments.freeze:
        import large_scale_queue_v1 as queue

        queue.require_remote(ROOT)
        if (arguments.control_freeze.is_symlink()
                or arguments.control_freeze.resolve().parent != ROOT
                or not arguments.control_freeze.name.startswith("queue-control-freeze-")):
            raise RuntimeError("compound freeze must remain in a new owned namespace")
        review.require_stopped(ROOT, ignore_pid=os.getpid())
        value = control_value()
        queue.write_new(arguments.control_freeze, value)
        print(json.dumps({"control_sha256": provenance_sha256(value)}))
    else:
        run(arguments.control_freeze)
