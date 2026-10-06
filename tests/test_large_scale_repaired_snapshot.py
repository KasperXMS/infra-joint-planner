import importlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
snapshot = importlib.import_module("large_scale_resident_repaired_snapshot_v1")


@pytest.mark.parametrize("disposition", ["valid", "confounder"])
def test_original_source_is_preserved_even_when_retrospectively_confounded(
    disposition: str,
) -> None:
    value = {"run_id": "original", "attempt_index": 1, "disposition": disposition,
             "execution_sha256": snapshot.resident.EXECUTION_FREEZE_SHA256}
    assert snapshot.validate_attempt_source(value, {"original"}) == "original-execution-001"


@pytest.mark.parametrize("index", [1, 2])
def test_never_started_and_affected_only_reruns_use_repaired_source(index: int) -> None:
    value = {"run_id": "new", "attempt_index": index,
             "execution_sha256": snapshot.REPAIR_SHA256}
    assert snapshot.validate_attempt_source(value, {"original"}) == "quote-integrity-repair-002"


@pytest.mark.parametrize("run, digest, index", [
    ("original", snapshot.REPAIR_SHA256, 1),
    ("new", snapshot.resident.EXECUTION_FREEZE_SHA256, 1),
    ("new", "0" * 64, 1),
    ("original", snapshot.resident.EXECUTION_FREEZE_SHA256, 2),
])
def test_source_drift_and_invented_old_retry_rejected(run: str, digest: str, index: int) -> None:
    with pytest.raises(RuntimeError):
        snapshot.validate_attempt_source({"run_id": run, "execution_sha256": digest,
                                          "attempt_index": index}, {"original"})
