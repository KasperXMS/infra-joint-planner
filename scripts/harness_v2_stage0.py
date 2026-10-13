# pyright: reportUnknownParameterType=false, reportMissingTypeArgument=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
"""Read-only, one-shot admission for the Harness v2 requalification block.

Run on the strong-4090 controller, from its isolated v2 app checkout.  The
private receipt stays on that machine; the script never reads task answers.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import yaml

APP = Path(__file__).resolve().parents[1]
TASK_ROOT = Path("/home/super/xiaoming/large-scale-cost-guidance-v1/preparation/task-freeze-002")
NODES = {
    "A4": ("edge@192.168.0.104", 11436, "qwen-vl4b-resident-32k-v1"),
    "A5": ("edge@192.168.0.105", 11436, "qwen-vl8b-resident-32k-v1"),
    "A28": ("edge@192.168.0.128", 11436, "qwen35-27b-resident-32k-v1"),
    "strong-4090-gpu0": (None, 11436, "qwen35-27b-resident-32k-v1"),
    "strong-4090-gpu1": (None, 11437, "qwen-vl8b-resident-32k-v1"),
}
PROTECTED = (
    "src/infra_joint/control/native_agents.py",
    "src/infra_joint/control/native_workflow_bridge.py",
    "src/infra_joint/control/workflow_state.py",
    "src/infra_joint/control/gateway.py",
    "src/infra_joint/control/verification.py",
    "src/infra_joint/control/ledger_native.py",
    "src/infra_joint/control/runner.py",
    "src/infra_joint/runtime/action_receipts.py",
    "src/infra_joint/worker/server.py",
    "src/infra_joint/benchmarks/multihop_rag.py",
    "src/infra_joint/benchmarks/longbench_v2.py",
    "src/infra_joint/benchmarks/video_mme.py",
    "configs/experiments/resident-diverse-environment-v1.yaml",
    "configs/experiments/lightweight-planner-competence-v1.json",
    "configs/experiments/blind-baseline-6task-competent-v2.yaml",
    "configs/skills/planner-procedural-v1.md",
)


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def node_json(host: str | None, code: str) -> dict:
    command = ["python3", "-c", code]
    if host is not None:
        import shlex

        command = [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "ConnectTimeout=8",
            host,
            "python3 -c " + shlex.quote(code),
        ]
    result = subprocess.run(command, check=True, text=True, capture_output=True, timeout=30)
    return json.loads(result.stdout)


def service(host: str | None, port: int, model: str) -> dict:
    code = f"""import json,urllib.request,hashlib
base='http://127.0.0.1:{port}'
def get(path, body=None):
 req=urllib.request.Request(
  base+path,
  data=None if body is None else json.dumps(body).encode(),
  headers={{'Content-Type':'application/json'}})
 return json.load(urllib.request.urlopen(req, timeout=8))
ps=get('/api/ps'); show=get('/api/show',{{'model':{model!r}}})
matches=[x for x in ps['models'] if x['name'] in {{{model!r},{model + ":latest"!r}}}]
assert len(matches)==1, 'expected exactly one resident model'
m=matches[0]
print(json.dumps({{'name':m['name'],'digest':m['digest'],'context_length':m['context_length'],
 'quantization':m['details']['quantization_level'],'parameter_size':m['details']['parameter_size'],
 'template_sha256':hashlib.sha256(show['template'].encode()).hexdigest(),
 'modelfile_parameters':show.get('parameters',''),'modelfile':show.get('modelfile','')}}))"""
    return node_json(host, code)


def main(output: Path) -> None:
    if output.exists():
        raise FileExistsError("stage-0 freeze exists; refusal prevents silent replacement")
    pool = yaml.safe_load(
        (APP / "configs/experiments/resident-diverse-environment-v1.yaml").read_text()
    )
    selection = json.loads((TASK_ROOT / "manifest.json").read_text())
    tasks = [row for row in selection["tasks"] if row["position"] in (1, 2)]
    assert len(tasks) == 6 and {row["family"] for row in tasks} == {
        "multihop_rag",
        "longbench_v2",
        "video_mme",
    }
    deployed = {}
    for name, (host, port, model) in NODES.items():
        actual = service(host, port, model)
        if actual["context_length"] != 32768 or actual["quantization"] != "Q4_K_M":
            raise RuntimeError(f"{name}: context or quantization drift")
        deployed[name] = {**actual, "host": host or "controller", "port": port}
    expected = {item["deployment_id"]: item for item in pool["environment"]["deployments"]}
    if len(expected) != 5 or not all(item["context_window"] == 32768 for item in expected.values()):
        raise RuntimeError("five-executor environment contract drift")
    receipt = {
        "version": "harness-v2-stage0-001",
        "created_utc": datetime.now(UTC).isoformat(),
        "source_sha256": {name: sha(APP / name) for name in PROTECTED},
        "task_manifest_sha256": sha(TASK_ROOT / "manifest.json"),
        "task_selection": [
            {
                key: row[key]
                for key in (
                    "family",
                    "position",
                    "source_task_id",
                    "task_bundle_sha256",
                    "evaluator_implementation_sha256",
                )
            }
            for row in tasks
        ],
        "services": deployed,
        "worker_urls": pool["worker_urls"],
        "historical_results_mutated": False,
        "formal_bridge_main_condition": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(
        json.dumps(
            {
                "admitted": True,
                "tasks": len(tasks),
                "services": len(deployed),
                "output": str(output),
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    main(parser.parse_args().output)
