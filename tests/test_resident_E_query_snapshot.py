import importlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
collector = importlib.import_module("large_scale_resident_E_query_snapshot_v1")


@pytest.mark.parametrize("sequence,epoch", [(1, 1), (170, 1), (171, 2), (228, 2), (229, 3),
                                           (260, 3), (261, 3), (290, 4), (600, 4)])
def test_all_four_execution_epochs_are_bound_to_actual_original_prefix(sequence, epoch) -> None:
    row = {"event": "reserved", "sequence": sequence,
           "execution_sha256": collector.EXECUTIONS[epoch]}
    assert collector.epoch_for(row) == epoch
    row["execution_sha256"] = collector.EXECUTIONS[epoch % 4 + 1]
    with pytest.raises(RuntimeError, match="actual durable"):
        collector.epoch_for(row)


def test_metadata_or_fake_admission_cannot_reassign_an_execution_epoch() -> None:
    with pytest.raises(RuntimeError, match="actual durable reservations"):
        collector.epoch_for({"event": "settled", "sequence": 291,
                             "execution_sha256": collector.EXECUTIONS[4]})
