# pyright: reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false
"""Print trace structure only; never print task or model payload values."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


def main(path: Path) -> None:
    seen: dict[str, set[str]] = defaultdict(set)
    nested: dict[str, set[str]] = defaultdict(set)
    for line in path.read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        kind = event["event_type"]
        payload = event.get("payload", {})
        if isinstance(payload, dict):
            seen[kind].update(payload)
            for key in ("action", "execution", "observation", "graph", "usage"):
                value = payload.get(key)
                if isinstance(value, dict):
                    nested[kind + "." + key].update(value)
    print(json.dumps({kind: sorted(keys) for kind, keys in sorted(seen.items())}, indent=2))
    print(json.dumps({kind: sorted(keys) for kind, keys in sorted(nested.items())}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("trace", type=Path)
    main(parser.parse_args().trace)
