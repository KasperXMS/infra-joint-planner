import hashlib
import json
import tarfile
import tempfile
import unittest
from pathlib import Path

from make_evidence_index import collect, export


class EvidenceTests(unittest.TestCase):
    def test_incomplete_refusal_and_explicit_engineering_retention(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stage = root / "results/engineering/model"
            episode = stage / "episodes/task__none"
            episode.mkdir(parents=True)
            source = stage / "frozen-source/runner.py"
            source.parent.mkdir()
            source.write_bytes(b"# frozen source\n")
            manifest = {"config": {"tasks": [{"task_id": "task"}], "conditions": ["none"]},
                        "source_sha256": {"runner.py": hashlib.sha256(source.read_bytes()).hexdigest()}, "config_sha256": "fixture"}
            (stage / "frozen-manifest.json").write_text(json.dumps(manifest))
            (episode / "started.json").write_text(json.dumps({"task": {"task_id": "task"}, "condition": "none"}))
            trace = b'{"event":"fixture"}\n'
            (episode / "trace.jsonl").write_bytes(trace)
            with self.assertRaisesRegex(RuntimeError, "unfinished"):
                collect(root)
            (stage / "engineering-invalidated.json").write_text(json.dumps({"reason": "fixture framing failure"}))
            (root / "checkpoints").mkdir()
            (root / "checkpoints/receipt.json").write_text('{"status":"fixture"}')
            (root / "models").mkdir()
            (root / "models/uncopied.txt").write_text("fixture model bytes outside archive whitelist")
            index, payload = collect(root)
            self.assertIn("checkpoints/receipt.json", payload)
            self.assertFalse(any(name.startswith("models/") for name in payload))
            self.assertFalse(index["studies"][0]["ability_evidence"])
            self.assertEqual(index["episodes"][0]["state"], "interrupted_engineering")
            self.assertEqual(index["episodes"][0]["trace_sha256"], hashlib.sha256(trace).hexdigest())
            archive, output = root / "evidence.tar.gz", root / "index.json"
            export(root, output, archive)
            with tarfile.open(archive) as tar:
                self.assertEqual(tar.extractfile("results/engineering/model/episodes/task__none/trace.jsonl").read(), trace)
            with self.assertRaisesRegex(RuntimeError, "never overwrite"):
                export(root, output, archive)


if __name__ == "__main__":
    unittest.main()
