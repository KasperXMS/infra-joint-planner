"""Calibrate both new A4->A5 metered data paths with study-owned replicas."""

import json
import time
import urllib.request
from pathlib import Path

manifest = [
    json.loads(line)
    for line in Path(__file__).with_name("source-residency.jsonl").read_text().splitlines()
]
small = next(
    row
    for row in manifest
    if row["resident_agent"] == "source-a" and 200 <= row["artifact_size"] <= 500
)
large = next(row for row in manifest if row["artifact_id"] == "multihop:corpus-shard:source-a")
out = Path(__file__).with_name("link-calibration-public.json")
if out.exists():
    raise FileExistsError(out)
measurements = []
for profile, port, mbps, rtt in (("Hslow", 63205, 3, 50), ("Hfast", 63206, 100, 5)):
    for row in (small, large):
        replica = "hypothesis-calibration-v1:" + profile + ":" + row["artifact_id"]
        body = json.dumps(
            {
                "artifact_id": replica,
                "source_url": f"http://192.168.0.104:{port}/artifact/{row['artifact_id']}",
                "expected_sha256": row["content_hash"],
            }
        ).encode()
        request = urllib.request.Request(
            "http://192.168.0.105:63217/artifact/pull",
            data=body,
            headers={"Content-Type": "application/json"},
        )
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                result = json.loads(response.read())
            elapsed = time.perf_counter() - started
            if (
                result["sha256_hex"] != row["content_hash"]
                or result["size_bytes"] != row["artifact_size"]
            ):
                raise RuntimeError("calibration hash or byte mismatch")
            measurements.append(
                {
                    "profile": profile,
                    "payload_kind": "large" if row is large else "small",
                    "configured_mbps": mbps,
                    "extra_rtt_ms": rtt,
                    "bytes": result["size_bytes"],
                    "sha256": result["sha256_hex"],
                    "elapsed_ms": round(elapsed * 1000, 3),
                    "achieved_mbps": round(result["size_bytes"] * 8 / elapsed / 1e6, 3),
                }
            )
        finally:
            delete = urllib.request.Request(
                "http://192.168.0.105:63217/artifact/" + replica, method="DELETE"
            )
            with urllib.request.urlopen(delete, timeout=30):
                pass
out.write_text(
    json.dumps(
        {
            "schema_version": "infra-hypothesis-feasibility-v1",
            "route": "A4 study proxy -> A5 Worker artifact pull",
            "measurements": measurements,
        },
        indent=2,
        sort_keys=True,
    )
    + "\n"
)
print(json.dumps({"profiles": len(measurements)}))
