import importlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
patch = importlib.import_module("large_scale_resident_E_query_patch_v1")
resident = importlib.import_module("large_scale_resident_queue_v1")


def maps() -> tuple[dict, dict]:
    parent = {"src/infra_joint/worker/server.py": "worker-unchanged",
              patch.SOURCE: "wrong-E", "configs/frozen.yaml": "unchanged"}
    current = {**parent, **{p: "provenance-only" for p in patch.ALLOWED_DELTA},
               patch.SOURCE: patch.SOURCE_SHA256}
    return parent, current


def test_E_repair_allows_only_reviewed_isolation_and_provenance_delta() -> None:
    parent, current = maps()
    assert set(patch.validate_source_delta(parent, current)) == patch.ALLOWED_DELTA
    assert patch.APP_NAME == resident.E_QUERY_APP_NAME
    assert patch.PARENT_APP_NAME == resident.CARDINALITY_APP_NAME
    assert parent[patch.SOURCE] != patch.SOURCE_SHA256


@pytest.mark.parametrize("damage", ["worker", "prompt", "budget", "scheduler", "operator",
                                    "missing", "source"])
def test_E_repair_cannot_smuggle_runtime_or_semantic_tuning(damage: str) -> None:
    parent, current = maps()
    if damage == "missing":
        del current[next(p for p in patch.ALLOWED_DELTA if p != patch.SOURCE)]
    elif damage == "source":
        current[patch.SOURCE] = "other-change"
    else:
        current[{"worker": "src/infra_joint/worker/server.py",
                 "prompt": "scripts/resource_blind_live_validation_v1.py",
                 "budget": "configs/frozen.yaml",
                 "scheduler": "src/infra_joint/control/physical.py",
                 "operator": "src/infra_joint/operators/retrieval.py"}[damage]] = "tuned"
    with pytest.raises(RuntimeError, match="exact audited"):
        patch.validate_source_delta(parent, current)
