import json
import unittest
from unittest.mock import patch

from make_heldout import paired_tasks
from microbench import Environment, reference
from runtime_binding import fact_inventory, structures
from test_microbench import action, reference_execution


class BindingControls(unittest.TestCase):
    def test_public_data_and_matched_fact_multiplicity(self):
        tasks, _ = paired_tasks("relative", 3, 31017)
        env = Environment(tasks[-1])
        with patch("microbench.expected", side_effect=AssertionError("No reference access")), \
             patch("microbench.reference", side_effect=AssertionError("No reference access")):
            joined, unjoined = structures(env)
        self.assertEqual(fact_inventory(joined, True), fact_inventory(unjoined, False))
        self.assertNotIn("predicate", json.dumps(joined))
        self.assertNotIn("choices", json.dumps(joined))
        self.assertNotIn("replacement", json.dumps(joined))
        root = reference_execution(env)
        action(env, "verify", artifact=root)
        joined, unjoined = structures(env)
        self.assertEqual(fact_inventory(joined, True), fact_inventory(unjoined, False))
        invalid = {h for h, a in env.artifacts.items() if not a["valid"]}
        rendered_handles = {i["artifact"] for n in joined["node_cards"] for i in n["ordered_inputs"]}
        self.assertFalse(invalid & rendered_handles)

    def test_update_pairs_change_values_without_disclosing_regime(self):
        for template in ("relative", "parity"):
            for depth in (1, 3):
                tasks, record = paired_tasks(template, depth, 31033)
                none, stable, flip = tasks
                self.assertEqual(none.sources, stable.sources)
                self.assertEqual(none.nodes, flip.nodes)
                self.assertEqual(none.changed_source, flip.changed_source)
                self.assertEqual(stable.public(), flip.public())
                initial = reference(none, False)
                for task in (stable, flip):
                    self.assertNotEqual(task.sources[task.changed_source], task.replacement)
                    after = reference(task, True)
                    self.assertNotEqual(initial["values"][task.root], after["values"][task.root])
                    self.assertEqual(initial["operations"] == after["operations"], task.update_mode == "stable")
                    public = task.public()
                    self.assertNotIn("update_mode", public)
                    self.assertNotIn("cluster_id", public)
                    self.assertNotIn("replacement", public)
                    self.assertNotIn("task_id", public)
                self.assertTrue(record["stable_candidates"])
                self.assertTrue(record["flip_candidates"])


if __name__ == "__main__":
    unittest.main()
