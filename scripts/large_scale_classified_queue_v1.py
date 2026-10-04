"""Offline classified-failure queue; launches the unchanged frozen execution app."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from large_scale_adjudicated_queue_v1 import control_freeze as json_control_freeze
from large_scale_provider_policy_review_v1 import (
    POLICY_DIRECTORY,
    ROOT,
    ClassifiedAttemptLedger,
    sha256,
)

from infra_joint.control.provenance import provenance_sha256


class ClassifiedQueueView(ClassifiedAttemptLedger):
    @property
    def completed_cells(self) -> tuple[str, ...]:
        receipts = tuple((folder, p.name, sha256(p))
                         for folder in ("adjudications", POLICY_DIRECTORY)
                         for p in sorted((self.path.parent / folder).glob("*.json")))
        original = self.original_attempts
        # Metadata is cache invalidation only, never an alternative to full proof
        # verification. Direct attempts/reservation/settlement still rehash evidence.
        evidence = tuple((item.run_id, str(p.relative_to(directory)), p.is_symlink(),
                          p.stat().st_size, p.stat().st_mtime_ns, p.stat().st_ctime_ns)
                         for item in original
                         if (self.path.parent / POLICY_DIRECTORY / (item.run_id + ".json")).exists()
                         for directory in [self.path.parent / "evidence" / item.cell_id /
                                           f"attempt{item.attempt_index}"]
                         for p in sorted(directory.rglob("*")) if p.is_file())
        key = (original, receipts, evidence)
        if getattr(self, "_completion_key", None) != key:
            admitted = {item.cell_id for item in self.attempts if item.disposition == "valid"}
            self._completion_value = tuple(cell for cell in self.cells if cell in admitted)
            self._completion_key = key
        return self._completion_value


def control_freeze() -> dict[str, Any]:
    return {"version": "offline-classified-failure-queue-v1",
            "previous_json_control": json_control_freeze(),
            "queue_control_source_sha256": sha256(Path(__file__)),
            "policy_reviewer_source_sha256": sha256(Path(__file__).with_name(
                "large_scale_provider_policy_review_v1.py")),
            "provider_policy_receipts": {p.name: sha256(p)
                                         for p in sorted((ROOT / POLICY_DIRECTORY).glob("*.json"))},
            "replacement_authorized": False, "schedule_unchanged": True,
            "formal_execution_changed": False}


def run(path: Path) -> None:
    import large_scale_queue_v1 as frozen

    if path.resolve().parent != ROOT or not path.name.startswith("queue-control-freeze-"):
        raise RuntimeError("classified queue receipt must be separately frozen in owned root")
    value = json.loads(path.read_text())
    if value != control_freeze() or not value["provider_policy_receipts"]:
        raise RuntimeError("classified queue provenance drift")
    frozen.AttemptLedger = ClassifiedQueueView
    frozen.run_queue(ROOT / "execution-freeze-002.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--control-freeze", type=Path, required=True)
    arguments = parser.parse_args()
    if arguments.freeze:
        if arguments.control_freeze.resolve().parent != ROOT:
            raise RuntimeError("classified freeze must stay in owned root")
        value = control_freeze()
        with arguments.control_freeze.open("x", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2)
        print(json.dumps({"control_freeze_sha256": provenance_sha256(value)}))
    else:
        run(arguments.control_freeze)
