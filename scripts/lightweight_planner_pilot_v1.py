"""One isolated, sequential, bounded 18-cell competence pilot; no capability gates."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import signal
import subprocess
import sys
from collections import Counter
from contextlib import AsyncExitStack
from dataclasses import asdict, replace
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic
from types import SimpleNamespace

import agents
import httpx
import yaml
from large_scale_execution_v1 import TASK_FREEZE_SHA256, frozen, frozen_task
from large_scale_repair_freeze_v1 import verified_prices
from lightweight_planner_context_gate_v1 import CONFIG as CONTEXT
from lightweight_planner_roles_v1 import manager_instructions, role_isolated_sdk
from lightweight_planner_tc_v1 import run_shaped
from openai import AsyncOpenAI as AsyncOpenAIClient
from prepare_resident_worker_v1 import worker_config
from resource_blind_live_validation_v1 import MANAGER_INSTRUCTIONS
from run_predecision_matrix_v1 import HOSTS, remote_python
from run_sdk_native_infra_cell_with_tc_v1_3 import DEFAULT_ENDPOINTS
from sdk_native_infra_preliminary_v1_3 import ModelRequestBodyAdapter, _load_control_plane_key

from infra_joint.config import PlannerConfig, RunnerConfig, StaticBackendConfig
from infra_joint.control.capabilities import build_static_capability_contract
from infra_joint.control.contracts import ProfileVisibility
from infra_joint.control.native_agents import OpenAIAgentsNativeRuntime
from infra_joint.control.provenance import blind_input_profile_findings
from infra_joint.control.runner import ControlPlaneBenchmarkRunner
from infra_joint.control.verification import OpenAIAgentsBlindVerifier
from infra_joint.core.state import LinkSpec
from infra_joint.experiments.api_cost import APIPriceCard, FXReference
from infra_joint.experiments.manager_context import OllamaManagerContextPreflight, truncation_events
from infra_joint.experiments.pilot_safety import PilotRequestBudget, strict_verifier_sdk
from infra_joint.experiments.sdk_api_meter import RawSDKAPIMeter
from infra_joint.operators.catalog import build_operator_catalog
from infra_joint.runtime.client import HttpWorkerClient, worker_http_limits

OWNER = Path("/home/super/xiaoming/lightweight-planner-competence-v1")
ROOT = OWNER / "formal-pilot-003"
APP = Path(__file__).resolve().parents[1]
HISTORICAL = Path("/home/super/xiaoming/large-scale-cost-guidance-resident-v1")
SELECTION = Path("/home/super/xiaoming/large-scale-cost-guidance-v1/preparation/task-freeze-002")
ORIGINAL = HISTORICAL / "app-E-query-contract-repair-004"
WORKER_APPS = {
    a: (
        str(HISTORICAL / "app-input-cardinality-repair-003")
        if h is None
        else "/mnt/ssd/large-scale-cost-guidance-resident-v1/app-input-cardinality-repair-003"
    )
    for a, h in HOSTS.items()
}
PORTS = {"A4": 62004, "A5": 62005, "A28": 62028, "strong-4090": 62112}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_new(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def journal(event, **data):
    value = {"utc": datetime.now(UTC).isoformat(), "event": event, **data}
    with (ROOT / "journal.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(value, ensure_ascii=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps(value, ensure_ascii=False), flush=True)


def node_json(agent, code):
    source = str(Path(WORKER_APPS[agent]) / "scripts")
    payload = "import sys; sys.path.insert(0," + repr(source) + "); " + code
    if HOSTS[agent] is None:
        output = subprocess.run(
            [sys.executable, "-c", payload], check=True, text=True, capture_output=True, timeout=60
        ).stdout
    else:
        output = remote_python(HOSTS[agent], payload)
    return json.loads(output)


async def residency():
    return dict(
        zip(
            HOSTS,
            await asyncio.gather(
                *(
                    asyncio.to_thread(
                        node_json,
                        a,
                        "import json; "
                        "from resident_model_pool_attestation_v1 import node_attestation; "
                        f"print(json.dumps(node_attestation({a!r})))",
                    )
                    for a in HOSTS
                )
            ),
            strict=True,
        )
    )


def protected_hashes():
    paths = [
        p for base in (HISTORICAL, SELECTION.parent.parent) for p in base.glob("*attempts*.jsonl")
    ]
    paths += [
        HISTORICAL / "phase2-attempts.jsonl",
        SELECTION / "manifest.json",
        APP / "configs/skills/planner-procedural-v1.md",
    ]
    return {str(p): digest(p) for p in sorted(set(paths))}


async def start_owned_worker(agent, config, store, run_id):
    host = HOSTS[agent]
    base = (
        ROOT
        if host is None
        else Path("/mnt/ssd/lightweight-planner-competence-v1/formal-pilot-003")
    )
    target = config if host is None else base / "worker-configs" / config.name
    code = "import json; from pathlib import Path; "
    code += f"base=Path({str(base)!r}); base.mkdir(parents=True,exist_ok=True); "
    code += "(base/'worker-configs').mkdir(exist_ok=True); (base/'logs').mkdir(exist_ok=True); "
    code += f"assert not Path({store!r}).exists(); "
    code += "import shutil; assert shutil.disk_usage(base).free >= 5*1024**3; print('{}')"
    await asyncio.to_thread(node_json, agent, code)
    if host is not None:
        await asyncio.to_thread(
            subprocess.run, ["scp", "-q", str(config), f"{host}:{target}"], check=True, timeout=30
        )
    app = WORKER_APPS[agent]
    values = {
        "app": app,
        "config": str(target),
        "log": str(base / "logs" / f"{run_id}-{agent}.log"),
        "port": PORTS[agent],
    }
    code = "import json,os,socket,subprocess; from pathlib import Path; "
    code += f"v={values!r}; s=socket.socket(); "
    code += "s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1); "
    code += 's.bind(("0.0.0.0",v["port"])); s.close(); '
    code += 'env=dict(os.environ,PYTHONPATH=v["app"]+"/src",OLLAMA_API_KEY="ollama"); '
    code += 'p=subprocess.Popen([v["app"]+"/.venv/bin/python","-m","infra_joint.cli","worker",'
    code += '"--config",v["config"]],cwd=v["app"],env=env,stdin=subprocess.DEVNULL,'
    code += 'stdout=open(v["log"],"x"),stderr=subprocess.STDOUT,start_new_session=True); '
    code += 'print(json.dumps({"pid":p.pid,"config":v["config"]}))'
    return await asyncio.to_thread(node_json, agent, code)


async def states(urls, *, fresh=False):
    async with httpx.AsyncClient(timeout=8) as client:
        result = {}
        for agent, url in urls.items():
            for attempt in range(60 if fresh else 1):
                try:
                    response = await client.get(url + "/state")
                    response.raise_for_status()
                    state = response.json()
                    if state["agent_id"] != agent or (fresh and state["artifacts"]):
                        raise RuntimeError("Worker identity/artifact namespace isolation failed")
                    result[agent] = state
                    break
                except httpx.HTTPError:
                    if attempt == (59 if fresh else 0):
                        raise
                    await asyncio.sleep(1)
        return result


async def resident_slots(snapshot):
    async def check(agent):
        ports = []
        for instance in snapshot[agent]["instances"]:
            command = instance["runner"]["command"]
            ports.append(int(command[command.index("--port") + 1]))
        code = "import json,urllib.request; "
        code += f"ports={ports!r}; "
        code += 'result={p:json.load(urllib.request.urlopen("http://127.0.0.1:"+str(p)+"/slots",'
        code += "timeout=5)) for p in ports}; print(json.dumps(result))"
        return agent, await asyncio.to_thread(node_json, agent, code)

    return dict(await asyncio.gather(*(check(a) for a in snapshot)))


async def cleanup_workers(pids, urls, out, snapshot):
    deadline = monotonic() + 1260
    errors, exited = [], {}
    drained = not pids
    try:
        while pids and monotonic() < deadline:
            current = await states({a: urls[a] for a in pids})
            if all(v["in_flight"] == 0 for v in current.values()):
                slots = await resident_slots(snapshot)
                if all(
                    not slot["is_processing"]
                    for ports in slots.values()
                    for values in ports.values()
                    for slot in values
                ):
                    drained = True
                    write_new(out / "private/worker-state-drained.json", current)
                    write_new(out / "private/model-slots-drained.json", slots)
                    break
            await asyncio.sleep(2)
        if not drained:
            errors.append("worker/model in-flight requests did not drain within cleanup budget")
    except Exception as exc:
        errors.append("worker_drain:" + type(exc).__name__)
    for agent, identity in pids.items():
        code = "import json,os,signal,time; from pathlib import Path; "
        code += f'p=Path("/proc/{identity["pid"]}/cmdline"); '
        code += "cmd=p.read_bytes().decode() if p.exists() else ''; "
        code += f'assert not cmd or {identity["config"]!r} in cmd, "PID ownership changed"; '
        code += f"os.kill({identity['pid']},signal.SIGTERM) if cmd else None; "
        code += "\nfor _ in range(20):\n if not p.exists() or not p.read_bytes(): break"
        code += "\n time.sleep(.5)"
        code += '\nprint(json.dumps({"exited":not p.exists() or not p.read_bytes()}))'
        try:
            value = await asyncio.to_thread(node_json, agent, code)
            exited[agent] = value["exited"]
            if not value["exited"]:
                errors.append(agent + ":owned worker did not exit")
        except Exception as exc:
            errors.append(agent + ":" + type(exc).__name__)
    record = {
        "errors": errors,
        "drained": drained,
        "verified_exited": all(exited.values()) and len(exited) == len(pids),
        "owned_processes": pids,
    }
    write_new(out / "worker-shutdown.json", record)
    return record


async def execute(cell, out, config, protocol):
    manifest = json.loads((SELECTION / "manifest.json").read_text())
    bundle, row = frozen_task(SELECTION, manifest, cell["family"], cell["position"])
    expected = protocol["tasks"][cell["task_index"] - 1]
    if any(row[k] != expected[k] for k in ("task_bundle_sha256", "agent_task_sha256")):
        raise RuntimeError("selected task hash drift")
    reference = frozen.protocol()
    base = frozen.base_config(reference)
    base["environment_config"] = protocol["infrastructure_design"]["model_pool_path"]
    label = f"{cell['family']}-{cell['position']}"
    base["execution"]["initial_placement"][label] = [a["initial_worker"] for a in row["artifacts"]]
    environment = frozen._environment(base, label, bundle)
    environment = environment.model_copy(
        update={
            "links": tuple(
                LinkSpec(
                    source_agent_id=a.agent_id,
                    target_agent_id=b.agent_id,
                    bandwidth_mbps=100,
                    rtt_ms=5,
                )
                for a in environment.agents
                for b in environment.agents
                if a.agent_id != b.agent_id
            )
        }
    )
    registry = build_operator_catalog()
    harness = frozen.load_harness(APP / protocol["infrastructure_design"]["frozen_harness_path"])
    capability = build_static_capability_contract(
        environment, registry, harness.available_operations
    )
    derived = harness.model_copy(
        update={
            "runtime": {
                **harness.runtime,
                "source_sha256": digest(APP / "src/infra_joint/control/native_agents.py"),
            }
        }
    )
    frozen.validate_harness(derived, environment, capability, harness.available_operations)
    group = cell["group"]
    local = group != "B0"
    selected_model = protocol["groups"][group]["manager_model"]
    skills = (APP / protocol["skills"]["path"]).read_text() if group == "B2" else None
    write_new(
        out / "attempt-freeze.json",
        {
            "cell": cell,
            "task_receipt": row,
            "derived_harness": derived.model_dump(mode="json"),
            "context": asdict(CONTEXT),
            "base_manager_instructions_sha256": hashlib.sha256(
                MANAGER_INSTRUCTIONS.encode()
            ).hexdigest(),
            "skills_sha256": protocol["skills"]["sha256"] if skills is not None else None,
            "formal_source_freeze_sha256": digest(ROOT / "execution-freeze.json"),
            "config": config,
        },
    )
    price_path, price_sha = verified_prices(SELECTION.parent.parent, APP)
    pricing = json.loads(price_path.read_text())
    cards = {k: APIPriceCard.model_validate(v) for k, v in pricing["prices"].items()}
    fx = FXReference.model_validate(pricing["fx"])
    budget = PilotRequestBudget(ROOT / "STOP", monotonic() + 3600)
    meters = {}
    for provider, price_map in [("cloud", cards), ("local", {})]:
        meters[provider] = RawSDKAPIMeter(
            provider="aliyun-model-studio" if provider == "cloud" else "ollama-local",
            region="cn-beijing" if provider == "cloud" else "controller-gpu1",
            prices=price_map,
            fx=fx if provider == "cloud" else None,
            private_sink=lambda kind, identifier, value, p=provider: write_new(
                out / "private/api" / p / f"{identifier}-{kind}.json", value
            ),
        )
    guard = None
    verdict_calls = []
    started = monotonic()
    result = None
    try:
        async with AsyncExitStack() as stack:
            helper = await stack.enter_async_context(
                httpx.AsyncClient(event_hooks={"request": [budget.helper_hook]})
            )
            guard = OllamaManagerContextPreflight(
                CONTEXT,
                helper,
                sink=lambda kind, value: write_new(
                    out / "private/context" / f"{len(guard.receipts):03d}-{kind}.json", value
                ),
            )
            cloud_http = await stack.enter_async_context(
                httpx.AsyncClient(
                    timeout=180,
                    event_hooks={
                        "request": [budget.control_hook, meters["cloud"].request_hook],
                        "response": [meters["cloud"].response_hook],
                    },
                )
            )
            local_http = await stack.enter_async_context(
                httpx.AsyncClient(
                    timeout=180,
                    event_hooks={
                        "request": [
                            guard.request_hook,
                            budget.control_hook,
                            meters["local"].request_hook,
                        ],
                        "response": [meters["local"].response_hook, guard.response_hook],
                    },
                )
            )
            cloud_client = await stack.enter_async_context(
                AsyncOpenAIClient(
                    base_url=protocol["strong_cloud"]["base_url"],
                    api_key=os.environ["DASHSCOPE_API_KEY"],
                    max_retries=0,
                    timeout=180,
                    http_client=cloud_http,
                )
            )
            local_client = await stack.enter_async_context(
                AsyncOpenAIClient(
                    base_url=CONTEXT.ollama_url + "/v1",
                    api_key="ollama",
                    max_retries=0,
                    timeout=180,
                    http_client=local_http,
                )
            )
            strong = ModelRequestBodyAdapter(
                agents.OpenAIChatCompletionsModel(model="qwen3.8-max", openai_client=cloud_client),
                {"enable_thinking": False},
            )
            manager = (
                agents.OpenAIChatCompletionsModel(model=selected_model, openai_client=local_client)
                if local
                else strong
            )
            roles = role_isolated_sdk(
                agents,
                manager_model=manager,
                specialist_model=strong,
                manager_model_id=selected_model,
                specialist_model_id="qwen3.8-max",
                manager_meter=meters["local" if local else "cloud"],
                specialist_meter=meters["cloud"],
            )
            constructed = {}

            def construct(**kwargs):
                if local and kwargs["name"] == "manager":
                    kwargs["model_settings"] = replace(
                        kwargs["model_settings"], max_tokens=2048, temperature=1, top_p=0.95
                    )
                agent = roles.Agent(**kwargs)
                constructed[kwargs["name"]] = agent
                return agent

            facade = SimpleNamespace(**{**agents.__dict__, "Agent": construct})
            verifier = OpenAIAgentsBlindVerifier(
                model=meters["cloud"].model(
                    strong,
                    recipient="verifier",
                    agent_name="blind_evidence_verifier",
                    requested_model="qwen3.8-max",
                ),
                sdk_module=strict_verifier_sdk(agents, verdict_calls.append),
            )
            runtime = OpenAIAgentsNativeRuntime(
                name="manager",
                instructions=manager_instructions(MANAGER_INSTRUCTIONS, skills=skills),
                model=manager,
                registry=registry,
                available_operations=harness.available_operations,
                sdk_module=facade,
                blind_verifier=verifier,
                record_input_provenance=True,
                validate_raw_tool_calls=True,
            )
            clients = {}
            for agent, url in config["worker_urls"].items():
                http = await stack.enter_async_context(
                    httpx.AsyncClient(
                        base_url=url,
                        timeout=1200,
                        limits=worker_http_limits(),
                        event_hooks={"request": [budget.worker_hook]},
                    )
                )
                clients[agent] = HttpWorkerClient(agent, http)
            runner = ControlPlaneBenchmarkRunner(
                RunnerConfig(
                    environment=environment,
                    worker_urls=config["worker_urls"],
                    planner=PlannerConfig(model=StaticBackendConfig(response="unused")),
                    output_root=out / "runs",
                    max_planning_steps=20,
                    http_timeout_seconds=1200,
                ),
                None,
                harness.available_operations,
                worker_clients=clients,
                profile_visibility=ProfileVisibility.BLIND,
                loop_budget=harness.budget,
                logical_runtime=runtime,
            )
            task = asyncio.create_task(runner.run(bundle, run_id=config["run_id"]))
            try:
                while not task.done():
                    await asyncio.wait({task}, timeout=2)
                    budget.check()
                result = task.result()
            finally:
                if not task.done():
                    task.cancel()
                    await asyncio.gather(task, return_exceptions=True)
            # Exact evaluator rerun without any model call, including score=0 results.
            if result.execution_completed:
                repeated = await bundle.private_evaluation.build_evaluator().evaluate(
                    bundle.execution.task, result.final_answer
                )
                if repeated != result.evaluation:
                    raise RuntimeError("evaluator consistency error")
            write_new(
                out / "private/role-configuration.json",
                {
                    "manager_model": selected_model,
                    "specialist_model": "qwen3.8-max",
                    "verifier_model": "qwen3.8-max",
                    "manager_settings": asdict(constructed["manager"].model_settings)
                    if constructed
                    else None,
                    "specialist_settings": asdict(constructed["bounded_specialist"].model_settings)
                    if constructed
                    else None,
                    "verifier_settings": asdict(verifier._agent.model_settings),
                },
            )
    except Exception as exc:
        write_new(
            out / "private/execution-exception.json",
            {"type": type(exc).__name__, "message": str(exc)},
        )
        if result is None:
            write_new(
                out / "administrative-outcome.json",
                {
                    "execution_completed": False,
                    "failure": {
                        "exception_type": type(exc).__name__,
                        "code": getattr(exc, "code", "administrative_failure"),
                    },
                },
            )
        else:
            raise
    finally:
        write_new(out / "budget.json", budget.receipt())
        write_new(out / "api-accounting.json", {k: v.summary() for k, v in meters.items()})
        write_new(out / "context-receipts.json", guard.receipts if guard else [])
        write_new(out / "verifier-schema.json", verdict_calls)
        write_new(
            out / "execution-timing.json",
            {"wall_ms": (monotonic() - started) * 1000, "price_freeze_sha256": price_sha},
        )


def inspect_cell(cell, out, config, cleanup, protected):
    run = out / "runs" / config["run_id"]
    raw = (
        json.loads((run / "result.json").read_text())
        if (run / "result.json").exists()
        else json.loads((out / "administrative-outcome.json").read_text())
    )
    events = (
        [json.loads(line) for line in (run / "trace.jsonl").read_text().splitlines()]
        if (run / "trace.jsonl").exists()
        else []
    )
    problems = []
    if not cleanup["drained"] or not cleanup["verified_exited"] or cleanup["errors"]:
        problems.append("worker_cleanup_failed")
    if protected_hashes() != protected:
        problems.append("historical_or_frozen_input_drift")
    tc = json.loads((out / "tc-attestation.json").read_text())
    if tc["cleanup_error"] or tc["original_qdisc"] != tc["restored_qdisc"]:
        problems.append("network_restoration_failed")
    context = json.loads((out / "context-receipts.json").read_text())
    for row in context:
        if row.get("error_code") in {"context_integrity_failed", "context_preflight_unavailable"}:
            problems.append(row["error_code"])
        if (
            row.get("decision") == "allow"
            and row.get("http_status") == 200
            and not row.get("integrity_verified")
        ):
            problems.append("accepted_context_not_verified")
    for event in events:
        if event["event_type"] == "logical.reasoning.input":
            p = event["payload"]
            if p.get("current_anonymous_profile") is not None or blind_input_profile_findings(
                p["input_items"]
            ):
                problems.append("blind_profile_leakage")
    usage = []
    for path in (out / "private/api").rglob("*-usage.json"):
        data = json.loads(path.read_text())
        usage.append(data)
        if data["status"] in (401, 403):
            problems.append("provider_authentication_failed")
    counters = Counter()
    for event in events:
        if event["event_type"] == "logical.observation" and not event["payload"]["succeeded"]:
            counters[event["payload"]["failure_code"]] += 1
    schema = [e["payload"] for e in events if e["event_type"] == "logical.tool.schema_validation"]
    reasoning = [e["payload"] for e in events if e["event_type"] == "logical.reasoning.started"]
    graphs = [e["payload"] for e in events if e["event_type"] == "workflow.graph.snapshot"]
    graph = graphs[-1] if graphs else {"nodes": [], "edges": []}
    physical = [e["payload"] for e in events if e["event_type"] == "physical.execution"]
    executions = [e["execution"] for e in physical if e.get("execution")]
    model_calls = [e["model_telemetry"] for e in executions if e.get("model_telemetry")]
    failed_physical = [e for e in physical if e.get("failure")]
    transfers = [t for e in executions for t in e.get("transfers", [])]
    initial = raw.get("initial_transfers", [])
    role_metrics = {}
    for role in ("manager", "specialist", "verifier"):
        selected = [u for u in usage if u["recipient"] == role]

        def total(field, selected=selected):
            values = [(u.get("usage") or {}).get(field) for u in selected]
            return sum(values) if all(type(v) is int for v in values) else None

        role_metrics[role] = {
            "requests": len(selected),
            "input_tokens": total("prompt_tokens"),
            "output_tokens": total("completion_tokens"),
            "cached_input_tokens": sum(
                (u.get("usage") or {}).get("prompt_tokens_details", {}).get("cached_tokens", 0)
                for u in selected
            )
            if all(
                "cached_tokens" in (u.get("usage") or {}).get("prompt_tokens_details", {})
                for u in selected
            )
            else None,
            "provider_latency_ms": sum(u["latency_ms"] for u in selected),
            "turns": len(
                [
                    r
                    for r in reasoning
                    if (r["logical_agent_id"] == "manager") == (role == "manager")
                ]
            )
            if role != "verifier"
            else len(selected),
        }
    owner_names = {"manager": "manager"}
    for n in graph["nodes"]:
        if n["owner_agent_id"] not in owner_names:
            owner_names[n["owner_agent_id"]] = f"specialist_{len(owner_names)}"
    node_names = {n["action_id"]: i for i, n in enumerate(graph["nodes"])}
    safe_graph = {
        "nodes": [
            {
                "index": i,
                "owner": owner_names[n["owner_agent_id"]],
                "operator": n["operator"],
                "status": n["status"],
                "input_count": len(n["inputs"]),
                "output_count": len(n["outputs"]),
            }
            for i, n in enumerate(graph["nodes"])
        ],
        "edges": [
            {
                "producer": node_names[e["producer_action_id"]],
                "consumer": node_names[e["consumer_action_id"]],
            }
            for e in graph["edges"]
        ],
    }
    completed = raw["execution_completed"]
    evaluation = raw.get("evaluation")
    failure = raw.get("failure")
    if failure and failure.get("code") in {"surface_mismatch", "configuration_invalid"}:
        problems.append(failure["code"])
    if failure and failure.get("exception_type") in {
        "AttributeError",
        "NameError",
        "KeyError",
        "AssertionError",
        "ImportError",
        "FileNotFoundError",
    }:
        problems.append("controller_implementation_error")
    safe_failure = (
        {k: failure[k] for k in ("code", "exception_type") if k in failure} if failure else None
    )
    record = {
        "cell": cell,
        "completed": completed,
        "original_evaluation": evaluation,
        "successful": bool(completed and evaluation and evaluation["benchmark_score"] == 1),
        "failure": safe_failure,
        "failure_counts": dict(counters),
        "schema_attempts": len(schema),
        "schema_valid": sum(s["valid"] for s in schema),
        "schema_failures": sum(not s["valid"] for s in schema),
        "roles": role_metrics,
        "cost_accounting": json.loads((out / "api-accounting.json").read_text()),
        "physical": {
            "admitted_requests": json.loads((out / "budget.json").read_text())["physical_requests"],
            "successful_inference_calls": len(model_calls),
            "failed_actions": len(failed_physical),
            "input_tokens": sum(m["input_tokens"] for m in model_calls)
            if all(m["input_tokens"] is not None for m in model_calls)
            else None,
            "output_tokens": sum(m["output_tokens"] for m in model_calls)
            if all(m["output_tokens"] is not None for m in model_calls)
            else None,
            "known_model_service_ms": sum(m["service_latency_ms"] for m in model_calls),
            "unmeasured_failed_model_service_work": bool(failed_physical),
            "operator_ms": sum(e["operator_latency_ms"] for e in executions),
            "initial_transfer_bytes": sum(t["bytes_transferred"] for t in initial),
            "action_transfer_bytes": sum(t["bytes_transferred"] for t in transfers),
            "gpu_seconds": None,
            "gpu_cost": None,
        },
        "timing": json.loads((out / "execution-timing.json").read_text()),
        "telemetry": raw.get("telemetry"),
        "workflow": safe_graph,
        "created_specialists": sum(e["event_type"] == "logical.subagent.start" for e in events),
        "budget": json.loads((out / "budget.json").read_text()),
        "context_rejections": sum(r.get("decision") == "context_limit_exceeded" for r in context),
        "cleanup": {"drained": cleanup["drained"], "verified_exited": cleanup["verified_exited"]},
        "system_problems": sorted(set(problems)),
        "raw_files_sha256": {
            str(p.relative_to(out)): digest(p) for p in sorted(out.rglob("*")) if p.is_file()
        },
    }
    # Export scores and numeric accounting; private evaluator details remain remote.
    record["original_evaluation"] = {"score": evaluation["benchmark_score"]} if evaluation else None
    for meter in record["cost_accounting"].values():
        meter.pop("model_attempts", None)
    return record


async def one_cell(cell, protocol, pool, protected):
    out = ROOT / "cells" / cell["cell_id"]
    out.mkdir(parents=True, exist_ok=False)
    run_id = f"lightweight-planner-competence-v1-formal-003-{cell['cell_id']}"
    stores = {
        a: str(
            (Path("/home/super") if h is None else Path("/mnt/ssd"))
            / "heterogeneous-v1/artifacts/lightweight-planner-competence-v1/formal-pilot-003"
            / cell["cell_id"]
            / a
        )
        for a, h in HOSTS.items()
    }
    urls = {
        a: url.rsplit(":", 1)[0] + ":" + str(PORTS[a]) for a, url in pool["worker_urls"].items()
    }
    config = {
        "run_id": run_id,
        "cell_id": cell["cell_id"],
        "worker_urls": urls,
        "fresh_worker_stores": stores,
        "network": {"regime": "fast", "bandwidth_mbps": 100, "added_rtt_ms": 5},
    }
    cell_config = ROOT / "cell-configs" / (cell["cell_id"] + ".yaml")
    cell_config.parent.mkdir(exist_ok=True)
    with cell_config.open("x") as stream:
        yaml.safe_dump(config, stream)
    before = await residency()
    write_new(out / "private/residency-before.json", before)
    slots = await resident_slots(before)
    if any(
        slot["is_processing"]
        for ports in slots.values()
        for values in ports.values()
        for slot in values
    ):
        raise RuntimeError("resident model has external in-flight work before cell")
    pids = {}
    cleanup = None

    async def shaped(_args):
        nonlocal cleanup
        try:
            for agent in HOSTS:
                original = frozen._yaml(
                    APP
                    / "configs/experiments/workers/blind-3family-video-v1.3"
                    / f"worker-{agent.lower()}.yaml"
                )
                worker = worker_config(
                    {**pool, "worker_urls": urls}, original, agent, Path(stores[agent])
                )
                path = ROOT / "worker-configs" / f"{run_id}-{agent}.yaml"
                path.parent.mkdir(exist_ok=True)
                with path.open("x") as stream:
                    yaml.safe_dump(worker.model_dump(mode="json"), stream, sort_keys=False)
                pids[agent] = await start_owned_worker(agent, path, stores[agent], run_id)
                write_new(out / "worker-starts" / (agent + ".json"), pids[agent])
            write_new(out / "private/worker-state-before.json", await states(urls, fresh=True))
            await execute(cell, out, config, protocol)
        finally:
            cleanup = await cleanup_workers(pids, urls, out, before)

    args = argparse.Namespace(config=cell_config, output=out, endpoint_config=DEFAULT_ENDPOINTS)
    await run_shaped(args, execute_cell=shaped)
    after = await residency()
    write_new(out / "private/residency-after.json", after)
    interval_problems = []
    for agent in HOSTS:
        code = "import json; from resident_model_pool_attestation_v1 import audit_log_interval; "
        code += f"print(json.dumps(audit_log_interval({before[agent]!r},{after[agent]!r})))"
        audit = await asyncio.to_thread(node_json, agent, code)
        write_new(out / "private/residency-log-intervals" / (agent + ".json"), audit)
        for value in audit["intervals"].values():
            interval_problems += truncation_events(value["text"])
    record = inspect_cell(cell, out, config, cleanup, protected)
    if interval_problems:
        record["system_problems"].append("actual_provider_truncation")
    write_new(out / "sanitized-result.json", record)
    return record


async def main(args):
    if sys.platform != "linux" or APP != ROOT / "app":
        raise RuntimeError("formal pilot must run in its isolated controller app")
    if (ROOT / "journal.jsonl").exists():
        raise RuntimeError("pilot has already started; no automatic rerun/resume")
    if digest(SELECTION / "manifest.json") != TASK_FREEZE_SHA256:
        raise RuntimeError("task freeze drift")
    protocol = json.loads(
        (APP / "configs/experiments/lightweight-planner-competence-v1.json").read_text()
    )
    if digest(APP / protocol["skills"]["path"]) != protocol["skills"]["sha256"]:
        raise RuntimeError("frozen Skills drift")
    _load_control_plane_key(args.api_key_file, "DASHSCOPE_API_KEY")
    agents.set_tracing_disabled(True)
    protected = protected_hashes()
    files = {
        str(p.relative_to(APP)): digest(p)
        for folder in ("src", "scripts", "configs")
        for p in sorted((APP / folder).rglob("*"))
        if p.is_file() and "__pycache__" not in p.parts
    }
    write_new(
        ROOT / "execution-freeze.json",
        {
            "base_commit": "41d034d",
            "protocol_amendment": "strict raw schema rejection, recover within original turns; "
            "model failures are outcomes, "
            "only system safety/integrity failures stop matrix; no capability gate",
            "source_sha256": files,
            "protected_sha256": protected,
            "ordered_cells": protocol["order"],
            "context": asdict(CONTEXT),
            "maximum_attempts": 18,
            "control_requests_per_cell": 72,
            "physical_requests_per_cell": 64,
            "helper_requests_per_cell": 4096,
            "task_timeout_seconds": 3600,
            "cleanup_timeout_seconds": 1260,
            "setup_and_attestation_allowance_seconds_per_cell": 240,
            "matrix_wall_ceiling_seconds": 91800,
            "control_input_bytes_per_cell": 128 * 1024**2,
            "dollar_ceiling": None,
            "request_budget_is_primary_resource_ceiling": True,
            "no_extra_capability_probe": True,
            "historical_phase2_resumed": False,
        },
    )
    pool = frozen._yaml(APP / protocol["infrastructure_design"]["model_pool_path"])
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: (ROOT / "STOP").touch(exist_ok=True))
    journal("started", pid=os.getpid(), cells=18)
    rows = []
    matrix_deadline = monotonic() + 91800
    try:
        for cell in protocol["order"]:
            if (ROOT / "STOP").exists() or monotonic() >= matrix_deadline:
                raise RuntimeError("administrative matrix stop/deadline")
            if protected_hashes() != protected or any(
                digest(APP / p) != sha for p, sha in files.items()
            ):
                raise RuntimeError("frozen sources or protected history changed")
            journal("cell_started", cell=cell)
            row = await asyncio.wait_for(one_cell(cell, protocol, pool, protected), timeout=5100)
            rows.append(row)
            journal(
                "cell_finished",
                cell=cell["cell_id"],
                completed=row["completed"],
                score=row["original_evaluation"],
                schema_failures=row["schema_failures"],
                system_problems=row["system_problems"],
            )
            if row["system_problems"]:
                raise RuntimeError(
                    "system safety/integrity failure: " + ",".join(row["system_problems"])
                )
            if len(rows) == 3:
                write_new(
                    ROOT / "first-task-audit.json",
                    {
                        "cells": 3,
                        "system_problems": [],
                        "worker_cleanup_verified": True,
                        "evaluator_consistency": True,
                        "proceed_remaining_15": True,
                    },
                )
                journal("first_task_audit_passed", automatic_continuation=True)
        write_new(
            ROOT / "matrix-complete.json",
            {
                "cells": 18,
                "order_preserved": True,
                "semantic_retries": 0,
                "protected_history_unchanged": protected_hashes() == protected,
            },
        )
        journal("completed", cells=len(rows))
    except BaseException as exc:
        write_new(
            ROOT / "matrix-stopped.json",
            {
                "type": type(exc).__name__,
                "message": str(exc),
                "completed_cells": len(rows),
                "historical_phase2_resumed": False,
            },
        )
        journal("stopped", exception=type(exc).__name__, completed_cells=len(rows))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-key-file", type=Path, required=True)
    asyncio.run(main(parser.parse_args()))
