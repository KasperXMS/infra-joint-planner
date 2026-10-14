"""Remove only verified probe-created replicas and derived artifacts."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

import httpx


async def cleanup(
    manifest_path: Path, receipt_path: Path, source_a_url: str, source_b_url: str
) -> dict[str, Any]:
    manifest = [json.loads(line) for line in manifest_path.read_text(encoding="utf-8").splitlines()]
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    base = {
        node: {
            row["artifact_id"]: row["content_hash"]
            for row in manifest
            if row["resident_agent"] == node
        }
        for node in ("source-a", "source-b")
    }
    allowed = {node: set() for node in base}
    for row in receipt["results"]:
        for operation in row["evidence_operations"]:
            if operation["operator"] == "bm25_retrieve":
                allowed[operation["node"]].add(operation["artifact_id"])
        allowed["source-b"].add(row["transfer"]["artifact_id"])
    removed = {}
    async with (
        httpx.AsyncClient(base_url=source_a_url, timeout=60.0) as a,
        httpx.AsyncClient(base_url=source_b_url, timeout=60.0) as b,
    ):
        for node, client in (("source-a", a), ("source-b", b)):
            state = (await client.get("/state")).json()
            observed = {item["artifact_id"]: item["sha256_hex"] for item in state["artifacts"]}
            if any(observed.get(key) != value for key, value in base[node].items()):
                raise ValueError(f"base source artifact missing or changed on {node}")
            extras = set(observed) - set(base[node])
            if not extras <= allowed[node]:
                raise ValueError(f"unexpected artifact on {node}; refusing cleanup")
            for artifact_id in sorted(extras):
                response = await client.delete(f"/artifact/{artifact_id}")
                response.raise_for_status()
                if not response.json()["deleted"]:
                    raise ValueError(f"failed to remove study artifact: {artifact_id}")
            final = (await client.get("/state")).json()
            final_ids = {item["artifact_id"] for item in final["artifacts"]}
            if final_ids != set(base[node]):
                raise ValueError(f"source store did not return to base manifest on {node}")
            removed[node] = len(extras)
    return {"removed_study_artifacts": removed, "base_residency_restored": True}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--source-a-url", required=True)
    parser.add_argument("--source-b-url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    result = asyncio.run(
        cleanup(args.manifest, args.receipt, args.source_a_url, args.source_b_url)
    )
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
