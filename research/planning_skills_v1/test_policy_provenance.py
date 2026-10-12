"""Independent semantic fixtures; these are tests, never model experiment results."""
import hashlib
import json
import tempfile
import unittest
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from analyze_heldout import details
from microbench import Environment, Task


def fixture(directory, values=(2, 3), repair=False):
    task = Task("semantic-fixture", "development", 0, 1, 2, False, False,
                {"u": values[0], "v": values[1]}, 8, "u",
                [{"node": "r", "parents": ["u", "v"], "policy": "Use sum.",
                  "predicate": "always", "threshold": 0, "choices": ["sum", "sum"]}],
                "r", "fixture", "fixture-cluster", "none")
    env = Environment(task)
    actions = [{"name": "fetch", "arguments": {"key": key}} for key in ("u", "v")]
    actions.append({"name": "compute", "arguments": {"node": "r", "operation": "max", "inputs": ["a1", "a2"]}})
    if repair:
        actions.append({"name": "compute", "arguments": {"node": "r", "operation": "sum", "inputs": ["a1", "a2"]}})
    root = "a4" if repair else "a3"
    actions += [{"name": "verify", "arguments": {"artifact": root}},
                {"name": "submit", "arguments": {"artifact": root, "receipt": "v1"}}]
    records = []
    for turn, action in enumerate(actions, 1):
        raw = json.dumps(action)
        observation, category = env.step(raw)
        records.append({"event": "inference", "turn": turn, "action": action, "raw_output": raw,
                        "observation": observation, "category": category})
    (directory / "started.json").write_text(json.dumps({"task": asdict(task), "condition": "none"}))
    trace = "".join(json.dumps(record) + "\n" for record in records).encode()
    (directory / "trace.jsonl").write_bytes(trace)
    result = {"completion": env.completed, "success": env.success, "submitted_value": env.submitted_value,
              "turns": len(actions), "trace_sha256": hashlib.sha256(trace).hexdigest(), "error_counts": {},
              "tool_counts": dict(Counter(a["name"] for a in actions))}
    (directory / "result.json").write_text(json.dumps(result))
    return details(directory)


class PolicyProvenanceTests(unittest.TestCase):
    def test_wrong_unconditional_root_is_not_called_policy_correct(self):
        with tempfile.TemporaryDirectory() as directory:
            row = fixture(Path(directory))
        self.assertFalse(row["all_executed_policy_choices_correct"])
        self.assertTrue(row["completion"])
        self.assertFalse(row["success"])
        self.assertEqual(row["submitted_provenance_policy_errors"], 1)

    def test_discarded_wrong_computation_differs_from_submitted_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            row = fixture(Path(directory), repair=True)
        self.assertFalse(row["all_executed_policy_choices_correct"])
        self.assertTrue(row["success"])
        self.assertTrue(row["submitted_provenance_policy_compliant"])
        self.assertTrue(row["recovered_policy_provenance"])

    def test_numeric_collision_does_not_rewrite_original_success(self):
        with tempfile.TemporaryDirectory() as directory:
            row = fixture(Path(directory), values=(0, 5))
        self.assertTrue(row["success"])
        self.assertFalse(row["submitted_provenance_policy_compliant"])
        self.assertTrue(row["numeric_success_with_policy_violation"])


if __name__ == "__main__":
    unittest.main()
