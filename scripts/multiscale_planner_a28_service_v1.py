"""Move only the new Planner cache/service to A28 without loading any model."""

from __future__ import annotations

import hashlib
import json
import socket
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path("/home/super/xiaoming/multiscale-planner-evaluation-v1/run-001")
REMOTE_ROOT = "/mnt/ssd/multiscale-planner-evaluation-v1/run-001/planner-service-001"
HOST = "edge@192.168.0.128"
BINARY = "/mnt/ssd/heterogeneous-v1/runtime/ollama-0.34.0/bin/ollama"

REMOTE_CODE = r"""
import hashlib,json,os,pathlib,shutil,socket,subprocess,time,urllib.request
root=pathlib.Path(payload["remote_root"])
assert str(root.resolve())=="/mnt/ssd/multiscale-planner-evaluation-v1/run-001/planner-service-001"
def api(port, route):
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/{route}",timeout=5) as stream:
        return json.load(stream)
def state():
    info={}
    for line in pathlib.Path("/proc/meminfo").read_text().splitlines():
        key,value=line.split(":",1)
        if key in ("MemTotal","MemAvailable"):
            info[key+"_bytes"]=int(value.split()[0])*1024
    info["disk_free_bytes"]=shutil.disk_usage("/mnt/ssd").free
    receipt=pathlib.Path("/mnt/ssd/resident-model-pool-v1/services/start-003/resident-a28-qwen35-27b-v1-receipt.json")
    server_pid=json.loads(receipt.read_text())["pid"]
    runners=[]
    for proc in pathlib.Path("/proc").iterdir():
        if not proc.name.isdigit():continue
        try:
            status=(proc/"status").read_text()
            parent=int(next(line.split()[1] for line in status.splitlines()
                if line.startswith("PPid:")))
            argv=(proc/"cmdline").read_bytes().decode().split("\0")
            if parent==server_pid and pathlib.Path(argv[0]).name=="llama-server":
                runners.append({"pid":int(proc.name),"command":argv,
                    "start_ticks":(proc/"stat").read_text().rsplit(")",1)[1].split()[19]})
        except (OSError,StopIteration):pass
    assert len(runners)==1,"Exactly one existing Executor runner required"
    info["executor"]={"server_pid":server_pid,"runners":runners,"resident":api(11436,"ps")}
    return info
before=state()
if payload["operation"]=="prepare":
    assert before["MemAvailable_bytes"]>=16*1024**3,"Insufficient spare unified memory"
    assert before["disk_free_bytes"]>=25*1024**3,"Insufficient free disk"
    assert not root.exists(),"Planner service namespace already exists"
    with socket.socket() as probe:
        probe.settimeout(1)
        assert probe.connect_ex(("127.0.0.1",11450))!=0,"Independent Planner port occupied"
    root.mkdir(parents=True,exist_ok=False)
    (root/"models").mkdir()
    (root/"executor-before.json").write_text(json.dumps(before,indent=2))
    print(json.dumps(before))
elif payload["operation"]=="start":
    original=json.loads((root/"executor-before.json").read_text())
    assert before["executor"]==original["executor"],"Executor changed during cache copy"
    checked=[]
    for entry in payload["files"]:
        path=root/"models"/entry["relative"]
        assert path.is_file() and path.stat().st_size==entry["bytes"],"Copied cache size invalid"
        actual=hashlib.sha256(path.read_bytes()).hexdigest()
        assert actual==entry["sha256"],"Copied cache checksum mismatch"
        checked.append({"relative":entry["relative"],"bytes":entry["bytes"],"sha256":actual})
    env={key:value for key,value in os.environ.items() if not key.startswith("OLLAMA_")
        and key not in {"CUDA_VISIBLE_DEVICES","HIP_VISIBLE_DEVICES","GGML_VK_VISIBLE_DEVICES",
                        "ROCR_VISIBLE_DEVICES","GPU_DEVICE_ORDINAL"}}
    env.update(OLLAMA_HOST="127.0.0.1:11450",OLLAMA_MODELS=str(root/"models"),
        OLLAMA_KEEP_ALIVE="-1",OLLAMA_NUM_PARALLEL="1",OLLAMA_MAX_LOADED_MODELS="1",
        OLLAMA_KV_CACHE_TYPE="q8_0",OLLAMA_FLASH_ATTENTION="1",OLLAMA_VULKAN="0",OLLAMA_NO_CLOUD="1")
    process=subprocess.Popen([payload["binary"],"serve"],env=env,stdin=subprocess.DEVNULL,
        stdout=(root/"server.log").open("xb"),stderr=subprocess.STDOUT,start_new_session=True)
    for _ in range(30):
        if process.poll() is not None:raise RuntimeError("Independent Planner service exited")
        try:
            version=api(11450,"version")
            break
        except OSError:time.sleep(1)
    else:raise RuntimeError("Independent Planner endpoint did not become ready")
    resident=api(11450,"ps")
    assert resident.get("models")==[],"Bootstrap must not load any model"
    after=state()
    assert after["executor"]==original["executor"],"Executor changed during isolated service start"
    result={"server_pid":process.pid,"binary_sha256":hashlib.sha256(pathlib.Path(payload["binary"]).read_bytes()).hexdigest(),
        "remote_service_root":str(root),"port":11450,"version":version,"before":original,"after":after,
        "executor_runners_unchanged":True,"cache_files_verified":checked,"loaded_models":resident["models"],
        "model_inference_calls":0}
    (root/"ownership-receipt.json").write_text(json.dumps(result,indent=2))
    print(json.dumps(result))
else:raise RuntimeError("Unknown bootstrap operation")
"""


def write(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


def remote(operation, **extra):
    payload = {"operation": operation, "remote_root": REMOTE_ROOT, "binary": BINARY, **extra}
    source = "payload=" + repr(payload) + "\n" + REMOTE_CODE
    process = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", HOST, "python3", "-"],
        input=source,
        capture_output=True,
        text=True,
        timeout=300,
    )
    if process.returncode:
        raise RuntimeError("A28 bootstrap failed: " + process.stderr[-3000:])
    return json.loads(process.stdout)


def cache_files():
    models = ROOT / "models"
    files = []
    for path in sorted(models.rglob("*")):
        if not path.is_file():
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if path.parent.name == "blobs":
            assert path.name == "sha256-" + digest, "Controller cache blob content mismatch"
        files.append(
            {
                "relative": str(path.relative_to(models)),
                "bytes": path.stat().st_size,
                "sha256": digest,
            }
        )
    assert files, "Empty source Planner cache"
    return files


def main():
    assert sys.platform == "linux", "Bootstrap must run on the experiment controller"
    assert not (ROOT / "a28-service.json").exists(), "Bootstrap receipt already exists"
    reporting = ROOT / "reporting"
    reporting.mkdir(exist_ok=True)
    started = time.monotonic()
    before = remote("prepare")
    write(ROOT / "a28-service-preparation.json", before)
    print(
        json.dumps({"phase": "copy_started", "ram_available_bytes": before["MemAvailable_bytes"]}),
        flush=True,
    )
    with (reporting / "a28-cache-copy.log").open("xb") as log:
        process = subprocess.Popen(
            [
                "rsync",
                "-a",
                "--ignore-existing",
                "--stats",
                "--timeout=120",
                "-e",
                "ssh -o BatchMode=yes -o ConnectTimeout=8",
                str(ROOT / "models") + "/",
                HOST + ":" + REMOTE_ROOT + "/models/",
            ],
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(cache_files)
            if process.wait(timeout=1800):
                raise RuntimeError("Planner cache transfer failed; inspect private copy log")
            files = future.result()
    print(
        json.dumps(
            {
                "phase": "copy_finished",
                "seconds": time.monotonic() - started,
                "bytes": sum(entry["bytes"] for entry in files),
            }
        ),
        flush=True,
    )
    service = remote("start", files=files)
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 11451))
    tunnel = subprocess.Popen(
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
            "127.0.0.1:11451:127.0.0.1:11450",
            HOST,
        ],
        stdin=subprocess.DEVNULL,
        stdout=(reporting / "a28-tunnel.log").open("xb"),
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    import urllib.request

    for _ in range(20):
        if tunnel.poll() is not None:
            raise RuntimeError("Owned A28 tunnel exited before readiness")
        try:
            with urllib.request.urlopen("http://127.0.0.1:11451/api/ps", timeout=3) as stream:
                assert json.load(stream).get("models") == []
            break
        except OSError:
            time.sleep(1)
    else:
        raise RuntimeError("Owned A28 tunnel did not become ready")
    receipt = {
        **service,
        "tunnel_pid": tunnel.pid,
        "tunnel_url": "http://127.0.0.1:11451",
        "elapsed_ms": (time.monotonic() - started) * 1000,
        "cache_manifest_digests": [
            entry for entry in files if entry["relative"].startswith("manifests/")
        ],
        "controller_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "scope": "Only new Planner cache and service; no Executor or external process mutation",
    }
    write(ROOT / "a28-service.json", receipt)
    print(
        json.dumps(
            {
                "ready": True,
                "server_pid": service["server_pid"],
                "tunnel_pid": tunnel.pid,
                "elapsed_seconds": time.monotonic() - started,
                "model_inference_calls": 0,
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
