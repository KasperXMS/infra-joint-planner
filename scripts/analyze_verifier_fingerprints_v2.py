"""Read existing traces only; emit an offline verifier fingerprint summary."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from infra_joint.control.verifier_offline import analyze_verifier_trace


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("traces", nargs="+", type=Path)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    reports = {}
    for path in arguments.traces:
        with path.open(encoding="utf-8") as stream:
            events = [json.loads(line) for line in stream if line.strip()]
        reports[str(path)] = analyze_verifier_trace(events).model_dump(mode="json")
    payload = json.dumps(reports, ensure_ascii=False, indent=2) + "\n"
    if arguments.output is None:
        print(payload, end="")
    else:
        arguments.output.write_text(payload, encoding="utf-8")


if __name__ == "__main__":
    main()
