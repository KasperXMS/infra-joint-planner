"""Repair slow package acquisition using the unchanged lock's official PyPI hashes."""
import concurrent.futures
import json
import time

from materialize_models_ranged import ROOT, materialize

state = {"started_epoch": time.time(), "status": "running", "verified_wheels": []}
receipt = ROOT / "evidence/large-wheel-materialization.json"
wheels = json.loads((ROOT / "large-wheels.lock.json").read_bytes())


def fetch(wheel):
    materialize("wheelhouse", wheel["filename"], wheel, ROOT / "wheelhouse", chunk_size=1024 * 1024, workers=32)
    return wheel


try:
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        for future in concurrent.futures.as_completed([pool.submit(fetch, wheel) for wheel in wheels]):
            state["verified_wheels"].append(future.result())
            receipt.write_text(json.dumps(state, indent=2) + "\n")
    state["status"] = "pass"
except Exception as exc:
    state.update(status="failed", error=type(exc).__name__, detail=str(exc))
    raise
finally:
    state["finished_epoch"] = time.time()
    receipt.write_text(json.dumps(state, indent=2) + "\n")
