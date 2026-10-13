"""Test a frozen private terminal candidate against both native choice checks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from infra_joint.control.native_agents import (
    _deterministic_terminal_answer,
    _leading_declared_choice,
)
from infra_joint.core.task import OutputContract


def main(trace_path: Path) -> None:
    events = [json.loads(line) for line in trace_path.read_text().splitlines() if line.strip()]
    prepared = {
        event["payload"]["action"]["action_id"]: event["payload"]["action"]["action_type"]
        for event in events
        if event["event_type"] == "logical.action.prepared"
    }
    candidate = next(
        (
            event["payload"]
            for event in reversed(events)
            if event["event_type"] == "logical.observation"
            and event["payload"].get("owner_agent_id") == "manager"
            and event["payload"].get("succeeded")
            and prepared.get(event["payload"].get("action_id")) == "model"
        ),
        None,
    )
    verification = next(
        (
            event["payload"]
            for event in reversed(events)
            if event["event_type"] == "logical.verification.input"
        ),
        None,
    )
    if candidate is None or verification is None:
        raise RuntimeError("candidate or verifier context is missing")
    text = str(candidate["output"].get("text") or "")
    contract_data = dict(verification["context"]["task"]["output_contract"])
    if "schema_definition" in contract_data:
        contract_data["schema"] = contract_data.pop("schema_definition")
    contract = OutputContract.model_validate(contract_data)
    results = {}
    for name, check in (
        ("leading_declared_choice", _leading_declared_choice),
        ("deterministic_terminal_answer", _deterministic_terminal_answer),
    ):
        try:
            check(contract, text)
            results[name] = True
        except Exception as exc:
            results[name] = type(exc).__name__
    print(
        json.dumps(
            {
                "candidate_exists": bool(text.strip()),
                "candidate_length": len(text),
                "choice_count": len(contract.choices or ()),
                "checks": results,
                "raw_text_exported": False,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("trace_path", type=Path)
    main(parser.parse_args().trace_path)
