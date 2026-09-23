import asyncio
import io
import math
import shutil
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from PIL import Image
from pydantic import Field

from infra_joint.core.action import SemanticAction
from infra_joint.core.base import ContractModel
from infra_joint.operators.artifacts import ProducedArtifact
from infra_joint.operators.registry import OperatorRegistry, OperatorSpec
from infra_joint.worker.artifact_store import ArtifactStore, StoredArtifact


class MediaExecutionError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class CommandResult:
    return_code: int
    stdout: str
    stderr: str


class AsyncCommandRunner(Protocol):
    async def run(self, arguments: Sequence[str], cwd: Path | None = None) -> CommandResult: ...


class SubprocessCommandRunner:
    async def run(self, arguments: Sequence[str], cwd: Path | None = None) -> CommandResult:
        process = await asyncio.create_subprocess_exec(
            *arguments,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        return CommandResult(
            return_code=process.returncode or 0,
            stdout=stdout.decode("utf-8", errors="replace"),
            stderr=stderr.decode("utf-8", errors="replace"),
        )


@dataclass(frozen=True, slots=True)
class FfmpegCapability:
    available: bool
    executable: str | None
    version: str | None
    reason: str | None = None


async def probe_ffmpeg(
    executable: str | None = None,
    runner: AsyncCommandRunner | None = None,
    *,
    probe_input: Path | None = None,
) -> FfmpegCapability:
    resolved = executable or shutil.which("ffmpeg")
    if resolved is None:
        return FfmpegCapability(False, None, None, "ffmpeg executable was not found")
    command_runner = runner or SubprocessCommandRunner()
    try:
        result = await command_runner.run((resolved, "-version"))
    except OSError as exc:
        return FfmpegCapability(False, resolved, None, str(exc))
    if result.return_code != 0:
        return FfmpegCapability(False, resolved, None, result.stderr.strip())
    first_line = result.stdout.splitlines()[0] if result.stdout.splitlines() else ""
    if not first_line.casefold().startswith("ffmpeg version"):
        return FfmpegCapability(False, resolved, None, "unexpected ffmpeg version output")
    if probe_input is not None:
        if not probe_input.is_file():
            return FfmpegCapability(
                False,
                resolved,
                first_line,
                f"ffmpeg probe input does not exist: {probe_input}",
            )
        with tempfile.TemporaryDirectory(prefix="infra-joint-ffmpeg-probe-") as temp:
            output_pattern = Path(temp) / "frame-%06d.jpg"
            probe_result = await command_runner.run(
                (
                    resolved,
                    "-nostdin",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-i",
                    str(probe_input),
                    "-frames:v",
                    "1",
                    "-q:v",
                    "2",
                    "-y",
                    str(output_pattern),
                )
            )
            frame = Path(temp) / "frame-000001.jpg"
            if probe_result.return_code != 0 or not frame.is_file() or frame.stat().st_size == 0:
                detail = probe_result.stderr.strip()[-1000:]
                return FfmpegCapability(
                    False,
                    resolved,
                    first_line,
                    f"ffmpeg media decode probe failed: {detail or 'no frame produced'}",
                )
    return FfmpegCapability(True, resolved, first_line)


class MediaBackend(Protocol):
    async def sample_frames(
        self,
        input_path: Path,
        output_pattern: Path,
        *,
        every_seconds: float,
        max_frames: int,
    ) -> None: ...

    async def extract_clip(
        self,
        input_path: Path,
        output_path: Path,
        *,
        start_seconds: float,
        duration_seconds: float,
    ) -> None: ...


class FfmpegMediaBackend:
    def __init__(
        self,
        executable: str,
        runner: AsyncCommandRunner | None = None,
    ) -> None:
        self._executable = executable
        self._runner = runner or SubprocessCommandRunner()

    async def sample_frames(
        self,
        input_path: Path,
        output_pattern: Path,
        *,
        every_seconds: float,
        max_frames: int,
    ) -> None:
        await self._execute(
            (
                self._executable,
                "-nostdin",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(input_path),
                "-vf",
                f"fps=1/{every_seconds:g}",
                "-frames:v",
                str(max_frames),
                "-q:v",
                "2",
                "-y",
                str(output_pattern),
            )
        )

    async def extract_clip(
        self,
        input_path: Path,
        output_path: Path,
        *,
        start_seconds: float,
        duration_seconds: float,
    ) -> None:
        await self._execute(
            (
                self._executable,
                "-nostdin",
                "-hide_banner",
                "-loglevel",
                "error",
                "-ss",
                f"{start_seconds:g}",
                "-i",
                str(input_path),
                "-t",
                f"{duration_seconds:g}",
                "-map",
                "0:v:0",
                "-map",
                "0:a?",
                "-c",
                "copy",
                "-y",
                str(output_path),
            )
        )

    async def _execute(self, arguments: Sequence[str]) -> None:
        result = await self._runner.run(arguments)
        if result.return_code != 0:
            detail = result.stderr.strip()[-2000:]
            raise MediaExecutionError(f"ffmpeg failed: {detail}")


class SampleFramesArguments(ContractModel):
    every_seconds: float = Field(gt=0, le=3600)
    max_frames: int = Field(default=16, gt=0, le=32)
    output_prefix: str = Field(min_length=1)


class ExtractClipArguments(ContractModel):
    start_seconds: float = Field(ge=0)
    duration_seconds: float = Field(gt=0, le=36000)
    output_artifact_id: str = Field(min_length=1)


class ContactSheetArguments(ContractModel):
    columns: int = Field(default=4, ge=1, le=8)
    cell_width: int = Field(default=320, ge=64, le=2048)
    cell_height: int = Field(default=180, ge=64, le=2048)
    output_artifact_id: str = Field(min_length=1)


def media_operator_specs() -> tuple[OperatorSpec, ...]:
    one_video = {
        "type": "array",
        "items": {"type": "string"},
        "minItems": 1,
        "maxItems": 1,
    }
    return (
        OperatorSpec(
            operator_id="sample_frames",
            description=(
                "Sample up to max_frames video frames at a fixed interval. This does not "
                "summarize the video. The plan must declare exactly max_frames outputs named "
                "output_prefix/frame-000001.jpg through output_prefix/frame-NNNNNN.jpg."
            ),
            input_schema=one_video,
            argument_schema=SampleFramesArguments.model_json_schema(),
            output_schema={"type": "array", "items": {"$ref": "ProducedArtifact"}},
            capability_requirements=frozenset({"media.ffmpeg"}),
        ),
        OperatorSpec(
            operator_id="extract_clip",
            description="Extract a temporal clip from a video artifact.",
            input_schema=one_video,
            argument_schema=ExtractClipArguments.model_json_schema(),
            output_schema={"$ref": "ProducedArtifact"},
            capability_requirements=frozenset({"media.ffmpeg"}),
        ),
        OperatorSpec(
            operator_id="make_contact_sheet",
            description=(
                "Arrange every supplied image artifact into one deterministic JPEG contact "
                "sheet; inputs must be the concrete frame artifact IDs, not a frame-set alias."
            ),
            input_schema={
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
                "maxItems": 64,
            },
            argument_schema=ContactSheetArguments.model_json_schema(),
            output_schema={"$ref": "ProducedArtifact"},
            capability_requirements=frozenset({"media.image"}),
        ),
    )


def _metadata(artifact: StoredArtifact) -> ProducedArtifact:
    return ProducedArtifact(
        artifact_id=artifact.artifact_id,
        media_type=artifact.media_type,
        size_bytes=len(artifact.content),
        sha256_hex=artifact.sha256_hex,
    )


def _video_input(store: ArtifactStore, action: SemanticAction) -> StoredArtifact:
    if len(action.inputs) != 1:
        raise ValueError(f"{action.operator} requires exactly one video input")
    artifact = store.get(action.inputs[0])
    if not artifact.media_type.startswith("video/"):
        raise ValueError(f"input artifact is not video: {artifact.artifact_id}")
    return artifact


def register_media_operators(
    registry: OperatorRegistry,
    store: ArtifactStore,
    media_backend: MediaBackend | None,
) -> None:
    specs = {spec.operator_id: spec for spec in media_operator_specs()}

    async def sample_frames(action: SemanticAction) -> dict[str, Any]:
        if media_backend is None:
            raise MediaExecutionError("ffmpeg capability is unavailable")
        arguments = SampleFramesArguments.model_validate(action.arguments)
        source = _video_input(store, action)
        with tempfile.TemporaryDirectory(prefix="infra-joint-media-") as temp:
            directory = Path(temp)
            input_path = directory / "input.mp4"
            output_pattern = directory / "frame-%06d.jpg"
            input_path.write_bytes(source.content)
            await media_backend.sample_frames(
                input_path,
                output_pattern,
                every_seconds=arguments.every_seconds,
                max_frames=arguments.max_frames,
            )
            produced: list[ProducedArtifact] = []
            for index, frame_path in enumerate(sorted(directory.glob("frame-*.jpg")), start=1):
                artifact = StoredArtifact.create(
                    f"{arguments.output_prefix}/frame-{index:06d}.jpg",
                    "image/jpeg",
                    frame_path.read_bytes(),
                )
                store.put(artifact)
                produced.append(_metadata(artifact))
        if not produced:
            raise MediaExecutionError("ffmpeg produced no frames")
        return {"artifacts": [item.model_dump() for item in produced]}

    async def extract_clip(action: SemanticAction) -> dict[str, Any]:
        if media_backend is None:
            raise MediaExecutionError("ffmpeg capability is unavailable")
        arguments = ExtractClipArguments.model_validate(action.arguments)
        source = _video_input(store, action)
        with tempfile.TemporaryDirectory(prefix="infra-joint-media-") as temp:
            directory = Path(temp)
            input_path = directory / "input.mp4"
            output_path = directory / "clip.mp4"
            input_path.write_bytes(source.content)
            await media_backend.extract_clip(
                input_path,
                output_path,
                start_seconds=arguments.start_seconds,
                duration_seconds=arguments.duration_seconds,
            )
            if not output_path.is_file() or output_path.stat().st_size == 0:
                raise MediaExecutionError("ffmpeg produced no clip")
            artifact = StoredArtifact.create(
                arguments.output_artifact_id,
                "video/mp4",
                output_path.read_bytes(),
            )
            store.put(artifact)
        return _metadata(artifact).model_dump()

    def make_contact_sheet(action: SemanticAction) -> dict[str, Any]:
        arguments = ContactSheetArguments.model_validate(action.arguments)
        if not action.inputs or len(action.inputs) > 64:
            raise ValueError("make_contact_sheet requires between 1 and 64 images")
        images: list[Image.Image] = []
        for artifact_id in action.inputs:
            artifact = store.get(artifact_id)
            if not artifact.media_type.startswith("image/"):
                raise ValueError(f"input artifact is not an image: {artifact_id}")
            try:
                with Image.open(io.BytesIO(artifact.content)) as opened:
                    image = opened.convert("RGB")
                    image.thumbnail((arguments.cell_width, arguments.cell_height))
                    images.append(image.copy())
            except OSError as exc:
                raise ValueError(f"invalid image artifact: {artifact_id}") from exc
        rows = math.ceil(len(images) / arguments.columns)
        sheet = Image.new(
            "RGB",
            (arguments.columns * arguments.cell_width, rows * arguments.cell_height),
            color="black",
        )
        for index, image in enumerate(images):
            column = index % arguments.columns
            row = index // arguments.columns
            offset_x = column * arguments.cell_width + (arguments.cell_width - image.width) // 2
            offset_y = row * arguments.cell_height + (arguments.cell_height - image.height) // 2
            sheet.paste(image, (offset_x, offset_y))
        output = io.BytesIO()
        sheet.save(output, format="JPEG", quality=90, optimize=True)
        artifact = StoredArtifact.create(
            arguments.output_artifact_id,
            "image/jpeg",
            output.getvalue(),
        )
        store.put(artifact)
        return _metadata(artifact).model_dump()

    handlers = {
        "sample_frames": sample_frames,
        "extract_clip": extract_clip,
        "make_contact_sheet": make_contact_sheet,
    }
    for operator_id in (
        "make_contact_sheet",
        *(("sample_frames", "extract_clip") if media_backend is not None else ()),
    ):
        registry.register(specs[operator_id], handlers[operator_id])
