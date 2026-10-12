"""Reconcile the completed original delivery without inference or token replay."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import subprocess
import tarfile
from pathlib import Path


BASELINE = "a8da9a76fdcc13611c8e596bd28e03446ea5e1d1"
PREFIX = "research/planning_skills_v1/"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path):
    return json.loads(path.read_text(encoding="utf8"))


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=repo, text=True).strip()


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def audit(root: Path, private_archive: Path) -> dict:
    repo = root.parents[1]
    index = read(root / "evidence/final-evidence-index.json")
    delivery = read(root / "evidence/final-private-delivery-verification.json")
    require(delivery["status"] == "pass", "Original member verification missing")
    require(len(index["studies"]) == 13, "Stage population differs")
    require(len(index["episodes"]) == 1012, "Recorded workflow index differs")
    require(len(index["decision_probes"]) == 2316, "Decision index differs")
    require(sum(not e["engineering_invalidated"] for e in index["episodes"]) == 1000,
            "Valid workflow population differs")
    archives = [(private_archive, index["archive"])]
    source_index = read(root / "evidence/final-frozen-source-index.json")
    archives.append((root / "evidence/final-frozen-inference-source.tar.gz", source_index["archive"]))
    for path, expected in archives:
        require(path.stat().st_size == expected["bytes"] and sha(path) == expected["sha256"],
                f"Archive changed: {path.name}")
    # Original per-member verification is retained. Reconcile the public source
    # archive's allowlist; never extract an archive or expose private raw contents.
    with tarfile.open(archives[1][0], "r:gz") as bundle:
        names = [m.name for m in bundle.getmembers() if m.isfile()]
    require(len(names) == len(set(names)) == 242, "Source archive member population")
    require(all(Path(n).suffix in (".py", ".sh") and ".." not in Path(n).parts
                and not Path(n).is_absolute() for n in names), "Source archive allowlist")
    preparation = read(root / "evidence/final-artifact-preparation.json")
    require(preparation["status"] == "pass", "Final preparation not passed")
    for name, expected in preparation["outputs"].items():
        path = private_archive if name == private_archive.name else root / "evidence" / name
        require(path.stat().st_size == expected["bytes"] and sha(path) == expected["sha256"],
                f"Frozen preparation output changed: {name}")

    indexed_episodes = {(e["stage"].split("/")[1], e["model"], e["episode_id"]): e
                        for e in index["episodes"] if not e["engineering_invalidated"]}
    group_count = workflow_requests = workflow_prompt = workflow_output = 0
    totals = {}
    for stage, count in (("diagnostic-v2", 64), ("role-placement-v1", 48),
                         ("heldout-binding-v1", 504), ("structural-transfer-v1", 384)):
        directory = root / "results" / stage
        rows = read(directory / "episode-results.json")
        summary = read(directory / "summary.json")
        require(len(rows) == count, f"Incomplete cohort: {stage}")
        keys = {(row["model"], row["episode_id"]) for row in rows}
        require(len(keys) == count, f"Duplicate episode: {stage}")
        for row in rows:
            record = indexed_episodes[(stage, row["model"], row["episode_id"])]
            require(row["trace_sha256"] == record["trace_sha256"], "Trace-index mismatch")
            require(row["completion"] == record["completion"] and row["success"] == record["success"],
                    "Published outcome differs from original indexed outcome")
            require(row["local_gpu_usd"] is None and row["cloud_calls"] == 0, "Cost invention")
        for group in summary["groups"]:
            selected = [r for r in rows if [r["model"], r["condition"]] == group["group"]]
            require(len(selected) == group["n"], "Group denominator differs")
            require(sum(r["completion"] for r in selected) == group["completion_count"], "Completion differs")
            require(sum(r["success"] for r in selected) == group["success_count"], "Success differs")
            for field in ("turns", "prompt_tokens", "completion_tokens"):
                require(sum(r[field] for r in selected) == group[field], f"Group work differs: {field}")
            group_count += 1
        workflow_requests += sum(r["turns"] for r in rows)
        workflow_prompt += sum(r["prompt_tokens"] for r in rows)
        workflow_output += sum(r["completion_tokens"] for r in rows)
        totals[stage] = {"episodes": count, "completion": sum(r["completion"] for r in rows),
                         "numeric_success": sum(r["success"] for r in rows)}
        if stage in ("heldout-binding-v1", "structural-transfer-v1"):
            totals[stage]["numeric_policy_collisions"] = sum(r["numeric_success_with_policy_violation"] for r in rows)
            totals[stage]["policy_compliant_success"] = sum(bool(r["success"] and r["submitted_provenance_policy_compliant"]) for r in rows)
    require(group_count == 36 and workflow_requests == 27388, "Workflow inventory differs")
    require(totals["heldout-binding-v1"]["policy_compliant_success"] == 20, "Primary ancestry differs")
    require(totals["structural-transfer-v1"]["policy_compliant_success"] == 7, "Transfer ancestry differs")
    general = read(root / "results/decision-generalization-v1/decision-results.json")
    require(len(general) == 2028, "Incomplete diagnostic")
    require(len({(r["model"], r["condition"], r["query_id"]) for r in general}) == 2028,
            "Duplicate diagnostic execution")
    require(all(r["schema_valid"] and r["target_correct"] for r in general), "Diagnostic validity differs")
    for row in general:
        require(not ({"messages", "history", "raw_output", "gold_operator", "observed_values"} & row.keys()),
                "Private probe content in public output")
    general_summary = read(root / "results/decision-generalization-v1/summary.json")
    for group in general_summary["groups"]:
        selected = [r for r in general if r["model"] == group["model"] and r["condition"] == group["condition"]]
        require(len(selected) == group["n"] == 338, "Probe group population")
        require(sum(r["decision_correct"] for r in selected) == group["decision_correct"], "Probe score differs")

    resources = read(root / "evidence/final-resource-work.json")["stages"]
    recorded = read(root / "evidence/final-derived-totals.json")
    require(sum(s["logical_model_requests"] for s in resources) == recorded["all_recorded_model_requests"] == 30108,
            "Recorded requests differ")
    require(sum(s["physical_generate_batches"] for s in resources) == recorded["physical_generate_batches"] == 14498,
            "Physical work differs")
    require(sum(s["unpadding_prompt_tokens"] for s in resources) == recorded["all_recorded_prompt_tokens"] == 86048955,
            "Prompt work differs")
    require(math.isclose(sum(s["model_service_batch_wall_seconds"] for s in resources),
                         recorded["batch_service_wall_seconds"], abs_tol=1e-6), "Service wall differs")
    dev_probe = read(root / "results/decision-context-probe-v1/summary.json")
    dev_groups = [g for model in dev_probe.values() for g in model["groups"]]
    require(workflow_prompt + sum(r["prompt_tokens"] for r in general)
            + sum(g["prompt_tokens"] for g in dev_groups) == recorded["all_recorded_prompt_tokens"] - recorded["engineering_prompt_tokens"],
            "Valid prompt accounting differs")
    require(workflow_output + sum(r["completion_tokens"] for r in general)
            + sum(g["completion_tokens"] for g in dev_groups) == recorded["valid_completion_tokens"] == 857212,
            "Valid completion accounting differs")
    for name, count in (("model-stage-work.csv", 13), ("workflow-condition-results.csv", 36)):
        with (root / "results" / name).open(encoding="utf8", newline="") as f:
            require(len(list(csv.DictReader(f))) == count, "CSV inventory differs")

    verification = read(root / "results/structural-transfer-v1/publication-verification-v2.json")
    for name, digest in verification["verified_files"].items():
        require(sha(root / "results/structural-transfer-v1" / name) == digest, "Transfer publication changed")
    guard_receipt = read(root / "evidence/final-guard-shutdown-regression.json")
    require(sha(root / "runtime_guard.py") == guard_receipt["source_sha256"], "Guard regression stale")
    require(read(root / "evidence/final-model-byte-recheck.json")["status"] == "pass", "Weight recheck absent")
    require(read(root / "evidence/final-backup-and-cleanup-precheck.json")["status"] == "pass", "Backup absent")
    require(read(root / "evidence/final-shutdown-observation.json")["actual_provider_invoice"] == "unknown",
            "Billing uncertainty lost")

    documents = ("README.md", "final-research-report.md", "completion-evidence-map.md", "research-landscape.md",
                 "literature-novelty-ledger.md", "research-journal.md", "mechanism-ablations.md", "reproducibility.md")
    for name in documents:
        text = (root / name).read_text(encoding="utf8")
        for target in re.findall(r"\]\(([^)]+)\)", text):
            if re.match(r"[A-Za-z]+://", target) or target.startswith("#"):
                continue
            relative = target.split("#")[0]
            require((root / relative).exists(), f"Broken document link in {name}: {relative}")
    report = (root / "final-research-report.md").read_text(encoding="utf8")
    require(not any(word in report for word in ("待填", "尚未完成", "内部草稿")), "Report unfinished")
    for field in ("Problem Statement", "Closest Related Work", "Unresolved Gap", "Proposed Mechanism",
                  "Supporting Experimental Evidence", "Alternative Explanations", "Expected Novelty",
                  "Required Next Experiments", "Risks and Failure Cases"):
        require(field in report, f"Recommendation field missing: {field}")

    changed = set(git(repo, "diff", "--name-only", BASELINE).splitlines())
    changed.update(git(repo, "ls-files", "--others", "--exclude-standard").splitlines())
    require(all(p == ".gitattributes" or p.startswith(PREFIX) for p in changed), "Historical scope changed")
    require(not git(repo, "diff", "HEAD", "--", PREFIX + "configs"), "Frozen config changed during final publication")
    attribute_diff = git(repo, "diff", BASELINE, "--", ".gitattributes")
    edits = [line[1:] for line in attribute_diff.splitlines() if line[:1] in ("+", "-")
             and not line.startswith(("+++", "---"))]
    require(all(line.startswith("/" + PREFIX) for line in edits), "Unscoped attributes changed")
    forbidden = ("device_info", "raw-decisions.jsonl", "private-queries", "-traces.tar.gz", "id_rsa", "id_ed25519", ".env")
    credential_patterns = [rb"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----",
                           rb"\bAKIA[0-9A-Z]{16}\b", rb"\bsk-[A-Za-z0-9_-]{32,}\b",
                           rb"\bhf_[A-Za-z0-9]{30,}\b"]
    for name in changed:
        path = repo / name
        require(not any(s in path.name for s in forbidden), "Private filename in publication scope")
        if path.is_file():
            data = path.read_bytes()
            require(not any(re.search(pattern, data) for pattern in credential_patterns), "Credential-shaped content in publication")
            if path.suffix == ".py":
                compile(data, str(path), "exec")

    return {"status": "pass", "baseline": BASELINE, "branch": git(repo, "branch", "--show-current"),
            "studies": totals, "valid_workflows": 1000, "decision_queries": 2316,
            "recorded_requests": 30108, "physical_batches": 14498, "workflow_groups": group_count,
            "private_archive_sha256": sha(private_archive), "source_archive_members": len(names),
            "report_sha256": sha(root / "final-research-report.md"), "documents_checked": list(documents),
            "scope": "Only research/planning_skills_v1 and its scoped .gitattributes rules",
            "checks": "Original outcomes/index/work totals/publication hashes/archives/links/fields/source syntax/scope/credential-shaped content",
            "note": "No inference or repeated exact-token/tool replay. Original member/audit receipts retained. Credential scan is targeted, not an exhaustive secrecy proof. Invoice and independent billing acknowledgement unknown. Git publication is verified separately after commit/push."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(Path(__file__).resolve().parent, args.private_archive)
    with args.output.open("x", encoding="utf8") as out:
        json.dump(result, out, indent=2, sort_keys=True)
        out.write("\n")
    print(json.dumps({k: result[k] for k in ("status", "valid_workflows", "decision_queries", "recorded_requests")}))
