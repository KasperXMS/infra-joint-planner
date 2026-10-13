# pyright: reportPrivateUsage=false, reportUnknownMemberType=false
"""Freeze the three previously studied Stage-2 anchors without model calls."""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
from pathlib import Path
from typing import Any

import yaml
from blind_3family_validation_v1 import _load_bundle

from infra_joint.agents.context import AgentTaskView
from infra_joint.control.provenance import provenance_sha256

APP = Path(__file__).resolve().parents[1]
SOURCE = APP / "configs/experiments/blind-baseline-6task-competent-v2.yaml"
LABELS = ("multihop-multisource", "longbench-multidoc", "video-long-payload")
FILES = {
    "multihop_corpus": Path("/home/super/xiaoming/blind_baseline_6task_v1/data/corpus.json"),
    "multihop_queries": Path("/home/super/xiaoming/blind_baseline_6task_v1/data/MultiHopRAG.json"),
    "longbench_samples": Path(
        "/home/super/xiaoming/infra-bench/scenario-mining/data/longbench_v2/selected.jsonl"
    ),
    "video_tasks": Path(
        "/home/super/xiaoming/mas_validity_v1/infra-bench/configs/calibration_v0/tasks.yaml"
    ),
    "video_answers": Path(
        "/home/super/xiaoming/mas_validity_v1/infra-bench/configs/calibration_v0/"
        "evaluator_only/answers.json"
    ),
    "video_sources": Path("/home/super/xiaoming/calibration_v0/source"),
}


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def load() -> tuple[dict[str, tuple[Any, dict[str, Any]]], dict[str, Any]]:
    base = yaml.safe_load(SOURCE.read_text(encoding="utf-8"))
    args = argparse.Namespace(**FILES)
    selected = {row["label"]: row for row in base["dataset"]["tasks"]}
    cache: dict[str, tuple[Any, dict[str, Any]]] = {}
    tasks = []
    from blind_baseline_6task_v1 import _public_bundle_digest

    for label in LABELS:
        bundle, source = _load_bundle({"task": label}, base, args)
        row = selected[label]
        initial = list(base["execution"]["initial_placement"][label])
        if len(initial) != len(bundle.prepared_artifacts):
            raise RuntimeError(f"initial placement / artifact mismatch: {label}")
        family, position = {
            "multihop-multisource": ("multihop_rag", 100),
            "longbench-multidoc": ("longbench_v2", 100),
            "video-long-payload": ("video_mme", 100),
        }[label]
        evaluator_source = inspect.getsourcefile(type(bundle.private_evaluation.build_evaluator()))
        if evaluator_source is None:
            raise RuntimeError(f"evaluator source is unavailable: {label}")
        receipt = {
            "label": label,
            "family": family,
            "position": position,
            "source_task_id": row["source_task_id"],
            "task_bundle_sha256": _public_bundle_digest(bundle),
            "agent_task_sha256": provenance_sha256(
                AgentTaskView.from_contract(bundle.execution.task).model_dump(
                    mode="json", by_alias=True
                )
            ),
            "evaluator_implementation_sha256": digest(Path(evaluator_source)),
            "source_sha256": source,
            "artifacts": [
                {
                    "artifact_id": artifact.spec.artifact_id,
                    "sha256": artifact.sha256_hex,
                    "size_bytes": artifact.spec.size_bytes,
                    "initial_worker": worker,
                }
                for artifact, worker in zip(bundle.prepared_artifacts, initial, strict=True)
            ],
        }
        tasks.append(receipt)
        cache[label] = (bundle, receipt)
    manifest = {
        "version": "harness-v2-anchor-freeze-001",
        "source_config_sha256": digest(SOURCE),
        "selection_before_stage2_outcomes": True,
        "selection": list(LABELS),
        "tasks": tasks,
    }
    return cache, manifest


def freeze(output: Path) -> None:
    if output.exists():
        raise FileExistsError("Anchor freeze exists; refusing overwrite")
    _cache, manifest = load()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(manifest, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"frozen_anchors": len(manifest["tasks"]), "output": str(output)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    freeze(parser.parse_args().output)
