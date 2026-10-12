"""Presentation-only transfer: opaque identifiers and shuffled PUBLIC node order.

Private evaluator order/operations and real tools are unchanged. Runtime support
sees the same shuffled public order as the model, never a hidden frontier.
"""
from dataclasses import dataclass, field

from microbench import BASE_PROMPT, Environment, Task as BaseTask, digest, task_text


@dataclass
class Task(BaseTask):
    presentation_order: list[str] = field(default_factory=list)

    def public(self):
        public = super().public()
        public.pop("presentation_order")
        if self.presentation_order:
            indexed = {node["node"]: node for node in public["nodes"]}
            if set(indexed) != set(self.presentation_order) or len(indexed) != len(self.presentation_order):
                raise ValueError("Public presentation order must be a complete node permutation")
            public["nodes"] = [indexed[name] for name in self.presentation_order]
        return public
