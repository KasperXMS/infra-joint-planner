"""Derive one cell-specific Worker config from the frozen v1.3 Worker contract."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlparse

import yaml

REPO = Path(__file__).resolve().parents[1]


def _yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"configuration must be a mapping: {path}")
    return cast(dict[str, Any], value)


def prepare(cell_path: Path, agent_id: str, output: Path) -> None:
    if output.exists():
        raise FileExistsError(f"refusing to overwrite Worker config: {output}")
    cell = _yaml(cell_path)
    worker_urls = cast(dict[str, str], cell["worker_urls"])
    stores = cast(dict[str, str], cell["fresh_worker_stores"])
    if agent_id not in worker_urls or agent_id not in stores:
        raise ValueError(f"cell has no Worker settings for {agent_id}")
    base_name = "strong-4090" if agent_id == "strong-4090" else agent_id.lower()
    base_path = (
        REPO
        / "configs/experiments/workers/blind-3family-video-v1.3"
        / f"worker-{base_name}.yaml"
    )
    worker = _yaml(base_path)
    url = urlparse(worker_urls[agent_id])
    if url.scheme != "http" or url.port is None:
        raise ValueError(f"Worker URL must declare an HTTP port: {worker_urls[agent_id]}")
    worker["port"] = url.port
    worker["artifact_root"] = stores[agent_id]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        yaml.safe_dump(worker, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cell", type=Path, required=True)
    parser.add_argument("--agent-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    prepare(args.cell, args.agent_id, args.output)
