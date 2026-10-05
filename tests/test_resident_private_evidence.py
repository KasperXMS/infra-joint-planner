import hashlib
import importlib
import json
import sys
from pathlib import Path

import pytest

from infra_joint.control.provenance import provenance_sha256

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
audit = importlib.import_module("large_scale_resident_private_evidence_v1")


@pytest.mark.parametrize("handle", ["queue-lease.json", "queue-process-001.json",
                                    "evidence/cell/attempt1/process.json"])
def test_private_body_audit_rejects_actual_live_new_namespace_handles(
    tmp_path: Path, handle: str,
) -> None:
    root, proc = tmp_path / "new-resident", tmp_path / "proc"
    record = root / handle
    record.parent.mkdir(parents=True)
    record.write_text(json.dumps({"pid": 123}))
    command = proc / "123/cmdline"
    command.parent.mkdir(parents=True)
    command.write_bytes(b"python\0/new-resident/app/scripts/queue.py\0")
    with pytest.raises(RuntimeError, match="inactive queue and atomic"):
        audit.assert_inactive(root, proc_root=proc)
    # PID reuse for an unrelated process is not a live experimental handle.
    command.write_bytes(b"python\0/unrelated/app/server.py\0")
    audit.assert_inactive(root, proc_root=proc)
    command.unlink()
    audit.assert_inactive(root, proc_root=proc)


def test_private_phase_one_audit_does_not_scan_partial_or_live_block(tmp_path, monkeypatch):
    called = []
    monkeypatch.setattr(audit, "collect", lambda *args: {
        "phase1_complete": False, "pending_count": 1, "confounded_attempts": 0})
    monkeypatch.setattr(audit, "audit_multihop", lambda *args: called.append(args))
    with pytest.raises(RuntimeError, match="completed resolved168"):
        audit.audit_phase_one(tmp_path, tmp_path, tmp_path / "corpus")
    assert not called


@pytest.mark.parametrize("changed", ["namespace", "run_id", "store_root"])
def test_private_remote_scan_is_exact_run_and_owner_bound(changed: str, monkeypatch) -> None:
    run_id = audit.ROOT.name + "-phase1-synthetic-attempt1"
    request = {"namespace": audit.ROOT.name, "run_id": run_id, "supports": [], "artifacts": [],
               "store_root": f"/home/super/heterogeneous-v1/artifacts/{audit.ROOT.name}/"
                             f"{run_id}/strong-4090"}
    called = []
    monkeypatch.setattr(audit, "scan_store", lambda value: called.append(value) or [])
    assert audit.scan_request("strong-4090", request) == []
    assert len(called) == 1
    request[changed] = "unrelated"
    with pytest.raises(RuntimeError, match="exact frozen run/owner"):
        audit.scan_request("strong-4090", request)
    assert len(called) == 1


@pytest.fixture
def multihop_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple:
    directory = tmp_path / "cell"
    private_folder = directory / "private"
    private_folder.mkdir(parents=True)
    document = {"title": "Synthetic title", "body": "PRIVATE FACT", "author": None,
                "source": "synthetic", "published_at": "2020", "category": "test",
                "url": "https://example.test/doc"}
    corpus = tmp_path / "corpus.json"
    corpus.write_text(json.dumps([document]))
    private = {"gold_answer": "PRIVATE GOLD", "supporting_evidence": [
        {"title": document["title"], "url": document["url"],
         "source": document["source"], "fact": "PRIVATE FACT"}]}
    source_private = tmp_path / "private-original.json"
    source_private.write_text(json.dumps(private, indent=2, sort_keys=True) + "\n")
    # Equivalent values with different indentation/newline must remain valid.
    (private_folder / "private-evaluation.json").write_text(json.dumps(private))
    document_id = audit.support_mapping(private, [document])[0]["document_ids"][0]
    bodies = {"retrieved": json.dumps([{"document_id": document_id,
                                        "body": "PRIVATE FACT"}]).encode(),
              "note": b"A paraphrase without literal or document IDs."}
    metadata = [{"artifact_id": identifier, "media_type": (
        "application/json" if identifier == "retrieved" else "text/plain"),
        "sha256_hex": hashlib.sha256(body).hexdigest(), "size_bytes": len(body)}
                for identifier, body in bodies.items()]
    (private_folder / "worker-state-after.json").write_text(json.dumps({"A4": {
        "artifacts": metadata}}))
    attempt = {"task_receipt": {"family": "multihop_rag", "position": 1,
                               "private_evaluation_sha256": audit.sha256(source_private),
                               "source": {"corpus_file_sha256": audit.sha256(corpus)}},
               "fresh_worker_stores": {"A4": "synthetic_store"}}
    (directory / "attempt-freeze.json").write_text(json.dumps(attempt))
    (directory / "process.json").write_text('{"pid":9999999,"run_id":"run"}')
    run = directory / "runs/run"
    run.mkdir(parents=True)
    result = {"execution_completed": True}
    (run / "result.json").write_text(json.dumps(result))
    (directory / "admission.json").write_text(json.dumps({
        "result_sha256": provenance_sha256(result)}))
    actions = [
        {"action_id": "retrieve", "owner_agent_id": "manager", "action_type": "tool",
         "operator": "bm25_retrieve", "inputs": [], "outputs": [{"artifact_id": "retrieved"}]},
        {"action_id": "reduce", "owner_agent_id": "manager", "action_type": "tool",
         "operator": "select_fields", "inputs": ["retrieved"],
         "outputs": [{"artifact_id": "note"}]},
        {"action_id": "terminal", "owner_agent_id": "manager", "action_type": "model",
         "prompt": "PRIVATE PROMPT\u2028do not export", "inputs": ["note"], "outputs": []},
    ]
    events = []
    for action in actions:
        events.extend([
            {"event_type": "logical.action.prepared", "payload": {"action": action}},
            {"event_type": "logical.observation", "payload": {
                "action_id": action["action_id"], "succeeded": True,
                "produced_information": action["outputs"]}},
        ])
    events.append({"event_type": "logical.loop.end", "payload": {"terminal_action_id": "terminal"}})
    (run / "trace.jsonl").write_text("".join(json.dumps(e, ensure_ascii=False) + "\n"
                                           for e in events), encoding="utf-8")
    calls = []

    def scanner(agent: str, request: dict) -> list:
        calls.append((agent, request))
        return [{"artifact_id": m["artifact_id"], "sha256": m["sha256_hex"],
                 "size_bytes": m["size_bytes"], **audit.coverage(
                     bodies[m["artifact_id"]], m["media_type"], request["supports"])}
                for m in request["artifacts"]]

    monkeypatch.setattr(audit, "scan_request", scanner)
    return directory, corpus, source_private, calls


def test_private_paths_are_bounded_and_paraphrase_retention_is_unknown(multihop_fixture):
    directory, corpus, source_private, calls = multihop_fixture
    before = {p: p.read_bytes() for p in directory.rglob("*") if p.is_file()}
    value = audit.audit_multihop(directory, corpus, source_private)
    assert len(calls) == 1
    text = json.dumps(value)
    assert all(secret not in text for secret in ("PRIVATE GOLD", "PRIVATE FACT", "PRIVATE PROMPT"))
    assert value["model_calls"] == 0 and value["semantic_evidence_retention"] is None
    paths = value["action_evidence_paths"]
    assert paths[0]["outputs"][0]["coverage"][0]["support_document_retained"] is True
    assert paths[1]["outputs"][0]["coverage"][0]["support_document_retained"] is None
    assert paths[2]["is_terminal_source"]
    assert paths[2]["inputs"][0]["coverage"][0]["support_document_retained"] is None
    assert all(p.read_bytes() == data for p, data in before.items())


@pytest.mark.parametrize("target", ["private_copy", "original_annotation", "corpus", "result"])
def test_private_paths_reject_source_or_result_drift_before_scanning(multihop_fixture, target):
    directory, corpus, source_private, calls = multihop_fixture
    targets = {"private_copy": directory / "private/private-evaluation.json",
               "original_annotation": source_private, "corpus": corpus,
               "result": directory / "runs/run/result.json"}
    targets[target].write_text('{"changed":true}')
    with pytest.raises(RuntimeError, match="drift"):
        audit.audit_multihop(directory, corpus, source_private)
    assert not calls


def test_private_paths_reject_replica_drift_and_scanner_membership(multihop_fixture, monkeypatch):
    directory, corpus, source_private, calls = multihop_fixture
    states_file = directory / "private/worker-state-after.json"
    states = json.loads(states_file.read_text())
    replica = dict(states["A4"]["artifacts"][0], sha256_hex="changed")
    states["A5"] = {"artifacts": [replica]}
    states_file.write_text(json.dumps(states))
    with pytest.raises(RuntimeError, match="replicated artifact"):
        audit.audit_multihop(directory, corpus, source_private)
    assert not calls
    del states["A5"]
    states_file.write_text(json.dumps(states))
    monkeypatch.setattr(audit, "scan_request", lambda *args: [])
    with pytest.raises(RuntimeError, match="artifact membership"):
        audit.audit_multihop(directory, corpus, source_private)


def test_unannotated_quality_is_not_zero_or_automatic_semantic_failure(tmp_path, monkeypatch):
    journal = tmp_path / "phase1-attempts.jsonl"
    journal.write_text("frozen journal")
    directory = tmp_path / "evidence/cell/attempt1"
    directory.mkdir(parents=True)
    (directory / "worker-shutdown.json").write_text('{"verified_exited":true}')
    snapshot = {"phase1_complete": True, "pending_count": 0, "confounded_attempts": 0,
                "journal_sha256": audit.sha256(journal), "execution_freeze_sha256": "freeze",
                "collector_source_sha256": {}, "rows": [{
                    "condition": {"cell_id": "cell", "task": {
                        "family": "longbench_v2", "position": 1}},
                    "attempts": [{"disposition": "valid", "attempt_index": 1,
                                  "run_id": "run", "benchmark_score": None}]}]}
    monkeypatch.setattr(audit, "collect", lambda *args: snapshot)
    monkeypatch.setattr(audit, "audit_multihop", lambda *args: pytest.fail("unannotated body scan"))
    value = audit.audit_phase_one(tmp_path, tmp_path, tmp_path / "unused-corpus")
    assert value["records"][0]["benchmark_score"] is None
    assert value["records"][0]["semantic_primary_cause"] is None
    assert value["records"][0]["coverage"] is None
    assert not value["phase2_authorized"] and not value["semantic_audit_complete"]
