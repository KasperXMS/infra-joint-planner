"""Acquire official wheels locally and stream verified bytes over SSH to AutoDL.

Credentials are read from the existing private device file in memory only.
Remote writes are confined to this study's wheelhouse. No task code executes.
"""
import argparse
import concurrent.futures
import hashlib
import json
import re
import shlex
import threading
import time
import urllib.request
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
import paramiko

WORKSPACE = Path("D:/Codes/infra-aware-mas-new")
REMOTE_ROOT = "/root/autodl-tmp/real-benchmark-skills-v1/wheelhouse/"


def sha(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def main(probe):
    wheels = json.loads((WORKSPACE / ".code-staging/large-wheels.lock.json").read_bytes())
    if probe:
        wheels = wheels[:1]
    cache = WORKSPACE / ".code-staging/wheelhouse"
    cache.mkdir(exist_ok=True)
    source = (WORKSPACE / "device_info.txt").read_text(encoding="utf-8-sig")
    target = re.search(r"ssh[^\r\n]*root@connect\.westd\.seetacloud\.com[^\r\n]*", source)
    password = re.search(r"(?:password|passwd|密码|口令)\s*[:：=]\s*[`\x27\x22]?([^\s`\x27\x22]+)", source[target.start():], re.I)
    client = paramiko.SSHClient()
    client.load_host_keys(str(Path.home() / ".ssh/known_hosts"))
    client.set_missing_host_key_policy(paramiko.RejectPolicy())
    client.connect("connect.westd.seetacloud.com", port=39059, username="root", password=password.group(1),
                   look_for_keys=False, allow_agent=False, timeout=15, auth_timeout=15, banner_timeout=15)
    client.get_transport().set_keepalive(20)
    guard = threading.Lock()
    state = {"started_epoch": time.time(), "status": "running", "files": []}
    receipt = WORKSPACE / ("real-benchmark-raw-ssh-probe.json" if probe else "real-benchmark-wheel-upload.json")

    def transfer(wheel):
        local = cache / wheel["filename"]
        if not local.exists():
            temporary = local.with_suffix(".download-partial")
            with urllib.request.urlopen(wheel["download_url"], timeout=120) as response, temporary.open("wb") as output:
                while data := response.read(4 * 1024 * 1024):
                    output.write(data)
            if sha(temporary) != wheel["sha256"]:
                raise ValueError("Official local wheel hash mismatch")
            temporary.replace(local)
        elif sha(local) != wheel["sha256"]:
            raise ValueError("Cached wheel hash mismatch")
        remote = REMOTE_ROOT + wheel["filename"] + (".raw-probe" if probe else "")
        # All shell text is our constant Python program plus repr literals,
        # passed as one shell-quoted argument; no credentials enter commands.
        code = f"""
import hashlib,json,sys
from pathlib import Path
p=Path({remote!r})
assert p.parent == Path({REMOTE_ROOT!r})
expected={wheel['sha256']!r}
if p.exists():
    with p.open('rb') as f:
        valid=hashlib.file_digest(f,'sha256').hexdigest()==expected
    if valid:
        print(json.dumps({{'already_verified':True}}),flush=True)
        sys.exit(0)
print(json.dumps({{'ready':True}}),flush=True)
t=p.with_suffix(p.suffix+'.ssh-partial')
h=hashlib.sha256()
with t.open('wb') as f:
    while data:=sys.stdin.buffer.read(1024*1024):
        h.update(data)
        f.write(data)
assert t.stat().st_size == {wheel['bytes']!r}
assert h.hexdigest()==expected
t.replace(p)
print(json.dumps({{'verified':True,'sha256':expected}}),flush=True)
"""
        started = time.time()
        stdin, stdout, stderr = client.exec_command("/root/miniconda3/bin/python -c " + shlex.quote(code), timeout=300)
        ready = json.loads(stdout.readline())
        if not ready.get("already_verified"):
            with local.open("rb") as source:
                while data := source.read(1024 * 1024):
                    stdin.channel.sendall(data)
            stdin.channel.shutdown_write()
            final = json.loads(stdout.readline())
            if not final.get("verified"):
                raise RuntimeError("Remote verification failed")
        else:
            stdin.channel.shutdown_write()
        if stdout.channel.recv_exit_status() != 0:
            raise RuntimeError("Remote wheel materialization failed")
        record = {"filename": wheel["filename"], "bytes": wheel["bytes"], "sha256": wheel["sha256"],
                  "upload_seconds": time.time() - started, "already_verified": ready.get("already_verified", False)}
        with guard:
            state["files"].append(record)
            receipt.write_text(json.dumps(state, indent=2) + "\n")
            print(json.dumps(record), flush=True)
        return record

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(transfer, wheels))
        state["status"] = "pass"
    except Exception as exc:
        state.update(status="failed", error=type(exc).__name__)
        raise
    finally:
        client.close()
        state["finished_epoch"] = time.time()
        receipt.write_text(json.dumps(state, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe", action="store_true")
    main(parser.parse_args().probe)
