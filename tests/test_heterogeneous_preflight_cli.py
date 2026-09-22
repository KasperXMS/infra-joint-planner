import argparse
import json
from collections.abc import Sequence
from hashlib import sha256

import httpx
import pytest

import scripts.heterogeneous_v1 as cli
from infra_joint.heterogeneous.hardware import (
    collect_hardware_preflight_evidence,
    parse_nvidia_smi_csv,
    require_rtx_4090,
)
from infra_joint.heterogeneous.traffic_control import TcEndpoint


class FakeSshRunner:
    def __init__(self) -> None:
        self.commands: list[tuple[str, tuple[str, ...]]] = []

    async def run(self, ssh_target: str, command: Sequence[str]) -> str:
        normalized = tuple(command)
        self.commands.append((ssh_target, normalized))
        if normalized[0] == "nvidia-smi":
            return (
                "NVIDIA GeForce RTX 4090, GPU-a, 580.82.09\n"
                "NVIDIA GeForce RTX 4090, GPU-b, 580.82.09\n"
            )
        return "qdisc mq 0: root\n"


def endpoint(agent_id: str, host: str) -> TcEndpoint:
    return TcEndpoint(
        agent_id=agent_id,
        ssh_target=f"test@{host}",
        interface="eth0",
        address=host,
        peer_addresses=("192.0.2.30",),
        supports_netem=agent_id == "strong-4090",
    )


def config_dict() -> dict[str, object]:
    replica_common = {
        "checkpoint_id": "qwen3-vl",
        "checkpoint_fingerprint": "sha256:model",
        "quantization": "q4_k_m",
        "runtime": "ollama",
        "runtime_version": "0.12.3",
        "context_window": 32768,
        "max_output_tokens": 1024,
        "prompt_template_id": "chatml-v1",
        "generation_config_id": "greedy-v1",
    }
    return {
        "environment": {
            "agents": [
                {
                    "agent_id": "A28",
                    "device": "AGX Orin",
                    "capabilities": ["model"],
                },
                {
                    "agent_id": "strong-4090",
                    "device": "2x RTX 4090",
                    "capabilities": ["model"],
                },
            ],
            "deployments": [
                {
                    "deployment_id": "orin-replica",
                    "agent_id": "A28",
                    "model_id": "qwen3-vl",
                    "modalities": ["text", "image"],
                    "context_window": 32768,
                    "reserved_output_tokens": 1024,
                },
                {
                    "deployment_id": "rtx-replica",
                    "agent_id": "strong-4090",
                    "model_id": "qwen3-vl",
                    "modalities": ["text", "image"],
                    "context_window": 32768,
                    "reserved_output_tokens": 1024,
                },
            ],
        },
        "worker_urls": {
            "A28": "http://192.0.2.28:9100",
            "strong-4090": "http://192.0.2.29:9100",
        },
        "equivalent_replicas": {
            "logical_model_id": "qwen3-vl-equivalent",
            "canonical_deployment_id": "orin-replica",
            "replicas": [
                {
                    "replica_id": "orin",
                    "agent_id": "A28",
                    "deployment_id": "orin-replica",
                    **replica_common,
                },
                {
                    "replica_id": "rtx",
                    "agent_id": "strong-4090",
                    "deployment_id": "rtx-replica",
                    **replica_common,
                },
            ],
        },
        "required_agent_ids": ["A28", "strong-4090"],
        "rtx_agent_id": "strong-4090",
        "tc_endpoints": [
            endpoint("A28", "192.0.2.28").model_dump(mode="json"),
            endpoint("strong-4090", "192.0.2.29").model_dump(mode="json"),
        ],
    }


def test_hard_preflight_config_parses_frozen_v1_surface(tmp_path) -> None:
    path = tmp_path / "v1.yaml"
    import yaml

    path.write_text(yaml.safe_dump(config_dict()), encoding="utf-8")
    parsed = cli._operational_preflight_config(path)

    assert set(parsed.worker_urls) == {"A28", "strong-4090"}
    assert parsed.equivalent_replicas.canonical_deployment_id == "orin-replica"
    assert parsed.artifact_probe.mode == cli.ArtifactProbeMode.EXISTING


def test_hard_preflight_config_requires_explicit_namespaced_write_ack() -> None:
    raw = config_dict()
    raw["artifact_probe"] = {"mode": "deterministic_namespaced"}

    with pytest.raises(ValueError, match="allow_namespaced_write"):
        cli.OperationalPreflightConfig.model_validate(raw)


def test_nvidia_smi_parser_requires_real_rtx_4090_evidence() -> None:
    devices = parse_nvidia_smi_csv(
        "NVIDIA GeForce RTX 4090, GPU-123, 580.82.09\n"
    )
    require_rtx_4090(devices)

    with pytest.raises(ValueError, match="RTX 4090"):
        require_rtx_4090(
            parse_nvidia_smi_csv("NVIDIA A100, GPU-other, 580.82.09\n")
        )


@pytest.mark.asyncio
async def test_hardware_preflight_is_read_only_and_checks_tc_on_every_endpoint() -> None:
    endpoints = (
        endpoint("A28", "192.0.2.28"),
        endpoint("strong-4090", "192.0.2.29"),
    )
    runner = FakeSshRunner()

    evidence = await collect_hardware_preflight_evidence(
        endpoints, "strong-4090", runner
    )

    assert len(evidence.gpus) == 2
    assert {item.agent_id for item in evidence.tc_read} == {"A28", "strong-4090"}
    assert runner.commands[0][1][0] == "nvidia-smi"
    tc_commands = [command for _, command in runner.commands if command[0] == "sudo"]
    assert tc_commands == [
        ("sudo", "-n", "tc", "qdisc", "show", "dev", "eth0"),
        ("sudo", "-n", "tc", "qdisc", "show", "dev", "eth0"),
    ]
    assert all("replace" not in command and "del" not in command for command in tc_commands)


@pytest.mark.asyncio
async def test_artifact_get_probe_verifies_body_header_and_media_type() -> None:
    content = b"existing artifact"
    checksum = sha256(content).hexdigest()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/artifact/evidence"
        return httpx.Response(
            200,
            content=content,
            headers={
                "content-type": "text/plain",
                "x-artifact-sha256": checksum,
            },
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="http://worker.test",
    ) as client:
        evidence = await cli._get_and_validate_artifact(
            "A28",
            "evidence",
            "text/plain",
            len(content),
            checksum,
            client,
            cli.ArtifactProbeMode.EXISTING,
        )

    assert evidence.sha256_hex == checksum
    assert evidence.probe_mode == cli.ArtifactProbeMode.EXISTING


def test_hard_preflight_cli_failure_is_machine_readable(monkeypatch, capsys) -> None:
    async def fail(_: argparse.Namespace) -> None:
        raise RuntimeError("injected preflight failure")

    monkeypatch.setattr(cli, "_hard_preflight", fail)
    monkeypatch.setattr(
        "sys.argv",
        ["heterogeneous_v1.py", "hard-preflight", "--config", "unused.yaml"],
    )

    with pytest.raises(SystemExit) as raised:
        cli.main()

    assert raised.value.code == 1
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "failed"
    assert output["error"] == {
        "type": "RuntimeError",
        "message": "injected preflight failure",
    }
