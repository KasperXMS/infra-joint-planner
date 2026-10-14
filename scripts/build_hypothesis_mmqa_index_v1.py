"""Build a versioned source-local candidate index from frozen public task refs."""

import hashlib
import json
import sys
import time
from pathlib import Path

from infra_joint.worker.artifact_store import FileArtifactStore, StoredArtifact


def main():
    store = FileArtifactStore(Path(sys.argv[1]))
    tasks = [json.loads(line) for line in Path(sys.argv[2]).read_text().splitlines()]
    task_id = sys.argv[3]
    task = next(row for row in tasks if row["task_id"] == task_id)
    records = []
    sources = []
    for artifact_id in task["source_artifact_refs"]:
        if not artifact_id.startswith("mmqa:text:"):
            continue
        source = store.get(artifact_id)
        row = json.loads(source.content)
        records.append({**row, "_origin_artifact_id": artifact_id})
        sources.append({"artifact_id": artifact_id, "sha256": source.sha256_hex})
    if not records:
        raise RuntimeError("No local text candidates")
    output_id = "hypothesis-v1:mmqa-candidates:" + task_id
    content = json.dumps(records, sort_keys=True, separators=(",", ":")).encode()
    started = time.time()
    store.put(StoredArtifact.create(output_id, "application/json", content))
    receipt = {
        "task_id": task_id,
        "artifact_id": output_id,
        "sha256": hashlib.sha256(content).hexdigest(),
        "bytes": len(content),
        "source_hashes": sources,
        "built_unix": started,
        "kind": "cold_setup; no gold or answer fields",
    }
    Path(sys.argv[4]).write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"artifact_id": output_id, "bytes": len(content), "sources": len(sources)}))


if __name__ == "__main__":
    main()
