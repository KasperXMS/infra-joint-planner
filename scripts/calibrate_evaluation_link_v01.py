"""Measure study-owned Hslow/Hfast proxy on actual Worker pull data path."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from time import perf_counter
from typing import Any

import httpx

PROFILES = (
    ("Hslow", 63105, 3, 50),
    ("Hfast", 63106, 100, 5),
)


async def calibrate(manifest_path: Path, source_b_url: str) -> dict[str, Any]:
    rows = [json.loads(line) for line in manifest_path.read_text(encoding="utf-8").splitlines()]
    source_a = [row for row in rows if row["resident_agent"] == "source-a"]
    small = next(row for row in source_a if 200 <= row["artifact_size"] <= 500)
    large = next(
        row for row in source_a if row["artifact_id"] == "multihop:corpus-shard:source-a"
    )
    measurements = []
    async with httpx.AsyncClient(base_url=source_b_url, timeout=60.0) as client:
        for name, port, bandwidth_mbps, added_rtt_ms in PROFILES:
            for sample, repeat in ((small, 1), (small, 2), (small, 3), (large, 1)):
                dest_id = f"calibration-v01:{name}:{sample['artifact_id']}:{repeat}"
                started = perf_counter()
                try:
                    response = await client.post(
                        "/artifact/pull",
                        json={
                            "artifact_id": dest_id,
                            "source_url": (
                                f"http://192.168.0.104:{port}/artifact/"
                                + sample["artifact_id"]
                            ),
                            "expected_sha256": sample["content_hash"],
                        },
                    )
                    response.raise_for_status()
                    payload = response.json()
                    elapsed = perf_counter() - started
                    if payload["size_bytes"] != sample["artifact_size"]:
                        raise ValueError("calibration payload size drift")
                    measurements.append(
                        {
                            "profile": name,
                            "sample_kind": "small" if sample is small else "large",
                            "configured_bandwidth_mbps": bandwidth_mbps,
                            "configured_added_rtt_ms": added_rtt_ms,
                            "payload_bytes": payload["size_bytes"],
                            "payload_sha256": payload["sha256_hex"],
                            "elapsed_ms": round(elapsed * 1000, 3),
                            "achieved_mbps": round(payload["size_bytes"] * 8 / elapsed / 1e6, 3),
                        }
                    )
                finally:
                    # Only this script's unique calibration copy is removed.
                    await client.delete(f"/artifact/{dest_id}")
    return {
        "schema_version": "infra-evaluation-workload-v0.1",
        "link_implementation": "study-owned paced HTTP proxy on source-a; host tc untouched",
        "measurements": measurements,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--source-b-url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    result = asyncio.run(calibrate(args.manifest, args.source_b_url))
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"measurements": len(result["measurements"])}))


if __name__ == "__main__":
    main()
