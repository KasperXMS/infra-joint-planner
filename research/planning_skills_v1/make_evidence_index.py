"""Final-only evidence index and private raw archive; no models/cache/credentials.

Refuses to export unfinished ability studies. Engineering-invalidated traces are
retained explicitly, including partial episodes and incurred work. Public index
contains hashes/counts/relative paths, never raw prompts or private data values.
"""
import argparse
import hashlib
import io
import json
import tarfile
import time
from pathlib import Path


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_jsonl(data):
    return [json.loads(line) for line in data.decode().splitlines() if line.strip()]


def collect(root):
    payload, studies, episodes, probes = {}, [], [], []
    groups = {}

    def capture(path):
        relative = str(path.relative_to(root)).replace("\\", "/")
        if relative not in payload:
            payload[relative] = path.read_bytes()
        return payload[relative]

    for manifest_path in sorted((root / "results").glob("*/*/frozen-manifest.json")):
        stage = manifest_path.parent
        manifest = json.loads(capture(manifest_path))
        config = manifest["config"]
        invalid_path = next((p for p in (stage / "engineering-invalidated.json", stage.parent / "engineering-invalidated.json") if p.exists()), None)
        invalid = json.loads(capture(invalid_path)) if invalid_path else None
        if not invalid and not (stage / "complete.json").exists():
            raise RuntimeError(f"Ability study is unfinished; no final export: {stage.relative_to(root)}")
        for name, digest in manifest["source_sha256"].items():
            source = stage / "frozen-source" / name
            if sha(capture(source)) != digest:
                raise RuntimeError(f"Frozen source mismatch: {source.relative_to(root)}")
        kind = "decision_probe_no_tools" if "queries" in config else "workflow"
        record = {"stage": str(stage.relative_to(root)), "model": stage.name, "kind": kind,
                  "engineering_invalidated": bool(invalid), "ability_evidence": not bool(invalid),
                  "manifest_sha256": sha(capture(manifest_path)), "config_sha256": manifest["config_sha256"],
                  "frozen_source_files_verified": len(manifest["source_sha256"])}
        if invalid:
            record["engineering_exclusion_reason"] = invalid["reason"]
        batches_path = stage / "service-batches.jsonl"
        batches = read_jsonl(capture(batches_path)) if batches_path.exists() else []
        record["physical_generate_batches"] = len(batches)
        record["logical_model_requests"] = sum(b["requests"] for b in batches)
        if kind == "workflow":
            expected = {t["task_id"] + "__" + c for t in config["tasks"] for c in config["conditions"]}
            directories = sorted((stage / "episodes").glob("*"))
            actual = {p.name for p in directories if (p / "result.json").exists()}
            if not invalid and actual != expected:
                raise RuntimeError("Missing/extra completed workflow identities")
            if not invalid and {p.name for p in directories} != expected:
                raise RuntimeError("Unexpected workflow directory")
            index_path = stage / "results.jsonl"
            indexed_results = read_jsonl(capture(index_path)) if index_path.exists() else []
            if len(indexed_results) != len(actual) or {r["episode_id"] for r in indexed_results} != actual:
                raise RuntimeError("Duplicate/missing completed result-index record")
            record.update(expected_episodes=len(expected), started_episodes=len(directories), completed_episodes=len(actual))
            for directory in directories:
                started = json.loads(capture(directory / "started.json"))
                result_path = directory / "result.json"
                result = json.loads(capture(result_path)) if result_path.exists() else None
                trace_path = directory / "trace.jsonl"
                trace = capture(trace_path) if trace_path.exists() else None
                trace_hash = sha(trace) if trace is not None else None
                if result and result["trace_sha256"] != trace_hash:
                    raise RuntimeError("Result trace hash differs from exact archived bytes")
                episodes.append({"stage": record["stage"], "model": stage.name, "episode_id": directory.name,
                                 "task_id": started["task"]["task_id"], "condition": started["condition"],
                                 "engineering_invalidated": bool(invalid),
                                 "state": "finished" if result else "interrupted_engineering",
                                 "trace_sha256": trace_hash, "trace_bytes": len(trace) if trace else 0,
                                 "trace_records": len(read_jsonl(trace)) if trace else 0,
                                 "completion": result["completion"] if result else None,
                                 "success": result["success"] if result else None})
        else:
            raw_path = stage / "raw-decisions.jsonl"
            raw = read_jsonl(capture(raw_path))
            expected = {(q["query_id"], c) for q in config["queries"] for c in config["conditions"]}
            if len(raw) != len(expected) or {(r["query_id"], r["condition"]) for r in raw} != expected:
                raise RuntimeError("Missing/duplicate probe identity")
            record.update(expected_probe_requests=len(expected), completed_probe_requests=len(raw))
            for line, result in enumerate(raw, 1):
                probes.append({"stage": record["stage"], "model": stage.name, "query_id": result["query_id"],
                               "condition": result["condition"], "raw_file": str(raw_path.relative_to(root)),
                               "line": line, "raw_file_sha256": sha(capture(raw_path)), "actual_tool_executions": 0})
        studies.append(record)
        experiment = stage.parent.name
        group = groups.setdefault(experiment, {"models": set(), "expected": set(config.get("models", [stage.name])), "ability": False})
        group["models"].add(stage.name)
        group["ability"] |= not bool(invalid)

    for experiment, group in groups.items():
        if group["ability"] and group["models"] != group["expected"]:
            raise RuntimeError(f"Missing model stages: {experiment}")
        if experiment in ("heldout-binding-v1", "structural-transfer-v1"):
            complete = root / "results" / experiment / "analysis/postprocess-complete.json"
            if not complete.exists() or json.loads(complete.read_text())["status"] != "pass":
                raise RuntimeError(f"Final postprocessing is unfinished: {experiment}")

    # Freeze exact final study/config/analysis bytes. Never copy weights, caches,
    # environments, root download logs, device-info or unlisted home files.
    for base in (root / "results", root / "configs"):
        for path in sorted(base.rglob("*")):
            if path.is_file() and path.suffix in (".json", ".jsonl", ".py", ".sh", ".csv", ".md", ".txt") and "__pycache__" not in path.parts:
                capture(path)
    names = ["resource-budget.json", "resources.jsonl", "administration.jsonl", "owned-processes.jsonl",
             "repository-file-sizes.json", "environment-freeze.txt",
             "structural-transfer-v1-launch-policy.json", "structural-transfer-v1-not-launched.json"]
    names += [path.name for path in root.glob("Qwen*-identity.json")]
    for name in names:
        path = root / name
        if path.exists():
            capture(path)
    index = {"snapshot_epoch": time.time(), "studies": studies, "episodes": episodes, "decision_probes": probes,
             "files": [{"path": name, "bytes": len(data), "sha256": sha(data)} for name, data in sorted(payload.items())],
             "note": "Public metadata index. Raw archive stays on experiment machine/shared storage and outside Git in the user's first workspace. Inference download logs, weights, caches and credentials are excluded. Mutable telemetry is a byte-exact snapshot."}
    return index, payload


def export(root, output, archive):
    if output.exists() or archive.exists():
        raise RuntimeError("Existing evidence export; never overwrite a previous archive/index")
    index, payload = collect(root)
    archive.parent.mkdir(parents=True, exist_ok=True)
    with archive.open("xb") as destination:
        with tarfile.open(fileobj=destination, mode="w:gz", compresslevel=6) as tar:
            for name, data in sorted(payload.items()):
                info = tarfile.TarInfo(name)
                info.size, info.mtime, info.mode = len(data), int(index["snapshot_epoch"]), 0o600
                tar.addfile(info, io.BytesIO(data))
    index["archive"] = {"filename": archive.name, "bytes": archive.stat().st_size, "sha256": sha(archive.read_bytes())}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x") as stream:
        json.dump(index, stream, indent=2, sort_keys=True)
    print(json.dumps({"stages": len(index["studies"]), "workflow_records": len(index["episodes"]),
                      "probe_requests": len(index["decision_probes"]), "files": len(payload), "archive": index["archive"]}))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--root", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--archive", required=True, type=Path)
    args = p.parse_args()
    export(args.root, args.output, args.archive)
