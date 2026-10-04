import importlib
import json
import sys
from pathlib import Path

import pytest

from infra_joint.agents.context import AgentTaskView
from infra_joint.benchmarks.base import AdaptedExecutionCase
from infra_joint.benchmarks.longbench_v2 import LongBenchV2Sample
from infra_joint.experiments.large_scale_protocol import SelectedTask, validate_task_set

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
selection = importlib.import_module("large_scale_task_selection_v1")
video = importlib.import_module("large_scale_video_sources_v1")


def test_preselected_eighteen_ids_are_distinct_and_history_independent() -> None:
    tasks = [SelectedTask("multihop_rag", identity, position)
             for position, (_, identity, _) in enumerate(selection.MULTIHOP_SELECTION, start=1)]
    tasks += [SelectedTask("longbench_v2", identity, position) for position, (identity, _, _, _)
              in enumerate(selection.LONGBENCH_SELECTION, start=1)]
    tasks += [SelectedTask("video_mme", identity, position)
              for position, (identity, _) in enumerate(video.VIDEO_SELECTION, start=1)]
    assert len(validate_task_set(tasks, e_history_tasks=selection.E_HISTORY)) == 18


def test_unknown_original_source_count_is_not_prepared_container_count() -> None:
    value = selection.source_groups((0,), None)
    assert value["original_document_count"] is None
    assert value["prepared_document_groups"] == 1
    assert "internal source boundaries unknown" in value["boundary_semantics"]
    assert selection.source_groups((0, 5712), 2)["original_document_count"] == 2
    with pytest.raises(RuntimeError, match="Audited original"):
        selection.source_groups((0, 5712), 3)


def test_video_options_preserve_official_text_and_labels() -> None:
    options = selection.original_options(["A. Original first.", "B. Original second."])
    assert [(value.label, value.text) for value in options] == [
        ("A", "Original first."), ("B", "Original second."),
    ]
    with pytest.raises(RuntimeError, match="safely parseable"):
        selection.original_options(["invent a label from prose"])


def test_selection_rejects_local_storage_before_source_or_rules_access(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="4090 preparation root"):
        selection.freeze(tmp_path / "out", tmp_path, tmp_path / "absent-rules")
    assert not (tmp_path / "out").exists()


def test_frozen_task_and_agent_view_are_strictly_reloadable(tmp_path: Path) -> None:
    sample = LongBenchV2Sample(
        sample_id="synthetic", domain="Multi-Document QA", sub_domain="synthetic",
        difficulty="hard", length="medium", question="synthetic query",
        choice_A="first", choice_B="second", choice_C="third", choice_D="fourth",
        answer="A", context="lossless synthetic context\n",
    )
    bundle = selection._longbench_multidoc_bundle(sample, "synthetic-revision", (0,))
    selection.persist_bundle(tmp_path, SelectedTask("longbench_v2", "synthetic", 1),
                             bundle, {"source": "synthetic"}, ("A4",))
    folder = tmp_path / "longbench_v2-1"
    execution = AdaptedExecutionCase.model_validate(json.loads(
        (folder / "execution.json").read_text()))
    agent = AgentTaskView.model_validate(json.loads((folder / "agent-task-view.json").read_text()))
    assert execution == bundle.execution
    assert agent == AgentTaskView.from_contract(bundle.execution.task)
