import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest

SCRIPT = Path(__file__).parents[1] / "scripts/build_cost_guidance_history_v1.py"
spec = importlib.util.spec_from_file_location("cost_history_freeze", SCRIPT)
assert spec is not None and spec.loader is not None
builder: Any = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def test_evidence_hashes_and_unicode_separators_verified_without_reading_result(
    tmp_path: Path,
) -> None:
    trace = tmp_path / "runs/test/trace.jsonl"
    trace.parent.mkdir(parents=True)
    trace.write_text(json.dumps({"text": "a\u2028b\u2029c"}, ensure_ascii=False) + "\n",
                     encoding="utf-8")
    result = trace.with_name("result.json")
    result.write_text("not parsed by cost extractor", encoding="utf-8")
    record = {"run_id": "test", "evidence_hashes": {
        "runs/test/trace.jsonl": builder.file_sha256(trace),
        "runs/test/result.json": builder.file_sha256(result),
    }}
    assert builder.verified_trace(tmp_path, record) == [{"text": "a\u2028b\u2029c"}]
    result.write_text("tampered", encoding="utf-8")
    with pytest.raises(ValueError, match="provenance mismatch"):
        builder.verified_trace(tmp_path, record)


def test_eligibility_does_not_filter_wrong_or_incomplete_semantic_result() -> None:
    record = {
        "validation": {"validity": "operational_checks_pass", "problems": [], "probe_errors": []},
        "persistence": {"pass": True}, "provenance": {"pass": True},
        "summary": {"logical_privacy_pass": True}, "terminal_answer_provenance_pass": None,
        "evaluation": {"score": 0}, "completed": False,
    }
    assert builder.eligible(record, crossbenchmark=True)
    record["validation"]["problems"] = ["privacy bug"]
    assert not builder.eligible(record, crossbenchmark=True)


def test_frozen_audit_hash_is_required(tmp_path: Path) -> None:
    path = tmp_path / "audit.json"
    path.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="audit hash mismatch"):
        builder.verified_json(path, "0" * 64)


def test_path_outside_evidence_directory_rejected(tmp_path: Path) -> None:
    root = tmp_path / "evidence"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.write_text("private", encoding="utf-8")
    record = {"run_id": "test", "evidence_hashes": {
        "runs/test/trace.jsonl": "0" * 64,
        "runs/test/result.json": "0" * 64,
        "../outside": builder.file_sha256(outside),
    }}
    # Visit the escaping path first: no raw content should be accepted.
    record["evidence_hashes"] = (
        {"../outside": builder.file_sha256(outside)} | record["evidence_hashes"]
    )
    with pytest.raises(ValueError, match="provenance mismatch"):
        builder.verified_trace(root, record)
