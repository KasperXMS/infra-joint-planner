"""Source-local schema inspection; prints keys/types only, never source text."""

import json
import sys
from pathlib import Path

from infra_joint.worker.artifact_store import FileArtifactStore

store = FileArtifactStore(Path(sys.argv[1]))
for artifact_id in sys.argv[2:]:
    artifact = store.get(artifact_id)
    value = json.loads(artifact.content)
    print(
        json.dumps(
            {
                "artifact_id": artifact_id,
                "bytes": len(artifact.content),
                "type": type(value).__name__,
                "keys": list(value) if isinstance(value, dict) else None,
                "first_record_keys": list(value[0])
                if isinstance(value, list) and value and isinstance(value[0], dict)
                else None,
            }
        )
    )
