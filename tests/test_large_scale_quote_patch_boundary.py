import importlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
patch = importlib.import_module("large_scale_resident_quote_patch_v1")
controller = importlib.import_module("large_scale_resident_quote_repair_queue_v1")


def source_maps() -> tuple[dict, dict]:
    parent = {"src/infra_joint/worker/server.py": "worker-unchanged",
              "configs/environment.yaml": "unchanged",
              patch.QUOTE_PATH: "old-quote",
              "scripts/large_scale_resident_queue_v1.py": "old-entrypoint"}
    current = {**parent, **{path: "new-accounting" for path in patch.ALLOWED_DELTA},
               patch.QUOTE_PATH: patch.FIXED_QUOTE_SHA256}
    return parent, current


def test_only_exact_integrity_and_accounting_source_delta_is_allowed() -> None:
    parent, current = source_maps()
    delta = patch.validate_source_delta(parent, current)
    assert set(delta) == patch.ALLOWED_DELTA
    assert delta[patch.QUOTE_PATH]["patched_sha256"] == patch.FIXED_QUOTE_SHA256


@pytest.mark.parametrize("damage", ["worker", "config", "missing", "extra", "wrong-fix"])
def test_substrate_prompt_environment_or_unreviewed_patch_drift_is_rejected(damage: str) -> None:
    parent, current = source_maps()
    if damage == "worker":
        current["src/infra_joint/worker/server.py"] = "changed"
    elif damage == "config":
        current["configs/environment.yaml"] = "changed"
    elif damage == "missing":
        del current["scripts/large_scale_quote_repair_ledger_v1.py"]
    elif damage == "extra":
        current["src/infra_joint/control/new_method.py"] = "changed"
    else:
        current[patch.QUOTE_PATH] = "unreviewed"
    with pytest.raises(RuntimeError, match="exact audited delta"):
        patch.validate_source_delta(parent, current)


@pytest.mark.parametrize("failure", ["quoted_action_mutated", "context_limit_exceeded"])
def test_quote_integrity_bug_stops_but_ordinary_context_failure_does_not(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str,
) -> None:
    original = {"disposition": "valid", "reason": "valid_semantic_failure", "problems": [],
                "original_evaluation": {"benchmark_score": 0}}
    monkeypatch.setattr(controller.frozen, "admit", lambda *args: original)
    run = tmp_path / "runs/run"
    run.mkdir(parents=True)
    (run / "trace.jsonl").write_text(json.dumps({
        "event_type": "logical.cost_quote.rejected", "payload": {"failure_code": failure}}))
    value = controller.admission(tmp_path, {"run_id": "run"}, tmp_path / "prices")
    assert value["disposition"] == ("confounder" if failure == "quoted_action_mutated" else "valid")
    assert original["disposition"] == "valid" and original["problems"] == []


def test_quote_gate_preserves_other_existing_harness_findings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(controller.frozen, "admit", lambda *args: {
        "disposition": "confounder", "reason": "privacy", "problems": ["privacy"]})
    run = tmp_path / "runs/run"
    run.mkdir(parents=True)
    (run / "trace.jsonl").write_text(json.dumps({
        "event_type": "logical.cost_quote.rejected", "payload": {
            "failure_code": "quoted_action_mutated"}}))
    value = controller.admission(tmp_path, {"run_id": "run"}, tmp_path / "prices")
    assert value["disposition"] == "confounder"
    assert value["problems"] == ["privacy", controller.reviewer.REASON]
