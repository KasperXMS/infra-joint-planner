"""Acquire pinned original Video-MME sources on 4090, never on the dev PC.

This is preparation only: no Planner, benchmark execution, Worker or tc calls.
ZIP members are copied losslessly using bounded, validated HTTP ranges. Dataset
annotations and videos remain remote; stdout contains structural metadata only.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import subprocess
import urllib.request
import zipfile
from collections import OrderedDict
from pathlib import Path
from typing import Any

DATASET = "lmms-eval/Video-MME"
REVISION = "ead1408f75b618502df9a1d8e0950166bf0a2a0b"
BASE = f"https://huggingface.co/datasets/{DATASET}/resolve/{REVISION}"
REMOTE_ROOT = Path("/home/super/xiaoming/large-scale-cost-guidance-v1/preparation")
BLOCK_BYTES = 1024 * 1024
VIDEO_SELECTION = (
    ("602-2", "long temporal reasoning; Knowledge; Phase I duration contrast"),
    ("131-3", "short object recognition; Sports; Phase I localized-evidence proxy"),
    ("481-2", "medium action reasoning; Artistic Performance"),
    ("394-2", "medium information synopsis; Film & Television"),
    ("224-3", "short temporal reasoning; Life Record"),
    ("891-1", "long object reasoning; Multilingual"),
)


def require_remote(path: Path) -> Path:
    resolved = path.resolve()
    if os.name == "nt" or not resolved.is_relative_to(REMOTE_ROOT.resolve()):
        raise RuntimeError("Dataset acquisition is restricted to the new 4090 preparation root")
    if resolved == REMOTE_ROOT.resolve():
        raise RuntimeError("Use a new child directory, not the preparation root")
    return resolved


def write_new(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write("\n")


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        while data := stream.read(BLOCK_BYTES):
            result.update(data)
    return result.hexdigest()


class RangeZipReader(io.RawIOBase):
    """Small LRU range reader. A server ignoring Range is rejected before reading."""

    def __init__(self, url: str) -> None:
        super().__init__()
        with urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=30) as r:
            self.length = int(r.headers["Content-Length"])
            self.etag = r.headers.get("ETag")
            self.url = r.geturl()
        self.position = 0
        self.cache: OrderedDict[int, bytes] = OrderedDict()
        self.fetched_bytes = 0
        self.range_requests = 0

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def tell(self) -> int:
        return self.position

    def seek(self, offset: int, whence: int = io.SEEK_SET) -> int:
        origin = {io.SEEK_SET: 0, io.SEEK_CUR: self.position, io.SEEK_END: self.length}[whence]
        target = origin + offset
        if target < 0:
            raise ValueError("Negative ZIP position")
        self.position = target
        return target

    def _block(self, start: int) -> bytes:
        if start in self.cache:
            self.cache.move_to_end(start)
            return self.cache[start]
        end = min(start + BLOCK_BYTES, self.length) - 1
        request = urllib.request.Request(self.url, headers={"Range": f"bytes={start}-{end}"})
        with urllib.request.urlopen(request, timeout=60) as r:
            expected = f"bytes {start}-{end}/{self.length}"
            if r.status != 206 or r.headers.get("Content-Range") != expected:
                raise RuntimeError("Server did not honor the exact bounded archive range")
            data = r.read(end - start + 2)
        if len(data) != end - start + 1:
            raise RuntimeError("Archive range length mismatch")
        self.fetched_bytes += len(data)
        self.range_requests += 1
        self.cache[start] = data
        if len(self.cache) > 4:
            self.cache.popitem(last=False)
        return data

    def read(self, size: int = -1) -> bytes:
        if size < 0:
            size = max(0, self.length - self.position)
        if size > 32 * BLOCK_BYTES:
            raise RuntimeError("Unbounded or oversized archive read prohibited")
        remaining = min(size, max(0, self.length - self.position))
        parts: list[bytes] = []
        while remaining:
            start = self.position // BLOCK_BYTES * BLOCK_BYTES
            block = self._block(start)
            offset = self.position - start
            part = block[offset : offset + remaining]
            parts.append(part)
            self.position += len(part)
            remaining -= len(part)
        return b"".join(parts)


def annotation_inventory(output: Path) -> dict[str, Any]:
    """Persist private annotation remotely; publish IDs/types, never Q/A/gold."""
    output = require_remote(output)
    import pyarrow.parquet as parquet

    output.mkdir(parents=True, exist_ok=False)
    path = output / "annotation.parquet"
    url = f"{BASE}/videomme/test-00000-of-00001.parquet"
    with urllib.request.urlopen(url, timeout=60) as r:
        data = r.read(4 * BLOCK_BYTES + 1)
    if len(data) > 4 * BLOCK_BYTES:
        raise RuntimeError("Annotation exceeds bounded preparation download")
    with path.open("xb") as stream:
        stream.write(data)
    rows = parquet.read_table(path).to_pylist()
    groups: dict[str, int] = {}
    candidates: dict[str, list[dict[str, str]]] = {}
    private_rows = output / "annotation-private.json"
    write_new(private_rows, rows)
    for row in rows:
        duration = str(row.get("duration", "unknown"))
        kind = str(row.get("task_type", "unknown"))
        key = f"{duration}/{kind}"
        groups[key] = groups.get(key, 0) + 1
        bucket = candidates.setdefault(key, [])
        if len(bucket) < 3:
            bucket.append({
                "question_id": str(row.get("question_id", "")),
                "video_id": str(row.get("videoID", "")),
                "category": str(row.get("sub_category", "unknown")),
            })
    receipt = {
        "dataset": DATASET,
        "revision": REVISION,
        "annotation_sha256": digest(path),
        "row_count": len(rows),
        "columns": sorted(rows[0]) if rows else [],
        "groups": groups,
        "candidate_ids_only": candidates,
        "planner_calls": 0,
        "formal_runs": 0,
    }
    write_new(output / "inventory.json", receipt)
    return receipt


def archive_index(output: Path, numbers: list[int]) -> dict[str, Any]:
    output = require_remote(output)
    output.mkdir(parents=True, exist_ok=False)
    total = 0
    receipts = []
    for number in numbers:
        if not 1 <= number <= 20:
            raise ValueError("Original dataset has twenty video archives")
        name = f"videos_chunked_{number:02d}.zip"
        reader = RangeZipReader(f"{BASE}/{name}")
        with zipfile.ZipFile(reader) as archive:
            entries = [{
                "name": entry.filename,
                "bytes": entry.file_size,
                "compressed_bytes": entry.compress_size,
                "crc32": entry.CRC,
                "compression": entry.compress_type,
                "header_offset": entry.header_offset,
            } for entry in archive.infolist()]
        receipt = {
            "dataset": DATASET,
            "revision": REVISION,
            "archive": name,
            "archive_bytes": reader.length,
            "etag": reader.etag,
            "index_fetched_bytes": reader.fetched_bytes,
            "range_requests": reader.range_requests,
            "entries": entries,
        }
        write_new(output / f"{name}.index.json", receipt)
        total += reader.fetched_bytes
        receipts.append({"archive": name, "entries": len(entries)})
    summary = {"archives": receipts, "index_fetched_bytes": total, "formal_runs": 0}
    write_new(output / "summary.json", summary)
    return summary


def extract_video(output: Path, index: Path, member: str) -> dict[str, Any]:
    output = require_remote(output)
    index = require_remote(index)
    if not re.fullmatch(r"[A-Za-z0-9_-]+\.mp4", Path(member).name):
        raise ValueError("Only original MP4 video members can be acquired")
    output.mkdir(parents=True, exist_ok=False)
    metadata = json.loads(index.read_text(encoding="utf-8"))
    if metadata["dataset"] != DATASET or metadata["revision"] != REVISION:
        raise RuntimeError("Archive provenance differs from pinned original dataset")
    name = metadata["archive"]
    if not re.fullmatch(r"videos_chunked_\d{2}\.zip", name):
        raise ValueError("Invalid archive identity")
    reader = RangeZipReader(f"{BASE}/{name}")
    if reader.length != metadata["archive_bytes"] or reader.etag != metadata["etag"]:
        raise RuntimeError("Archive identity drift")
    target = output / Path(member).name
    with zipfile.ZipFile(reader) as archive:
        entry = archive.getinfo(member)
        if entry.file_size > 1024 * BLOCK_BYTES:
            raise RuntimeError("Selected video exceeds one-GiB acquisition guard")
        with archive.open(entry) as source, target.open("xb") as sink:
            while chunk := source.read(BLOCK_BYTES):
                sink.write(chunk)
        if target.stat().st_size != entry.file_size:
            raise RuntimeError("Video member size mismatch")
    receipt = {
        "dataset": DATASET,
        "revision": REVISION,
        "archive": name,
        "member": member,
        "source_crc32": entry.CRC,
        "size_bytes": target.stat().st_size,
        "sha256": digest(target),
        "network_fetched_bytes": reader.fetched_bytes,
        "range_requests": reader.range_requests,
        "transformation": "lossless_original_zip_member_extraction",
        "formal_runs": 0,
    }
    write_new(output / "provenance.json", receipt)
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "format=duration:stream=codec_type,codec_name,width,height", "-of", "json", str(target)],
        capture_output=True, text=True, check=True, timeout=60,
    )
    write_new(output / "media.json", json.loads(probe.stdout))
    return receipt


def select_videos(output: Path, annotation: Path, indexes: Path) -> dict[str, Any]:
    """Preregister six distinct sources by annotation strata, before any outcomes."""
    output = require_remote(output)
    annotation = require_remote(annotation)
    indexes = require_remote(indexes)
    rows = json.loads((annotation / "annotation-private.json").read_text(encoding="utf-8"))
    entries = {
        Path(entry["name"]).stem: (path.name, entry)
        for path in sorted(indexes.glob("*.index.json"))
        for entry in json.loads(path.read_text(encoding="utf-8"))["entries"]
        if entry["name"].endswith(".mp4")
    }
    selected = []
    for position, (question_id, rationale) in enumerate(VIDEO_SELECTION, start=1):
        matches = [row for row in rows if row["question_id"] == question_id]
        if len(matches) != 1:
            raise RuntimeError("Selected original question must exist exactly once")
        row = matches[0]
        index_name, entry = entries[row["videoID"]]
        public_task = {"question": row["question"], "options": row["options"]}
        selected.append({
            "position": position,
            "question_id": question_id,
            "video_id": row["videoID"],
            "duration_class": row["duration"],
            "task_type": row["task_type"],
            "domain": row["domain"],
            "subcategory": row["sub_category"],
            "source_bytes": entry["bytes"],
            "index": index_name,
            "member": entry["name"],
            "task_sha256": hashlib.sha256(
                json.dumps(public_task, sort_keys=True, ensure_ascii=False).encode()
            ).hexdigest(),
            "private_gold_sha256": hashlib.sha256(str(row["answer"]).encode()).hexdigest(),
            "rationale": rationale,
            "evidence_span_seconds": None,
            "evidence_span_note": "Task types are proxies, not annotated evidence-span proofs",
        })
    if len({row["video_id"] for row in selected}) != 6:
        raise RuntimeError("Six independent original videos required")
    if any(row["video_id"] == "D97vMwfWxvI" for row in selected):
        raise RuntimeError("E history video cannot be held-out evaluation input")
    receipt = {"dataset": DATASET, "revision": REVISION, "tasks": selected,
               "formal_runs_at_selection": 0, "not_complete_18_task_freeze": True}
    output.mkdir(parents=True, exist_ok=False)
    write_new(output / "selection.json", receipt)
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("annotation", "index", "extract", "select"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--archives", type=int, nargs="+", default=list(range(1, 21)))
    parser.add_argument("--index", type=Path)
    parser.add_argument("--member")
    parser.add_argument("--annotation", type=Path)
    parser.add_argument("--indexes", type=Path)
    args = parser.parse_args()
    if args.mode == "annotation":
        result = annotation_inventory(args.output)
    elif args.mode == "index":
        result = archive_index(args.output, args.archives)
    elif args.mode == "select":
        if args.annotation is None or args.indexes is None:
            parser.error("select requires --annotation and --indexes")
        result = select_videos(args.output, args.annotation, args.indexes)
    else:
        if args.index is None or args.member is None:
            parser.error("extract requires --index and --member")
        result = extract_video(args.output, args.index, args.member)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
