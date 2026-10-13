"""Official BenchFlow/OpenHands adapter with explicit native LLM settings.

Only the launch-time settings JSON changes. The official pinned install command,
ACP protocol, tools, skill paths, permissions, and solver remain unchanged.
"""
import hashlib
import inspect
import json
from pathlib import Path

from benchflow.agents.registry import AGENTS, register_agent

original = AGENTS["openhands"]
marker = "printf '}}'"
if original.launch_cmd.count(marker) != 1:
    raise RuntimeError("Official adapter changed; review configuration injection")
settings = {"temperature": 0.0, "top_p": 1.0, "max_input_tokens": 32768,
            "max_output_tokens": 4096, "num_retries": 0}
suffix = "," + json.dumps(settings, separators=(",", ":"))[1:-1] + "}}"
launch = original.launch_cmd.replace(marker, "printf '" + suffix + "'")
kwargs = {name: getattr(original, name) for name in inspect.signature(register_agent).parameters}
kwargs["launch_cmd"] = launch
register_agent(**kwargs)
receipt = {"adapter": "official openhands ACP", "llm_settings": settings,
           "official_launch_sha256": hashlib.sha256(original.launch_cmd.encode()).hexdigest(),
           "configured_launch_sha256": hashlib.sha256(launch.encode()).hexdigest(),
           "official_install_sha256": hashlib.sha256(original.install_cmd.encode()).hexdigest()}
root = Path("/root/skillsbench-local-20261013")
(root / "evidence/frozen-openhands-launch.json").write_text(json.dumps(receipt, indent=2) + "\n")

if __name__ == "__main__":
    from benchflow.cli.main import app
    app()
