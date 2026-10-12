"""Export content-free per-request v2 timing after the frozen matrix completes."""

import argparse
import json
from pathlib import Path


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not (args.root / "matrix-complete.json").exists():
        raise RuntimeError("request-timing export requires completed matrix")
    admission = read(args.root / "replica-admission.json")
    freeze = read(args.root / "execution-freeze.json")
    cells = []
    for cell in freeze["ordered_cells"]:
        directory = args.root / "cells" / cell["cell_id"]
        transport = []
        for path in sorted((directory / "private/manager-admission").glob("*.json")):
            item = read(path)
            transport.append(
                {
                    "sequence": int(path.stem),
                    "endpoint_slot": item["endpoint_slot"],
                    "queue_wait_ms": item["queue_wait_ms"],
                    "provider_latency_ms": item["provider_latency_ms"],
                    "http_status": item["http_status"],
                    "error_type": item["error_type"],
                    "transport_timeout_seconds": item["transport_timeout_seconds"],
                }
            )
        usage = []
        for path in (directory / "private/api/local").glob("*-usage.json"):
            item = read(path)
            tokens = item.get("usage") or {}
            usage.append(
                {
                    "started_utc": item.get("started_utc"),
                    "finished_utc": item.get("finished_utc"),
                    "sdk_latency_ms": item.get("latency_ms"),
                    "http_status": item.get("status"),
                    "error_type": item.get("error_type"),
                    "prompt_tokens": tokens.get("input_tokens") or tokens.get("prompt_tokens"),
                    "completion_tokens": tokens.get("output_tokens") or tokens.get("completion_tokens"),
                }
            )
        cells.append(
            {
                "cell_id": cell["cell_id"],
                "candidate": cell["candidate"],
                "skill_condition": cell["skill_condition"],
                "transport_requests": transport,
                "sdk_requests": sorted(usage, key=lambda item: item["started_utc"] or ""),
            }
        )
    output = {
        "version": "skill-granularity-v2-content-free-request-timing",
        "serving": admission["serving"],
        "a28_manager_request_capacity": admission["manager_request_capacity"],
        "max_concurrent_workflow_cells": admission["max_concurrent_workflow_cells"],
        "manager_context_per_replica": admission["manager_context_per_replica"],
        "cells": cells,
        "latency_accounting": "queue wait and HTTP provider latency are separate; neither is exclusive GPU time",
        "raw_request_or_response_content_exported": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        raise RuntimeError("timing export already exists")
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"cells": len(cells), "transport_requests": sum(len(c["transport_requests"]) for c in cells)}))


if __name__ == "__main__":
    main()
