import unittest
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

from make_heldout import paired_tasks
from make_transfer import transform
from launch_conditional_transfer import trigger
from microbench import Environment, expected
from runtime_binding import fact_inventory, structures
from test_microbench import action, reference_execution


class TransferTests(unittest.TestCase):
    def test_renderer_measurement_preserves_prompt_content(self):
        from run_transfer_model import instrument_support
        with tempfile.TemporaryDirectory() as directory:
            original = lambda condition, env, tokenizer: ("exact unchanged support", {"system_skill": True})
            wrapped = instrument_support(original, Path(directory))
            text, metadata = wrapped("binding_system", SimpleNamespace(task=SimpleNamespace(task_id="test")), tokenizer=None)
            self.assertEqual(text, "exact unchanged support")
            self.assertTrue(metadata["system_skill"])
            self.assertGreaterEqual(metadata["support_wall_seconds"], 0)
            record = json.loads((Path(directory) / "support-work.jsonl").read_text())
            self.assertEqual(record["episode_id"], "test__binding_system")

    def test_frozen_launch_trigger_uses_complete_groups_without_model_selection(self):
        def rows(a, b, c):
            return [{"condition": condition, "success": i < count}
                    for condition, count in (("binding_system", a), ("unbound_system", b), ("static_system", c))
                    for i in range(36)]
        self.assertFalse(trigger(rows(0, 0, 0))[0])
        self.assertTrue(trigger(rows(4, 0, 0))[0])
        self.assertTrue(trigger(rows(0, 4, 0))[0])
        self.assertFalse(trigger(rows(20, 20, 20))[0])
        self.assertFalse(trigger(rows(20, 20, 21))[0])

    def test_public_permutation_preserves_evaluation_and_no_frontier_leak(self):
        variants, record = paired_tasks("relative", 4, 71017)
        tasks, _ = transform(variants, record)
        stable, flip = tasks[1:]
        self.assertEqual(stable.public(), flip.public())
        self.assertNotEqual([n["node"] for n in stable.nodes], [n["node"] for n in stable.public()["nodes"]])
        for task in tasks:
            self.assertNotIn("presentation_order", task.public())
            self.assertTrue(all(n["node"].startswith("v") for n in task.public()["nodes"]))
            env = Environment(task)
            root = reference_execution(env)
            result = action(env, "verify", artifact=root)
            if task.refresh:
                self.assertEqual(result["error"], "source_updated")
                root = reference_execution(env)
                result = action(env, "verify", artifact=root)
            joined, unjoined = structures(env)
            self.assertEqual([n["node"] for n in joined["node_cards"]], task.presentation_order)
            self.assertEqual(fact_inventory(joined, True), fact_inventory(unjoined, False))
            action(env, "submit", artifact=root, receipt=result["receipt"])
            self.assertTrue(env.success)
            self.assertEqual(env.submitted_value, expected(task, task.refresh))


if __name__ == "__main__":
    unittest.main()
