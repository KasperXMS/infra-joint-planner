"""Run inside the locked Controller mount namespace; emit redacted P1 receipts.

The caller mounts only /study (public manifest), /out, /usr, /lib, /lib64,
/proc and /dev. No source store, benchmark copy, token or gold is mounted.
"""

import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

SOURCES = {"source-a": "http://192.168.0.104:63204", "source-b": "http://192.168.0.105:63217"}
PROXY = "http://192.168.0.104:63206"
DENIED_PATHS = (
    "/home/super/xiaoming/infra-evaluation-workload-v0.1/artifacts",
    "/home/super/xiaoming/infra-evaluation-workload-v0.1/private/evaluator-private.jsonl",
    "/home/super/xiaoming/blind_baseline_6task_v1",
    "/mnt/ssd/infra-hypothesis-feasibility-v1/source-a/artifacts",
    "/mnt/ssd/infra-hypothesis-feasibility-v1/source-b/artifacts",
    "/proc/1/root/home/super/xiaoming/infra-evaluation-workload-v0.1/private/evaluator-private.jsonl",
    "/study/private/evaluator-private.jsonl",
)


def call(base, route, *, payload=None):
    body = None if payload is None else json.dumps(payload).encode()
    method = "GET" if payload is None else "POST"
    request = urllib.request.Request(base + route, data=body, method=method)
    if body is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


def main():
    started = time.time()
    run_id = os.environ.get("STUDY_RUN_ID", "p1-001")
    if not run_id.replace("-", "").isalnum():
        raise ValueError("invalid run ID")
    out = Path("/out/" + run_id + "-isolation-receipt.json")
    if out.exists():
        raise FileExistsError(out)
    denied = {}
    for name in DENIED_PATHS:
        try:
            with open(name, "rb") as handle:
                handle.read(1)
            denied[name] = False
        except (FileNotFoundError, PermissionError, NotADirectoryError):
            denied[name] = True
    if not all(denied.values()):
        raise RuntimeError("Controller has an unmetered local read path")
    mounts = Path("/proc/self/mountinfo").read_text().splitlines()
    forbidden_mounts = [
        line
        for line in mounts
        if (line.split()[4].startswith("/home/") or line.split()[4].startswith("/mnt/ssd"))
    ]
    if forbidden_mounts:
        raise RuntimeError("Controller inherited forbidden host mounts")

    manifest = [
        json.loads(line) for line in Path("/study/source-residency.jsonl").read_text().splitlines()
    ]
    expected = {row["artifact_id"]: row for row in manifest}
    states = {}
    for node, base in SOURCES.items():
        status, raw = call(base, "/state")
        if status != 200:
            raise RuntimeError("Worker state unavailable: " + node)
        state = json.loads(raw)
        if state["agent_id"] != node:
            raise RuntimeError("Worker identity mismatch")
        states[node] = {row["artifact_id"]: row for row in state["artifacts"]}
    for artifact_id, row in expected.items():
        local = states[row["resident_agent"]].get(artifact_id)
        other = "source-a" if row["resident_agent"] == "source-b" else "source-b"
        if (
            local is None
            or local["sha256_hex"] != row["content_hash"]
            or artifact_id in states[other]
        ):
            raise RuntimeError("Source residency/hash mismatch")
    if len(expected) != 686:
        raise RuntimeError("Historical corrected manifest count changed")

    unauthorized = {}
    for node, base in SOURCES.items():
        unauthorized[node + ":get"] = call(base, "/artifact/multihop:corpus-shard:" + node)[0]
        unauthorized[node + ":unknown"] = call(base, "/artifact/unauthorized-v1:no-such-version")[0]
    if any(unauthorized[node + ":get"] != 403 for node in SOURCES):
        raise RuntimeError("Unauthenticated source GET was allowed")
    if any(unauthorized[node + ":unknown"] not in (403, 404) for node in SOURCES):
        raise RuntimeError("Unknown source version was allowed")

    chosen = {}
    for node in SOURCES:
        row = next(
            row
            for row in manifest
            if row["resident_agent"] == node
            and row["artifact_size"] < 16000
            and row["artifact_id"].startswith("multihop:")
        )
        chosen[node] = row
        action_id = "hypothesis-" + run_id + ":" + node + ":read"
        status, raw = call(
            SOURCES[node],
            "/execute/operator",
            payload={
                "action_id": action_id,
                "action": {
                    "operator": "read_artifact",
                    "inputs": [row["artifact_id"]],
                    "arguments": {},
                },
            },
        )
        if status != 200:
            raise RuntimeError("Authorized read failed: " + node + ":" + str(status))
        if "output" not in json.loads(raw):
            raise RuntimeError("Authorized read missing output")
        receipt_status, _ = call(SOURCES[node], "/execute/receipt/" + action_id)
        if receipt_status != 200:
            raise RuntimeError("Source action receipt absent")

    # A nonresident/unknown version must fail with a preserved typed receipt.
    failure_id = "hypothesis-" + run_id + ":source-b:unknown-version"
    status, _ = call(
        SOURCES["source-b"],
        "/execute/operator",
        payload={
            "action_id": failure_id,
            "action": {
                "operator": "read_artifact",
                "inputs": ["multihop:unknown-source-version"],
                "arguments": {},
            },
        },
    )
    receipt_status, failure_raw = call(SOURCES["source-b"], "/execute/receipt/" + failure_id)
    if status == 200 or receipt_status != 200 or json.loads(failure_raw)["status"] != "failed":
        raise RuntimeError("Unknown source version did not leave a failure receipt")

    # A protected source-a artifact moves over the study-owned Hfast proxy.
    source = chosen["source-a"]
    t0 = time.perf_counter()
    status, raw = call(
        SOURCES["source-b"],
        "/artifact/pull",
        payload={
            "artifact_id": source["artifact_id"],
            "source_url": PROXY + "/artifact/" + source["artifact_id"],
            "expected_sha256": source["content_hash"],
        },
    )
    transfer_ms = (time.perf_counter() - t0) * 1000
    if status != 200:
        raise RuntimeError("Metered pull failed: " + str(status))
    transfer = json.loads(raw)
    if (
        transfer["sha256_hex"] != source["content_hash"]
        or transfer["size_bytes"] != source["artifact_size"]
    ):
        raise RuntimeError("Metered transfer hash/byte mismatch")
    # Administrative cleanup is restricted to the study-created replica.
    delete = urllib.request.Request(
        SOURCES["source-b"] + "/artifact/" + source["artifact_id"], method="DELETE"
    )
    with urllib.request.urlopen(delete, timeout=30) as response:
        if response.status not in (200, 204):
            raise RuntimeError("Study replica cleanup failed")
    if source["artifact_id"] in {
        row["artifact_id"]
        for row in json.loads(call(SOURCES["source-b"], "/state")[1])["artifacts"]
    }:
        raise RuntimeError("Study replica remained after cleanup")

    result = {
        "schema_version": "infra-hypothesis-feasibility-v1",
        "started_unix": started,
        "controller_uid": os.getuid(),
        "denied_local_paths": denied,
        "forbidden_mount_count": len(forbidden_mounts),
        "manifest_sha256": hashlib.sha256(
            Path("/study/source-residency.jsonl").read_bytes()
        ).hexdigest(),
        "manifest_count": len(expected),
        "worker_counts": {node: len(state) for node, state in states.items()},
        "unauthorized_status": unauthorized,
        "authorized_read_receipts": [
            "hypothesis-" + run_id + ":source-a:read",
            "hypothesis-" + run_id + ":source-b:read",
        ],
        "failure_receipt": {
            "action_id": failure_id,
            "http_status": status,
            "receipt_status": "failed",
        },
        "transfer": {
            "artifact_id": source["artifact_id"],
            "sha256": transfer["sha256_hex"],
            "bytes": transfer["size_bytes"],
            "latency_ms": round(transfer_ms, 3),
            "proxy": "Hfast:63206",
            "replica_cleaned": True,
        },
        "ended_unix": time.time(),
    }
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "p1": "pass",
                "manifest_count": len(expected),
                "transfer_bytes": transfer["size_bytes"],
            }
        )
    )


if __name__ == "__main__":
    main()
