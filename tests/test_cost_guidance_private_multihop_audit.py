import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from cost_guidance_private_multihop_audit_v1 import (  # noqa: E402
    assert_queue_inactive,
    coverage,
    scan_store,
    support_mapping,
)


def test_private_doc_identity_and_literal_coverage_are_not_a_quality_oracle() -> None:
    supports = [{"document_ids": ["doc-1"], "fact": "A factual statement."},
                {"document_ids": ["doc-2"], "fact": "Another statement."},
                {"document_ids": [], "fact": "Unmatched evidence."}]
    rows = [{"document_id": "doc-1", "body": "A FACTUAL\n statement."}]
    value = coverage(json.dumps(rows).encode(), "application/json", supports)
    assert [c["support_document_retained"] for c in value["coverage"]] == [True, False, None]
    assert value["coverage"][0]["exact_fact_literal_present"] is True
    assert value["coverage"][0]["literal_absence_is_semantic_absence"] is False
    assert value["document_presence_is_complete_fact_coverage"] is False
    assert "A factual statement." not in json.dumps(value)


def test_projection_or_model_summary_without_ids_is_unknown_not_missing_document() -> None:
    supports = [{"document_ids": ["doc"], "fact": "Fact"}]
    for media, content in [("text/plain", b"A paraphrased note."),
                           ("application/json", b'[{"body":"Fact"}]')]:
        assert coverage(content, media, supports)["coverage"][0][
            "support_document_retained"] is None
    assert coverage(b"[]", "application/json", supports)["coverage"][0][
        "support_document_retained"] is False


def test_private_annotation_mapping_uses_full_corpus_identity_not_hint_injection() -> None:
    doc = {"title": "Title", "body": "Body", "author": None, "source": "source",
           "published_at": "2020", "category": "test", "url": "https://example.test/doc"}
    private = {"supporting_evidence": [{"title": "Title", "url": doc["url"],
                                        "source": "source", "fact": "private fact"}]}
    mapped = support_mapping(private, [doc])
    assert len(mapped[0]["document_ids"]) == 1 and len(mapped[0]["document_ids"][0]) == 64
    private["supporting_evidence"][0]["url"] = "https://example.test/unknown"
    assert support_mapping(private, [doc])[0]["document_ids"] == []


def test_private_scan_refuses_nonexperimental_or_missing_store(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="exact existing"):
        scan_store({"store_root": str(tmp_path), "namespace": "experiment",
                    "supports": [], "artifacts": []})


def test_private_artifact_audit_waits_for_live_owned_controllers(tmp_path: Path) -> None:
    root = tmp_path / "experiment-root"
    root.mkdir()
    (root / "controller.json").write_text(json.dumps({"pid": 123}))
    proc = tmp_path / "proc"
    (proc / "123").mkdir(parents=True)
    cmd = proc / "123/cmdline"
    cmd.write_bytes(b"python\0experiment-root/app/scripts/cell.py")
    with pytest.raises(RuntimeError, match="inactive"):
        assert_queue_inactive(root, proc_root=proc)
    cmd.write_bytes(b"python\0unrelated-project/app/server.py")
    assert_queue_inactive(root, proc_root=proc)


def test_node_scan_helper_does_not_import_an_old_editable_install(tmp_path: Path) -> None:
    script = Path(__file__).parents[1] / "scripts/cost_guidance_private_multihop_audit_v1.py"
    result = subprocess.run(
        [sys.executable, "-S", str(script), "--scan-store"],
        input=json.dumps({"store_root": str(tmp_path), "namespace": "experiment",
                          "supports": [], "artifacts": []}),
        capture_output=True, text=True, check=False, timeout=10,
    )
    assert result.returncode != 0
    assert "private scan outside exact existing experimental store" in result.stderr
    assert "ModuleNotFoundError" not in result.stderr
