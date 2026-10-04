import importlib
import json
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
repair = importlib.import_module("large_scale_repair_freeze_v1")
queue = importlib.import_module("large_scale_queue_v1")


@pytest.mark.parametrize("agent", ["A4", "A5", "A28", "strong-4090"])
def test_worker_repair_changes_only_jetson_decoder_not_surface_or_model_contract(
    tmp_path: Path, agent: str,
) -> None:
    cell = tmp_path / "cell.yaml"
    cell.write_text(yaml.safe_dump({
        "worker_urls": {agent: "http://127.0.0.1:65004"},
        "fresh_worker_stores": {agent: "/synthetic/fresh/store"},
        "model_service_timeout_seconds": 1200,
    }))
    original, new = tmp_path / "original.yaml", tmp_path / "repaired.yaml"
    repair.original_workers.prepare(cell, agent, original)
    repair.prepare(cell, agent, new)
    before, after = yaml.safe_load(original.read_text()), yaml.safe_load(new.read_text())
    if agent != "strong-4090":
        assert after["ffmpeg_executable"] == str(repair.ARM_FFMPEG)
        before["ffmpeg_executable"] = str(repair.ARM_FFMPEG)
    assert before == after
    original_bytes = new.read_bytes()
    with pytest.raises(FileExistsError):
        repair.prepare(cell, agent, new)
    assert new.read_bytes() == original_bytes


def test_pricing_repair_preserves_prices_fx_and_original_but_binds_actual_calculator(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = tmp_path / "app"
    source = app / "src/infra_joint/experiments/api_cost.py"
    source.parent.mkdir(parents=True)
    source.write_text("synthetic exact calculator")
    parent = tmp_path / "preparation/pricing-001/price-freeze.json"
    parent.parent.mkdir(parents=True)
    original = {"version": "synthetic-parent", "formal_runs": 0,
                "prices": {"model": {"input": "12", "output": "36"}},
                "fx": {"date": "frozen", "rate": "1.1225"},
                "calculator_source_sha256": "old-calculator"}
    parent.write_text(json.dumps(original))
    original_bytes = parent.read_bytes()
    monkeypatch.setattr(repair, "PARENT_PRICE_SHA256", repair.sha256(parent))
    repair.prepare_prices(tmp_path, app)
    path, digest = repair.verified_prices(tmp_path, app)
    assert digest == repair.sha256(path)
    new = json.loads(path.read_text())
    assert new["prices"] == original["prices"] and new["fx"] == original["fx"]
    assert new["calculator_source_sha256"] == repair.sha256(source)
    assert new["parent_price_freeze_sha256"] == repair.sha256(parent)
    assert parent.read_bytes() == original_bytes
    with pytest.raises(FileExistsError):
        repair.prepare_prices(tmp_path, app)
    source.write_text("drift")
    with pytest.raises(RuntimeError, match="provenance drift"):
        repair.verified_prices(tmp_path, app)


def test_repaired_freeze_never_accepts_original_freeze_filename(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(queue, "ROOT", tmp_path)
    original = tmp_path / "execution-freeze.json"
    original.write_text('{"original":true}')
    with pytest.raises(RuntimeError, match="new owned namespace"):
        queue.verify_execution_freeze(original)
    assert original.read_text() == '{"original":true}'


def decoder_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "readiness/decoder-repair-validation-001.json"
    path.parent.mkdir()
    row = {"binary_sha256": repair.ARM_FFMPEG_SHA256, "historical_binary_unchanged": True,
           "decoder_probes": {codec: {"returncode": 0, "frames": 1, "jpeg_bytes": 123}
                              for codec in ("h264", "av1")}}
    path.write_text(json.dumps({agent: row for agent in ("A4", "A5", "A28")}))
    monkeypatch.setattr(repair, "DECODER_RECEIPT_SHA256", repair.sha256(path))
    monkeypatch.setattr(repair, "HOSTS", {"A4": "synthetic-host"})


def test_decoder_fingerprint_fail_closed_on_actual_binary_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    decoder_fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(repair, "remote_python", lambda *args: "0" * 64)
    with pytest.raises(RuntimeError, match="binary drift"):
        repair.environment_fingerprint(tmp_path)
    monkeypatch.setattr(repair, "remote_python", lambda *args: repair.ARM_FFMPEG_SHA256)
    assert repair.environment_fingerprint(tmp_path)["binary_sha256"] == {
        "A4": repair.ARM_FFMPEG_SHA256}


def test_decoder_fingerprint_rejects_failed_h264_even_with_matching_binary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    decoder_fixture(tmp_path, monkeypatch)
    path = tmp_path / "readiness/decoder-repair-validation-001.json"
    value = json.loads(path.read_text())
    value["A4"]["decoder_probes"]["h264"]["frames"] = 0
    path.write_text(json.dumps(value))
    monkeypatch.setattr(repair, "DECODER_RECEIPT_SHA256", repair.sha256(path))
    monkeypatch.setattr(repair, "remote_python", lambda *args: repair.ARM_FFMPEG_SHA256)
    with pytest.raises(RuntimeError, match="required codec"):
        repair.environment_fingerprint(tmp_path)
