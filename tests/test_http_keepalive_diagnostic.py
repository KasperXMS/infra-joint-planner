import json
import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
import diagnose_http_keepalive_v1 as diagnostic  # noqa: E402


@pytest.mark.asyncio
async def test_transport_diagnostic_only_returns_fixed_health_payload() -> None:
    sent: list[dict[str, Any]] = []

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    await diagnostic.healthy_app({"type": "http"}, None, send)
    assert sent[0]["status"] == 200
    assert json.loads(sent[1]["body"]) == {"healthy": True}
    with pytest.raises(ValueError, match="HTTP-only"):
        await diagnostic.healthy_app({"type": "websocket"}, None, send)


@pytest.mark.asyncio
async def test_diagnostic_preserves_existing_evidence_before_any_probe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "diagnostic.json"
    output.write_text("retained")
    monkeypatch.setattr(sys, "argv", ["diagnostic", "--output", str(output)])
    with pytest.raises(FileExistsError, match="not be overwritten"):
        await diagnostic.main()
    assert output.read_text() == "retained"


@pytest.mark.asyncio
async def test_counterexample_is_labeled_not_historical_root_cause_or_formal_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "diagnostic.json"
    values: list[float] = []

    async def probe(*, client_expiry: float) -> dict[str, Any]:
        values.append(client_expiry)
        return {"second_request": "RemoteProtocolError" if client_expiry == 5 else "PASS"}

    monkeypatch.setattr(diagnostic, "probe_pair", probe)
    monkeypatch.setattr(sys, "argv", ["diagnostic", "--output", str(output)])
    await diagnostic.main()
    result = json.loads(output.read_text())
    assert values == [5, 4]
    assert result["benchmark_calls"] == result["model_calls"] == result["formal_attempts"] == 0
    assert result["real_network_shaping"] is False
    assert "not historical root-cause proof" in result["classification"]
