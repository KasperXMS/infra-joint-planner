"""Focused invariants for the bounded H1/H2 controller and public trial record."""

from scripts.run_hypothesis_cell_v1 import bm25
from scripts.run_hypothesis_feasibility_v1 import H1_ORDER, H2_ORDER, TASKS, public_trial


def test_candidate_ranking_preserves_original_records() -> None:
    records = [
        {"id": "irrelevant", "body": "sports match"},
        {"id": "relevant", "body": "software revenue subscription revenue"},
    ]
    result = bm25(records, "software revenue", 1, "body")
    assert result == [records[1]]
    assert records[1] == {"id": "relevant", "body": "software revenue subscription revenue"}


def test_frozen_order_is_balanced_and_h1_counts_toward_h2() -> None:
    assert len(TASKS) == 2
    assert len(H1_ORDER) == 4
    assert len(H1_ORDER + H2_ORDER) == 16
    for task_index in range(2):
        for workflow in ("G0", "G1"):
            for profile in ("Hslow", "Hfast"):
                assert (
                    sum(row == (task_index, workflow, profile) for row in H1_ORDER + H2_ORDER) == 2
                )


def test_public_trial_excludes_answer_and_evidence_content() -> None:
    raw = {
        "run_id": "trial-1",
        "task_id": TASKS[0],
        "workflow": "G0",
        "profile": "Hfast",
        "answer": "private-answer-sentinel",
        "evidence_ids": ["artifact-1"],
        "error": None,
        "e2e_ms": 400,
        "metrics": {
            "source_actions": [
                {
                    "node": "source-b",
                    "ms": 10,
                    "response_bytes": 500,
                    "secret_text": "private-evidence-sentinel",
                }
            ],
            "transfers": [{"bytes": 100, "ms": 20}],
            "model": {
                "usage": {"prompt_tokens": 20, "completion_tokens": 2},
                "provider_latency_ms": 300,
                "queue_ms": None,
                "cache_state": "unknown",
            },
            "cleanup": [{"status": 200}],
        },
    }
    result = public_trial(raw, {"format_valid": True, "benchmark_score": 1.0, "task_success": True})
    assert result["a4_to_a5_bytes"] == 100
    assert result["a5_to_controller_response_bytes"] == 500
    assert result["cleanup_ok"]
    assert "private-answer-sentinel" not in str(result)
    assert "private-evidence-sentinel" not in str(result)
