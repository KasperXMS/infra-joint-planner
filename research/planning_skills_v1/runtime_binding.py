"""Observation-only policy/input joins and an equally informed unjoined control.

No reference solver, branch choice, next-action selection, action repair or
execution lives here. Every task node is represented, including missing inputs.
"""
import json


def structures(env):
    projection = env.state_projection()
    latest = {}
    for handle, artifact in projection["artifacts"].items():
        if artifact["valid"]:
            latest[artifact["node"]] = {"node": artifact["node"], "artifact": handle, "value": artifact["value"]}
    joined, nodes, bag = [], [], []
    for node in env.task.public()["nodes"]:
        inputs = [latest.get(parent, {"node": parent, "artifact": None, "value": None}) for parent in node["parents"]]
        current_output = latest.get(node["node"])
        joined.append({"node": node["node"], "policy": node["policy"], "ordered_inputs": inputs,
                       "current_output": current_output})
        nodes.append({"node": node["node"], "policy": node["policy"], "parents": node["parents"],
                      "current_output": current_output})
        # Repetition frequencies match the joined cards, not merely unique facts.
        bag.extend(inputs)
    bag.sort(key=lambda record: (record["node"], record["artifact"] or ""))
    common = {"phase": projection["phase"], "receipt": projection["receipt"]}
    return {**common, "node_cards": joined}, {**common, "nodes": nodes, "artifact_bag": bag}


def encode(text, tokenizer):
    return tokenizer.encode(text, add_special_tokens=False)


def matched_texts(env, tokenizer):
    joined, unjoined = structures(env)
    prefix = ("Current observed facts; null means no currently observed valid artifact. "
              "No operation or next node has been selected. Public policies remain authoritative.\n")
    texts = [prefix + json.dumps(data, sort_keys=True, separators=(",", ":")) + "\nInert padding:"
             for data in (joined, unjoined)]
    target = max(len(encode(text, tokenizer)) for text in texts) + 4
    padded = []
    for text in texts:
        deficit = target - len(encode(text, tokenizer))
        for unit in (" x", " a", " z", " 0"):
            candidate = text + unit * deficit
            if len(encode(candidate, tokenizer)) == target:
                padded.append(candidate)
                break
        else:
            raise RuntimeError("Cannot match binding/control tokens exactly; stop before inference")
    return padded[0], padded[1], target


def fact_inventory(data, joined):
    """For tests/audit: same policy, parent sequence and repeated observed facts."""
    if joined:
        nodes = [{"node": n["node"], "policy": n["policy"], "parents": [i["node"] for i in n["ordered_inputs"]],
                  "current_output": n["current_output"]}
                 for n in data["node_cards"]]
        facts = [i for n in data["node_cards"] for i in n["ordered_inputs"]]
    else:
        nodes, facts = data["nodes"], data["artifact_bag"]
    return {"nodes": nodes, "facts": sorted(json.dumps(f, sort_keys=True) for f in facts),
            "phase": data["phase"], "receipt": data["receipt"]}
