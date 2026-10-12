"""Owned A28 Planner service and cached resource admission for the skills pilot.

Bootstrap serves existing verified weights without loading a model. All mutable
files belong to this pilot; old cached blobs are linked individually read-only.
"""

# ruff: noqa: E501 -- Embedded remote Python keeps its exact transport text.

from __future__ import annotations

import argparse
import asyncio
import contextlib
import hashlib
import json
import os
import re
import signal
import socket
import subprocess
import time
import urllib.request
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/home/super/xiaoming/skill-granularity-pilot-v1/run-001")
UTC = timezone.utc  # noqa: UP017 -- Bootstrap also runs on controller Python 3.10.
REMOTE_ROOT = "/mnt/ssd/skill-granularity-pilot-v1/run-001/planner-service-001"
OLD_STORE = "/mnt/ssd/multiscale-planner-evaluation-v1/run-001/planner-service-001/models"
HOST = "edge@192.168.0.128"
BINARY = "/mnt/ssd/heterogeneous-v1/runtime/ollama-0.34.0/bin/ollama"
URL = "http://127.0.0.1:11451"
RUNNER_URL = "http://127.0.0.1:11452"
TEMPLATE = "b507b9c2f6ca642bffcd06665ea7c91f235fd32daeefdf875a0f938db05fb315"
PINNED = {
    "qwen35-4b": {
        "model": "multiscale-qwen35-4b-32k-v1",
        "digest": "4da6b5b4d7d7f2ff27fbf83d4f84d5cff821a6459b413eff496a497916d1a4a9",
        "model_blob": "sha256-a9d0a3e1d8c91732a3812becd31f8d4a8ff57414903f226306069f0437e2ac50",
        "renderer": "qwen3.5",
        "parser": "qwen3.5",
    },
    "qwen35-9b": {
        "model": "multiscale-qwen35-9b-32k-v1",
        "digest": "86a0db6f4ae0a6ed01dc3a0f12d981637e095520ed6f86763fd6d2e05ec5c341",
        "model_blob": "sha256-02d45dc1cf451ba2475ac33b301c2dd8f985abe4c182ce04a1f2f5bf0260278d",
        "renderer": "qwen3.5",
        "parser": "qwen3.5",
    },
    "qwen35-27b": {
        "model": "qwen35-27b-resident-32k-v1",
        "digest": "9770c614b936fc722ff9f0fb3ecc0bd6dd0e91a001bf22a402e16ec968096bae",
        "model_blob": "sha256-f5f1dd8920d417aac2718b0bda3403da274301efdd6760b4f0f4b864ff2ad57d",
        "renderer": "qwen3.8",
        "parser": "qwen3.5",
    },
}

REMOTE_CODE = r"""
import hashlib,json,os,pathlib,shutil,signal,socket,subprocess,time,urllib.request
root=pathlib.Path(payload['remote_root'])
assert str(root.resolve())=='/mnt/ssd/skill-granularity-pilot-v1/run-001/planner-service-001'
def api(port,route):
 with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/{route}',timeout=8) as s:return json.load(s)
def proc(pid):
 p=pathlib.Path('/proc')/str(pid)
 return {'pid':pid,'start_ticks':p.joinpath('stat').read_text().rsplit(')',1)[1].split()[19],
  'argv':p.joinpath('cmdline').read_bytes().decode().split('\0')[:-1]}
def executor():
 receipt=pathlib.Path('/mnt/ssd/resident-model-pool-v1/services/start-003/resident-a28-qwen35-27b-v1-receipt.json')
 pid=json.loads(receipt.read_text())['pid']; runners=[]
 for p in pathlib.Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:
   pp=int(next(s.split()[1] for s in (p/'status').read_text().splitlines() if s.startswith('PPid:')))
   v=proc(int(p.name))
   if pp==pid and pathlib.Path(v['argv'][0]).name=='llama-server':runners.append(v)
  except (OSError,StopIteration,IndexError):pass
 assert len(runners)==1,'original_executor_runner_missing'
 ps=api(11436,'ps')['models']; assert len(ps)==1 and ps[0]['context_length']==32768
 return {'server':proc(pid),'runners':runners,'models':[{'name':m['name'],'digest':m['digest'],'context_length':m['context_length']} for m in ps]}
def memory():
 return {s.split(':')[0]:int(s.split()[1]) for s in pathlib.Path('/proc/meminfo').read_text().splitlines() if s.startswith(('MemAvailable:','MemTotal:'))}
def owned():
 r=json.loads((root/'ownership-receipt.json').read_text()); p=proc(r['server_pid'])
 assert p==r['server_identity'],'owned_server_identity_changed'
 env=dict(x.split('=',1) for x in (pathlib.Path('/proc')/str(p['pid'])/'environ').read_bytes().decode().split('\0') if '=' in x)
 assert env.get('OLLAMA_MODELS')==str(root/'models') and env.get('OLLAMA_HOST')=='127.0.0.1:11450'
 return r
op=payload['operation']
if op=='bootstrap':
 assert not root.exists(),'new_service_namespace_exists'
 mem=memory(); assert mem['MemAvailable']>=16*1024**2,'insufficient_A28_start_memory'
 assert shutil.disk_usage('/mnt/ssd').free>=25*1024**3,'insufficient_A28_disk'
 with socket.socket() as s:assert s.connect_ex(('127.0.0.1',11450))!=0,'new_planner_port_occupied'
 before=executor(); root.mkdir(parents=True); store=root/'models'; (store/'blobs').mkdir(parents=True)
 cached=[]; old=pathlib.Path(payload['old_store'])
 for pin in payload['pinned']:
  relative=pathlib.Path('manifests/registry.ollama.ai/library')/pin['model']/'latest'
  source=old/relative; raw=source.read_bytes(); assert hashlib.sha256(raw).hexdigest()==pin['digest'],'manifest_digest_changed'
  target=store/relative; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(raw)
  manifest=json.loads(raw)
  for desc in [manifest['config'],*manifest['layers']]:
   name=desc['digest'].replace(':','-'); src=old/'blobs'/name; dst=store/'blobs'/name
   assert src.is_file() and src.stat().st_size==desc['size'],'cached_blob_missing_or_size_changed'
   if not dst.exists():dst.symlink_to(src)
  cached.append({'model':pin['model'],'manifest_sha256':pin['digest'],'blob_sizes_verified':True})
 env={k:v for k,v in os.environ.items() if not k.startswith('OLLAMA_') and k not in {'CUDA_VISIBLE_DEVICES','HIP_VISIBLE_DEVICES','GGML_VK_VISIBLE_DEVICES','ROCR_VISIBLE_DEVICES','GPU_DEVICE_ORDINAL'}}
 env.update(OLLAMA_HOST='127.0.0.1:11450',OLLAMA_MODELS=str(store),OLLAMA_KEEP_ALIVE='-1',OLLAMA_NUM_PARALLEL='1',OLLAMA_MAX_LOADED_MODELS='1',OLLAMA_KV_CACHE_TYPE='q8_0',OLLAMA_FLASH_ATTENTION='1',OLLAMA_VULKAN='0',OLLAMA_NO_CLOUD='1')
 p=subprocess.Popen([payload['binary'],'serve'],env=env,stdin=subprocess.DEVNULL,stdout=(root/'server.log').open('xb'),stderr=subprocess.STDOUT,start_new_session=True)
 for _ in range(30):
  assert p.poll() is None,'new_server_exited'
  try:version=api(11450,'version');break
  except OSError:time.sleep(1)
 else:raise RuntimeError('new_server_not_ready')
 assert api(11450,'ps')['models']==[],'bootstrap_must_not_load_model'
 assert executor()==before,'original_executor_changed'
 result={'server_pid':p.pid,'server_identity':proc(p.pid),'remote_service_root':str(root),'log_path':str(root/'server.log'),'port':11450,'binary_sha256':hashlib.sha256(pathlib.Path(payload['binary']).read_bytes()).hexdigest(),'version':version,'executor_before':before,'executor_runners_unchanged':True,'cache_manifest_digests':cached,'a28_memory_kib':mem,'disk_free_bytes':shutil.disk_usage('/mnt/ssd').free,'model_inference_calls':0,'loaded_models':[]}
 (root/'ownership-receipt.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
elif op=='memory':print(json.dumps(memory()))
elif op=='identity':
 r=owned(); assert executor()==r['executor_before'],'original_executor_changed';print(json.dumps({'server_identity':r['server_identity'],'executor_unchanged':True}))
elif op=='runner':
 r=owned();found=[]
 for p in pathlib.Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:
   pp=int(next(s.split()[1] for s in (p/'status').read_text().splitlines() if s.startswith('PPid:'))); v=proc(int(p.name))
   if pp==r['server_pid'] and pathlib.Path(v['argv'][0]).name=='llama-server':found.append(v)
  except (OSError,StopIteration,IndexError):pass
 assert len(found)==1,'owned_runner_missing';v=found[0];v['port']=int(v['argv'][v['argv'].index('--port')+1]);print(json.dumps(v))
elif op=='log':
 owned(); p=root/'server.log'; size=p.stat().st_size
 if payload.get('offset') is None:print(json.dumps(size))
 else:
  offset=payload['offset']; assert 0<=offset<=size and size-offset<=32*1024**2,'log_interval_invalid'
  with p.open('rb') as s:s.seek(offset);data=s.read()
  print(json.dumps({'text':data.decode(errors='replace'),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'offset':offset,'end_offset':size}))
elif op=='close':
 r=owned(); assert executor()==r['executor_before'];os.kill(r['server_pid'],signal.SIGTERM)
 for _ in range(40):
  if not pathlib.Path('/proc',str(r['server_pid'])).exists():break
  time.sleep(.25)
 else:raise RuntimeError('owned_server_did_not_exit')
 assert executor()==r['executor_before'];print(json.dumps({'owned_server_stopped':True,'original_executor_unchanged':True,'cache_logs_preserved':True}))
else:raise RuntimeError('unknown_service_operation')
"""


def write_new(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


def remote(operation, **kwargs):
    payload = {"operation": operation, "remote_root": REMOTE_ROOT, **kwargs}
    p = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", HOST, "python3", "-"],
        input="payload=" + repr(payload) + "\n" + REMOTE_CODE,
        text=True,
        capture_output=True,
        timeout=90,
    )
    if p.returncode:
        raise RuntimeError("owned_A28_service_operation_failed: " + p.stderr[-2000:])
    return json.loads(p.stdout)


def api_json(url, body=None, timeout=10):
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as stream:
        return json.load(stream)


def process_identity(pid):
    proc = Path("/proc") / str(pid)
    return {
        "pid": pid,
        "start_ticks": proc.joinpath("stat").read_text().rsplit(")", 1)[1].split()[19],
        "argv": proc.joinpath("cmdline").read_bytes().decode().split("\0")[:-1],
    }


def start_tunnel(root, port, destination, name):
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", port))
    forwarding = f"127.0.0.1:{port}:127.0.0.1:{destination}"
    p = subprocess.Popen(
        [
            "ssh",
            "-N",
            "-o",
            "BatchMode=yes",
            "-o",
            "ConnectTimeout=8",
            "-o",
            "ExitOnForwardFailure=yes",
            "-o",
            "ServerAliveInterval=15",
            "-o",
            "ServerAliveCountMax=3",
            "-L",
            forwarding,
            HOST,
        ],
        stdin=subprocess.DEVNULL,
        stdout=(root / "private" / (name + ".log")).open("xb"),
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    return {**process_identity(p.pid), "forwarding": forwarding}


def stop_tunnel(identity):
    if not identity:
        return
    if not Path("/proc", str(identity["pid"])).exists():
        return
    actual = process_identity(identity["pid"])
    assert all(actual[k] == identity[k] for k in ("pid", "start_ticks", "argv")), (
        "owned_tunnel_identity_changed"
    )
    assert identity["forwarding"] in actual["argv"] and HOST in actual["argv"]
    os.kill(identity["pid"], signal.SIGTERM)
    for _ in range(40):
        p = Path("/proc", str(identity["pid"]))
        if not p.exists() or p.joinpath("stat").read_text().rsplit(")", 1)[1].split()[0] == "Z":
            return
        time.sleep(0.1)
    raise RuntimeError("owned_tunnel_did_not_exit")


def bootstrap(root=ROOT):
    root = Path(root)
    assert root.resolve() == ROOT, "controller_namespace_changed"
    assert not (root / "a28-service.json").exists(), "service_receipt_exists"
    (root / "private").mkdir(parents=True, exist_ok=True)
    for port in (11451, 11452):
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", port))
    started = time.monotonic()
    receipt = remote(
        "bootstrap",
        old_store=OLD_STORE,
        binary=BINARY,
        pinned=[PINNED[c] for c in ("qwen35-4b", "qwen35-9b")],
    )
    # Persist ownership before tunnel readiness so failures remain cleanable.
    write_new(root / "a28-server-ownership.json", receipt)
    tunnel = start_tunnel(root, 11451, 11450, "a28-api-tunnel")
    write_new(root / "api-tunnel-ownership.json", tunnel)
    for _ in range(30):
        try:
            assert api_json(URL + "/api/ps")["models"] == []
            break
        except OSError:
            time.sleep(0.5)
    else:
        raise RuntimeError("owned_api_tunnel_not_ready")
    receipt.update(
        tunnel_pid=tunnel["pid"],
        tunnel_identity=tunnel,
        tunnel_url=URL,
        elapsed_ms=(time.monotonic() - started) * 1000,
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    )
    write_new(root / "a28-service.json", receipt)
    return receipt


def resource_sample():
    p = subprocess.run(
        [
            "nvidia-smi",
            "--query-gpu=index,memory.used,memory.free",
            "--format=csv,noheader,nounits",
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
    )
    gpu = [
        {"index": int(v[0]), "used_mib": int(v[1]), "free_mib": int(v[2])}
        for line in p.stdout.splitlines()
        if (v := line.replace(" ", "").split(","))
    ]
    assert len(gpu) == 2, "controller_gpu_inventory_changed"
    return {"utc": datetime.now(UTC).isoformat(), "gpu": gpu, "a28_memory_kib": remote("memory")}


class Service:
    def __init__(self, root=ROOT, baseline=None):
        self.root = Path(root)
        self.baseline = baseline
        self.receipt = json.loads((self.root / "a28-service.json").read_text())
        self.current = None
        self.tokenizer = None
        self.samples = []
        self.sample = None
        self.sample_error = None
        self.resource_failure = None
        self.sample_at = 0.0
        self.sample_task = None
        self.sample_lock = asyncio.Lock()
        self.closed = False
        deployments = list((self.root / "private/deployment").glob("*.json"))
        self.sequence = max(
            (
                int(match[1])
                for p in deployments
                if (match := re.match(r"(?:tunnel-)?(\d+)", p.stem))
            ),
            default=0,
        )
        try:
            remote("identity")
            tunnel = self.receipt["tunnel_identity"]
            actual = process_identity(tunnel["pid"])
            assert all(actual[k] == tunnel[k] for k in ("pid", "start_ticks", "argv"))
            assert tunnel["forwarding"] in actual["argv"] and HOST in actual["argv"]
            models = api_json(URL + "/api/ps")["models"]
            assert len(models) <= 1, "unexpected_owned_service_residents"
            if models:
                matching = [
                    c
                    for c in ("qwen35-4b", "qwen35-9b")
                    if models[0]["name"] in {PINNED[c]["model"], PINNED[c]["model"] + ":latest"}
                    and models[0]["digest"] == PINNED[c]["digest"]
                    and models[0]["context_length"] == 32768
                ]
                assert len(matching) == 1, "unexpected_owned_service_model"
                self.current = matching[0]
            active = []
            for path in deployments:
                if not path.stem.startswith("tunnel-"):
                    continue
                identity = json.loads(path.read_text())
                try:
                    actual = process_identity(identity["pid"])
                except FileNotFoundError:
                    continue
                if (
                    all(actual[k] == identity[k] for k in ("pid", "start_ticks", "argv"))
                    and identity["forwarding"] in actual["argv"]
                    and HOST in actual["argv"]
                ):
                    active.append(identity)
            assert len(active) <= 1, "multiple_owned_tokenizer_tunnels"
            self.tokenizer = active[0] if active else None
        except Exception as exc:
            raise RuntimeError(
                "owned_service_unavailable_restore_required_without_cell_rerun"
            ) from exc

    async def _sample(self):
        async with self.sample_lock:
            try:
                self.sample = await asyncio.to_thread(resource_sample)
                self.sample_error = None
                self.samples.append(self.sample)
                self.sample_at = time.monotonic()
            except Exception as exc:
                self.sample_error = str(exc)

    async def _sampler(self):
        while not self.closed:
            await asyncio.sleep(10)
            await self._sample()

    def _stop_check(self, deadline):
        from infra_joint.experiments.pilot_safety import PilotBudgetExceeded, PilotStopped

        if (self.root / "STOP").exists():
            raise PilotStopped("pilot STOP requested")
        if deadline is not None and time.monotonic() >= deadline:
            raise PilotBudgetExceeded("deadline exhausted during resource wait")

    async def check_resource(self, *, force=False, wait_timeout=240, deadline=None):
        self._stop_check(deadline)
        if force or self.sample is None:
            await self._sample()
        if self.sample_task is None:
            self.sample_task = asyncio.create_task(self._sampler())
        started = time.monotonic()
        while True:
            self._stop_check(deadline)
            if self.sample_error or time.monotonic() - self.sample_at > 35:
                self.resource_failure = "resource_sample_unavailable"
                raise RuntimeError("resource_sample_unavailable: " + str(self.sample_error))
            sample = self.sample
            okay = (
                all(g["free_mib"] >= 512 for g in sample["gpu"])
                and sample["a28_memory_kib"]["MemAvailable"] >= 8 * 1024**2
            )
            if okay:
                return sample
            if time.monotonic() - started >= wait_timeout:
                self.resource_failure = "resource_reserve_wait_exhausted"
                raise RuntimeError("resource_reserve_wait_exhausted")
            remaining = wait_timeout - (time.monotonic() - started)
            if deadline is not None:
                remaining = min(remaining, deadline - time.monotonic())
            await asyncio.sleep(max(0, min(1, remaining)))

    def budget_class(self):
        from infra_joint.experiments.pilot_safety import PilotBudgetExceeded, PilotRequestBudget

        service = self

        class ResourceBudget(PilotRequestBudget):
            async def resource_admission(self):
                try:
                    await service.check_resource(deadline=self.deadline)
                except PilotBudgetExceeded:
                    raise
                except RuntimeError as exc:
                    service.resource_failure = service.resource_failure or str(exc)
                    raise

            async def control_hook(self, request):
                self.check()
                await self.resource_admission()
                await super().control_hook(request)

            async def worker_hook(self, request):
                self.check()
                await self.resource_admission()
                await super().worker_hook(request)

        return ResourceBudget

    async def load(self, candidate, phase="load"):
        import httpx
        from multiscale_planner_context_v1 import (
            MultiscaleContextConfig,
            MultiscaleContextPreflight,
        )

        assert candidate in PINNED
        await self.check_resource(force=True, wait_timeout=600)
        started = time.monotonic()
        await asyncio.to_thread(remote, "identity")
        await self._unload()
        pin = PINNED[candidate]
        ollama, runner = URL, RUNNER_URL
        owned_runner = None
        if candidate == "qwen35-27b":
            assert self.baseline is not None, "resident_Manager_baseline_required"
            matches = [
                instance
                for instance in self.baseline["strong-4090"]["instances"]
                if instance["target"]["derived_tag"] == pin["model"]
            ]
            assert len(matches) == 1, "resident_Manager_baseline_ambiguous"
            instance = matches[0]
            command = instance["runner"]["command"]
            port = int(command[command.index("--port") + 1])
            ollama = "http://127.0.0.1:" + str(instance["target"]["port"])
            runner = "http://127.0.0.1:" + str(port)
        else:
            await asyncio.to_thread(
                api_json,
                URL + "/api/generate",
                {
                    "model": pin["model"],
                    "prompt": "",
                    "stream": False,
                    "keep_alive": -1,
                    "think": False,
                    "options": {"num_ctx": 32768, "num_predict": 0},
                },
                240,
            )
            self.current = candidate
            owned_runner = await asyncio.to_thread(remote, "runner")
            self.sequence += 1
            self.tokenizer = start_tunnel(
                self.root, 11452, owned_runner["port"], f"tokenizer-{self.sequence:03d}-{candidate}"
            )
            write_new(
                self.root / "private/deployment" / f"tunnel-{self.sequence:03d}.json",
                self.tokenizer,
            )
            for _ in range(60):
                try:
                    await asyncio.to_thread(api_json, runner + "/props")
                    break
                except OSError:
                    await asyncio.sleep(0.2)
            else:
                raise RuntimeError("owned_tokenizer_not_ready")
        context = MultiscaleContextConfig(
            **pin,
            template_sha256=TEMPLATE,
            ollama_url=ollama,
            runner_url=runner,
            disable_thinking=True,
        )
        async with httpx.AsyncClient(timeout=20) as helper:
            await MultiscaleContextPreflight(context, helper).attest()
        await asyncio.to_thread(remote, "identity")
        sample = await self.check_resource(force=True, wait_timeout=600)
        resident = await asyncio.to_thread(api_json, ollama + "/api/ps")
        self.sequence += 1
        write_new(
            self.root / "private/deployment" / f"{self.sequence:03d}-{phase}-{candidate}.json",
            {
                "candidate": candidate,
                "phase": phase,
                "context": asdict(context),
                "elapsed_ms": (time.monotonic() - started) * 1000,
                "resources": sample,
                "resident": resident,
                "owned_runner": owned_runner,
                "executor_runners_unchanged": True,
                "model_generation_calls": 0,
            },
        )
        return context

    async def slots(self, context):
        return await asyncio.to_thread(api_json, context.runner_url + "/slots")

    async def log_size(self):
        return await asyncio.to_thread(remote, "log")

    async def log_interval(self, offset):
        return await asyncio.to_thread(remote, "log", offset=offset)

    async def _unload(self):
        try:
            if self.current is not None:
                await asyncio.to_thread(
                    api_json,
                    URL + "/api/generate",
                    {
                        "model": PINNED[self.current]["model"],
                        "keep_alive": 0,
                        "stream": False,
                    },
                    90,
                )
                self.current = None
        finally:
            if self.tokenizer:
                await asyncio.to_thread(stop_tunnel, self.tokenizer)
                self.tokenizer = None

    async def _cancel_sampler(self):
        self.closed = True
        if self.sample_task:
            self.sample_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.sample_task
            self.sample_task = None

    async def suspend(self):
        """Drain only owned model/tokenizer; retain the idle server for resume."""
        await self._cancel_sampler()
        await asyncio.to_thread(remote, "identity")
        await self._unload()
        assert (await asyncio.to_thread(api_json, URL + "/api/ps"))["models"] == []
        self.sequence += 1
        write_new(
            self.root / "private/deployment" / f"{self.sequence:03d}-service-suspended.json",
            {
                "utc": datetime.now(UTC).isoformat(),
                "owned_model_unloaded": True,
                "owned_tokenizer_tunnel_stopped": True,
                "idle_owned_server_preserved": True,
                "owned_api_tunnel_preserved": True,
                "cache_logs_preserved": True,
                "resume_requires_same_owned_server_identity": True,
            },
        )
        self.closed = False
        self.sample = None

    async def close(self):
        await self._cancel_sampler()
        await asyncio.to_thread(remote, "identity")
        await self._unload()
        cleanup = await asyncio.to_thread(remote, "close")
        await asyncio.to_thread(stop_tunnel, self.receipt["tunnel_identity"])
        write_new(
            self.root / "owned-service-cleanup.json",
            {
                "utc": datetime.now(UTC).isoformat(),
                **cleanup,
                "owned_api_tunnel_stopped": True,
                "foreign_processes_untouched": True,
            },
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bootstrap", action="store_true", required=True)
    args = parser.parse_args()
    if args.bootstrap:
        receipt = bootstrap()
        print(
            json.dumps(
                {
                    k: receipt[k]
                    for k in ("server_pid", "tunnel_pid", "elapsed_ms", "model_inference_calls")
                }
            )
        )


if __name__ == "__main__":
    main()
