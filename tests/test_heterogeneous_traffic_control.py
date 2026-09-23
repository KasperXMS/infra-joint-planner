import asyncio
from collections.abc import Sequence

import pytest

import infra_joint.heterogeneous.traffic_control as traffic_control_module
from infra_joint.heterogeneous.traffic_control import (
    SshCommandRunner,
    TcController,
    TcEndpoint,
    TcRegime,
    build_tc_command_plan,
)


def endpoint(*, netem: bool = False) -> TcEndpoint:
    return TcEndpoint(
        agent_id="G4090" if netem else "A28",
        ssh_target="super@192.168.0.12" if netem else "edge@192.168.0.128",
        interface="wlp6s0" if netem else "wlP1p1s0",
        address="192.168.0.12" if netem else "192.168.0.128",
        peer_addresses=("192.168.0.104",),
        supports_netem=netem,
    )


def regime() -> TcRegime:
    return TcRegime(
        configuration_id="tc-30mbit-rtt20",
        bandwidth_mbps=30,
        added_rtt_ms=20,
        worker_ports=(9100, 9212),
    )


def test_tc_plan_shapes_only_filtered_experiment_traffic() -> None:
    plan = build_tc_command_plan(endpoint(netem=True), regime())
    flattened = [" ".join(command) for command in plan.apply]

    assert "htb default 10" in flattened[0]
    assert "classid 1:10 htb rate 1000mbit" in flattened[1]
    assert "classid 1:20 htb rate 30mbit ceil 30mbit" in flattened[2]
    assert "burst 1250kb" in flattened[1]
    assert "burst 64kb" in flattened[2]
    assert any("netem delay 20ms" in command for command in flattened)
    assert any("dport 9100" in command for command in flattened)
    assert any("sport 9212" in command for command in flattened)
    assert any("dport 5201" in command for command in flattened)
    assert any("protocol 1" in command for command in flattened)
    assert all("22" not in command.split() for command in flattened)


def test_orin_plan_does_not_request_unavailable_netem() -> None:
    plan = build_tc_command_plan(endpoint(), regime())
    assert not any("netem" in command for command in plan.apply)


class RecordingRunner:
    def __init__(self, *, fail_on_apply: bool = False) -> None:
        self.commands: list[tuple[str, tuple[str, ...]]] = []
        self.fail_on_apply = fail_on_apply
        self.shaped = False

    async def run(self, ssh_target: str, command: Sequence[str]) -> str:
        values = tuple(command)
        self.commands.append((ssh_target, values))
        if self.fail_on_apply and "filter" in values:
            raise RuntimeError("injected apply failure")
        if "replace" in values and "root" in values:
            self.shaped = True
        if "del" in values and "root" in values:
            self.shaped = False
            return ""
        if "show" in values:
            if self.shaped:
                return "qdisc htb 1: root refcnt 2 default 0x10\n"
            return "qdisc mq 0: root\nqdisc fq_codel 0: parent :1\n"
        return ""


@pytest.mark.asyncio
async def test_tc_controller_restores_original_root() -> None:
    runner = RecordingRunner()
    controller = TcController(runner)
    plan = build_tc_command_plan(endpoint(), regime())

    await controller.apply((plan,))
    assert runner.shaped
    await controller.cleanup()

    assert not runner.shaped
    assert any("del" in command for _, command in runner.commands)


@pytest.mark.asyncio
async def test_tc_controller_cleans_up_after_apply_failure() -> None:
    runner = RecordingRunner(fail_on_apply=True)
    controller = TcController(runner)
    plan = build_tc_command_plan(endpoint(), regime())

    with pytest.raises(RuntimeError, match="injected"):
        await controller.apply((plan,))

    assert not runner.shaped


def test_ssh_runner_rejects_nonpositive_timeout() -> None:
    with pytest.raises(ValueError, match="positive"):
        SshCommandRunner(connect_timeout_seconds=0)
    with pytest.raises(ValueError, match="command timeout"):
        SshCommandRunner(command_timeout_seconds=0)


@pytest.mark.asyncio
async def test_ssh_runner_kills_a_command_that_exceeds_total_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class HangingProcess:
        returncode: int | None = None
        killed = False

        async def communicate(self) -> tuple[bytes, bytes]:
            await asyncio.sleep(60)
            return b"", b""

        def kill(self) -> None:
            self.killed = True
            self.returncode = -9

        async def wait(self) -> int:
            return -9

    process = HangingProcess()

    async def create_hanging_process(*args: object, **kwargs: object) -> HangingProcess:
        del args, kwargs
        return process

    monkeypatch.setattr(
        traffic_control_module.asyncio,
        "create_subprocess_exec",
        create_hanging_process,
    )
    runner = SshCommandRunner(command_timeout_seconds=1)

    with pytest.raises(RuntimeError, match="timed out.*after 1s"):
        await runner.run("edge@192.168.0.105", ("rm", "-f", "safe-file"))
    assert process.killed


@pytest.mark.asyncio
async def test_ssh_runner_disables_stdin_and_tty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: tuple[object, ...] = ()

    class CompletedProcess:
        returncode = 0

        async def communicate(self) -> tuple[bytes, bytes]:
            return b"ok", b""

    async def create_completed_process(
        *args: object, **kwargs: object
    ) -> CompletedProcess:
        nonlocal captured
        del kwargs
        captured = args
        return CompletedProcess()

    monkeypatch.setattr(
        traffic_control_module.asyncio,
        "create_subprocess_exec",
        create_completed_process,
    )

    output = await SshCommandRunner().run("edge@192.168.0.105", ("true",))

    assert output == "ok"
    assert "-n" in captured
    assert "-T" in captured
    assert "ConnectionAttempts=1" in captured
