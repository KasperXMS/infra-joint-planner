"""Official BenchFlow/OpenHands adapter with explicit native LLM settings.

Only the launch-time settings JSON changes. The official pinned install command,
ACP protocol, tools, skill paths, permissions, and solver remain unchanged.
"""
import hashlib
import inspect
import json
import shlex
from pathlib import Path

from benchflow.agents.registry import AGENTS, register_agent

original = AGENTS["openhands"]
marker = "printf '}}'"
if original.launch_cmd.count(marker) != 1:
    raise RuntimeError("Official adapter changed; review configuration injection")
settings = {"temperature": 0.0, "top_p": 1.0, "stream": False, "max_input_tokens": 32768,
            "max_output_tokens": 4096, "num_retries": 0}
suffix = "," + json.dumps(settings, separators=(",", ":"))[1:-1] + "}}"
launch = original.launch_cmd.replace(marker, "printf '" + suffix + "'")
condenser_settings = {"kind": "LLMSummarizingCondenser", "max_tokens": 20000,
                      "max_size": 240, "keep_first": 2, "hard_context_reset_max_retries": 1}
configure_condenser = (
    "import json; from pathlib import Path; "
    "p=Path.home()/'.openhands/agent_settings.json'; d=json.loads(p.read_text()); "
    f"d['condenser']={condenser_settings!r}; "
    "d['condenser']['llm']={**d['llm'],'usage_id':'condenser'}; p.write_text(json.dumps(d))"
)
# Some official task images contain no system python3. The pinned OpenHands
# installation already provides a Python interpreter in its entrypoint shebang.
# Use that exact interpreter only to write the unchanged condenser settings.
openhands_python = '"$(head -n 1 "$(command -v openhands)" | cut -c 3-)"'
launch = launch.replace(" && openhands acp", " && " + openhands_python + " -c "
                        + shlex.quote(configure_condenser) + " && openhands acp")
kwargs = {name: getattr(original, name) for name in inspect.signature(register_agent).parameters}
kwargs["launch_cmd"] = launch
register_agent(**kwargs)
receipt = {"adapter": "official openhands ACP", "llm_settings": settings,
           "native_condenser_settings": condenser_settings,
           "condenser_config_interpreter": "Python from pinned OpenHands entrypoint shebang",
           "official_launch_sha256": hashlib.sha256(original.launch_cmd.encode()).hexdigest(),
           "configured_launch_sha256": hashlib.sha256(launch.encode()).hexdigest(),
           "official_install_sha256": hashlib.sha256(original.install_cmd.encode()).hexdigest()}
root = Path("/root/skillsbench-local-20261013")
(root / "evidence/frozen-openhands-launch.json").write_text(json.dumps(receipt, indent=2) + "\n")

if __name__ == "__main__":
    from benchflow.cli.main import app
    app()
