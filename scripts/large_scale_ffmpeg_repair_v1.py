"""Isolated environment repair: same FFmpeg/dav1d versions, add H.264 software decode.

Source downloads/distribution happen on 4090, never the development PC. No Worker,
Agent, model inference, benchmark run or network shaping is launched by this script.
Historical binaries/configs/evidence are never overwritten.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path

CONTROLLER = Path("/home/super/xiaoming/large-scale-cost-guidance-v1")
JETSON = Path("/mnt/ssd/large-scale-cost-guidance-v1/environment-repair-001")
SOURCES = {
    "ffmpeg-8.0.1.tar.xz": "https://ffmpeg.org/releases/ffmpeg-8.0.1.tar.xz",
    "dav1d-1.4.3.tar.xz":
        "https://downloads.videolan.org/pub/videolan/dav1d/1.4.3/dav1d-1.4.3.tar.xz",
}


def write_new(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2)


def download(url: str, target: Path) -> dict[str, object]:
    with urllib.request.urlopen(url, timeout=120) as response, target.open("xb") as stream:
        shutil.copyfileobj(response, stream)
    return {"url": url, "filename": target.name, "bytes": target.stat().st_size,
            "sha256": hashlib.sha256(target.read_bytes()).hexdigest()}


def ninja_binary(tools: Path) -> Path:
    candidates = []
    for path in tools.rglob("ninja"):
        if path.is_file():
            with path.open("rb") as stream:
                if stream.read(4) == b"\x7fELF":
                    candidates.append(path)
    if len(candidates) != 1:
        raise RuntimeError("the pinned ARM wheel must contain exactly one Ninja ELF binary")
    return candidates[0]


def prepare() -> dict[str, object]:
    if sys.platform != "linux" or not CONTROLLER.exists() or platform.machine() != "x86_64":
        raise RuntimeError("download and distribute sources only on the 4090 controller")
    root = CONTROLLER / "preparation/environment-repair-001"
    root.mkdir(exist_ok=False)
    files = [download(url, root / name) for name, url in SOURCES.items()]
    for package, version in (("meson", "1.9.0"), ("ninja", "1.13.0")):
        with urllib.request.urlopen(
            f"https://pypi.org/pypi/{package}/{version}/json", timeout=60,
        ) as response:
            metadata = json.load(response)
        candidates = [row for row in metadata["urls"] if row["filename"].endswith(".whl")
                      and ("py3-none-any" in row["filename"] or
                           ("aarch64" in row["filename"] and "manylinux" in row["filename"]))]
        if len(candidates) != 1:
            raise RuntimeError("unambiguous pinned ARM build-tool wheel required")
        row = candidates[0]
        receipt = download(row["url"], root / row["filename"])
        if receipt["sha256"] != row["digests"]["sha256"]:
            raise RuntimeError("official build-tool wheel digest mismatch")
        files.append(receipt)
    record = {"files": files, "ffmpeg_version": "8.0.1", "dav1d_version": "1.4.3",
              "intended_change": "add native h264 decoder and h264 parser",
              "Planner_calls": 0, "formal_cells": 0, "tc_operations": 0}
    write_new(root / "sources.json", record)
    # All downloaded sources/wheels and this source-only build script move from
    # controller to owning node; no benchmark artifact passes through the PC.
    host = "edge@192.168.0.128"
    subprocess.run(["ssh", "-n", "-o", "BatchMode=yes", host,
                    f"mkdir {JETSON}"], check=True, capture_output=True)
    subprocess.run(["scp", "-q", *(str(root / str(row["filename"])) for row in files),
                    str(root / "sources.json"), str(Path(__file__).resolve()),
                    f"{host}:{JETSON}/"], check=True, capture_output=True)
    return {"source_count": len(files), "root": str(root), "build_node": "A28"}


def build() -> dict[str, object]:
    if sys.platform != "linux" or platform.machine() != "aarch64":
        raise RuntimeError("native ARM environment build must run on A28")
    if Path(__file__).resolve().parent != JETSON:
        raise RuntimeError("build script is outside the isolated repair namespace")
    if (JETSON / "build-completed.json").exists():
        raise FileExistsError("completed environment build cannot be overwritten")
    manifest = json.loads((JETSON / "sources.json").read_text())
    for row in manifest["files"]:
        if hashlib.sha256((JETSON / row["filename"]).read_bytes()).hexdigest() != row["sha256"]:
            raise RuntimeError("source/build-tool hash drift")
    sources, tools = JETSON / "sources", JETSON / "tools"
    # An interrupted bootstrap can re-extract the same hash-verified code inputs;
    # neither completed receipts nor historical binaries are overwritten.
    sources.mkdir(exist_ok=True)
    tools.mkdir(exist_ok=True)
    for row in manifest["files"]:
        archive = JETSON / row["filename"]
        if archive.suffix == ".whl":
            with zipfile.ZipFile(archive) as wheel:
                if any(tools.resolve() not in (tools / name).resolve().parents
                       for name in wheel.namelist()):
                    raise RuntimeError("wheel path escapes repair namespace")
                wheel.extractall(tools)
        else:
            with tarfile.open(archive) as source:
                for item in source.getmembers():
                    if sources.resolve() not in (sources / item.name).resolve().parents:
                        raise RuntimeError("source path escapes repair namespace")
            subprocess.run(["tar", "-xf", str(archive), "-C", str(sources)], check=True)
    ninja = ninja_binary(tools)
    ninja.chmod(0o755)
    env = {**os.environ, "PYTHONPATH": str(tools),
           "PATH": str(ninja.parent) + ":" + os.environ.get("PATH", "")}
    library = JETSON / "dav1d-static"
    meson = [sys.executable, "-m", "mesonbuild.mesonmain"]
    subprocess.run([
        *meson, "setup", str(JETSON / "dav1d-build"), str(sources / "dav1d-1.4.3"),
        "--prefix", str(library), "--libdir", "lib", "--default-library", "static",
        "--buildtype", "release", "-Denable_tools=false", "-Denable_tests=false",
    ], check=True, env=env)
    subprocess.run([str(ninja), "-C", str(JETSON / "dav1d-build"), "-j4"], check=True, env=env)
    subprocess.run([str(ninja), "-C", str(JETSON / "dav1d-build"), "install"],
                   check=True, env=env)
    prefix = JETSON / "ffmpeg-av1-h264-sw-v8.0.1"
    env["PKG_CONFIG_PATH"] = str(library / "lib/pkgconfig")
    flags = [
        f"--prefix={prefix}", "--disable-doc", "--disable-debug", "--disable-network",
        "--disable-autodetect", "--disable-everything", "--enable-ffmpeg",
        "--enable-avcodec", "--enable-avformat", "--enable-avfilter", "--enable-swscale",
        "--enable-protocol=file,pipe", "--enable-demuxer=mov,matroska",
        "--enable-decoder=libdav1d,h264", "--enable-libdav1d", "--enable-encoder=mjpeg",
        "--enable-muxer=image2,null,mp4,mov", "--enable-filter=fps,scale,format",
        "--enable-parser=av1,h264", "--pkg-config-flags=--static",
    ]
    ffmpeg_source = sources / "ffmpeg-8.0.1"
    subprocess.run([str(ffmpeg_source / "configure"), *flags], cwd=ffmpeg_source,
                   check=True, env=env)
    subprocess.run(["make", "-j4"], cwd=ffmpeg_source, check=True, env=env)
    subprocess.run(["make", "install"], cwd=ffmpeg_source, check=True, env=env)
    binary = prefix / "bin/ffmpeg"
    decoders = subprocess.run([str(binary), "-hide_banner", "-decoders"],
                              check=True, capture_output=True, text=True)
    names = {line.split()[1] for line in decoders.stdout.splitlines() if len(line.split()) >= 2}
    if not {"h264", "libdav1d"} <= names:
        raise RuntimeError("build did not retain both required software decoders")
    receipt = {"binary": str(binary), "binary_sha256": hashlib.sha256(
        binary.read_bytes()).hexdigest(), "configure_flags": flags,
        "h264_decoder": True, "libdav1d_decoder": True,
        "inference_or_benchmark_runs": 0, "historical_binary_modified": False}
    write_new(JETSON / "build-completed.json", receipt)
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "build"))
    args = parser.parse_args()
    print(json.dumps(prepare() if args.mode == "prepare" else build(), sort_keys=True))
