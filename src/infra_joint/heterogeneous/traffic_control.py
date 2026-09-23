import asyncio
import ipaddress
import shlex
from collections.abc import Sequence
from dataclasses import dataclass
from math import ceil
from typing import Protocol

from pydantic import Field, field_validator

from infra_joint.core.base import ContractModel


class TcEndpoint(ContractModel):
    agent_id: str = Field(min_length=1)
    ssh_target: str = Field(pattern=r"^[A-Za-z0-9_.-]+@[A-Za-z0-9_.:-]+$")
    interface: str = Field(pattern=r"^[A-Za-z0-9_.:-]+$")
    address: str
    peer_addresses: tuple[str, ...] = Field(min_length=1)
    supports_netem: bool

    @field_validator("address")
    @classmethod
    def address_is_ipv4(cls, value: str) -> str:
        address = ipaddress.ip_address(value)
        if address.version != 4:
            raise ValueError("tc v1 currently supports IPv4 experiment paths only")
        return value

    @field_validator("peer_addresses")
    @classmethod
    def peers_are_distinct_ipv4(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if len(values) != len(set(values)):
            raise ValueError("tc peer addresses must be unique")
        for value in values:
            if ipaddress.ip_address(value).version != 4:
                raise ValueError("tc v1 currently supports IPv4 experiment paths only")
        return values


class TcRegime(ContractModel):
    configuration_id: str = Field(min_length=1)
    bandwidth_mbps: float = Field(gt=0)
    added_rtt_ms: float = Field(ge=0)
    worker_ports: tuple[int, ...] = Field(min_length=1)
    iperf_port: int = Field(default=5201, ge=1, le=65535)

    @field_validator("worker_ports")
    @classmethod
    def ports_are_unique(cls, values: tuple[int, ...]) -> tuple[int, ...]:
        if len(values) != len(set(values)):
            raise ValueError("tc worker ports must be unique")
        if any(value < 1 or value > 65535 for value in values):
            raise ValueError("tc worker ports must be valid TCP ports")
        return values


class TcCommandPlan(ContractModel):
    endpoint: TcEndpoint
    regime: TcRegime
    apply: tuple[tuple[str, ...], ...]
    inspect: tuple[str, ...]
    cleanup: tuple[str, ...]


def build_tc_command_plan(endpoint: TcEndpoint, regime: TcRegime) -> TcCommandPlan:
    """Build narrowly filtered data-plane shaping commands.

    Every unmatched packet remains on a 1 Gbps default HTB class, above the
    physical Wi-Fi capacity. NETEM is installed only on the designated endpoint;
    the v1 topology uses the 4090
    egress to add one full round-trip delay because the Orin kernel lacks NETEM.
    """

    device = endpoint.interface
    # Bound HTB's initial token credit to roughly 10 ms of configured traffic
    # (with a 64 KiB floor for low rates). A fixed multi-megabyte burst makes
    # the 8 MiB calibration point largely bypass low-bandwidth regimes.
    default_burst_kib = max(64, ceil(1000 * 1.25))
    shaped_burst_kib = max(64, ceil(regime.bandwidth_mbps * 1.25))
    apply: list[tuple[str, ...]] = [
        (
            "sudo",
            "-n",
            "tc",
            "qdisc",
            "replace",
            "dev",
            device,
            "root",
            "handle",
            "1:",
            "htb",
            "default",
            "10",
        ),
        (
            "sudo",
            "-n",
            "tc",
            "class",
            "replace",
            "dev",
            device,
            "parent",
            "1:",
            "classid",
            "1:10",
            "htb",
            "rate",
            "1000mbit",
            "ceil",
            "1000mbit",
            "burst",
            f"{default_burst_kib}kb",
        ),
        (
            "sudo",
            "-n",
            "tc",
            "class",
            "replace",
            "dev",
            device,
            "parent",
            "1:",
            "classid",
            "1:20",
            "htb",
            "rate",
            f"{regime.bandwidth_mbps:g}mbit",
            "ceil",
            f"{regime.bandwidth_mbps:g}mbit",
            "burst",
            f"{shaped_burst_kib}kb",
        ),
    ]
    if endpoint.supports_netem and regime.added_rtt_ms > 0:
        apply.append(
            (
                "sudo",
                "-n",
                "tc",
                "qdisc",
                "replace",
                "dev",
                device,
                "parent",
                "1:20",
                "handle",
                "20:",
                "netem",
                "delay",
                f"{regime.added_rtt_ms:g}ms",
            )
        )

    for peer in endpoint.peer_addresses:
        peer_cidr = f"{peer}/32"
        apply.append(_u32_filter(device, peer_cidr, ("protocol", "1", "0xff")))
        for port in (*regime.worker_ports, regime.iperf_port):
            apply.append(
                _u32_filter(
                    device,
                    peer_cidr,
                    ("protocol", "6", "0xff"),
                    ("sport", str(port), "0xffff"),
                )
            )
            apply.append(
                _u32_filter(
                    device,
                    peer_cidr,
                    ("protocol", "6", "0xff"),
                    ("dport", str(port), "0xffff"),
                )
            )
    return TcCommandPlan(
        endpoint=endpoint,
        regime=regime,
        apply=tuple(apply),
        inspect=("sudo", "-n", "tc", "-s", "qdisc", "show", "dev", device),
        cleanup=("sudo", "-n", "tc", "qdisc", "del", "dev", device, "root"),
    )


def _u32_filter(
    device: str,
    peer_cidr: str,
    *matches: tuple[str, str, str],
) -> tuple[str, ...]:
    command = [
        "sudo",
        "-n",
        "tc",
        "filter",
        "add",
        "dev",
        device,
        "protocol",
        "ip",
        "parent",
        "1:",
        "prio",
        "10",
        "u32",
        "match",
        "ip",
        "dst",
        peer_cidr,
    ]
    for field, value, mask in matches:
        command.extend(("match", "ip", field, value, mask))
    command.extend(("flowid", "1:20"))
    return tuple(command)


class RemoteCommandRunner(Protocol):
    async def run(self, ssh_target: str, command: Sequence[str]) -> str: ...


@dataclass(frozen=True, slots=True)
class AppliedTcState:
    endpoint: TcEndpoint
    original_qdisc: str
    shaped_qdisc: str


class TcController:
    """Apply tc plans transactionally and restore the observed default root."""

    def __init__(self, runner: RemoteCommandRunner) -> None:
        self._runner = runner
        self._applied: list[tuple[TcCommandPlan, AppliedTcState]] = []

    async def apply(self, plans: Sequence[TcCommandPlan]) -> tuple[AppliedTcState, ...]:
        if self._applied:
            raise RuntimeError("tc controller already has an active configuration")
        try:
            for plan in plans:
                original = await self._runner.run(
                    plan.endpoint.ssh_target,
                    ("sudo", "-n", "tc", "qdisc", "show", "dev", plan.endpoint.interface),
                )
                _validate_restorable_root(original)
                # Root replacement is atomic. Track it only after that first
                # mutation succeeds; all later partial failures are restored.
                await self._runner.run(plan.endpoint.ssh_target, plan.apply[0])
                self._applied.append((plan, AppliedTcState(plan.endpoint, original, "")))
                for command in plan.apply[1:]:
                    await self._runner.run(plan.endpoint.ssh_target, command)
                shaped = await self._runner.run(plan.endpoint.ssh_target, plan.inspect)
                if "qdisc htb 1: root" not in shaped:
                    raise RuntimeError(f"tc root verification failed on {plan.endpoint.agent_id}")
                state = AppliedTcState(plan.endpoint, original, shaped)
                self._applied[-1] = (plan, state)
        except BaseException:
            await self.cleanup()
            raise
        return tuple(state for _, state in self._applied)

    async def cleanup(self) -> None:
        errors: list[str] = []
        for plan, state in reversed(self._applied):
            try:
                await self._runner.run(plan.endpoint.ssh_target, plan.cleanup)
                restored = await self._runner.run(
                    plan.endpoint.ssh_target,
                    ("sudo", "-n", "tc", "qdisc", "show", "dev", plan.endpoint.interface),
                )
                expected = _root_kind(state.original_qdisc)
                if _root_kind(restored) != expected:
                    raise RuntimeError(f"expected root {expected}, observed {_root_kind(restored)}")
            except BaseException as exc:  # noqa: BLE001 - cleanup must attempt every endpoint
                errors.append(f"{plan.endpoint.agent_id}: {exc}")
        self._applied.clear()
        if errors:
            raise RuntimeError(f"tc cleanup failed: {'; '.join(errors)}")


class SshCommandRunner:
    def __init__(
        self,
        *,
        connect_timeout_seconds: int = 5,
        command_timeout_seconds: int = 60,
    ) -> None:
        if connect_timeout_seconds < 1:
            raise ValueError("SSH connect timeout must be positive")
        if command_timeout_seconds < 1:
            raise ValueError("SSH command timeout must be positive")
        self._connect_timeout_seconds = connect_timeout_seconds
        self._command_timeout_seconds = command_timeout_seconds

    async def run(self, ssh_target: str, command: Sequence[str]) -> str:
        remote_command = shlex.join(command)
        process = await asyncio.create_subprocess_exec(
            "ssh",
            "-n",
            "-T",
            "-o",
            "BatchMode=yes",
            "-o",
            f"ConnectTimeout={self._connect_timeout_seconds}",
            "-o",
            "ConnectionAttempts=1",
            ssh_target,
            remote_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=self._command_timeout_seconds
            )
        except TimeoutError as exc:
            process.kill()
            await process.wait()
            raise RuntimeError(
                f"remote command timed out on {ssh_target} after "
                f"{self._command_timeout_seconds}s"
            ) from exc
        if process.returncode != 0:
            message = stderr.decode("utf-8", errors="replace").strip()
            raise RuntimeError(
                f"remote command failed on {ssh_target} ({process.returncode}): {message}"
            )
        return stdout.decode("utf-8", errors="strict")


def _validate_restorable_root(qdisc: str) -> None:
    kind = _root_kind(qdisc)
    if kind not in {"mq", "noqueue"}:
        raise RuntimeError(f"unsupported original root qdisc: {kind}")
    if "netem" in qdisc or "tbf" in qdisc or "htb 1:" in qdisc:
        raise RuntimeError("refusing to overwrite an existing shaped tc configuration")


def _root_kind(qdisc: str) -> str:
    roots = [line.split() for line in qdisc.splitlines() if " root" in line]
    if len(roots) != 1 or len(roots[0]) < 2 or roots[0][0] != "qdisc":
        raise RuntimeError("could not identify exactly one root qdisc")
    return roots[0][1]
