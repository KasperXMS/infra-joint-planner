"""Deterministic, synthetic dependency/evidence planning environment.

The reference solver is evaluator-only. Neither skills nor the state projection
can call it. Source values become visible only through actual fetch operations.
"""
from __future__ import annotations

import copy
import hashlib
import json
import random
from dataclasses import asdict, dataclass

OPS = ("sum", "difference", "max", "min")


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def apply_op(op: str, values: list[int]) -> int:
    if op == "sum":
        return sum(values)
    if op == "difference":
        return values[0] - values[1]
    if op == "max":
        return max(values)
    if op == "min":
        return min(values)
    raise ValueError(op)


@dataclass
class Task:
    task_id: str
    split: str
    seed: int
    depth: int
    width: int
    refresh: bool
    transient: bool
    sources: dict[str, int]
    replacement: int
    changed_source: str
    nodes: list[dict]
    root: str
    template: str

    def public(self) -> dict:
        result = asdict(self)
        for key in ("sources", "replacement", "changed_source", "seed"):
            result.pop(key)
        result["sources"] = list(self.sources)
        return result


def make_task(split: str, seed: int, depth=2, width=2, refresh=False,
              transient=False, template="comparison") -> Task:
    """Split-specific names, values and branch policies; no benchmark answers in skills."""
    rng = random.Random(f"evidence-bench-v1/{split}/{seed}/{depth}/{width}/{template}")
    prefix = {"development": "d", "heldout": "h", "transfer": "x"}[split]
    names = [f"{prefix}{rng.randrange(1000, 9999)}" for _ in range(width)]
    while len(set(names)) != width:
        names = [f"{prefix}{rng.randrange(1000, 9999)}" for _ in range(width)]
    sources = {name: rng.randrange(2, 24) for name in names}
    previous = names
    nodes = []
    for level in range(depth):
        current = []
        for branch in range(width):
            name = f"{prefix}n{level}_{branch}"
            parents = [previous[branch], previous[(branch + 1) % width]]
            threshold = rng.randrange(6, 20)
            choices = rng.sample(OPS, 2)
            if template == "comparison":
                policy = f"Use {choices[0]} if the first input is greater than {threshold}; otherwise use {choices[1]}."
                predicate = "greater"
            elif template == "relative":
                policy = f"When the first input is smaller than the second, use {choices[0]}; in all other cases use {choices[1]}."
                predicate = "less_second"
            elif template == "parity":
                policy = f"Choose {choices[0]} when the first input is an even integer. Choose {choices[1]} when it is odd."
                predicate = "even"
            else:
                raise ValueError(template)
            nodes.append({"node": name, "parents": parents, "policy": policy,
                          "predicate": predicate, "threshold": threshold,
                          "choices": choices})
            current.append(name)
        previous = current
    # Final merge forces the outcome to depend on every branch.
    nodes.append({"node": f"{prefix}root", "parents": previous, "policy": "Use sum.",
                  "predicate": "always", "threshold": 0, "choices": ["sum", "sum"]})
    return Task(task_id=f"{split}-{template}-s{seed}-d{depth}-w{width}-r{int(refresh)}-e{int(transient)}",
                split=split, seed=seed, depth=depth, width=width, refresh=refresh,
                transient=transient, sources=sources, replacement=rng.randrange(25, 48),
                changed_source=rng.choice(names), nodes=nodes, root=f"{prefix}root", template=template)


def expected(task: Task, refreshed: bool) -> int:
    """Private reference calculation; never called by tool observations or support."""
    values = dict(task.sources)
    if refreshed:
        values[task.changed_source] = task.replacement
    for node in task.nodes:
        operands = [values[parent] for parent in node["parents"]]
        predicate = node["predicate"]
        yes = {"greater": operands[0] > node["threshold"],
               "less_second": operands[0] < operands[1],
               "even": operands[0] % 2 == 0, "always": True}[predicate]
        values[node["node"]] = apply_op(node["choices"][0 if yes else 1], operands)
    return values[task.root]


def task_text(task: Task) -> str:
    public = task.public()
    for node in public["nodes"]:
        for key in ("predicate", "threshold", "choices"):
            node.pop(key)
    return ("Build the specified root artifact from fetched sources. The input order in each node is meaningful. "
            "Select operations by the node's policy and the observed numeric inputs. "
            "Obtain a verification receipt for the root, then submit that exact artifact and receipt. "
            "Verification checks provenance/freshness, NOT arithmetic or policy correctness. "
            "Only final root numeric correctness is scored as task success.\nTASK="
            + json.dumps(public, sort_keys=True))


ACTION_SCHEMA = {
    "oneOf": [
        {"type": "object", "required": ["name", "arguments"], "additionalProperties": False,
         "properties": {"name": {"const": "fetch"}, "arguments": {
             "type": "object", "required": ["key"], "additionalProperties": False,
             "properties": {"key": {"type": "string"}}}}},
        {"type": "object", "required": ["name", "arguments"], "additionalProperties": False,
         "properties": {"name": {"const": "compute"}, "arguments": {
             "type": "object", "required": ["node", "operation", "inputs"], "additionalProperties": False,
             "properties": {"node": {"type": "string"}, "operation": {"enum": list(OPS)},
                            "inputs": {"type": "array", "items": {"type": "string"}, "minItems": 2}}}}},
        {"type": "object", "required": ["name", "arguments"], "additionalProperties": False,
         "properties": {"name": {"const": "verify"}, "arguments": {
             "type": "object", "required": ["artifact"], "additionalProperties": False,
             "properties": {"artifact": {"type": "string"}}}}},
        {"type": "object", "required": ["name", "arguments"], "additionalProperties": False,
         "properties": {"name": {"const": "submit"}, "arguments": {
             "type": "object", "required": ["artifact", "receipt"], "additionalProperties": False,
             "properties": {"artifact": {"type": "string"}, "receipt": {"type": "string"}}}}},
    ]
}

BASE_PROMPT = """You control a deterministic evidence workflow. Output exactly ONE JSON action with name and arguments, without Markdown or explanations. No implicit or repaired calls are executed.
Tools:
fetch(key): get a source value and its artifact handle.
compute(node,operation,inputs): execute an operation on artifact handles in exactly the node's declared parent order. It does NOT choose the correct operation for you. sum adds inputs, difference subtracts the second from the first, max/min select the largest/smallest.
verify(artifact): validate current root provenance and issue a receipt. A source may change on the first valid-root verification; the observation explicitly reports changed sources and invalidated handles. A transient failure may occur once and is retryable. Premature verification cannot trigger updates. Verification never reveals or checks the correct numeric answer.
submit(artifact,receipt): end the workflow using the verified root and matching receipt. After a receipt is issued, only submit is permitted. A submitted wrong numeric value is an evaluated task failure.
Inputs must be existing, currently valid artifact handles. A source update invalidates all its descendants and all earlier receipts. Tool errors do not end the task; each response consumes one turn. The action schema below is authoritative.
SCHEMA=""" + json.dumps(ACTION_SCHEMA, separators=(",", ":"))


class Environment:
    def __init__(self, task: Task):
        self.task = task
        self.sources = dict(task.sources)
        self.artifacts: dict[str, dict] = {}
        self.receipts: dict[str, str] = {}
        self.changed = False
        self.transient_seen = False
        self.phase = "collect"
        self.completed = False
        self.success = False
        self.submitted_value = None
        self.events = []

    def valid(self, handle: str) -> bool:
        return handle in self.artifacts and self.artifacts[handle]["valid"]

    def new_artifact(self, node, value, parents) -> dict:
        handle = f"a{len(self.artifacts) + 1}"
        self.artifacts[handle] = {"artifact": handle, "node": node, "value": value,
                                  "parents": list(parents), "valid": True}
        return copy.deepcopy(self.artifacts[handle])

    def observation(self, action: dict) -> dict:
        name, args = action["name"], action["arguments"]
        if self.phase == "submit" and name != "submit":
            return {"error": "phase_violation", "phase": "submit"}
        if name == "fetch":
            key = args["key"]
            if key not in self.sources:
                return {"error": "unknown_source"}
            return {"status": "fetched", **self.new_artifact(key, self.sources[key], [])}
        if name == "compute":
            node = next((n for n in self.task.nodes if n["node"] == args["node"]), None)
            if node is None:
                return {"error": "unknown_node"}
            handles = args["inputs"]
            if not all(self.valid(h) for h in handles):
                return {"error": "invalid_or_stale_artifact"}
            if [self.artifacts[h]["node"] for h in handles] != node["parents"]:
                return {"error": "dependency_mismatch", "required_parents": node["parents"]}
            value = apply_op(args["operation"], [self.artifacts[h]["value"] for h in handles])
            return {"status": "computed", **self.new_artifact(node["node"], value, handles)}
        if name == "verify":
            handle = args["artifact"]
            if not self.valid(handle):
                return {"error": "invalid_or_stale_artifact"}
            if self.artifacts[handle]["node"] != self.task.root:
                return {"error": "not_root"}
            if self.task.transient and not self.transient_seen:
                self.transient_seen = True
                return {"error": "transient_unavailable", "retryable": True}
            if self.task.refresh and not self.changed:
                self.changed = True
                key = self.task.changed_source
                self.sources[key] = self.task.replacement
                invalidated = []
                for handle, artifact in self.artifacts.items():
                    if artifact["node"] == key or any(p in invalidated for p in artifact["parents"]):
                        artifact["valid"] = False
                        invalidated.append(handle)
                self.receipts.clear()
                return {"error": "source_updated", "changed_sources": [key], "invalidated": invalidated,
                        "receipts_invalidated": True}
            receipt = f"v{len(self.receipts) + 1}"
            self.receipts[receipt] = handle
            self.phase = "submit"
            return {"status": "verified", "artifact": handle, "receipt": receipt, "phase": "submit"}
        if name == "submit":
            handle = args["artifact"]
            if self.receipts.get(args["receipt"]) != handle or not self.valid(handle):
                return {"error": "terminal_contract_failed"}
            self.completed = True
            self.phase = "complete"
            self.submitted_value = self.artifacts[handle]["value"]
            self.success = self.submitted_value == expected(self.task, self.changed)
            # No correctness feedback: terminal response contains completion only.
            return {"status": "submitted", "phase": "complete"}
        raise AssertionError("Validated action names are exhaustive")

    def step(self, raw: str) -> tuple[dict, str | None]:
        from jsonschema import Draft202012Validator
        category = None
        try:
            action = json.loads(raw)
        except json.JSONDecodeError:
            action = None
            category = "json_parse_failed"
            result = {"error": category, "instruction": "Return one JSON object matching the schema."}
        else:
            errors = sorted(Draft202012Validator(ACTION_SCHEMA).iter_errors(action), key=lambda e: str(e.path))
            if errors:
                category = "schema_validation_failed"
                result = {"error": category, "detail": errors[0].message[:400]}
            else:
                result = self.observation(action)
                category = result.get("error")
        self.events.append({"action": action, "observation": result, "category": category})
        return result, category

    def state_projection(self) -> dict:
        """Reconstruct only fields already observed, never evaluator/private state.

        Deliberately no frontier, next action, answer, required operation or policy evaluation.
        """
        visible = {}
        phase = "collect"
        receipt = None
        for event in self.events:
            obs = event["observation"]
            if obs.get("status") in ("fetched", "computed"):
                visible[obs["artifact"]] = {k: obs[k] for k in ("node", "value", "parents", "valid")}
            for handle in obs.get("invalidated", []):
                if handle in visible:
                    visible[handle]["valid"] = False
            if obs.get("receipts_invalidated"):
                receipt = None
            if obs.get("status") == "verified":
                receipt = {k: obs[k] for k in ("artifact", "receipt")}
                phase = "submit"
        return {"artifacts": visible, "receipt": receipt, "phase": phase}
