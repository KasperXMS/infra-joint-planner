import inspect
import io
from collections.abc import Sequence
from pathlib import Path

import pytest
from PIL import Image
from pydantic import ValidationError

from infra_joint.core.action import SemanticAction
from infra_joint.operators.media import (
    CommandResult,
    FfmpegMediaBackend,
    SampleFramesArguments,
    probe_ffmpeg,
    register_media_operators,
)
from infra_joint.operators.registry import OperatorRegistry
from infra_joint.worker.artifact_store import InMemoryArtifactStore, StoredArtifact


class FakeFfmpegRunner:
    def __init__(self) -> None:
        self.commands: list[tuple[str, ...]] = []

    async def run(self, arguments: Sequence[str], cwd: Path | None = None) -> CommandResult:
        del cwd
        command = tuple(arguments)
        self.commands.append(command)
        if command[-1] == "-version":
            return CommandResult(0, "ffmpeg version test-build\n", "")
        output = Path(command[-1])
        if "%06d" in output.name:
            output.parent.joinpath("frame-000001.jpg").write_bytes(b"frame-one")
            output.parent.joinpath("frame-000002.jpg").write_bytes(b"frame-two")
        else:
            output.write_bytes(b"clip-bytes")
        return CommandResult(0, "", "")


def test_sample_frames_contract_bounds_serializable_fan_out() -> None:
    assert SampleFramesArguments(
        every_seconds=60,
        max_frames=32,
        output_prefix="frames",
    ).max_frames == 32
    with pytest.raises(ValidationError, match="less than or equal to 32"):
        SampleFramesArguments(
            every_seconds=60,
            max_frames=33,
            output_prefix="frames",
        )


@pytest.mark.asyncio
async def test_ffmpeg_probe_executes_version_command() -> None:
    runner = FakeFfmpegRunner()
    capability = await probe_ffmpeg("ffmpeg-test", runner)

    assert capability.available
    assert capability.version == "ffmpeg version test-build"
    assert runner.commands == [("ffmpeg-test", "-version")]


@pytest.mark.asyncio
async def test_ffmpeg_probe_decodes_configured_media_before_exposing_operators(
    tmp_path: Path,
) -> None:
    probe_input = tmp_path / "probe.mp4"
    probe_input.write_bytes(b"benchmark-codec-probe")
    runner = FakeFfmpegRunner()

    capability = await probe_ffmpeg("ffmpeg-test", runner, probe_input=probe_input)

    assert capability.available
    assert runner.commands[0] == ("ffmpeg-test", "-version")
    assert str(probe_input) in runner.commands[1]


@pytest.mark.asyncio
async def test_ffmpeg_probe_fails_closed_when_media_probe_is_missing(tmp_path: Path) -> None:
    capability = await probe_ffmpeg(
        "ffmpeg-test",
        FakeFfmpegRunner(),
        probe_input=tmp_path / "missing.mp4",
    )

    assert not capability.available
    assert "does not exist" in (capability.reason or "")


@pytest.mark.asyncio
async def test_sample_frames_and_extract_clip_register_artifacts() -> None:
    runner = FakeFfmpegRunner()
    backend = FfmpegMediaBackend("ffmpeg-test", runner)
    store = InMemoryArtifactStore((StoredArtifact.create("video", "video/mp4", b"fake-video"),))
    registry = OperatorRegistry()
    register_media_operators(registry, store, backend)

    frame_call = registry.binding("sample_frames").handler(
        SemanticAction(
            operator="sample_frames",
            inputs=("video",),
            arguments={
                "every_seconds": 5,
                "max_frames": 2,
                "output_prefix": "sampled",
            },
        )
    )
    assert inspect.isawaitable(frame_call)
    frame_result = await frame_call
    clip_call = registry.binding("extract_clip").handler(
        SemanticAction(
            operator="extract_clip",
            inputs=("video",),
            arguments={
                "start_seconds": 10,
                "duration_seconds": 3,
                "output_artifact_id": "clip",
            },
        )
    )
    assert inspect.isawaitable(clip_call)
    clip_result = await clip_call

    assert [item["artifact_id"] for item in frame_result["artifacts"]] == [
        "sampled/frame-000001.jpg",
        "sampled/frame-000002.jpg",
    ]
    assert store.get("clip").content == b"clip-bytes"
    assert clip_result["artifact_id"] == "clip"
    sample_command = runner.commands[0]
    assert "fps=1/5" in sample_command
    assert "-frames:v" in sample_command
    assert "2" in sample_command


def _jpeg(width: int, height: int, color: str) -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (width, height), color=color).save(output, format="JPEG")
    return output.getvalue()


def test_contact_sheet_works_without_ffmpeg() -> None:
    store = InMemoryArtifactStore(
        (
            StoredArtifact.create("one", "image/jpeg", _jpeg(100, 50, "red")),
            StoredArtifact.create("two", "image/jpeg", _jpeg(50, 100, "blue")),
        )
    )
    registry = OperatorRegistry()
    register_media_operators(registry, store, media_backend=None)

    result = registry.binding("make_contact_sheet").handler(
        SemanticAction(
            operator="make_contact_sheet",
            inputs=("one", "two"),
            arguments={
                "columns": 2,
                "cell_width": 100,
                "cell_height": 100,
                "output_artifact_id": "sheet",
            },
        )
    )

    assert result["artifact_id"] == "sheet"
    with Image.open(io.BytesIO(store.get("sheet").content)) as sheet:
        assert sheet.size == (200, 100)
    assert set(registry) == {"make_contact_sheet"}
