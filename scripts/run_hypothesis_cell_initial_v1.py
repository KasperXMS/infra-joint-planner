"""One frozen G0/G1 task cell inside the P1-isolated Controller namespace.

Only public manifests are mounted. Raw evidence and model output stay in /out.
"""

import argparse
import json
import math
import re
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

SOURCE_A = "http://192.168.0.104:63204"
SOURCE_B = "http://192.168.0.105:63217"
MODEL_URL = "http://127.0.0.1:11436"
TOKENIZER_URL = "http://127.0.0.1:37797"
MODEL_ID = "qwen35-27b-resident-32k-v1:latest"
PROFILES = {"Hslow": "http://192.168.0.104:63205", "Hfast": "http://192.168.0.104:63206"}
TASK_IDS = ("multihop:a647807d9a1d0efd", "mmqa:0ed625390ca7f919b46fd99fe85d80b5")
TOKEN_RE = re.compile(r"\w+", flags=re.UNICODE)
SYSTEM = (
    "Answer the original question using only the provided source evidence. "
    "Return one short answer, without explanation. "
    "If the evidence does not support an answer, return UNKNOWN."
)


def request(url, *, payload=None, method=None, timeout=90):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, method=method or ("POST" if data is not None else "GET")
    )
    if data is not None:
        req.add_header("Content-Type", "application/json")
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = response.read()
            status = response.status
    except urllib.error.HTTPError as error:
        body = error.read()
        status = error.code
    return status, body, round((time.perf_counter() - started) * 1000, 3), len(data or b"")


def require_json(url, *, payload=None, method=None, timeout=90):
    status, raw, elapsed, sent = request(url, payload=payload, method=method, timeout=timeout)
    if status < 200 or status >= 300:
        raise RuntimeError(
            "HTTP "
            + str(status)
            + " from "
            + url.split("/")[2]
            + ":"
            + raw[:180].decode(errors="replace")
        )
    return json.loads(raw), elapsed, sent, len(raw)


def action(node, operator, inputs, arguments, action_id, metrics):
    base = SOURCE_A if node == "source-a" else SOURCE_B
    response, ms, sent, received = require_json(
        base + "/execute/operator",
        payload={
            "action_id": action_id,
            "action": {"operator": operator, "inputs": inputs, "arguments": arguments},
        },
    )
    metrics["source_actions"].append(
        {
            "node": node,
            "operator": operator,
            "action_id": action_id,
            "input_ids": inputs,
            "output_artifact_id": response["output"].get("artifact_id"),
            "output_sha256": response["output"].get("sha256_hex"),
            "output_size_bytes": response["output"].get("size_bytes"),
            "ms": ms,
            "request_bytes": sent,
            "response_bytes": received,
        }
    )
    return response["output"]


def pull_to_b(artifact_id, expected_sha, profile, metrics, temporary):
    response, ms, sent, received = require_json(
        SOURCE_B + "/artifact/pull",
        payload={
            "artifact_id": artifact_id,
            "source_url": PROFILES[profile] + "/artifact/" + artifact_id,
            "expected_sha256": expected_sha,
        },
    )
    if response["sha256_hex"] != expected_sha:
        raise RuntimeError("transfer hash mismatch")
    metrics["transfers"].append(
        {
            "artifact_id": artifact_id,
            "bytes": response["size_bytes"],
            "ms": ms,
            "request_bytes": sent,
            "response_bytes": received,
            "profile": profile,
            "route": "A4-proxy-to-A5",
        }
    )
    temporary.append(artifact_id)


def read(node, artifact_id, run_id, metrics):
    action_id = run_id + ":read:" + str(len(metrics["source_actions"]))
    output = action(node, "read_artifact", [artifact_id], {}, action_id, metrics)
    return json.loads(output["text"])


def bm25(records, query, count, field):
    docs = [TOKEN_RE.findall(str(record.get(field, "")).casefold()) for record in records]
    terms = TOKEN_RE.findall(query.casefold())
    n = len(docs)
    avg = (sum(map(len, docs)) / n) if n else 1
    df = Counter(term for doc in docs for term in set(doc))
    scored = []
    for record, doc in zip(records, docs, strict=True):
        tf = Counter(doc)
        value = 0.0
        for term in terms:
            if tf[term]:
                value += math.log(1 + (n - df[term] + 0.5) / (df[term] + 0.5)) * (
                    tf[term] * 2.5 / (tf[term] + 1.5 * (0.25 + 0.75 * len(doc) / max(avg, 1)))
                )
        scored.append((value, record))
    return [row for _, row in sorted(scored, key=lambda pair: -pair[0])[:count]]


def acquire(task, workflow, profile, residency, run_id, metrics, temporary):
    if task["benchmark"] == "MultiHop-RAG":
        if workflow == "G0":
            chosen = [
                row
                for row in residency
                if row["source_group"] in ("publisher:TechCrunch", "publisher:Hacker News")
                and row["artifact_id"].startswith("multihop:")
            ]
            if len(chosen) < 2:
                raise RuntimeError("publisher inventory missing")
            originals = []
            for row in chosen:
                node = row["resident_agent"]
                if node == "source-a":
                    pull_to_b(row["artifact_id"], row["content_hash"], profile, metrics, temporary)
                doc = read("source-b", row["artifact_id"], run_id, metrics)
                doc["_origin_artifact_id"] = row["artifact_id"]
                doc["_source_group"] = row["source_group"]
                originals.append(doc)
            metrics["acquired_original_count"] = len(originals)
            evidence = []
            for publisher in ("publisher:TechCrunch", "publisher:Hacker News"):
                evidence.extend(
                    bm25(
                        [doc for doc in originals if doc["_source_group"] == publisher],
                        task["question"],
                        3,
                        "body",
                    )
                )
            return evidence
        evidence = []
        for node in ("source-a", "source-b"):
            output_id = run_id + ":" + node + ":bm25-top4"
            output = action(
                node,
                "bm25_retrieve",
                ["multihop:corpus-shard:" + node],
                {
                    "query": task["question"],
                    "top_k": 4,
                    "text_field": "body",
                    "output_artifact_id": output_id,
                },
                run_id + ":" + node + ":bm25",
                metrics,
            )
            metrics.setdefault("source_output_ids", []).append(
                {"node": node, "artifact_id": output_id}
            )
            if node == "source-a":
                pull_to_b(output_id, output["sha256_hex"], profile, metrics, temporary)
            records = read("source-b", output_id, run_id, metrics)
            for record in records:
                record["_origin_shard"] = "multihop:corpus-shard:" + node
            evidence.extend(records)
        metrics["acquired_original_count"] = len(evidence)
        return evidence

    if workflow == "G0":
        text_records = []
        for artifact_id in task["source_artifact_refs"]:
            if not artifact_id.startswith("mmqa:text:"):
                continue
            row = next(row for row in residency if row["artifact_id"] == artifact_id)
            if row["resident_agent"] != "source-a":
                raise RuntimeError("MMQA text placement drift")
            pull_to_b(artifact_id, row["content_hash"], profile, metrics, temporary)
            record = read("source-b", artifact_id, run_id, metrics)
            record["_origin_artifact_id"] = artifact_id
            text_records.append(record)
        metrics["acquired_original_count"] = len(text_records) + 1
        texts = bm25(text_records, task["question"], 3, "text")
    else:
        output_id = run_id + ":mmqa:bm25-top3"
        index_id = "hypothesis-v1:mmqa-candidates:" + task["task_id"]
        output = action(
            "source-a",
            "bm25_retrieve",
            [index_id],
            {
                "query": task["question"],
                "top_k": 3,
                "text_field": "text",
                "output_artifact_id": output_id,
            },
            run_id + ":mmqa:bm25",
            metrics,
        )
        metrics.setdefault("source_output_ids", []).append(
            {"node": "source-a", "artifact_id": output_id}
        )
        pull_to_b(output_id, output["sha256_hex"], profile, metrics, temporary)
        texts = read("source-b", output_id, run_id, metrics)
        metrics["acquired_original_count"] = len(texts) + 1
    table_id = next(item for item in task["source_artifact_refs"] if item.startswith("mmqa:table:"))
    table = read("source-b", table_id, run_id, metrics)
    table["_origin_artifact_id"] = table_id
    return texts + [table]


def model_answer(task, evidence, metrics):
    user = (
        "Original question: "
        + task["question"]
        + "\nEvidence (JSON with original provenance):\n"
        + json.dumps(evidence, ensure_ascii=False, separators=(",", ":"))
        + "\nShort answer:"
    )
    model_payload = {
        "model": MODEL_ID,
        "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}],
        "think": False,
        "stream": False,
        "options": {"num_predict": 128, "temperature": 0, "top_p": 1},
    }
    # The loaded Ollama llama-server supplies the actual GGUF tokenizer.
    tokenized, token_ms, _, _ = require_json(
        TOKENIZER_URL + "/tokenize", payload={"content": SYSTEM + "\n" + user}
    )
    count = len(tokenized.get("tokens", [])) if isinstance(tokenized.get("tokens"), list) else None
    if not isinstance(count, int) or count + 128 + 256 > 32768:
        raise RuntimeError("context_preflight_failed")
    metrics["context_tokens"] = count
    metrics["tokenize_ms"] = token_ms
    started = time.time()
    response, service_ms, sent, received = require_json(
        MODEL_URL + "/api/chat", payload=model_payload, timeout=300
    )
    metrics["model"] = {
        "model": response.get("model"),
        "started_unix": started,
        "ended_unix": time.time(),
        "provider_latency_ms": service_ms,
        "request_bytes": sent,
        "response_bytes": received,
        "usage": {
            "prompt_tokens": response.get("prompt_eval_count"),
            "completion_tokens": response.get("eval_count"),
        },
        "queue_ms": None,
        "cache_state": "unknown",
    }
    return response["message"]["content"].strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-id", choices=TASK_IDS, required=True)
    parser.add_argument("--workflow", choices=("G0", "G1"), required=True)
    parser.add_argument("--profile", choices=tuple(PROFILES), required=True)
    args = parser.parse_args()
    run_id = __import__("os").environ["STUDY_RUN_ID"]
    out = Path("/out/" + run_id + ".json")
    if out.exists():
        raise FileExistsError(out)
    tasks = {
        row["task_id"]: row
        for row in map(json.loads, Path("/study/task-candidates.jsonl").read_text().splitlines())
    }
    residency = list(
        map(json.loads, Path("/study/source-residency.jsonl").read_text().splitlines())
    )
    task = tasks[args.task_id]
    started = time.time()
    metrics = {"source_actions": [], "transfers": [], "acquired_original_count": 0}
    temporary = []
    answer = None
    error = None
    evidence = []
    try:
        evidence = acquire(task, args.workflow, args.profile, residency, run_id, metrics, temporary)
        answer = model_answer(task, evidence, metrics)
    except Exception as exc:
        error = {"type": type(exc).__name__, "message": str(exc)[:300]}
    finally:
        cleanup = []
        for artifact_id in temporary:
            status, _, ms, _ = request(SOURCE_B + "/artifact/" + artifact_id, method="DELETE")
            cleanup.append({"artifact_id": artifact_id, "status": status, "ms": ms})
        for item in metrics.get("source_output_ids", []):
            base = SOURCE_A if item["node"] == "source-a" else SOURCE_B
            status, _, ms, _ = request(base + "/artifact/" + item["artifact_id"], method="DELETE")
            cleanup.append({"artifact_id": item["artifact_id"], "status": status, "ms": ms})
        metrics["cleanup"] = cleanup
    result = {
        "schema_version": "infra-hypothesis-feasibility-v1",
        "run_id": run_id,
        "task_id": args.task_id,
        "workflow": args.workflow,
        "profile": args.profile,
        "started_unix": started,
        "ended_unix": time.time(),
        "e2e_ms": round((time.time() - started) * 1000, 3),
        "answer": answer,
        "error": error,
        "evidence_ids": [
            row.get("_origin_artifact_id", row.get("_origin_shard", "unknown")) for row in evidence
        ],
        "metrics": metrics,
    }
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "run_id": run_id,
                "status": "complete" if answer is not None else "failed",
                "e2e_ms": result["e2e_ms"],
            }
        )
    )


if __name__ == "__main__":
    main()
