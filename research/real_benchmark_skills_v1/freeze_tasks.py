"""Verify unchanged official packages and emit a pre-outcome task selection lock.

This is a static content audit, not evidence that a sandbox or evaluator works.
Requires PyYAML. Never executes task, oracle, verifier, or skill code.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import yaml

COMMIT = "b63b7b2850226b6aa4fb5929a8c1ac7bc4d9a6af"
DEVELOPMENT = {
    "dialogue-parser": "dialogue-graph-parsing",
    "azure-bgp-oscillation-route-leak": "bgp-route-analysis",
    "econ-detrending-correlation": "economic-time-series-detrending",
    "crystallographic-wyckoff-position-analysis": "crystal-symmetry",
    "adaptive-cruise-control": "vehicle-pid-control",
    "court-form-filling": "pdf-form-filling",
    "dapt-intrusion-detection": "packet-intrusion-detection",
    "civ6-adjacency-optimizer": "hex-grid-game-optimization",
}
EVALUATION = {
    "spring-boot-jakarta-migration": "java-framework-migration",
    "tictoc-unnecessary-abort-detection": "transaction-concurrency-analysis",
    "data-to-d3": "web-data-visualization",
    "sec-financial-report": "sec-institutional-holdings-analysis",
    "xlsx-recover-data": "spreadsheet-data-reconciliation",
    "lab-unit-harmonization": "lab-unit-harmonization",
    "gravitational-wave-detection": "gravitational-wave-matched-filtering",
    "glm-lake-mendota": "lake-model-calibration",
    "radar-vital-signs": "radar-vital-sign-extraction",
    "manufacturing-fjsp-optimization": "manufacturing-job-shop-scheduling",
    "manufacturing-codebook-normalization": "manufacturing-code-normalization",
    "pddl-airport-planning": "pddl-airport-planning",
    "bike-rebalance": "bike-inventory-routing",
    "software-dependency-audit": "software-vulnerability-audit",
    "setup-fuzzing-py": "python-fuzzer-setup",
    "offer-letter-generator": "docx-offer-letter-generation",
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def content_digest(files: dict[str, str]) -> str:
    digest = hashlib.sha256()
    for name in sorted(files):
        digest.update(name.encode("utf8") + b"\0" + bytes.fromhex(files[name]))
    return "sha256:" + digest.hexdigest()


def freeze(source: Path, manifest: Path) -> dict:
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=source, text=True).strip()
    if revision != COMMIT:
        raise ValueError("Wrong SkillsBench revision")
    official = json.loads(manifest.read_bytes())
    if official["commit"] != COMMIT or official["active_task_count"] != 87:
        raise ValueError("Unexpected release manifest")
    tasks = {t["name"]: t for t in official["tasks"] if not t["excluded"]}
    output = {"benchmark": "skillsbench", "release": "v1.1", "commit": COMMIT,
              "created_utc": datetime.now(timezone.utc).isoformat(),
              "release_manifest_sha256": sha(manifest.read_bytes()),
              "selection_status": "content_frozen_before_outcomes; sandbox_feasibility_pending",
              "oracle_runs": 0, "agent_runs": 0, "tasks": []}
    split_skills: dict[str, set[str]] = {}
    for split, selected in (("development", DEVELOPMENT), ("evaluation", EVALUATION)):
        split_skills[split] = set()
        for task_id, family in selected.items():
            task = tasks[task_id]
            root = source / task["path"]
            for required in ("task.md", "environment/Dockerfile", "environment/skills", "oracle", "verifier"):
                if not (root / required).exists():
                    raise ValueError(f"Missing {task_id}/{required}")
            files = {p.relative_to(root).as_posix(): sha(p.read_bytes())
                     for p in root.rglob("*") if p.is_file() and not p.is_symlink()}
            digest = content_digest(files)
            if digest != task["digest"]:
                raise ValueError(f"Official content mismatch: {task_id}; check Git line endings")
            text = (root / "task.md").read_text(encoding="utf8")
            config = yaml.safe_load(text.split("---", 2)[1])
            if config["metadata"]["category"] != task["category"]:
                raise ValueError(f"Metadata mismatch: {task_id}")
            skills = sorted(p.name for p in (root / "environment/skills").iterdir() if p.is_dir())
            split_skills[split].update(skills)
            output["tasks"].append({"id": task_id, "split": split, "family": family,
                "category": task["category"], "difficulty": task["difficulty"],
                "tags": task["tags"], "official_task_digest": digest,
                "skill_directories": skills, "files_sha256": dict(sorted(files.items())),
                "skill_digest": content_digest({k: v for k, v in files.items() if k.startswith("environment/skills/")}),
                "evaluator_digest": content_digest({k: v for k, v in files.items() if k.startswith("verifier/")}),
                "environment_digest": content_digest({k: v for k, v in files.items() if k.startswith("environment/")}),
                "agent": config.get("agent"), "verifier": config.get("verifier"),
                "environment": config.get("environment"), "sandbox_feasibility": "not_tested"})
    overlap = split_skills["development"] & split_skills["evaluation"]
    if overlap or set(DEVELOPMENT) & set(EVALUATION):
        raise ValueError(f"Split overlap: {sorted(overlap)}")
    if len({t["category"] for t in output["tasks"]}) < 4:
        raise ValueError("Insufficient domain coverage")
    output["skill_directory_overlap"] = []
    output["family_review"] = "Manual task-family labels plus zero shared skill directory names; semantic/content duplication audit pending before S2 design."
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = freeze(args.source, args.manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf8")
    print(json.dumps({"tasks": len(result["tasks"]), "status": result["selection_status"]}))
