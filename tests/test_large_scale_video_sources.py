import importlib
import io
import sys
import zipfile
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
sources = importlib.import_module("large_scale_video_sources_v1")


class Response(io.BytesIO):
    def __init__(self, body: bytes, headers: dict[str, str], status: int) -> None:
        super().__init__(body)
        self.headers = headers
        self.status = status

    def geturl(self) -> str:
        return "https://test.invalid/archive.zip"


def fake_archive(monkeypatch: pytest.MonkeyPatch, data: bytes, *, honor: bool = True) -> None:
    def opened(request: Any, timeout: int) -> Response:
        assert timeout in (30, 60)
        if request.get_method() == "HEAD":
            return Response(b"", {"Content-Length": str(len(data)), "ETag": "pinned"}, 200)
        interval = request.headers["Range"].removeprefix("bytes=")
        start, end = (int(value) for value in interval.split("-"))
        return Response(
            data[start : end + 1],
            {"Content-Range": f"bytes {start}-{end}/{len(data)}"},
            206 if honor else 200,
        )

    monkeypatch.setattr(sources.urllib.request, "urlopen", opened)


def test_range_zip_reads_original_members_and_validates_crc(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = bytes(range(256)) * 12000
    memory = io.BytesIO()
    with zipfile.ZipFile(memory, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("data/original.mp4", original)
    fake_archive(monkeypatch, memory.getvalue())
    reader = sources.RangeZipReader("https://test.invalid/archive.zip")
    with zipfile.ZipFile(reader) as archive:
        assert archive.read("data/original.mp4") == original
    assert reader.fetched_bytes == len(memory.getvalue())
    assert reader.range_requests == 1


def test_range_zip_never_reads_server_full_response(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_archive(monkeypatch, b"not-a-real-archive", honor=False)
    reader = sources.RangeZipReader("https://test.invalid/archive.zip")
    with pytest.raises(RuntimeError, match="exact bounded archive range"):
        reader.read(4)
    assert reader.fetched_bytes == 0


def test_range_reader_cross_block_seek_and_unbounded_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data = b"a" * sources.BLOCK_BYTES + b"b" * sources.BLOCK_BYTES
    fake_archive(monkeypatch, data)
    reader = sources.RangeZipReader("https://test.invalid/archive.zip")
    reader.seek(sources.BLOCK_BYTES - 2)
    assert reader.read(4) == b"aabb"
    reader.seek(-2, io.SEEK_END)
    assert reader.read() == b"bb"
    assert reader.range_requests == 2
    with pytest.raises(RuntimeError, match="oversized"):
        reader.read(33 * sources.BLOCK_BYTES)
    with pytest.raises(ValueError, match="Negative"):
        reader.seek(-1)


def test_dataset_acquisition_rejects_local_destination_before_download(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="4090 preparation root"):
        sources.annotation_inventory(tmp_path / "annotation")
    assert not (tmp_path / "annotation").exists()


def test_preparation_receipts_are_append_only(tmp_path: Path) -> None:
    path = tmp_path / "receipt.json"
    sources.write_new(path, {"original": True})
    original = path.read_bytes()
    with pytest.raises(FileExistsError):
        sources.write_new(path, {"replacement": True})
    assert path.read_bytes() == original
