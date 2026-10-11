"""Continue untouched cells after explicit authorization of external GPU contention.

Existing calls and stop evidence remain immutable. Only new Managers move to A28.
"""

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
from datetime import UTC, datetime, timedelta
from pathlib import Path
from time import monotonic

ROOT = Path("/home/super/xiaoming/multiscale-planner-evaluation-v1/run-001")
sys.path[:0] = [str(ROOT / "app/scripts"), str(ROOT / "app/src")]
import agents  # noqa: E402
import httpx  # noqa: E402
import multiscale_planner_evaluation_v1 as original  # noqa: E402
from multiscale_planner_context_v1 import MultiscaleContextConfig  # noqa: E402
from sdk_native_infra_preliminary_v1_3 import _load_control_plane_key  # noqa: E402

from infra_joint.experiments.manager_context import truncation_events  # noqa: E402
from infra_joint.experiments.pilot_safety import PilotRequestBudget  # noqa: E402

pilot = original.pilot
write = pilot.write_new
SERVICE = ROOT / "a28-service.json"
URL = "http://127.0.0.1:11451"
RUNNER_URL = "http://127.0.0.1:11452"
CURRENT = None
RESOURCE_SAMPLES = []
RESOURCE_FAILURE = None
LAST_RESOURCE_CHECK = 0.0
RESOURCE_LOCK = asyncio.Lock()
TOKENIZER_TUNNEL = None
CONTINUATION_ID = None


def configure():
    original.configure()
    original_node_json = pilot.node_json
    audit_wrapper = """def audit_log_interval(before, after):
 import copy
 raw_before=before.get("gpu_compute_processes")
 raw_after=after.get("gpu_compute_processes")
 before=copy.deepcopy(before); after=copy.deepcopy(after)
 allowed={3763,3764,1130531,1130540}
 for value in (before,after):
  if value.get("gpu_compute_processes") is not None:
   value["gpu_compute_processes"]=[p for p in value["gpu_compute_processes"] if p["pid"] in allowed]
 result=_resident_audit(before,after)
 result["external_gpu_process_set_changed"]=(
  {p["pid"] for p in raw_before or []}!={p["pid"] for p in raw_after or []})
 result["external_contention_authorized_for_continuation"]=True
 return result
"""

    def node_json(agent, code):
        needle = "from resident_model_pool_attestation_v1 import audit_log_interval; "
        if needle in code:
            code = code.replace(
                needle,
                "from resident_model_pool_attestation_v1 import audit_log_interval "
                "as _resident_audit; exec(" + repr(audit_wrapper) + "); ",
                1,
            )
        return original_node_json(agent, code)

    pilot.node_json = node_json
    pilot.PilotRequestBudget = ResourceBoundBudget


async def resource_check(*, force=False, wait_timeout=240):
    global LAST_RESOURCE_CHECK, RESOURCE_FAILURE
    async with RESOURCE_LOCK:
        if not force and monotonic() - LAST_RESOURCE_CHECK < 5:
            return
        wait_started = monotonic()
        waiting = False
        while True:
            gpu = await asyncio.to_thread(original.gpu_state)
            memory = await asyncio.to_thread(
                pilot.node_json,
                "A28",
                "import json; from pathlib import Path; "
                "v={s.split(':')[0]:int(s.split()[1]) for s in Path('/proc/meminfo')"
                ".read_text().splitlines() if s.startswith(('MemAvailable:','MemTotal:'))}; "
                "print(json.dumps(v))",
            )
            LAST_RESOURCE_CHECK = monotonic()
            sample = {"utc": datetime.now(UTC).isoformat(), "gpu": gpu, "a28_memory_kib": memory}
            RESOURCE_SAMPLES.append(sample)
            problem = None
            if any(row["free_mib"] < 512 for row in gpu):
                problem = "controller_gpu_headroom_below_512MiB"
            if memory["MemAvailable"] < 8 * 1024**2:
                problem = "A28_memory_headroom_below_8GiB"
            if problem is None:
                if waiting:
                    pilot.journal(
                        "resource_wait_completed", waited_seconds=monotonic() - wait_started
                    )
                return
            if not waiting:
                pilot.journal("resource_wait_started", code=problem, timeout_seconds=wait_timeout)
                waiting = True
            if (ROOT / "STOP").exists() or monotonic() - wait_started >= wait_timeout:
                RESOURCE_FAILURE = problem
                if (
                    CURRENT is not None
                    and not (CURRENT / "private/resource-boundary.json").exists()
                ):
                    write(CURRENT / "private/resource-boundary.json", {"code": problem, **sample})
                raise RuntimeError(problem)
            await asyncio.sleep(5)


class ResourceBoundBudget(PilotRequestBudget):
    async def control_hook(self, request):
        await resource_check()
        await super().control_hook(request)

    async def worker_hook(self, request):
        if request.method == "POST" and request.url.path == "/execute/operator":
            await resource_check()
        await super().worker_hook(request)


async def api(route, body=None, timeout=30):
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.request(
            "GET" if body is None else "POST", URL + "/api/" + route, json=body
        )
        response.raise_for_status()
        return response.json()


def stop_tokenizer_tunnel():
    global TOKENIZER_TUNNEL
    if TOKENIZER_TUNNEL is not None:
        proc = Path(f"/proc/{TOKENIZER_TUNNEL.pid}/cmdline")
        command = proc.read_bytes().decode() if proc.exists() else ""
        assert not command or "127.0.0.1:11452:127.0.0.1:" in command
        if command:
            TOKENIZER_TUNNEL.terminate()
            TOKENIZER_TUNNEL.wait(timeout=10)
        TOKENIZER_TUNNEL = None


async def load(candidate, phase):
    global TOKENIZER_TUNNEL
    phase = f"{CONTINUATION_ID}-{phase}"
    await resource_check(force=True, wait_timeout=600)
    if candidate == "qwen35-27b":
        return await original.load(candidate, "continued-" + phase)
    start = monotonic()
    service = json.loads(SERVICE.read_text())
    before = await pilot.residency()
    for model in (await api("ps")).get("models", []):
        assert model["name"].startswith("multiscale-")
        await api("generate", {"model": model["name"], "keep_alive": 0, "stream": False})
    stop_tokenizer_tunnel()
    tag = "multiscale-" + candidate + "-32k-v1"
    await api(
        "create",
        {
            "model": tag,
            "from": original.PLAN["downloads"][candidate],
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
    show = await api("show", {"model": tag})
    resident = next(m for m in (await api("ps"))["models"] if m["name"] in {tag, tag + ":latest"})
    code = "import json; from pathlib import Path; result=[]; "
    code += f"server_pid={service['server_pid']!r}; "
    code += "\nfor p in Path('/proc').iterdir():\n if not p.name.isdigit(): continue"
    code += "\n try:\n  status=(p/'status').read_text(); "
    code += "parent=int(next(s.split()[1] for s in status.splitlines() if s.startswith('PPid:'))); "
    code += "cmd=(p/'cmdline').read_bytes().decode().split('\\0'); "
    code += "result.append(cmd) if parent==server_pid and '--port' in cmd else None"
    code += "\n except (OSError,StopIteration): pass\nprint(json.dumps(result))"
    runners = await asyncio.to_thread(pilot.node_json, "A28", code)
    assert len(runners) == 1
    port = runners[0][runners[0].index("--port") + 1]
    TOKENIZER_TUNNEL = subprocess.Popen(
        [
            "ssh",
            "-N",
            "-o",
            "BatchMode=yes",
            "-o",
            "ExitOnForwardFailure=yes",
            "-o",
            "ServerAliveInterval=15",
            "-L",
            "127.0.0.1:11452:127.0.0.1:" + port,
            "edge@192.168.0.128",
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=(ROOT / "private" / f"tokenizer-{phase}-{candidate}.log").open("x"),
        start_new_session=True,
    )
    for _ in range(30):
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                response = await client.get(RUNNER_URL + "/props")
                response.raise_for_status()
                props = response.json()
            break
        except httpx.HTTPError:
            await asyncio.sleep(0.2)
    else:
        raise RuntimeError("owned_tokenizer_tunnel_unavailable")

    def field(key):
        found = re.search(r"^" + key + r" (.+)$", show["modelfile"], re.M)
        return found[1] if found else ""

    context = MultiscaleContextConfig(
        model=tag,
        digest=resident["digest"],
        model_blob=props["model_path"].rsplit("/", 1)[-1],
        template_sha256=hashlib.sha256(show["template"].encode()).hexdigest(),
        ollama_url=URL,
        runner_url=RUNNER_URL,
        renderer=field("RENDERER"),
        parser=field("PARSER"),
        disable_thinking=candidate.startswith("qwen35"),
    )
    old = json.loads((ROOT / "compatibility" / candidate / "receipt.json").read_text())["context"]
    for key in ("digest", "model_blob", "template_sha256", "renderer", "parser"):
        assert getattr(context, key) == old[key], "Manager identity changed during relocation"
    after = await pilot.residency()
    for node in before:
        for b, a in zip(before[node]["instances"], after[node]["instances"], strict=True):
            assert b["runner"]["pid"] == a["runner"]["pid"], "Executor runner changed"
    await resource_check(force=True)
    write(
        ROOT / "private/deployment" / f"continued-{phase}-{candidate}.json",
        {
            "candidate": candidate,
            "phase": phase,
            "manager_node": "A28",
            "elapsed_ms": (monotonic() - start) * 1000,
            "gpu": RESOURCE_SAMPLES[-1]["gpu"],
            "a28_memory_kib": RESOURCE_SAMPLES[-1]["a28_memory_kib"],
            "resident_size_vram": resident.get("size_vram"),
            "context": asdict(context),
            "show": show,
            "executor_runners_unchanged": True,
            "same_manager_weights_after_relocation": True,
            "tokenizer_tunnel_pid": TOKENIZER_TUNNEL.pid,
        },
    )
    return context


async def one(candidate, index, skills, stage, context, protocol, pool, protected):
    global CURRENT, RESOURCE_SAMPLES, RESOURCE_FAILURE
    identifier = f"{candidate}-t{index}" + ("-skills" if skills else "-plain")
    CURRENT = ROOT / "cells" / identifier
    RESOURCE_SAMPLES = []
    RESOURCE_FAILURE = None
    service = json.loads(SERVICE.read_text())
    log_path = service["remote_service_root"] + "/server.log"
    offset = await asyncio.to_thread(
        pilot.node_json,
        "A28",
        "import json; from pathlib import Path; print(json.dumps(Path("
        + repr(log_path)
        + ").stat().st_size))",
    )
    row = await original.run_cell(
        candidate, index, skills, stage, context, protocol, pool, protected
    )
    if candidate not in {"B0", "qwen35-27b"}:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(RUNNER_URL + "/slots")
            response.raise_for_status()
            if any(slot["is_processing"] for slot in response.json()):
                raise RuntimeError("owned_A28_Manager_not_drained_after_cell")
    code = "import json,hashlib; from pathlib import Path; "
    code += "data=Path(" + repr(log_path) + ").read_bytes()[" + str(offset) + ":]; "
    code += "print(json.dumps({'text':data.decode(errors='replace'),'bytes':len(data),"
    code += "'sha256':hashlib.sha256(data).hexdigest()}))"
    interval = await asyncio.to_thread(pilot.node_json, "A28", code)
    write(CURRENT / "private/a28-planner-log-interval.json", interval)
    write(
        CURRENT / "private/continuation-resources.json",
        {
            "manager_node": "strong-4090" if candidate in {"B0", "qwen35-27b"} else "A28",
            "external_gpu_contention_authorized": True,
            "samples": RESOURCE_SAMPLES,
            "resource_failure": RESOURCE_FAILURE,
        },
    )
    if (
        RESOURCE_FAILURE
        or truncation_events(interval["text"])
        or "out of memory" in interval["text"].lower()
    ):
        raise RuntimeError(RESOURCE_FAILURE or "new_Manager_OOM_or_truncation")
    CURRENT = None
    return row


async def main(args):
    global CONTINUATION_ID
    CONTINUATION_ID = args.continuation_id
    assert sys.platform == "linux" and (ROOT / "matrix-stopped.json").exists()
    freeze_name = f"continuation-freeze-{args.continuation_id}.json"
    assert not (ROOT / freeze_name).exists()
    configure()
    agents.set_tracing_disabled(True)
    _load_control_plane_key(args.api_key_file, "DASHSCOPE_API_KEY")
    freeze = json.loads((ROOT / "execution-freeze.json").read_text())
    protocol = json.loads(
        (ROOT / "app/configs/experiments/lightweight-planner-competence-v1.json").read_text()
    )
    protected = freeze["protected_sha256"]
    amendment = {
        "reason": (
            "explicit user permits continuation with unrelated external GPU work; do not pause it"
        ),
        "existing_stop_preserved": True,
        "existing_model_calls_repeated": 0,
        "new_manager_placement": "A28 independent endpoint; same weights/parser/context/settings",
        "external_processes_modified": False,
        "gpu_free_minimum_mib": 512,
        "headroom_amendment": (
            "Managers now use unified-memory A28; controller Executors remain resident. "
            "512MiB reserve replaces the 2GiB new-GPU-model-load threshold; actual OOM stops."
        ),
        "A28_available_ram_minimum_gib": 8,
        "resource_sample_interval_seconds": 5,
        "resource_wait_request_seconds": 240,
        "resource_wait_between_cells_seconds": 600,
        "resource_wait_counts_against_original_cell_and_matrix_deadlines": True,
        "skills_candidates": ["qwen35-9b", "qwen35-27b"],
        "skills_change_reason": (
            "4B plain cohort now has mixed Manager placement; 9B replacement frozen before "
            "its first benchmark score to preserve matched Skills conditions"
        ),
        "4b_cohort_mixed_hardware_must_be_stratified": True,
        "maximum_cells_unchanged": 42,
        "semantic_retries": 0,
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "original_execution_freeze_sha256": pilot.digest(ROOT / "execution-freeze.json"),
        "original_source_map_still_required": True,
        "source": str(Path(__file__).resolve()),
        "frozen_at": datetime.now(UTC).isoformat(),
    }
    write(ROOT / freeze_name, amendment)
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: (ROOT / "STOP").touch(exist_ok=True))
    journal = [json.loads(s) for s in (ROOT / "journal.jsonl").read_text().splitlines()]
    deadline = datetime.fromisoformat(journal[0]["utc"]) + timedelta(seconds=216000)
    rows = [
        json.loads(path.read_text()) for path in (ROOT / "cells").glob("*/sanitized-result.json")
    ]
    observed = {row["cell"]["cell_id"] for row in rows}
    admitted = json.loads((ROOT / "selection.json").read_text())["admitted"]
    pool = pilot.frozen._yaml(ROOT / "app" / protocol["infrastructure_design"]["model_pool_path"])

    async def check():
        if (ROOT / "STOP").exists() or datetime.now(UTC) >= deadline:
            raise RuntimeError("matrix_stop_or_original_deadline")
        if pilot.protected_hashes() != protected or any(
            pilot.digest(ROOT / "app" / name) != sha
            for name, sha in freeze["source_sha256"].items()
        ):
            raise RuntimeError("protected_history_or_original_source_changed")
        await resource_check(force=True, wait_timeout=600)

    pilot.journal(
        "continued",
        pid=os.getpid(),
        already_executed_cells=len(rows),
        external_processes_untouched=True,
        original_stop_preserved=True,
    )
    try:
        for stage, indices in [("screening", [1, 3, 5]), ("matrix-extension", [2, 4, 6])]:
            for candidate in admitted:
                remaining = [i for i in indices if f"{candidate}-t{i}-plain" not in observed]
                if not remaining:
                    continue
                await check()
                context = await load(candidate, stage)
                for index in remaining:
                    await check()
                    rows.append(
                        await one(
                            candidate, index, False, stage, context, protocol, pool, protected
                        )
                    )
        for index in range(1, 7):
            if f"B0-t{index}-plain" in observed:
                continue
            await check()
            rows.append(
                await one("B0", index, False, "matched-baseline", None, protocol, pool, protected)
            )
        skill_models = amendment["skills_candidates"]
        skills_selection = ROOT / "skills-selection.json"
        if skills_selection.exists():
            assert json.loads(skills_selection.read_text())["candidates"] == skill_models
        else:
            write(
                skills_selection,
                {
                    "candidates": skill_models,
                    "score_based_selection": False,
                    "matched_manager_placement": True,
                    "rule": amendment["skills_change_reason"],
                },
            )
        for candidate in skill_models:
            remaining = [i for i in range(1, 7) if f"{candidate}-t{i}-skills" not in observed]
            if not remaining:
                continue
            await check()
            context = await load(candidate, "skills")
            for index in remaining:
                await check()
                rows.append(
                    await one(
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
                "skills_candidates": skill_models,
                "semantic_retries": 0,
                "protected_history_unchanged": pilot.protected_hashes() == protected,
                "historical_phase2_resumed": False,
                "resumed_after_recorded_system_stop": True,
                "external_gpu_contention_observed": True,
                "mixed_4b_manager_placement": True,
            },
        )
        pilot.journal("completed", cells=len(rows), semantic_retries=0)
    except BaseException as exc:
        write(
            ROOT / f"continuation-stopped-{args.continuation_id}.json",
            {
                "type": type(exc).__name__,
                "message": str(exc),
                "completed_cells": len(rows),
                "external_processes_modified": False,
            },
        )
        pilot.journal("continuation_stopped", type=type(exc).__name__, completed_cells=len(rows))
        raise
    finally:
        for model in (await api("ps")).get("models", []):
            if model["name"].startswith("multiscale-"):
                await api("generate", {"model": model["name"], "keep_alive": 0, "stream": False})
        stop_tokenizer_tunnel()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-key-file", type=Path, required=True)
    parser.add_argument("--continuation-id", choices=["004"], required=True)
    asyncio.run(main(parser.parse_args()))
