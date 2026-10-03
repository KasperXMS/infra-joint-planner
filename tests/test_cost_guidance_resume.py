import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from resume_cost_guidance_exploration_v1 import _sha256, admitted  # noqa: E402


def test_resume_skips_admitted_cells_but_never_reexecutes_incomplete_attempt(
    tmp_path: Path,
) -> None:
    assert admitted(tmp_path / "not-started") is False
    with pytest.raises(RuntimeError, match="incomplete"):
        admitted(tmp_path)
    (tmp_path / "lightweight-validation.json").write_text(json.dumps({"problems": []}))
    with pytest.raises(RuntimeError, match="evidence missing"):
        admitted(tmp_path)
    run = tmp_path / "runs/test"
    run.mkdir(parents=True)
    (run / "result.json").write_text("{}")
    (run / "trace.jsonl").write_text("{}")
    assert admitted(tmp_path)


def test_postrun_admission_requires_independent_audit_and_unchanged_evidence(
    tmp_path: Path,
) -> None:
    (tmp_path / "lightweight-validation.json").write_text(json.dumps({"problems": ["audit"]}))
    run = tmp_path / "runs/test"
    run.mkdir(parents=True)
    (run / "result.json").write_text("{}")
    (run / "trace.jsonl").write_text("{}")
    with pytest.raises(RuntimeError, match="independent"):
        admitted(tmp_path)
    audit = {"effective_cell_retained": True, "rerun": False,
             "remaining_operational_gates_pass": True,
             "runtime_or_semantic_behavior_changed": False,
             "result_sha256": _sha256(run / "result.json"),
             "trace_sha256": _sha256(run / "trace.jsonl")}
    (tmp_path / "postrun-eligibility-audit-001.json").write_text(json.dumps(audit))
    assert admitted(tmp_path)
    (run / "trace.jsonl").write_text("changed")
    with pytest.raises(RuntimeError, match="inconsistent"):
        admitted(tmp_path)
