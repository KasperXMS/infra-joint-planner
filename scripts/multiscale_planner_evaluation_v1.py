"""Finite multi-scale pilot, reusing the frozen native runtime and physical pool."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import signal
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from time import monotonic

import agents
import httpx
import lightweight_planner_pilot_v1 as pilot
from lightweight_planner_compatibility_v1 import SyntheticGateway
from lightweight_planner_context_gate_v1 import INSTRUCTIONS, task
from multiscale_planner_context_v1 import MultiscaleContextConfig, MultiscaleContextPreflight
from openai import AsyncOpenAI
from sdk_native_infra_preliminary_v1_3 import ModelRequestBodyAdapter, _load_control_plane_key

from infra_joint.control.loop import AgentLoopBudget
from infra_joint.control.native_agents import OpenAIAgentsNativeRuntime
from infra_joint.evaluation.trace import JsonlTraceWriter
from infra_joint.experiments.manager_context import ManagerContextLimitExceeded
from infra_joint.operators.catalog import build_operator_catalog
from infra_joint.workflow.trace import WorkflowTraceRecorder

ROOT = Path("/home/super/xiaoming/multiscale-planner-evaluation-v1/run-001")
APP = Path(__file__).resolve().parents[1]
PLAN = json.loads((APP / "configs/experiments/multiscale-planner-execution-v1.json").read_text())
write = pilot.write_new


def configure():
    pilot.ROOT = ROOT
    pilot.OWNER = ROOT.parent
    pilot.EDGE_ROOT = Path("/mnt/ssd/multiscale-planner-evaluation-v1/run-001")
    pilot.ARTIFACT_NAMESPACE = "multiscale-planner-evaluation-v1/run-001"
    pilot.RUN_PREFIX = "multiscale-planner-v1-001"
    pilot.PORTS = {"A4": 63004, "A5": 63005, "A28": 63028, "strong-4090": 63112}
    pilot.OllamaManagerContextPreflight = MultiscaleContextPreflight
    # The matched cloud-only baseline creates no local requests.
    pilot.CONTEXT = MultiscaleContextConfig(**asdict(pilot.CONTEXT))
    previous_protected = pilot.protected_hashes

    def protected_history():
        values = previous_protected()
        prior = ROOT.parent.parent / "lightweight-planner-competence-v1/formal-pilot-003"
        paths = list(prior.glob("cells/*/sanitized-result.json"))
        paths += [
            prior / name
            for name in ("journal.jsonl", "matrix-complete.json", "execution-freeze.json")
        ]
        values.update({str(p): pilot.digest(p) for p in paths})
        return values

    pilot.protected_hashes = protected_history


async def api(route, body=None, timeout=30):
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.request(
            "GET" if body is None else "POST", "http://127.0.0.1:11450/api/" + route, json=body
        )
        response.raise_for_status()
        return response.json()


def gpu_state():
    output = subprocess.run(
        [
            "nvidia-smi",
            "--query-gpu=index,memory.used,memory.free",
            "--format=csv,noheader,nounits",
        ],
        check=True,
        text=True,
        capture_output=True,
    ).stdout
    return [
        dict(zip(["index", "used_mib", "free_mib"], map(int, line.split(",")), strict=True))
        for line in output.splitlines()
    ]


async def load(candidate, phase):
    started = monotonic()
    before = await pilot.residency()
    if candidate == "qwen35-27b":
        port = 11436
        tag = "qwen35-27b-resident-32k-v1"
        server_pid = before["strong-4090"]["instances"][0]["server"]["pid"]
    else:
        if not (ROOT / (candidate + "-download.json")).exists():
            raise RuntimeError("official_download_unavailable")
        port = 11450
        tag = "multiscale-" + candidate + "-32k-v1"
        owned = await api("ps")
        for model in owned.get("models", []):
            assert model["name"].startswith("multiscale-")
            await api("generate", {"model": model["name"], "keep_alive": 0, "stream": False})
        await api(
            "create",
            {
                "model": tag,
                "from": PLAN["downloads"][candidate],
                "parameters": {"num_ctx": 32768, "num_predict": 2048},
                "stream": False,
            },
            timeout=120,
        )
        await api(
            "generate",
            {
                "model": tag,
                "prompt": "",
                "stream": False,
                "keep_alive": -1,
                "options": {"num_predict": 0, "num_ctx": 32768},
            },
            timeout=180,
        )
        server_pid = json.loads((ROOT / "planner-server.json").read_text())["pid"]
    async with httpx.AsyncClient(timeout=30) as client:
        url = f"http://127.0.0.1:{port}"
        show_response = await client.post(url + "/api/show", json={"model": tag})
        show_response.raise_for_status()
        show = show_response.json()
        ps = (await client.get(url + "/api/ps")).json()
        resident = next(m for m in ps["models"] if m["name"] in {tag, tag + ":latest"})
        runners = []
        for path in Path("/proc").iterdir():
            if not path.name.isdigit():
                continue
            try:
                status = (path / "status").read_text()
                parent = int(
                    next(x.split()[1] for x in status.splitlines() if x.startswith("PPid:"))
                )
                cmd = (path / "cmdline").read_bytes().decode().split("\0")
                if parent == server_pid and "--port" in cmd:
                    runners.append(cmd)
            except (OSError, StopIteration):
                pass
        assert len(runners) == 1
        runner_url = "http://127.0.0.1:" + runners[0][runners[0].index("--port") + 1]
        props = (await client.get(runner_url + "/props")).json()

    def field(name):
        found = re.search(r"^" + name + r" (.+)$", show["modelfile"], re.M)
        return found[1] if found else ""

    context = MultiscaleContextConfig(
        model=tag,
        digest=resident["digest"],
        model_blob=props["model_path"].rsplit("/", 1)[-1],
        template_sha256=hashlib.sha256(show["template"].encode()).hexdigest(),
        ollama_url=url,
        runner_url=runner_url,
        renderer=field("RENDERER"),
        parser=field("PARSER"),
        disable_thinking=candidate.startswith("qwen35"),
    )
    after = await pilot.residency()
    for node in before:
        for b, a in zip(before[node]["instances"], after[node]["instances"], strict=True):
            assert b["runner"]["pid"] == a["runner"]["pid"], (
                "Executor runner changed during Manager load"
            )
    memory = gpu_state()
    receipt = {
        "candidate": candidate,
        "phase": phase,
        "elapsed_ms": (monotonic() - started) * 1000,
        "gpu": memory,
        "resident_size_vram": resident.get("size_vram"),
        "context": asdict(context),
        "show": show,
        "executor_runners_unchanged": True,
    }
    write(ROOT / "private/deployment" / f"{phase}-{candidate}.json", receipt)
    if (
        candidate != "qwen35-27b"
        and memory[1]["free_mib"] < PLAN["deployment_minimum_gpu_headroom_mib"]
    ):
        await api("generate", {"model": tag, "keep_alive": 0, "stream": False})
        raise RuntimeError("Manager_gpu_headroom_boundary")
    return context


async def compatibility(candidate, context):
    out = ROOT / "compatibility" / candidate
    out.mkdir(parents=True, exist_ok=False)
    started = monotonic()
    count = {"inference": 0, "helper": 0}
    raw_schemas = []
    outputs = []
    guard = None
    receipt = {
        "candidate": candidate,
        "context": asdict(context),
        "admitted": False,
        "model_errors": [],
        "safety_errors": [],
        "context_tiers": [],
    }

    async def helper_limit(request):
        count["helper"] += 1
        if count["helper"] > 512 or (ROOT / "STOP").exists():
            raise RuntimeError("compatibility_helper_budget")

    async def capture_request(request):
        count["inference"] += 1
        if count["inference"] > 8 or (ROOT / "STOP").exists():
            raise RuntimeError("compatibility_inference_budget")
        write(
            out / "private" / f"request-{count['inference']:02d}.json",
            json.loads(await request.aread()),
        )

    async def capture_response(response):
        await response.aread()
        write(out / "private" / f"response-{len(outputs) + 1:02d}.json", response.json())
        outputs.append({"status": response.status_code, "usage": response.json().get("usage")})

    try:
        async with httpx.AsyncClient(event_hooks={"request": [helper_limit]}) as helper:
            guard = MultiscaleContextPreflight(
                context,
                helper,
                sink=lambda kind, value: write(
                    out / "private" / f"render-{count['helper']:03d}-{kind}.json", value
                ),
            )
            async with httpx.AsyncClient(
                timeout=180,
                event_hooks={
                    "request": [guard.request_hook, capture_request],
                    "response": [capture_response, guard.response_hook],
                },
            ) as http:
                tools = json.loads(
                    (
                        pilot.OWNER.parent
                        / "lightweight-planner-competence-v1/gate-002/request-01.json"
                    ).read_text()
                )["tools"]
                for target in PLAN["compatibility"]["context_targets"]:
                    filler = target - 512
                    for _attempt in range(3):
                        wire = {
                            "model": context.model,
                            "max_tokens": 2048,
                            "stream": False,
                            "messages": [
                                {
                                    "role": "system",
                                    "content": "Return the HEAD, MIDDLE and TAIL sentinel values "
                                    "exactly as a JSON object. Padding has no other meaning.",
                                },
                                {
                                    "role": "user",
                                    "content": "HEAD=H482\n"
                                    + " x" * (filler // 2)
                                    + "\nMIDDLE=M739\n"
                                    + " x" * (filler - filler // 2)
                                    + "\nTAIL=T916",
                                },
                            ],
                            "tools": tools,
                        }
                        if context.disable_thinking:
                            wire["reasoning_effort"] = "none"
                        counted = await guard.inspect(wire)
                        delta = target - counted["prompt_tokens"]
                        if delta == 0:
                            break
                        filler += delta
                    else:
                        raise RuntimeError("context_count_calibration_failed")
                    record = {"target": target, **counted, "inference_requests": 0}
                    if target == 30720:
                        response = await http.post(
                            context.ollama_url + "/v1/chat/completions", json=wire
                        )
                        record["inference_requests"] = 1
                        record["http_status"] = response.status_code
                        if response.status_code == 200:
                            record["provider_prompt_tokens"] = (
                                response.json().get("usage", {}).get("prompt_tokens")
                            )
                            content = response.json()["choices"][0]["message"].get("content") or ""
                            record["sentinel_echo_all"] = all(
                                s in content for s in ["H482", "M739", "T916"]
                            )
                        else:
                            receipt["model_errors"].append("context_probe_provider_error")
                    elif target > 30720:
                        before = count["inference"]
                        try:
                            await http.post(context.ollama_url + "/v1/chat/completions", json=wire)
                            raise RuntimeError("overflow_was_forwarded")
                        except ManagerContextLimitExceeded:
                            record["overflow_blocked_before_inference"] = (
                                count["inference"] == before
                            )
                    receipt["context_tiers"].append(record)
                async with AsyncOpenAI(
                    base_url=context.ollama_url + "/v1",
                    api_key="ollama",
                    max_retries=0,
                    timeout=180,
                    http_client=http,
                ) as client:
                    model = agents.OpenAIChatCompletionsModel(
                        model=context.model, openai_client=client
                    )
                    if context.disable_thinking:
                        model = ModelRequestBodyAdapter(model, {"reasoning_effort": "none"})
                    original = agents.Agent

                    def construct(**kwargs):
                        from dataclasses import replace

                        kwargs["model_settings"] = replace(
                            kwargs["model_settings"], max_tokens=2048, temperature=1, top_p=0.95
                        )
                        return original(**kwargs)

                    from types import SimpleNamespace

                    sdk = SimpleNamespace(**{**agents.__dict__, "Agent": construct})
                    registry = build_operator_catalog()
                    gateway = SyntheticGateway()
                    runtime = OpenAIAgentsNativeRuntime(
                        name="manager",
                        instructions=INSTRUCTIONS,
                        model=model,
                        registry=registry,
                        available_operations=tuple(registry),
                        sdk_module=sdk,
                        validate_raw_tool_calls=True,
                    )
                    try:
                        result = await runtime.run(
                            task(),
                            gateway,
                            budget=AgentLoopBudget(
                                max_manager_turns=6,
                                max_subagent_turns=2,
                                max_tool_model_calls=6,
                                max_created_subagents=1,
                                max_active_subagents=1,
                            ),
                            trace=WorkflowTraceRecorder(
                                "multiscale-compatibility",
                                JsonlTraceWriter(out / "private/trace.jsonl"),
                            ),
                        )
                        write(out / "private/native-result.json", result.model_dump(mode="json"))
                        receipt["native_completed"] = result.final_answer == "A"
                        receipt["native_usage"] = result.usage.model_dump(mode="json")
                    except Exception as exc:
                        receipt["model_errors"].append(type(exc).__name__)
                    receipt["gateway_calls"] = gateway.calls
                    receipt["typed_failure_observed"] = gateway.read_failed
                    receipt["typed_failure_recovered"] = gateway.calls.count("read_artifact") >= 2
        verified = any(r.get("integrity_verified") for r in guard.receipts)
        receipt["safety_errors"] += [
            r["error_code"]
            for r in guard.receipts
            if r.get("error_code") in {"context_integrity_failed", "context_preflight_unavailable"}
        ]
        receipt["context_integrity_verified"] = verified
        receipt["admitted"] = (
            verified
            and not receipt["safety_errors"]
            and len(receipt["context_tiers"]) == 5
            and receipt["context_tiers"][-1].get("overflow_blocked_before_inference", False)
        )
        if not receipt["admitted"]:
            receipt["safety_errors"].append("context_integrity_unverified")
    except Exception as exc:
        receipt["safety_errors"].append(getattr(exc, "code", type(exc).__name__))
        write(out / "private/exception.json", {"type": type(exc).__name__, "message": str(exc)})
    trace = out / "private/trace.jsonl"
    if trace.exists():
        raw_schemas = [
            json.loads(s)["payload"]
            for s in trace.read_text().splitlines()
            if json.loads(s)["event_type"] == "logical.tool.schema_validation"
        ]
    receipt.update(
        request_counts=count,
        elapsed_ms=(monotonic() - started) * 1000,
        outputs=outputs,
        schema_attempts=len(raw_schemas),
        schema_valid=sum(s["valid"] for s in raw_schemas),
        schema_failures=sum(not s["valid"] for s in raw_schemas),
        context_receipts=guard.receipts if guard else [],
    )
    write(out / "receipt.json", receipt)
    return receipt


async def run_cell(candidate, index, skills, stage, context, protocol, pool, protected):
    expected = protocol["tasks"][index - 1]
    group = "B0" if candidate == "B0" else ("B2" if skills else "B1")
    cell = {
        "cell_id": f"{candidate}-t{index}" + ("-skills" if skills else "-plain"),
        "candidate": candidate,
        "task_index": index,
        "family": expected["family"],
        "position": expected["position"],
        "group": group,
        "skills": skills,
        "stage": stage,
    }
    if context is not None:
        pilot.CONTEXT = context
        protocol["groups"][group] = {
            "manager_model": context.model,
            "request_extra_body": {"reasoning_effort": "none"} if context.disable_thinking else {},
        }
    planner_log = ROOT / "planner-server.log"
    log_start = planner_log.stat().st_size
    pilot.journal("cell_started", cell=cell)
    row = await asyncio.wait_for(pilot.one_cell(cell, protocol, pool, protected), timeout=5100)
    with planner_log.open("rb") as stream:
        stream.seek(log_start)
        interval = stream.read()
    write(
        ROOT / "cells" / cell["cell_id"] / "private/planner-log-interval.json",
        {
            "text": interval.decode(errors="replace"),
            "bytes": len(interval),
            "sha256": hashlib.sha256(interval).hexdigest(),
        },
    )
    pilot.journal(
        "cell_finished",
        cell=cell["cell_id"],
        completed=row["completed"],
        evaluation=row["original_evaluation"],
        schema_failures=row["schema_failures"],
        system_problems=row["system_problems"],
    )
    if row["system_problems"]:
        raise RuntimeError("system_boundary:" + ",".join(row["system_problems"]))
    return row


async def main(args):
    assert sys.platform == "linux" and APP == ROOT / "app"
    assert not (ROOT / "journal.jsonl").exists(), "No automatic rerun/resume"
    configure()
    agents.set_tracing_disabled(True)
    _load_control_plane_key(args.api_key_file, "DASHSCOPE_API_KEY")
    protocol = json.loads(
        (APP / "configs/experiments/lightweight-planner-competence-v1.json").read_text()
    )
    assert pilot.digest(pilot.SELECTION / "manifest.json") == protocol["task_freeze_sha256"]
    assert pilot.digest(APP / protocol["skills"]["path"]) == protocol["skills"]["sha256"]
    protected = pilot.protected_hashes()
    files = {
        str(p.relative_to(APP)): pilot.digest(p)
        for folder in ("src", "scripts", "configs")
        for p in sorted((APP / folder).rglob("*"))
        if p.is_file() and "__pycache__" not in p.parts
    }
    write(
        ROOT / "execution-freeze.json",
        {
            "base_commit": "70a75ae",
            "source_sha256": files,
            "protected_sha256": protected,
            "plan": PLAN,
            "maximum_benchmark_cells": 42,
            "semantic_retries": 0,
            "historical_phase2_resumed": False,
        },
    )
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: (ROOT / "STOP").touch(exist_ok=True))
    deadline = monotonic() + PLAN["matrix_wall_ceiling_seconds"]
    pool = pilot.frozen._yaml(APP / protocol["infrastructure_design"]["model_pool_path"])
    rows = []
    admitted = []
    blocked = {}
    contexts = {}
    pilot.journal("started", pid=os.getpid(), maximum_cells=42)

    def check():
        if (ROOT / "STOP").exists() or monotonic() >= deadline:
            raise RuntimeError("matrix_stop_or_deadline")
        if pilot.protected_hashes() != protected or any(
            pilot.digest(APP / p) != sha for p, sha in files.items()
        ):
            raise RuntimeError("protected_history_or_source_changed")

    try:
        for candidate in PLAN["candidate_order"]:
            check()
            try:
                # Pipeline finite official downloads with earlier candidate validation.
                wait_until = monotonic() + PLAN["download_timeout_seconds_per_candidate"]
                while (
                    candidate in PLAN["downloads"]
                    and not (ROOT / (candidate + "-download.json")).exists()
                ):
                    check()
                    if (ROOT / "downloads-finished.json").exists() or monotonic() >= wait_until:
                        break
                    await asyncio.sleep(2)
                contexts[candidate] = await load(candidate, "compatibility")
                receipt = await asyncio.wait_for(
                    compatibility(candidate, contexts[candidate]), timeout=900
                )
                if receipt["admitted"]:
                    admitted.append(candidate)
                else:
                    blocked[candidate] = receipt["safety_errors"]
            except Exception as exc:
                if "Executor" in str(exc):
                    raise
                blocked[candidate] = [type(exc).__name__]
                write(
                    ROOT / "blocked" / f"{candidate}.json",
                    {"candidate": candidate, "type": type(exc).__name__, "message": str(exc)},
                )
            pilot.journal(
                "compatibility_finished", candidate=candidate, admitted=candidate in admitted
            )
        write(
            ROOT / "selection.json",
            {"admitted": admitted, "blocked": blocked, "score_based_selection": False},
        )
        for stage, indices in [("screening", [1, 3, 5]), ("matrix-extension", [2, 4, 6])]:
            for candidate in admitted:
                check()
                context = await load(candidate, stage)
                for index in indices:
                    check()
                    rows.append(
                        await run_cell(
                            candidate, index, False, stage, context, protocol, pool, protected
                        )
                    )
        # New matched baseline under the same resident pool and independent service.
        for index in range(1, 7):
            check()
            rows.append(
                await run_cell(
                    "B0", index, False, "matched-baseline", None, protocol, pool, protected
                )
            )
        skill_models = []
        for candidate in PLAN["skills_candidates"]:
            if candidate not in admitted:
                continue
            receipt = json.loads((ROOT / "compatibility" / candidate / "receipt.json").read_text())
            if not receipt["schema_valid"] and not any(
                r["schema_valid"] for r in rows if r["cell"]["candidate"] == candidate
            ):
                continue
            skill_models.append(candidate)
        write(
            ROOT / "skills-selection.json",
            {
                "candidates": skill_models,
                "rule": PLAN["skills_selection"],
                "score_based_selection": False,
            },
        )
        for candidate in skill_models:
            check()
            context = await load(candidate, "skills")
            for index in range(1, 7):
                check()
                rows.append(
                    await run_cell(
                        candidate,
                        index,
                        True,
                        "skills-ablation",
                        context,
                        protocol,
                        pool,
                        protected,
                    )
                )
        write(
            ROOT / "matrix-complete.json",
            {
                "cells": len(rows),
                "admitted_candidates": admitted,
                "blocked_candidates": blocked,
                "skills_candidates": skill_models,
                "semantic_retries": 0,
                "protected_history_unchanged": pilot.protected_hashes() == protected,
                "historical_phase2_resumed": False,
            },
        )
        pilot.journal("completed", cells=len(rows))
    except BaseException as exc:
        write(
            ROOT / "matrix-stopped.json",
            {
                "type": type(exc).__name__,
                "message": str(exc),
                "completed_cells": len(rows),
                "admitted": admitted,
                "blocked": blocked,
                "historical_phase2_resumed": False,
            },
        )
        pilot.journal("stopped", type=type(exc).__name__, completed_cells=len(rows))
        raise
    finally:
        # Only unload models belonging to this new endpoint; Executor endpoint untouched.
        for model in (await api("ps")).get("models", []):
            if model["name"].startswith("multiscale-"):
                await api("generate", {"model": model["name"], "keep_alive": 0, "stream": False})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-key-file", type=Path, required=True)
    asyncio.run(main(parser.parse_args()))
