import json
from types import SimpleNamespace

import pytest
import yaml

from scripts import lightweight_planner_tc_v1 as tc


@pytest.mark.asyncio
@pytest.mark.parametrize("fail_apply", [True, False])
async def test_partial_apply_or_cell_failure_restores_touched_network(
    tmp_path, monkeypatch, fail_apply
):
    config = tmp_path / "cell.yaml"
    config.write_text(
        yaml.safe_dump(
            {
                "run_id": "test",
                "worker_urls": {"A4": "http://node:62004"},
                "network": {"bandwidth_mbps": 100, "added_rtt_ms": 5},
            }
        )
    )
    endpoints = tmp_path / "endpoints.yaml"
    endpoints.write_text(
        yaml.safe_dump(
            {
                "tc_endpoints": [
                    {
                        "agent_id": "A4",
                        "ssh_target": "edge@node",
                        "interface": "eth0",
                        "address": "192.168.0.104",
                        "peer_addresses": ["192.168.0.12"],
                        "supports_netem": False,
                    }
                ]
            }
        )
    )
    active = False
    cleaned = []

    class Runner:
        def __init__(self, **_kwargs):
            pass

        async def run(self, target, command):
            nonlocal active
            if "del" in command:
                cleaned.append(target)
                active = False
            return "qdisc htb 1: root\n" if active else "qdisc noqueue 0: root\n"

    async def apply(_target, _commands):
        nonlocal active
        active = True
        if fail_apply:
            raise RuntimeError("partial apply")

    async def cell(_args):
        raise RuntimeError("cell failure")

    monkeypatch.setattr(tc, "SshCommandRunner", Runner)
    monkeypatch.setattr(tc, "batch_remote", apply)
    with pytest.raises(RuntimeError):
        await tc.run_shaped(
            SimpleNamespace(config=config, endpoint_config=endpoints, output=tmp_path), cell
        )
    record = json.loads((tmp_path / "tc-attestation.json").read_text())
    assert cleaned == ["edge@node"]
    assert record["restored_qdisc"] == record["original_qdisc"]
    assert record["cleanup_error"] is None
