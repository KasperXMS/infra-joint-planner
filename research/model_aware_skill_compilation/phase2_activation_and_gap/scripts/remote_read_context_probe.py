"""Return the local non-task context probe receipt (no model traffic body)."""
from pathlib import Path

print(Path('/root/autodl-tmp/model-aware-skill-compilation/phase2_32k_runtime_probe.json').read_text())
