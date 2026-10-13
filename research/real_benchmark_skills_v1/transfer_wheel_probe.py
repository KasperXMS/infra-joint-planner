"""Private local bounded SFTP throughput check using a verified official wheel."""
import concurrent.futures
import hashlib
import json
import re
import time
import urllib.request
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
import paramiko

workspace = Path("D:/Codes/infra-aware-mas-new")
wheel = json.loads((workspace / ".code-staging/large-wheels.lock.json").read_bytes())[0]
local = workspace / ".code-staging" / wheel["filename"]
if not local.exists():
    with urllib.request.urlopen(wheel["download_url"], timeout=60) as response:
        local.write_bytes(response.read())
assert hashlib.sha256(local.read_bytes()).hexdigest() == wheel["sha256"]
source = (workspace / "device_info.txt").read_text(encoding="utf-8-sig")
target = re.search(r"ssh[^\r\n]*root@connect\.westd\.seetacloud\.com[^\r\n]*", source)
password = re.search(r"(?:password|passwd|密码|口令)\s*[:：=]\s*[`\x27\x22]?([^\s`\x27\x22]+)", source[target.start():], re.I)
client = paramiko.SSHClient()
client.load_host_keys(str(Path.home() / ".ssh/known_hosts"))
client.set_missing_host_key_policy(paramiko.RejectPolicy())
client.connect("connect.westd.seetacloud.com", port=39059, username="root", password=password.group(1),
               look_for_keys=False, allow_agent=False, timeout=15, auth_timeout=15, banner_timeout=15)
remote = "/root/autodl-tmp/real-benchmark-skills-v1/wheelhouse/" + wheel["filename"] + ".sftp-probe"
with client.open_sftp() as transfer:
    with transfer.open(remote, "wb") as output:
        output.truncate(wheel["bytes"])
started = time.time()


def transfer(index):
    start = index * 1024 * 1024
    with local.open("rb") as source:
        source.seek(start)
        data = source.read(1024 * 1024)
    with client.open_sftp() as channel, channel.open(remote, "r+b") as output:
        output.set_pipelined(True)
        output.seek(start)
        output.write(data)


try:
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(transfer, range((wheel["bytes"] + 1024 * 1024 - 1) // (1024 * 1024))))
    result = {"bytes": wheel["bytes"], "seconds": time.time() - started, "remote_path": remote,
              "expected_sha256": wheel["sha256"]}
    (workspace / "real-benchmark-sftp-probe.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
finally:
    client.close()
