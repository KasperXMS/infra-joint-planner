"""One frozen 30-cell batch: real SDK/tools, one startup and one final audit.

Only experiment administration is new. Agent, tool, verifier, evaluator and
physical scheduling implementations are reused without changing their behavior.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import signal
import subprocess
import sys
from pathlib import Path
from time import monotonic, time

import agents
import httpx
import lightweight_planner_pilot_v2 as pilot
import yaml
from lightweight_planner_roles_v1 import manager_instructions
from multiscale_planner_context_v1 import MultiscaleContextPreflight
from sdk_native_infra_preliminary_v1_3 import _load_control_plane_key
from skill_granularity_service_v2_slot0 import Service, bootstrap

from infra_joint.experiments.manager_context import truncation_events

ROOT = Path("/home/super/xiaoming/skill-granularity-pilot-v2/run-001")
APP = Path(__file__).resolve().parents[1]
SELECTION = Path("/home/super/xiaoming/skill-granularity-pilot-v1/preparation/task-freeze-001")
PLAN_PATH = APP / "configs/experiments/skill-granularity-pilot-v2.json"
OLD = Path("/home/super/xiaoming/multiscale-planner-evaluation-v1/run-001")
PORTS = {"A4": 64004, "A5": 64005, "A28": 64028, "strong-4090": 64112}
write = pilot.write_new
ACTIVE_SKILL_TEXT = None
TASK_CACHE = {}
SERVICE = None
BASELINE = None
LOG_OFFSETS = {}
NETWORK_OUTPUT = ROOT


def source_hashes():
    return {
        str(p.relative_to(APP)): pilot.digest(p)
        for folder in ("src", "scripts", "configs")
        for p in sorted((APP / folder).rglob("*"))
        if p.is_file() and "__pycache__" not in p.parts
    }


def protected_hashes():
    paths = set()
    for historical in (
        OLD,
        Path("/home/super/xiaoming/lightweight-planner-competence-v1/formal-pilot-003"),
        Path("/home/super/xiaoming/skill-granularity-pilot-v1/run-001"),
    ):
        paths.update(historical.glob("cells/*/sanitized-result.json"))
        paths.update(
            historical / n
            for n in ("journal.jsonl", "matrix-complete.json", "execution-freeze.json")
        )
    for historical in (
        OLD,
        Path("/home/super/xiaoming/lightweight-planner-competence-v1/formal-pilot-003"),
        Path("/home/super/xiaoming/skill-granularity-pilot-v1/run-001"),
    ):
        frozen = json.loads((historical / "execution-freeze.json").read_text())
        paths.update(Path(p) for p in frozen.get("protected_sha256", {}))
    paths.add(APP / "configs/skills/planner-procedural-v1.md")
    paths.update(p for p in SELECTION.rglob("*") if p.is_file())
    return {str(p): pilot.digest(p) for p in sorted(paths)}


def validate_order(plan):
    expected = {
        (model, skill, task)
        for model in ("qwen35-4b", "qwen35-9b", "qwen35-27b")
        for skill in (("S0", "S3") if model == "qwen35-27b" else ("S0", "S1", "S2", "S3"))
        for task in (1, 2, 3)
    }
    observed = [(c["candidate"], c["skill_condition"], c["task_index"]) for c in plan["order"]]
    if len(observed) != 30 or len(set(observed)) != 30 or set(observed) != expected:
        raise RuntimeError("matrix must contain the exact 30 unique preregistered cells")
    if len({c["cell_id"] for c in plan["order"]}) != 30:
        raise RuntimeError("cell identifiers must be unique")
    for cell in plan["order"]:
        task = plan["tasks"][cell["task_index"] - 1]
        if (cell["family"], cell["position"]) != (task["family"], task["position"]):
            raise RuntimeError("cell task does not match the frozen manifest")


def configure(plan, service):
    global SERVICE
    SERVICE = service
    pilot.ROOT = ROOT
    pilot.OWNER = ROOT.parent
    pilot.APP = APP
    pilot.SELECTION = SELECTION
    pilot.EDGE_ROOT = Path("/mnt/ssd/skill-granularity-pilot-v2/run-001")
    pilot.ARTIFACT_NAMESPACE = "skill-granularity-pilot-v2/run-001"
    pilot.RUN_PREFIX = "skill-granularity-v2-001"
    pilot.PORTS = PORTS
    pilot.OllamaManagerContextPreflight = MultiscaleContextPreflight
    pilot.PilotRequestBudget = service.budget_class()
    # Strict task/evaluator/artifact validation is done once, before dispatch.
    loader = pilot.frozen_task
    manifest = json.loads((SELECTION / "manifest.json").read_text())
    if pilot.digest(SELECTION / "manifest.json") != plan["task_freeze_sha256"]:
        raise RuntimeError("new task freeze drift")
    for task in plan["tasks"]:
        bundle, receipt = loader(SELECTION, manifest, task["family"], task["position"])
        if any(receipt[k] != task[k] for k in ("task_bundle_sha256", "agent_task_sha256")):
            raise RuntimeError("new task bundle differs from preregistration")
        TASK_CACHE[(task["family"], task["position"])] = (bundle, receipt)
    pilot.frozen_task = lambda _root, _manifest, family, position: TASK_CACHE[(family, position)]
    # Prices are the previously frozen price cards; do not resolve a new tariff.
    price = pilot.verified_prices(Path("/home/super/xiaoming/large-scale-cost-guidance-v1"), APP)
    pilot.verified_prices = lambda *_args: price
    # Use the exact frozen in-memory Skill bytes, rather than editable disk text.
    pilot.manager_instructions = lambda base, *, skills=None: manager_instructions(
        base, skills=ACTIVE_SKILL_TEXT
    )


async def startup_workers(cell, config, pool, out):
    async def start(agent):
        app = pilot.WORKER_APPS[agent]
        base = ROOT if pilot.HOSTS[agent] is None else pilot.EDGE_ROOT
        target = base / "worker-configs" / (config["run_id"] + "-" + agent + ".json")
        original = pilot.frozen._yaml(
            APP
            / "configs/experiments/workers/blind-3family-video-v1.3"
            / f"worker-{agent.lower()}.yaml"
        )
        worker = pilot.worker_config(
            {**pool, "worker_urls": config["worker_urls"]},
            original,
            agent,
            Path(config["fresh_worker_stores"][agent]),
        ).model_dump(mode="json")
        values = {
            "app": app,
            "target": str(target),
            "worker": worker,
            "store": config["fresh_worker_stores"][agent],
            "port": PORTS[agent],
            "log": str(base / "logs" / (config["run_id"] + "-" + agent + ".log")),
        }
        code = """import json,os,shutil,socket,subprocess
from pathlib import Path
v=VALUES
target=Path(v['target']); target.parent.mkdir(parents=True,exist_ok=True)
Path(v['log']).parent.mkdir(parents=True,exist_ok=True)
assert not target.exists() and not Path(v['store']).exists(), 'Worker namespace already used'
assert shutil.disk_usage(target.parent).free >= 5*1024**3, 'Worker disk budget'
with socket.socket() as s:
 s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1); s.bind(('0.0.0.0',v['port']))
with target.open('x') as f: json.dump(v['worker'],f)
env=dict(os.environ,PYTHONPATH=v['app']+'/src',OLLAMA_API_KEY='ollama')
p=subprocess.Popen([v['app']+'/.venv/bin/python','-m','infra_joint.cli','worker','--config',str(target)],
 cwd=v['app'],env=env,stdin=subprocess.DEVNULL,stdout=open(v['log'],'x'),stderr=subprocess.STDOUT,start_new_session=True)
print(json.dumps({'pid':p.pid,'config':str(target)}))
""".replace("VALUES", repr(values), 1)
        value = await asyncio.to_thread(pilot.node_json, agent, code)
        write(out / "worker-starts" / (agent + ".json"), value)
        return agent, value

    values = await asyncio.gather(*(start(a) for a in pilot.HOSTS), return_exceptions=True)
    pids = dict(v for v in values if isinstance(v, tuple))
    errors = [type(v).__name__ for v in values if isinstance(v, BaseException)]
    if errors:
        write(out / "private/worker-start-errors.json", errors)
    return pids, errors


async def cleanup_workers(pids, urls, out, context):
    deadline = monotonic() + 1260
    errors = []
    drained = not pids
    while pids and monotonic() < deadline:
        try:
            state = await pilot.states({a: urls[a] for a in pids})
            if all(v["in_flight"] == 0 for v in state.values()):
                resident = await pilot.resident_slots(BASELINE)
                planner = await SERVICE.slots(context)
                if all(
                    not s["is_processing"]
                    for ports in resident.values()
                    for slots in ports.values()
                    for s in slots
                ) and all(not s["is_processing"] for s in planner):
                    drained = True
                    write(out / "private/worker-state-drained.json", state)
                    write(out / "private/model-slots-drained.json", resident)
                    break
        except Exception as exc:
            errors.append("worker_drain:" + type(exc).__name__)
            break
        await asyncio.sleep(2)
    if not drained:
        errors.append("worker_or_model_drain_timeout")

    async def stop(agent, identity):
        code = """import json,os,signal,time
from pathlib import Path
v=IDENTITY
p=Path('/proc')/str(v['pid'])/'cmdline'
cmd=p.read_bytes().decode() if p.exists() else ''
assert not cmd or v['config'] in cmd, 'Worker PID ownership changed'
if cmd: os.kill(v['pid'],signal.SIGTERM)
for _ in range(20):
 if not p.exists() or not p.read_bytes(): break
 time.sleep(.5)
print(json.dumps({'exited':not p.exists() or not p.read_bytes()}))
""".replace("IDENTITY", repr(identity), 1)
        return agent, await asyncio.to_thread(pilot.node_json, agent, code)

    values = await asyncio.gather(*(stop(a, p) for a, p in pids.items()), return_exceptions=True)
    exited = {}
    for value in values:
        if isinstance(value, BaseException):
            errors.append("worker_stop:" + type(value).__name__)
        else:
            exited[value[0]] = value[1]["exited"]
    record = {
        "drained": drained,
        "verified_exited": len(exited) == len(pids) and all(exited.values()),
        "errors": errors,
        "owned_processes": pids,
    }
    write(out / "worker-shutdown.json", record)
    return record


async def checkpoint(out=None):
    """Light boundary: known PIDs, /api/ps, new log segments; never full audit."""

    async def node(agent):
        known = []
        for instance in BASELINE[agent]["instances"]:
            row = {k: instance[k] for k in ("target", "server", "runner", "log_path")}
            row["target"] = {
                **instance["target"],
                "expected_digest": instance["resident"]["models"][0]["digest"],
            }
            row["offset"] = LOG_OFFSETS.get(
                (agent, instance["target"]["instance"]), instance["log_bytes"]
            )
            known.append(row)
        code = """import hashlib,json,urllib.request
from pathlib import Path
known=KNOWN
intervals={}; offsets={}
for item in known:
 for kind in ('server','runner'):
  expected=item[kind]; p=Path('/proc')/str(expected['pid'])
  command=(p/'cmdline').read_bytes().decode().split('\\0')
  assert command==expected['command'], 'Executor identity changed'
  start_ticks=(p/'stat').read_text().rsplit(')',1)[1].split()[19]
  assert start_ticks==expected['start_ticks'], 'Executor PID reused'
 target=item['target']; url='http://127.0.0.1:'+str(target['port'])+'/api/ps'
 models=json.load(urllib.request.urlopen(url,timeout=5))['models']
 assert len(models)==1, 'Executor model count changed'
 assert models[0]['name']==target['derived_tag']+':latest', 'Executor model changed'
 assert models[0]['digest']==target['expected_digest'], 'Executor digest changed'
 assert models[0]['context_length']==32768, 'Executor context changed'
 log=Path(item['log_path']); assert log.stat().st_size>=item['offset'], 'Model log truncated'
 with log.open('rb') as f: f.seek(item['offset']); data=f.read()
 name=target['instance'];offsets[name]=log.stat().st_size
 intervals[name]={'text':data.decode(errors='replace'),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
print(json.dumps({'passed':True,'intervals':intervals,'offsets':offsets}))
""".replace("KNOWN", repr(known), 1)
        value = await asyncio.to_thread(pilot.node_json, agent, code)
        for name, offset in value["offsets"].items():
            LOG_OFFSETS[(agent, name)] = offset
        for interval in value["intervals"].values():
            text = interval["text"]
            if (
                truncation_events(text)
                or "out of memory" in text.lower()
                or "starting runner" in text.lower()
            ):
                raise RuntimeError("Executor OOM/reload/truncation")
        if out is not None:
            write(out / "private/residency-log-intervals" / (agent + ".json"), value)
        return agent, {name: interval["bytes"] for name, interval in value["intervals"].items()}

    return dict(await asyncio.gather(*(node(a) for a in pilot.HOSTS)))


async def measure_skill_tokens(candidate, context, texts):
    path = ROOT / ("skill-token-lengths-" + candidate + ".json")
    if path.exists():
        return
    async with httpx.AsyncClient(timeout=30) as client:

        async def count(text):
            response = await client.post(
                context.runner_url + "/tokenize", json={"content": text, "add_special": False}
            )
            response.raise_for_status()
            tokens = response.json()["tokens"]
            if not all(type(t) is int for t in tokens):
                raise RuntimeError("invalid tokenizer token IDs")
            return len(tokens)

        base = await count(pilot.MANAGER_INSTRUCTIONS)
        lengths = {}
        for condition, text in texts.items():
            lengths[condition] = {
                "utf8_bytes": len((text or "").encode()),
                "standalone_tokens": await count(text) if text else 0,
                "manager_instruction_tokens": await count(
                    manager_instructions(pilot.MANAGER_INSTRUCTIONS, skills=text)
                ),
            }
            lengths[condition]["manager_instruction_increment_tokens"] = (
                lengths[condition]["manager_instruction_tokens"] - base
            )
    write(
        path,
        {
            "candidate": candidate,
            "tokenizer_model_blob": context.model_blob,
            "method": "resident llama tokenizer add_special=false; no model generation",
            "base_instruction_tokens": base,
            "skills": lengths,
            "inference_calls": 0,
        },
    )


def cell_boundary(out, cleanup, expected_budget):
    problems = []
    if not cleanup["drained"] or not cleanup["verified_exited"] or cleanup["errors"]:
        problems.append("worker_cleanup_failed")
    budget = json.loads((out / "budget.json").read_text())
    for key in ("control_requests", "physical_requests", "helper_requests", "control_bytes"):
        if budget[key] > budget["limits"][key] or budget["limits"][key] != expected_budget[key]:
            problems.append("request_budget_protection_failed")
    for receipt in json.loads((out / "context-receipts.json").read_text()):
        if receipt.get("error_code") in {
            "context_integrity_failed",
            "context_preflight_unavailable",
        }:
            problems.append(receipt["error_code"])
        if (
            receipt.get("decision") == "allow"
            and receipt.get("http_status") == 200
            and not receipt.get("integrity_verified")
        ):
            problems.append("silent_context_integrity_failure")
    for p in (out / "private/api").rglob("*-usage.json"):
        if json.loads(p.read_text())["status"] in (401, 403):
            problems.append("provider_authentication_failed")
    if SERVICE.resource_failure:
        problems.append(SERVICE.resource_failure)
    administrative = out / "administrative-outcome.json"
    if administrative.exists():
        failure = json.loads(administrative.read_text()).get("failure") or {}
        if failure.get("exception_type") in {
            "NameError",
            "UnboundLocalError",
            "ImportError",
            "ModuleNotFoundError",
            "AttributeError",
            "KeyError",
            "AssertionError",
            "FileNotFoundError",
            "PermissionError",
        }:
            problems.append("controller_implementation_or_configuration_failure")
    return sorted(set(problems))


async def one_cell(cell, plan, context, pool, texts):
    global ACTIVE_SKILL_TEXT
    out = ROOT / "cells" / cell["cell_id"]
    out.mkdir(parents=True, exist_ok=False)
    run_id = pilot.RUN_PREFIX + "-" + cell["cell_id"]
    urls = {
        a: url.rsplit(":", 1)[0] + ":" + str(PORTS[a]) for a, url in pool["worker_urls"].items()
    }
    stores = {
        a: str(
            (Path("/home/super") if host is None else Path("/mnt/ssd"))
            / "heterogeneous-v1/artifacts"
            / pilot.ARTIFACT_NAMESPACE
            / cell["cell_id"]
            / a
        )
        for a, host in pilot.HOSTS.items()
    }
    config = {
        "run_id": run_id,
        "cell_id": cell["cell_id"],
        "worker_urls": urls,
        "fresh_worker_stores": stores,
        "network": {"regime": "fast", "bandwidth_mbps": 100, "added_rtt_ms": 5},
    }
    path = ROOT / "cell-configs" / (cell["cell_id"] + ".yaml")
    path.parent.mkdir(exist_ok=True)
    with path.open("x") as f:
        yaml.safe_dump(config, f)
    write(
        out / "cell-started.json",
        {
            "cell": cell,
            "pid": os.getpid(),
            "network_receipt": str(NETWORK_OUTPUT.relative_to(ROOT) / "tc-attestation.json"),
            "resume_policy": "claimed cell is never inferred again",
        },
    )
    pilot.journal("cell_started", cell=cell["cell_id"])
    ACTIVE_SKILL_TEXT = texts[cell["skill_condition"]]
    pilot.CONTEXT = context
    protocol = {
        **plan,
        "skills": plan["skills"][cell["skill_condition"]],
        "groups": {
            cell["group"]: {
                "manager_model": context.model,
                "request_extra_body": {"reasoning_effort": "none"},
            }
        },
    }
    started = monotonic()
    log_start = await SERVICE.log_size()
    sample_start = len(SERVICE.samples)
    pids, errors = await startup_workers(cell, config, pool, out)
    cleanup = None
    try:
        if errors:
            raise RuntimeError("worker_start_or_namespace_failed")
        write(out / "private/worker-state-before.json", await pilot.states(urls, fresh=True))
        await asyncio.wait_for(pilot.execute(cell, out, config, protocol), timeout=3840)
    finally:
        cleanup = await cleanup_workers(pids, urls, out, context)
    await checkpoint(out)
    interval = await SERVICE.log_interval(log_start)
    if cell["candidate"] != "qwen35-27b":
        write(out / "private/a28-planner-log-interval.json", interval)
    if truncation_events(interval["text"]) or "out of memory" in interval["text"].lower():
        raise RuntimeError("owned_Planner_OOM_or_truncation")
    write(
        out / "private/continuation-resources.json",
        {
            "manager_node": "strong-4090" if cell["candidate"] == "qwen35-27b" else "A28",
            "external_gpu_contention_authorized": True,
            "samples": SERVICE.samples[sample_start:],
            "resource_failure": SERVICE.resource_failure,
        },
    )
    problems = cell_boundary(out, cleanup, plan["request_budgets"])
    record = {
        "cell": cell,
        "attempt_recorded": True,
        "wall_ms_including_worker_lifecycle": (monotonic() - started) * 1000,
        "budget": json.loads((out / "budget.json").read_text()),
        "worker_cleanup": {
            "drained": cleanup["drained"],
            "verified_exited": cleanup["verified_exited"],
        },
        "system_problems": problems,
        "raw_result_present": (out / "runs" / run_id / "result.json").exists(),
    }
    write(out / "cell-finished.json", record)
    pilot.journal("cell_finished", cell=cell["cell_id"], system_problems=problems)
    if problems:
        raise RuntimeError("system_boundary:" + ",".join(problems))
    return record


async def recover_claimed(cell, context):
    """An interrupted claim consumes the attempt; drain it and never re-infer it."""
    out = ROOT / "cells" / cell["cell_id"]
    if (out / "cell-finished.json").exists():
        return
    config = yaml.safe_load((ROOT / "cell-configs" / (cell["cell_id"] + ".yaml")).read_text())
    pids = {p.stem: json.loads(p.read_text()) for p in (out / "worker-starts").glob("*.json")}
    if (out / "worker-shutdown.json").exists():
        cleanup = json.loads((out / "worker-shutdown.json").read_text())
    else:
        cleanup = await cleanup_workers(pids, config["worker_urls"], out, context)
    if cleanup["errors"] or not cleanup["drained"] or not cleanup["verified_exited"]:
        raise RuntimeError("interrupted_worker_cleanup_failed")
    write(
        out / "cell-finished.json",
        {
            "cell": cell,
            "interrupted_attempt": True,
            "no_reinference": True,
            "raw_result_present": (out / "runs" / config["run_id"] / "result.json").exists(),
            "system_problems": [],
        },
    )
    pilot.journal("interrupted_claim_retained", cell=cell["cell_id"], inference_repeated=False)


async def final_audit(plan, frozen, complete):
    """One full source/history/task audit after the continuous queue finishes."""
    actual_source = source_hashes()
    actual_protected = protected_hashes()
    source_ok = actual_source == frozen["source_sha256"]
    protected_ok = actual_protected == frozen["protected_sha256"]
    after = await pilot.residency()
    write(ROOT / "private/residency-final.json", after)
    pids_ok = all(
        b["server"] == a["server"] and b["runner"] == a["runner"] and b["target"] == a["target"]
        for node in BASELINE
        for b, a in zip(BASELINE[node]["instances"], after[node]["instances"], strict=True)
    )
    network_receipts = [
        ROOT / "tc-attestation.json",
        *ROOT.glob("resume-network-*/tc-attestation.json"),
    ]
    network_ok = True
    for receipt in network_receipts:
        tc = json.loads(receipt.read_text())
        network_ok &= not tc["cleanup_error"] and tc["original_qdisc"] == tc["restored_qdisc"]
    # inspect_cell is a final-only pass; its historical hash request uses this
    # single just-computed snapshot, rather than rescanning history per cell.
    pilot.protected_hashes = lambda: actual_protected
    cells = []
    analysis_errors = []
    for cell in plan["order"]:
        out = ROOT / "cells" / cell["cell_id"]
        if not (out / "cell-finished.json").exists():
            continue
        try:
            if (out / "sanitized-result.json").exists():
                cells.append(json.loads((out / "sanitized-result.json").read_text()))
                continue
            config = yaml.safe_load(
                (ROOT / "cell-configs" / (cell["cell_id"] + ".yaml")).read_text()
            )
            if not (out / "tc-attestation.json").exists():
                claim = json.loads((out / "cell-started.json").read_text())
                tc = json.loads(
                    (ROOT / claim.get("network_receipt", "tc-attestation.json")).read_text()
                )
                write(
                    out / "tc-attestation.json",
                    {**tc, "scope": "shared continuous batch network attestation"},
                )
            cleanup = json.loads((out / "worker-shutdown.json").read_text())
            row = pilot.inspect_cell(cell, out, config, cleanup, frozen["protected_sha256"])
            write(out / "sanitized-result.json", row)
            cells.append(row)
        except Exception as exc:
            analysis_errors.append(
                {"cell_id": cell["cell_id"], "exception_type": type(exc).__name__}
            )
    problems = sorted({p for c in cells for p in c["system_problems"]})
    if not source_ok:
        problems.append("source_drift")
    if not protected_ok:
        problems.append("historical_task_or_skill_drift")
    if not pids_ok:
        problems.append("Executor_identity_changed")
    if not network_ok:
        problems.append("network_restoration_failed")
    if analysis_errors:
        problems.append("final_analysis_incomplete")
    if list(ROOT.glob("**/service-cleanup-error.json")):
        problems.append("owned_service_cleanup_failed")
    receipt = {
        "version": "skill-granularity-final-integrity-v1",
        "matrix_complete": complete,
        "executed_cell_records": len(cells),
        "planned_cells": 30,
        "source_unchanged": source_ok,
        "protected_history_tasks_and_skills_unchanged": protected_ok,
        "original_five_executor_instances_unchanged": pids_ok,
        "network_restored": network_ok,
        "all_executed_workers_drained_and_exited": all(
            c["cleanup"]["drained"] and c["cleanup"]["verified_exited"] for c in cells
        ),
        "source_files_checked": len(actual_source),
        "protected_files_checked": len(actual_protected),
        "system_problems": sorted(set(problems)),
        "analysis_errors": analysis_errors,
        "semantic_retries": 0,
        "private_raw_evidence_exported": False,
    }
    target = (
        ROOT / "final-integrity.json" if complete else NETWORK_OUTPUT / "partial-integrity.json"
    )
    write(target, receipt)
    return receipt


async def main(args):
    global BASELINE, NETWORK_OUTPUT
    if sys.platform != "linux" or APP != ROOT / "app":
        raise RuntimeError("run only in the new isolated controller app")
    plan = json.loads(PLAN_PATH.read_text())
    validate_order(plan)
    texts = {}
    for name, skill in plan["skills"].items():
        texts[name] = None if name == "S0" else (APP / skill["path"]).read_text()
        if name != "S0" and pilot.digest(APP / skill["path"]) != skill["sha256"]:
            raise RuntimeError("Skill freeze drift")
    if (
        pilot.digest(APP / "configs/skills/planner-procedural-v1.md")
        != "d8b75f3ce6e76ab19fa16328acc7f4ffce56988ab5d6abd794c95866d9b1f422"
    ):
        raise RuntimeError("S1 must preserve the original bytes")
    _load_control_plane_key(args.api_key_file, "DASHSCOPE_API_KEY")
    agents.set_tracing_disabled(True)
    if not (ROOT / "a28-service.json").exists():
        await asyncio.to_thread(bootstrap, ROOT)
    service = Service(ROOT)
    configure(plan, service)
    BASELINE = await pilot.residency()
    service.baseline = BASELINE
    protected = protected_hashes()
    files = source_hashes()
    freeze_path = ROOT / "execution-freeze.json"
    if freeze_path.exists():
        if not args.resume:
            raise RuntimeError("batch already started; use --resume for untouched cells only")
        frozen = json.loads(freeze_path.read_text())
        if (
            frozen["source_sha256"] != files
            or frozen["protected_sha256"] != protected
            or frozen["plan"] != plan
        ):
            raise RuntimeError("resume cannot change frozen source, tasks, Skills or order")
        if (ROOT / "matrix-complete.json").exists():
            raise RuntimeError("completed batch cannot be run again")
        original_baseline = json.loads((ROOT / "private/residency-startup.json").read_text())
        for node in BASELINE:
            for previous, current in zip(
                original_baseline[node]["instances"], BASELINE[node]["instances"], strict=True
            ):
                if any(previous[k] != current[k] for k in ("server", "runner", "target")):
                    raise RuntimeError("resume cannot change matched Executor deployment")
    else:
        if args.resume:
            raise RuntimeError("resume requires the original execution freeze")
        frozen = {
            "version": "skill-granularity-execution-freeze-v1",
            "base_commit": plan["base_commit"],
            "plan": plan,
            "ordered_cells": plan["order"],
            "source_sha256": files,
            "protected_sha256": protected,
            "maximum_attempts": 30,
            "no_ability_gate": True,
            "full_audits": "startup and final only",
            "no_selective_reruns": True,
            "historical_phase2_resumed": False,
            "matrix_deadline_epoch": time() + plan["matrix_wall_ceiling_seconds"],
        }
        write(freeze_path, frozen)
        write(ROOT / "private/residency-startup.json", BASELINE)
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: (ROOT / "STOP").touch(exist_ok=True))
    await service.check_resource(force=True, wait_timeout=600)
    pool = pilot.frozen._yaml(APP / plan["infrastructure_design"]["model_pool_path"])
    urls = {
        a: url.rsplit(":", 1)[0] + ":" + str(PORTS[a]) for a, url in pool["worker_urls"].items()
    }
    batch_config = ROOT / "batch-network.yaml"
    if not batch_config.exists():
        with batch_config.open("x") as f:
            yaml.safe_dump(
                {
                    "run_id": "skill-granularity-v1-001",
                    "worker_urls": urls,
                    "network": {"regime": "fast", "bandwidth_mbps": 100, "added_rtt_ms": 5},
                },
                f,
            )
    # One shaping transaction covers the whole unchanged network regime.
    sequence = len(list(ROOT.glob("resume-network-*"))) + 1
    tc_output = ROOT if not args.resume else ROOT / f"resume-network-{sequence:03d}"
    NETWORK_OUTPUT = tc_output
    tc_output.mkdir(exist_ok=True)
    shaped_args = argparse.Namespace(
        config=batch_config, output=tc_output, endpoint_config=pilot.DEFAULT_ENDPOINTS
    )
    deadline = monotonic() + max(0, frozen["matrix_deadline_epoch"] - time())
    complete = False
    failure = None
    pilot.journal("batch_started", pid=os.getpid(), planned_cells=30, resume=args.resume)

    async def batch(_args):
        last_candidate = None
        context = None
        await checkpoint()
        for cell in plan["order"]:
            out = ROOT / "cells" / cell["cell_id"]
            if (out / "cell-finished.json").exists():
                continue
            if (ROOT / "STOP").exists() or monotonic() >= deadline:
                raise RuntimeError("STOP_or_matrix_wall_budget")
            if cell["candidate"] != last_candidate:
                context = await service.load(cell["candidate"])
                await measure_skill_tokens(cell["candidate"], context, texts)
                last_candidate = cell["candidate"]
            if (out / "cell-started.json").exists():
                await recover_claimed(cell, context)
                continue
            await service.check_resource(force=True, wait_timeout=600, deadline=deadline)
            await asyncio.wait_for(one_cell(cell, plan, context, pool, texts), timeout=5100)

    try:
        await pilot.run_shaped(shaped_args, execute_cell=batch)
        complete = all(
            (ROOT / "cells" / c["cell_id"] / "cell-finished.json").exists() for c in plan["order"]
        )
    except Exception as exc:
        failure = type(exc).__name__
        write(
            NETWORK_OUTPUT / "batch-stopped.json",
            {"exception_type": failure, "message": str(exc), "semantic_retries": 0},
        )
        pilot.journal("batch_stopped", exception_type=failure)
    finally:
        try:
            if complete:
                await service.close()
            else:
                await service.suspend()
        except Exception as exc:
            failure = failure or "owned_service_cleanup_failed"
            write(
                NETWORK_OUTPUT / "service-cleanup-error.json",
                {"exception_type": type(exc).__name__},
            )
    integrity = await final_audit(plan, frozen, complete)
    if complete and not integrity["system_problems"] and failure is None:
        write(ROOT / "matrix-complete.json", {"cells": 30, "attempts": 30, "semantic_retries": 0})
        pilot.journal("batch_complete", cells=30)
        output = ROOT.parent / "sanitized-final-001"
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "reporting/analyze_skill_granularity_pilot_v1.py"),
                "--root",
                str(ROOT),
                "--output",
                str(output),
            ],
            check=True,
        )
    else:
        raise RuntimeError(failure or "final_system_integrity_failure")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-key-file", type=Path, required=True)
    parser.add_argument("--resume", action="store_true")
    asyncio.run(main(parser.parse_args()))
