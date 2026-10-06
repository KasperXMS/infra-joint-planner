"""Exact input-cardinality repair boundary; no semantic tuning or policy retry."""

from __future__ import annotations

import base64
import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml
from run_predecision_matrix_v1 import HOSTS, remote_python

from infra_joint.control.capabilities import build_static_capability_contract
from infra_joint.control.provenance import provenance_sha256
from infra_joint.core.state import EnvironmentSpec
from infra_joint.operators.catalog import build_operator_catalog

APP_NAME = "app-input-cardinality-repair-003"
PARENT_APP_NAME = "app-quote-integrity-repair-002"
PARENT_SHA256 = "9dd761f7d4022ae262ada59e8f810b4ab2cac7106e50f0817093916861977198"
PARENT_FILE_SHA256 = "9153d795bc8898f55b2620f40357dfa22ab5bcb075ab7de780b650430f9deb07"
BUG_PROOF = "analysis/resident-cell110-mixed-gate-diagnosis-001.json"
BUG_SHA256 = "a03af848086dd78c8cb91522340ee3b80d6e016695785993f2d6366b8287c984"
PREFIX_SHA256 = "fe7249cca15c2dcddb26fcc438b9ccfde596b9090714c5ddf5b1bc8645b97bf3"
ORIGINAL_RUN = ("large-scale-cost-guidance-resident-v1-phase1-multihop_rag-1-"
                "29e45040dce39dae-p1-slow-E-attempt1")
ORIGINAL_ADMISSION_SHA256 = "7498f37e2144622ddb0c1e66ea258a1bce7a3d00aab9cb6528fd1f27844716a3"
STRUCTURED_PATH = "src/infra_joint/operators/structured.py"
STRUCTURED_SHA256 = "aba65515289760504aaa19005634ae83b7669c54aa40bb767eaea4a7bf4210f5"
CAPABILITY_SHA256 = "daf641106bb91e46dbcd354cc0b57f3205bfe840ba7bfcbd9cec0ddac524e013"
HARNESS = "configs/experiments/infra-aware-predecision-resident-cardinality-v1.yaml"
ALLOWED_DELTA = frozenset({
    STRUCTURED_PATH, "scripts/large_scale_resident_queue_v1.py",
    "scripts/large_scale_execution_v1.py",
    "scripts/large_scale_resident_cardinality_patch_v1.py", HARNESS,
})


def validate_source_delta(parent: dict[str, str], current: dict[str, str]) -> dict[str, Any]:
    changed = {p for p in parent.keys() | current.keys() if parent.get(p) != current.get(p)}
    if changed != ALLOWED_DELTA or current.get(STRUCTURED_PATH) != STRUCTURED_SHA256:
        raise RuntimeError("cardinality repair requires the exact audited source delta")
    return {p: {"parent_sha256": parent.get(p), "patched_sha256": current.get(p)}
            for p in sorted(changed)}


def validate_harness_delta(parent: dict[str, Any], current: dict[str, Any]) -> None:
    expected = deepcopy(parent)
    expected["static_capability_contract_sha256"] = CAPABILITY_SHA256
    if current != expected:
        raise RuntimeError("cardinality repair cannot tune prompts, tools, budgets or models")


def verify_bug_evidence(root: Path) -> dict[str, Any]:
    from resident_model_pool_attestation_v1 import sha256

    path = root / BUG_PROOF
    proof = json.loads(path.read_text())
    if (sha256(path) != BUG_SHA256 or proof["run_id"] != ORIGINAL_RUN
            or proof["original_admission_sha256"] != ORIGINAL_ADMISSION_SHA256
            or proof["execution_sha256"] != PARENT_SHA256
            or proof["filter_contract_mismatch_count"] != 1
            or proof["earlier_same_cardinality_affected_runs"]
            or proof["policy_replacement_authorized"]):
        raise RuntimeError("affected-only cardinality proof drift")
    directory = root / "evidence" / ORIGINAL_RUN.removeprefix(root.name + "-").removesuffix(
        "-attempt1") / "attempt1"
    files = {str(p.relative_to(directory)): sha256(p) for p in directory.rglob("*")
             if p.is_file()}
    if files != proof["original_evidence_file_sha256"] or any(
            p.is_symlink() for p in directory.rglob("*")):
        raise RuntimeError("original confounded evidence must remain immutable")
    return proof


def repaired_execution_freeze(app: Path) -> dict[str, Any]:
    import large_scale_resident_queue_v1 as frozen

    root = frozen.ROOT
    if app.resolve() != (root / APP_NAME).resolve():
        raise RuntimeError("cardinality repair requires a separate immutable app")
    parent_path = root / "execution-freeze-002.json"
    parent = json.loads(parent_path.read_text())
    if (frozen.sha256(parent_path) != PARENT_FILE_SHA256
            or provenance_sha256(parent) != PARENT_SHA256):
        raise RuntimeError("parent execution freeze drift")
    for path, digest in parent["source_sha256"].items():
        if frozen.sha256(root / PARENT_APP_NAME / path) != digest:
            raise RuntimeError("immutable parent source drift")
    current = {str(p.relative_to(app)): frozen.sha256(p)
               for folder in ("src", "scripts", "configs") for p in (app / folder).rglob("*")
               if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"}
    delta = validate_source_delta(parent["source_sha256"], current)
    old_harness = app / frozen.ResidentBlock.harness_manifest
    validate_harness_delta(yaml.safe_load(old_harness.read_text()),
                           yaml.safe_load((app / HARNESS).read_text()))
    verify_bug_evidence(root)
    tests_path = root / "readiness/input-cardinality-validation-001.json"
    tests = json.loads(tests_path.read_text())
    if (tests["commit_sha"] != frozen.frozen._revision() or tests["passed"] is not True
            or tests["source_delta"] != delta or not tests["deployment_regressions"]["passed"]
            or not all(tests["checks"][k]["passed"] for k in
                       ("pytest", "ruff", "pyright", "diff_check"))):
        raise RuntimeError("complete source-bound repair validation required")
    ready = root / "readiness/worker-surface-003"
    validation = json.loads((ready / "validation.json").read_text())
    shutdown = json.loads((ready / "shutdown-verified.json").read_text())
    if (not validation["passed"] or validation["workers"] != 4
            or validation["deployments"] != 5
            or validation["execution_app"] != str(app) or not shutdown["passed"]
            or validation["capability_sha256"] != CAPABILITY_SHA256):
        raise RuntimeError("new actual Worker surface/readiness validation required")
    environment = EnvironmentSpec.model_validate(frozen.frozen._yaml(frozen.POOL_CONFIG)[
        "environment"])
    operations = tuple(frozen.frozen._yaml(app / HARNESS)["available_operations"])
    capability = build_static_capability_contract(environment, build_operator_catalog(), operations)
    frozen.frozen.validate_harness(frozen.frozen.load_harness(app / HARNESS), environment,
                                  capability, operations)
    if (frozen.frozen._capability_sha256(capability) != CAPABILITY_SHA256
            or frozen.sha256(frozen.PREDECESSOR / "phase1-attempts.jsonl")
            != frozen.OLD_JOURNAL_SHA256
            or frozen.schedule_sha256(frozen.schedule()) != parent["phase1_schedule_sha256"]
            or frozen.verified_prices(frozen.PREDECESSOR, app)[1] != parent["pricing_sha256"]
            or frozen.calibration_receipts() != parent["calibration_receipts"]
            or frozen.environment_fingerprint(frozen.PREDECESSOR) != parent["decoder"]):
        raise RuntimeError("tasks, model calibration, pricing or environment drift")
    return {
        **parent, "version": "large-scale-resident-input-cardinality-repair-v3",
        "commit_sha": frozen.frozen._revision(), "source_sha256": current,
        "parent_execution_sha256": PARENT_SHA256,
        "parent_execution_file_sha256": PARENT_FILE_SHA256,
        "execution_app": str(app), "worker_app": str(app), "source_delta": delta,
        "harness_manifest_sha256": frozen.sha256(app / HARNESS),
        "capability_sha256": CAPABILITY_SHA256, "bug_review_sha256": BUG_SHA256,
        "validation_receipt_sha256": frozen.sha256(tests_path),
        "readiness_sha256": {name: frozen.sha256(ready / name) for name in (
            "worker-states.json", "static-capability.json", "validation.json",
            "shutdown-verified.json")},
        "affected_original_runs": [ORIGINAL_RUN], "repair_repetitions": 1,
        "ordinary_semantic_retries": False, "provider_policy_replacement": False,
        "preserved_substrate_source_sha256": {p: h for p, h in
                                              parent["preserved_substrate_source_sha256"].items()
                                              if p != STRUCTURED_PATH},
        "operator_vocabulary_changed": False, "operator_handlers_changed": False,
        "planner_prompt_changed": False, "budgets_changed": False, "scheduler_changed": False,
    }


def start_patched_worker(root: Path, config: Path, agent: str, store: str) -> int:
    """Same Worker startup behavior, with an explicit nonhistorical code archive."""
    from large_scale_execution_v1 import RESIDENT_ROOT

    if sys.platform != "linux" or root.resolve() != RESIDENT_ROOT or agent not in HOSTS:
        raise RuntimeError("patched Workers are remote resident-block execution only")
    host = HOSTS[agent]
    app = root / APP_NAME if host is None else Path("/mnt/ssd") / root.name / APP_NAME
    target_config = config if host is None else app.parent / config.name
    log = root / "logs" / (config.stem + ".log") if host is None else app.parent / (
        config.stem + ".log")
    if host is not None:
        subprocess.run(["scp", "-q", str(config), f"{host}:{target_config}"], check=True)
    payload = base64.b64encode(json.dumps({
        "app": str(app), "config": str(target_config), "log": str(log), "store": store,
    }).encode()).decode()
    code = (
        "import base64,json,os,subprocess; from pathlib import Path; "
        f"v=json.loads(base64.b64decode({payload!r})); "
        "assert not Path(v['store']).exists(), 'fresh store already exists'; "
        "Path(v['log']).parent.mkdir(parents=True,exist_ok=True); "
        "env=dict(os.environ,PYTHONPATH=v['app']+'/src',OLLAMA_API_KEY='ollama'); "
        "p=subprocess.Popen([v['app']+'/.venv/bin/python','-m','infra_joint.cli','worker',"
        "'--config',v['config']],cwd=v['app'],env=env,stdin=subprocess.DEVNULL,"
        "stdout=open(v['log'],'x'),stderr=subprocess.STDOUT,start_new_session=True); print(p.pid)"
    )
    output = (subprocess.run([sys.executable, "-c", code], check=True, capture_output=True,
                             text=True).stdout if host is None else remote_python(host, code))
    return int(output.strip())
