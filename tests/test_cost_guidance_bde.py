import importlib
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
bde = importlib.import_module("cost_guidance_bde_v1")


def test_prospective_bde_scope_cap_and_isolated_store_namespaces() -> None:
    protocol = bde.protocol()
    assert protocol["primary_cells"] == 18 and protocol["global_primary_total"] == 34
    assert len(protocol["tasks"]) == 3 and len(bde.CONDITIONS) == 6
    assert not set(bde.TASKS) & set(bde.TRAIN_TASKS)
    stores, ids = set(), set()
    for row in protocol["tasks"]:
        for condition in bde.CONDITIONS:
            cfg = bde.cell_config(
                Path("/home/super/xiaoming/cost-guidance-exploration-v1-bde-test"), row, condition)
            assert cfg["profile_visibility"] == "blind" and cfg["method"] in {"B", "D", "E"}
            assert cfg["run_id"] not in ids
            ids.add(cfg["run_id"])
            for root in cfg["fresh_worker_stores"].values():
                assert cfg["run_id"] in root and root not in stores
                stores.add(root)
    assert len(ids) == 18 and len(stores) == 72


def test_distillation_selects_only_disjoint_prespecified_history_not_scores() -> None:
    selected = {"run_id": "crossbenchmark-v1-longbench-multidoc-financial-fast-blind",
                "evidence_directory": "/owned/history", "score": 0}
    heldout = {"run_id": "crossbenchmark-v1-longbench-multidoc-academic-fast-blind",
               "evidence_directory": "/owned/test", "score": 1}
    with patch.object(bde, "verified_trace", return_value=[]) as read, patch.object(
        bde, "anonymized_cost_trace", return_value={"example_id": "x"},
    ):
        assert bde.distillation_examples({"runs": [selected, heldout]}) == [{"example_id": "x"}]
        assert read.call_count == 1 and read.call_args.args[1] is selected
    with pytest.raises(ValueError, match="empty"):
        bde.distillation_examples({"runs": [heldout]})
