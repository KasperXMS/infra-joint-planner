import importlib
import io
from pathlib import Path

import pytest
from PIL import Image

from infra_joint.worker.model_backend import ModelInputLimitError, preflight_model_request


def test_calibration_is_deterministic_and_matches_frozen_preflight(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts"))
    calibration = importlib.import_module("resident_model_pool_calibration_v1")
    probes = calibration.fixtures()
    assert probes == calibration.fixtures()
    assert [name for name, _ in probes] == [
        "setup-load-text", "warm-text-envelope", "warm-image-frame", "warm-image-sheet",
    ]
    for _, request in probes:
        assert request.max_output_tokens == 2048
        estimated = preflight_model_request(
            request, modalities=frozenset({"text", "image"}), context_window=32768,
            reserved_output_tokens=2048, image_token_cost=2048,
        )
        assert estimated + 2048 <= 32768
    assert 30000 <= preflight_model_request(
        probes[1][1], modalities=frozenset({"text", "image"}), context_window=32768,
        reserved_output_tokens=2048, image_token_cost=2048,
    ) < 30720
    with pytest.raises(ModelInputLimitError):
        preflight_model_request(
            probes[1][1], modalities=frozenset({"text", "image"}), context_window=32768,
            reserved_output_tokens=4096, image_token_cost=2048,
        )


@pytest.mark.asyncio
async def test_calibration_refuses_the_development_pc(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts"))
    calibration = importlib.import_module("resident_model_pool_calibration_v1")
    monkeypatch.setattr(calibration.sys, "platform", "win32")
    with pytest.raises(RuntimeError, match="remote experiment nodes"):
        await calibration.calibrate("strong-4090")


@pytest.mark.asyncio
async def test_calibration_refuses_unsafe_evidence_namespace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts"))
    calibration = importlib.import_module("resident_model_pool_calibration_v1")
    monkeypatch.setattr(calibration.sys, "platform", "linux")
    with pytest.raises(ValueError, match="evidence namespace"):
        await calibration.calibrate("strong-4090", attempt="../../old-evidence")


def test_image_boundary_uses_runtime_pixel_envelope_not_parameter_size(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts"))
    calibration = importlib.import_module("resident_model_pool_calibration_v1")
    probes = calibration.fixtures("image-boundary")
    assert len(probes) == 1
    _, request = probes[0]
    with Image.open(io.BytesIO(request.artifacts[0].content)) as image:
        assert image.size == (2048, 2048)
    assert preflight_model_request(
        request, modalities=frozenset({"text", "image"}), context_window=32768,
        reserved_output_tokens=2048, image_token_cost=4096,
    ) == len(request.prompt.encode()) + 4096
    with pytest.raises(ValueError, match="unknown calibration"):
        calibration.fixtures("benchmark-gold")
