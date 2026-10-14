"""Bounded deterministic source-worker integration probe; never runs a Planner."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from time import perf_counter
from typing import Any

import httpx

from infra_joint.benchmarks.multihop_rag import MultiHopOfficialTokenOverlapEvaluator
from infra_joint.benchmarks.multimodalqa import MultiModalQAOfficialEvaluator
from infra_joint.core.task import OutputContract, OutputFormat, TaskContract

SELECTED = (
    "multihop:5390ae18477c53f9",
    "multihop:a647807d9a1d0efd",
    "multihop:a58e945f57294eca",
    "multihop:c1c98d6cf60878e4",
    "mmqa:33cf75c43fb268f267002cf8b9c28313",
    "mmqa:a33985b1e8b2502fc18cc8147dc27db8",
    "mmqa:0ed625390ca7f919b46fd99fe85d80b5",
    "mmqa:710a6d2254076ea58756c6c7cc211f1e",
)


def jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


async def action(
    client: httpx.AsyncClient, *, operator: str, inputs: list[str], arguments: dict[str, Any],
    action_id: str,
) -> dict[str, Any]:
    response = await client.post(
        "/execute/operator",
        json={
            "action_id": action_id,
            "action": {"operator": operator, "inputs": inputs, "arguments": arguments},
        },
    )
    response.raise_for_status()
    return response.json()["output"]


async def evaluator_smoke(task: dict[str, Any], private: dict[str, Any]) -> bool:
    case = TaskContract(
        task_id=task["task_id"],
        benchmark_id=task["benchmark"],
        objective=task["question"],
        artifacts=(),
        output_contract=OutputContract(format=OutputFormat.SHORT_TEXT),
        evaluator_id=private["evaluator_ref"],
    )
    if task["benchmark"] == "MultiHop-RAG":
        gold = private["answer"]
        evaluator = MultiHopOfficialTokenOverlapEvaluator(gold)
    else:
        gold = str(private["answers"][0]["answer"])
        evaluator = MultiModalQAOfficialEvaluator((gold,))
    scored = await evaluator.evaluate(case, gold)
    return scored.format_valid and scored.benchmark_score == 1.0


async def probe(
    public_root: Path,
    private_root: Path,
    source_a_url: str,
    source_b_url: str,
    selected_task_ids: tuple[str, ...] = SELECTED,
) -> dict[str, Any]:
    tasks = {row["task_id"]: row for row in jsonl(public_root / "task-candidates.jsonl")}
    private = {row["task_id"]: row for row in jsonl(private_root / "evaluator-private.jsonl")}
    artifacts = {row["artifact_id"]: row for row in jsonl(public_root / "source-residency.jsonl")}
    if any(task_id not in tasks or task_id not in private for task_id in selected_task_ids):
        raise ValueError("selected development task is absent")
    timeout = httpx.Timeout(60.0)
    async with (
        httpx.AsyncClient(base_url=source_a_url, timeout=timeout) as a,
        httpx.AsyncClient(base_url=source_b_url, timeout=timeout) as b,
    ):
        states = {}
        for node, client in (("source-a", a), ("source-b", b)):
            response = await client.get("/state")
            response.raise_for_status()
            state = response.json()
            if state["agent_id"] != node:
                raise ValueError(f"worker identity mismatch: {node}")
            states[node] = {item["artifact_id"]: item for item in state["artifacts"]}
        for artifact_id, record in artifacts.items():
            actual = states[record["resident_agent"]].get(artifact_id)
            if actual is None or actual["sha256_hex"] != record["content_hash"]:
                raise ValueError(f"source residency/hash mismatch: {artifact_id}")
            other = "source-b" if record["resident_agent"] == "source-a" else "source-a"
            if artifact_id in states[other]:
                raise ValueError(f"unexpected source replication: {artifact_id}")
        direct_get_status = {
            "source-a": (await a.get("/artifact/multihop:corpus-shard:source-a")).status_code,
            "source-b": (await b.get("/artifact/multihop:corpus-shard:source-b")).status_code,
        }
        if any(status != 403 for status in direct_get_status.values()):
            raise ValueError("unreceipted direct source read was not denied")
        rows: list[dict[str, Any]] = []
        for task_id in selected_task_ids:
            task = tasks[task_id]
            started = perf_counter()
            evidence_ops = []
            transfer_source: dict[str, Any]
            if task["benchmark"] == "MultiHop-RAG":
                for node, client in (("source-a", a), ("source-b", b)):
                    output_id = f"probe-v01:{task_id}:{node}:top3"
                    result = await action(
                        client,
                        operator="bm25_retrieve",
                        inputs=[f"multihop:corpus-shard:{node}"],
                        arguments={
                            "query": task["question"],
                            "top_k": 3,
                            "text_field": "body",
                            "output_artifact_id": output_id,
                        },
                        action_id=f"probe-v01:{task_id}:{node}:bm25",
                    )
                    evidence_ops.append({"node": node, "operator": "bm25_retrieve", **result})
                    if node == "source-a":
                        transfer_source = result
            else:
                text_ref = next(
                    ref for ref in task["source_artifact_refs"] if ref.startswith("mmqa:text:")
                )
                table_ref = next(
                    ref for ref in task["source_artifact_refs"] if ref.startswith("mmqa:table:")
                )
                for node, client, ref in (("source-a", a, text_ref), ("source-b", b, table_ref)):
                    result = await action(
                        client,
                        operator="read_artifact",
                        inputs=[ref],
                        arguments={},
                        action_id=f"probe-v01:{task_id}:{node}:read",
                    )
                    evidence_ops.append(
                        {
                            "node": node,
                            "operator": "read_artifact",
                            "input_artifact_id": ref,
                            "response_bytes": len(result["text"].encode("utf-8")),
                        }
                    )
                transfer_source = {
                    "artifact_id": text_ref,
                    "sha256_hex": artifacts[text_ref]["content_hash"],
                    "size_bytes": artifacts[text_ref]["artifact_size"],
                }
            transfer_started = perf_counter()
            moved = await b.post(
                "/artifact/pull",
                json={
                    "artifact_id": transfer_source["artifact_id"],
                    "source_url": (
                        source_a_url.rstrip("/") + "/artifact/" + transfer_source["artifact_id"]
                    ),
                    "expected_sha256": transfer_source["sha256_hex"],
                },
            )
            moved.raise_for_status()
            transfer_ms = (perf_counter() - transfer_started) * 1000
            payload = moved.json()
            if payload["size_bytes"] != transfer_source["size_bytes"]:
                raise ValueError("transfer byte accounting mismatch")
            if payload["sha256_hex"] != transfer_source["sha256_hex"]:
                raise ValueError("transfer hash mismatch")
            receipt = await b.get(f"/execute/receipt/probe-v01:{task_id}:source-b:read")
            if task["benchmark"] == "MultiModalQA" and receipt.status_code != 200:
                raise ValueError("missing source operation receipt")
            rows.append(
                {
                    "task_id": task_id,
                    "benchmark": task["benchmark"],
                    "status": "operator_and_evaluator_smoke_passed",
                    "evidence_operations": evidence_ops,
                    "transfer": {
                        "producer": "source-a",
                        "consumer": "source-b",
                        "artifact_id": transfer_source["artifact_id"],
                        "representation": (
                            "retrieved_passage_set"
                            if task["benchmark"] == "MultiHop-RAG"
                            else "original_text"
                        ),
                        "bytes": payload["size_bytes"],
                        "sha256": payload["sha256_hex"],
                        "latency_ms": round(transfer_ms, 3),
                        "network_profile": "unshaped_baseline",
                    },
                    "evaluator_smoke_passed": await evaluator_smoke(task, private[task_id]),
                    "task_e2e_probe_ms": round((perf_counter() - started) * 1000, 3),
                    "setup_bytes": 0,
                    "model_service_latency": None,
                    "gpu_monetary_cost": None,
                }
            )
        return {
            "schema_version": "infra-evaluation-workload-v0.1",
            "condition": "deterministic_environment_validation; no Planner or model answers",
            "worker_nodes": {node: len(state) for node, state in states.items()},
            "source_direct_get_status": direct_get_status,
            "task_probe_count": len(rows),
            "results": rows,
        }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--public-root", type=Path, required=True)
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--source-a-url", required=True)
    parser.add_argument("--source-b-url", required=True)
    parser.add_argument("--task-id", action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    result = asyncio.run(
        probe(
            args.public_root,
            args.private_root,
            args.source_a_url,
            args.source_b_url,
            tuple(args.task_id) if args.task_id else SELECTED,
        )
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"task_probe_count": result["task_probe_count"]}))


if __name__ == "__main__":
    main()
