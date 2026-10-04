import importlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
repair = importlib.import_module("large_scale_ffmpeg_repair_v1")


def test_pinned_ninja_wheel_layout_is_discovered_not_guessed(tmp_path: Path) -> None:
    path = tmp_path / "ninja/bin/ninja"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"\x7fELFsynthetic-aarch64-build-tool")
    assert repair.ninja_binary(tmp_path) == path
    wrapper = tmp_path / "scripts/ninja"
    wrapper.parent.mkdir()
    wrapper.write_bytes(b"python wrapper, not an ELF binary")
    assert repair.ninja_binary(tmp_path) == path


def test_missing_or_ambiguous_ninja_binary_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError):
        repair.ninja_binary(tmp_path)
    for name in ("first", "second"):
        path = tmp_path / name / "ninja"
        path.parent.mkdir()
        path.write_bytes(b"\x7fELFsynthetic")
    with pytest.raises(RuntimeError):
        repair.ninja_binary(tmp_path)
