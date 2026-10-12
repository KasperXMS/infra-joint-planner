"""Once-only final evidence preparation after the already selected studies finish.

No inference, new experiments, retries, prompt changes or active-source mutations.
The controller waits for unified audits, preserves their original outputs, then
prepares versioned analysis, checkpoint-byte verification and private evidence.
"""
import argparse
import hashlib
import io
import json
import os
import subprocess
import tarfile
import time
from pathlib import Path

from runtime_guard import append, register


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_new(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)


def audits_ready(root):
    for experiment in ("heldout-binding-v1", "structural-transfer-v1", "decision-generalization-v1"):
        stage = root / "results" / experiment
        for model in ("Qwen3.5-4B", "Qwen3.5-9B"):
            if not (stage / model / "complete.json").exists():
                return False
        receipt = stage / "analysis/postprocess-complete.json"
        if not receipt.exists():
            return False
        try:
            status = json.loads(receipt.read_text()).get("status")
        except json.JSONDecodeError:
            return False  # The once-only writer may have just opened its receipt.
        if status != "pass":
            raise RuntimeError(f"Unified audit did not pass: {experiment}")
    return True


def verify_checkpoint_bytes(root, output):
    models = []
    for model in ("Qwen3.5-4B", "Qwen3.5-9B"):
        identity_path = root / f"{model}-identity.json"
        identity = json.loads(identity_path.read_text())
        directory = Path(identity["local_path"])
        files = []
        for record in identity["files"]:
            path = directory / record["path"]
            actual_sha = digest(path)
            if path.stat().st_size != record["bytes"] or actual_sha != record["sha256"]:
                raise RuntimeError(f"Checkpoint bytes changed: {model}, {record['path']}")
            files.append({"path": record["path"], "bytes": record["bytes"], "sha256": actual_sha})
        models.append({"model": model, "identity_sha256": digest(identity_path), "files": files})
    write_new(output, {"status": "pass", "epoch": time.time(), "models": models,
                       "note": "Once-only post-inference recheck of every original checkpoint/config/tokenizer byte hash; no inference or replacement download."})


def export_public_source(raw_index, private_archive, output, archive):
    index = json.loads(raw_index.read_text())
    if archive.exists() or output.exists():
        raise RuntimeError("Existing final source export")
    expected = {f["path"]: f for f in index["files"] if Path(f["path"]).suffix in (".py", ".sh")}
    members = []
    with tarfile.open(private_archive, "r:gz") as original, archive.open("xb") as destination:
        with tarfile.open(fileobj=destination, mode="w:gz", compresslevel=6) as public:
            for member in original:
                if member.name not in expected:
                    continue
                data = original.extractfile(member).read()
                record = expected[member.name]
                if len(data) != record["bytes"] or hashlib.sha256(data).hexdigest() != record["sha256"]:
                    raise RuntimeError("Source bytes differ from final evidence index")
                copied = tarfile.TarInfo(member.name)
                copied.size, copied.mtime, copied.mode = len(data), int(index["snapshot_epoch"]), 0o644
                public.addfile(copied, io.BytesIO(data))
                members.append(record)
    if {f["path"] for f in members} != set(expected):
        raise RuntimeError("Incomplete frozen-source export")
    write_new(output, {"status": "pass", "files": sorted(members, key=lambda x: x["path"]),
                       "archive": {"filename": archive.name, "bytes": archive.stat().st_size, "sha256": digest(archive)},
                       "note": "Exact executed/frozen Python and shell sources from the final private evidence snapshot, including later transfer, queued diagnostic and final-analysis revisions. Configs, histories, values, traces, download logs and credentials are excluded. Earlier source export remains unchanged."})


def main(root, analysis_source):
    register(root, "final_research_artifacts")
    source = Path(__file__).parent
    python = str(root / ".venv/bin/python")
    checkpoints = root / "checkpoints"
    receipt = checkpoints / "final-artifact-preparation.json"
    if receipt.exists():
        raise RuntimeError("Final artifact controller already ran")
    append(root / "administration.jsonl", {"epoch": time.time(), "event": "final_artifact_controller_started",
                                           "pid": os.getpid(), "source_sha256": {p.name: digest(p) for p in source.glob("*.py")}})
    while not audits_ready(root):
        if (root / "STOP").exists() or (root / "SYSTEM_ISSUE").exists():
            raise RuntimeError("System STOP before final completion; retain partial evidence")
        time.sleep(30)
    begun = time.time()
    primary = root / "results/heldout-binding-v1/analysis-v2/postprocess-complete.json"
    if json.loads(primary.read_text()).get("status") != "pass":
        raise RuntimeError("Primary versioned final analysis is not verified")
    transfer = root / "results/structural-transfer-v1"
    subprocess.run([python, str(analysis_source / "finalize_analysis.py"), "--root", str(transfer),
                    "--output", str(transfer / "analysis-v2")], check=True)
    verify_checkpoint_bytes(root, checkpoints / "final-model-byte-recheck.json")
    subprocess.run([python, str(source / "summarize_resources.py"), "--root", str(root),
                    "--output", str(checkpoints / "final-resource-work.json")], check=True)
    raw_index = checkpoints / "final-evidence-index.json"
    raw_archive = checkpoints / "planning-skills-research-v1-traces.tar.gz"
    subprocess.run([python, str(source / "make_evidence_index.py"), "--root", str(root),
                    "--output", str(raw_index), "--archive", str(raw_archive)], check=True)
    source_index = checkpoints / "final-frozen-source-index.json"
    source_archive = checkpoints / "final-frozen-inference-source.tar.gz"
    export_public_source(raw_index, raw_archive, source_index, source_archive)
    write_new(receipt, {"status": "pass", "begun_epoch": begun, "finished_epoch": time.time(),
                        "controller_source_sha256": digest(Path(__file__)),
                        "outputs": {p.name: {"bytes": p.stat().st_size, "sha256": digest(p)} for p in
                                    (raw_index, raw_archive, source_index, source_archive,
                                     checkpoints / "final-model-byte-recheck.json", checkpoints / "final-resource-work.json")},
                        "note": "All selected model inference and original unified audits completed before preparation. This is not proof that interpretation, private archive transfer/member verification, final report, publication or instance cleanup is complete."})
    append(root / "administration.jsonl", {"epoch": time.time(), "event": "final_artifact_preparation_complete", "pid": os.getpid()})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--analysis-source", required=True, type=Path)
    args = parser.parse_args()
    main(args.root, args.analysis_source)
