import json
import unittest

from microbench import Environment, expected, make_task, task_text


def action(env, name, **arguments):
    return env.step(json.dumps({"name": name, "arguments": arguments}))[0]


def reference_execution(env):
    """Test-only solver, deliberately absent from the inference runner."""
    handles = {}
    for key in env.task.sources:
        existing = next((h for h, a in reversed(list(env.artifacts.items())) if a["node"] == key and a["valid"]), None)
        handles[key] = existing or action(env, "fetch", key=key)["artifact"]
    for node in env.task.nodes:
        old = next((h for h, a in reversed(list(env.artifacts.items())) if a["node"] == node["node"] and a["valid"]), None)
        if old:
            handles[node["node"]] = old
            continue
        operands = [env.artifacts[handles[p]]["value"] for p in node["parents"]]
        predicate = node["predicate"]
        yes = {"greater": operands[0] > node["threshold"], "less_second": operands[0] < operands[1],
               "even": operands[0] % 2 == 0, "always": True}[predicate]
        result = action(env, "compute", node=node["node"], operation=node["choices"][0 if yes else 1],
                        inputs=[handles[p] for p in node["parents"]])
        handles[node["node"]] = result["artifact"]
    return handles[env.task.root]


class ContractTests(unittest.TestCase):
    def test_all_templates_recover_without_oracle_observations(self):
        for template in ("comparison", "relative", "parity"):
            for seed in range(10):
                env = Environment(make_task("development", seed, depth=3, width=3,
                                            refresh=True, transient=True, template=template))
                root = reference_execution(env)
                self.assertEqual(action(env, "verify", artifact=root)["error"], "transient_unavailable")
                update = action(env, "verify", artifact=root)
                self.assertEqual(update["error"], "source_updated")
                self.assertFalse(env.valid(root))
                projection = env.state_projection()
                for h in update["invalidated"]:
                    self.assertFalse(projection["artifacts"][h]["valid"])
                root = reference_execution(env)
                receipt = action(env, "verify", artifact=root)["receipt"]
                self.assertEqual(action(env, "fetch", key=next(iter(env.sources)))["error"], "phase_violation")
                action(env, "submit", artifact=root, receipt=receipt)
                self.assertTrue(env.completed)
                self.assertTrue(env.success)
                self.assertEqual(env.submitted_value, expected(env.task, True))

    def test_invalid_schema_is_side_effect_free(self):
        env = Environment(make_task("development", 1))
        for raw in ('{"name":"fetch"}', '{"name":"fetch","arguments":{"key":1}}',
                    '{"name":"fetch","arguments":{"key":"x"},"extra":1}', '```json\n{}\n```'):
            result, category = env.step(raw)
            self.assertIn(category, ("schema_validation_failed", "json_parse_failed"))
            self.assertEqual(len(env.artifacts), 0)

    def test_wrong_answer_can_complete(self):
        env = Environment(make_task("development", 99, depth=1))
        root = reference_execution(env)
        env.artifacts[root]["value"] += 1
        receipt = action(env, "verify", artifact=root)["receipt"]
        self.assertNotIn("expected", json.dumps(env.events))
        action(env, "submit", artifact=root, receipt=receipt)
        self.assertTrue(env.completed)
        self.assertFalse(env.success)

    def test_public_task_and_projection_have_no_private_values(self):
        task = make_task("heldout", 901, refresh=True)
        prompt = task_text(task)
        self.assertNotIn("replacement", prompt)
        self.assertNotIn("predicate", prompt)
        self.assertNotIn("choices", prompt)
        env = Environment(task)
        self.assertEqual(env.state_projection()["artifacts"], {})
        fetched = action(env, "fetch", key=next(iter(task.sources)))
        self.assertEqual(len(env.state_projection()["artifacts"]), 1)
        self.assertEqual(env.state_projection()["artifacts"][fetched["artifact"]]["value"], fetched["value"])


if __name__ == "__main__":
    unittest.main()
