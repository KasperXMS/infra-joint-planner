from collections.abc import Sequence

from pydantic import Field

from infra_joint.core.base import ContractModel
from infra_joint.heterogeneous.traffic_control import RemoteCommandRunner, TcEndpoint


class GpuDeviceEvidence(ContractModel):
    name: str = Field(min_length=1)
    uuid: str = Field(min_length=1)
    driver_version: str = Field(min_length=1)


class TcReadEvidence(ContractModel):
    agent_id: str = Field(min_length=1)
    interface: str = Field(min_length=1)
    qdisc: str


class HardwarePreflightEvidence(ContractModel):
    rtx_agent_id: str = Field(min_length=1)
    gpus: tuple[GpuDeviceEvidence, ...] = Field(min_length=1)
    tc_read: tuple[TcReadEvidence, ...] = Field(min_length=1)


def parse_nvidia_smi_csv(output: str) -> tuple[GpuDeviceEvidence, ...]:
    devices: list[GpuDeviceEvidence] = []
    for line_number, line in enumerate(output.splitlines(), start=1):
        if not line.strip():
            continue
        fields = [field.strip() for field in line.split(",")]
        if len(fields) != 3 or any(not field for field in fields):
            raise ValueError(f"malformed nvidia-smi CSV on line {line_number}")
        devices.append(
            GpuDeviceEvidence(
                name=fields[0],
                uuid=fields[1],
                driver_version=fields[2],
            )
        )
    if not devices:
        raise ValueError("nvidia-smi returned no GPU devices")
    return tuple(devices)


def require_rtx_4090(devices: Sequence[GpuDeviceEvidence]) -> None:
    normalized = (device.name.casefold().replace(" ", "") for device in devices)
    if not any("rtx4090" in name for name in normalized):
        raise ValueError("RTX 4090 hardware evidence is missing")


async def collect_hardware_preflight_evidence(
    endpoints: Sequence[TcEndpoint],
    rtx_agent_id: str,
    runner: RemoteCommandRunner,
) -> HardwarePreflightEvidence:
    by_agent = {endpoint.agent_id: endpoint for endpoint in endpoints}
    if len(by_agent) != len(endpoints):
        raise ValueError("tc endpoint agent IDs must be unique")
    try:
        rtx = by_agent[rtx_agent_id]
    except KeyError as exc:
        raise ValueError("RTX agent is missing an SSH endpoint") from exc

    gpu_output = await runner.run(
        rtx.ssh_target,
        (
            "nvidia-smi",
            "--query-gpu=name,uuid,driver_version",
            "--format=csv,noheader,nounits",
        ),
    )
    devices = parse_nvidia_smi_csv(gpu_output)
    require_rtx_4090(devices)

    tc_evidence: list[TcReadEvidence] = []
    for endpoint in sorted(endpoints, key=lambda item: item.agent_id):
        qdisc = await runner.run(
            endpoint.ssh_target,
            (
                "sudo",
                "-n",
                "tc",
                "qdisc",
                "show",
                "dev",
                endpoint.interface,
            ),
        )
        tc_evidence.append(
            TcReadEvidence(
                agent_id=endpoint.agent_id,
                interface=endpoint.interface,
                qdisc=qdisc.strip(),
            )
        )
    return HardwarePreflightEvidence(
        rtx_agent_id=rtx_agent_id,
        gpus=devices,
        tc_read=tuple(tc_evidence),
    )
