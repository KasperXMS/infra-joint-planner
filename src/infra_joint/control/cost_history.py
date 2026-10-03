"""Reduce audited traces to cost-only receipts; never fit on evaluator answers."""

import json
from hashlib import sha256
from typing import Any

from infra_joint.control.consequence_profiles import (
    CostHistory,
    ModelServiceSample,
    NetworkCategory,
    OperatorWorkSample,
    TransferSample,
)
from infra_joint.worker.model_backend import is_text_media_type


def extract_cost_history(
    events: list[dict[str, Any]],
    *,
    run_id: str,
    network_category: NetworkCategory,
) -> CostHistory:
    artifacts: dict[str, dict[str, Any]] = {}
    prepared: dict[str, dict[str, Any]] = {}
    input_metadata: dict[str, tuple[dict[str, Any] | None, ...]] = {}
    model_classes: list[dict[str, Any]] = []
    models: list[ModelServiceSample] = []
    operators: list[OperatorWorkSample] = []
    transfers: list[TransferSample] = []
    physical_ids: set[str] = set()
    for event in events:
        if event.get("run_id", run_id) != run_id:
            raise ValueError("mixed run IDs in cost history")
        payload = event["payload"]
        if event["event_type"] == "logical.loop.start":
            artifacts.update({item["artifact_id"]: item for item in payload["task"]["artifacts"]})
            model_classes = payload["static_capability_contract"]["model_classes"]
        elif event["event_type"] == "logical.action.prepared":
            action = payload["action"]
            identifier = action["action_id"]
            if identifier in prepared:
                raise ValueError("duplicate prepared action in cost history")
            prepared[identifier] = action
            input_metadata[identifier] = tuple(artifacts.get(value) for value in action["inputs"])
        elif event["event_type"] == "logical.observation":
            artifacts.update({item["artifact_id"]: item
                              for item in payload.get("produced_information", [])})
        elif event["event_type"] == "physical.execution":
            identifier = payload["action_id"]
            if identifier in physical_ids:
                raise ValueError("duplicate physical receipt in cost history")
            physical_ids.add(identifier)
            action = prepared[identifier]
            execution = payload.get("execution")
            if execution is None:
                continue  # Missing failed-action detail is not a zero-cost training sample.
            inputs = input_metadata[identifier]
            size = (sum(item["size_bytes"] for item in inputs if item is not None)
                    if all(item is not None and item.get("size_bytes") is not None
                           for item in inputs) else None)
            sample_id = _sample_id(run_id, identifier, "execution")
            if action["action_type"] == "model":
                telemetry = execution.get("model_telemetry")
                if telemetry is not None and len(model_classes) == 1:
                    model_class = model_classes[0]
                    image_count = sum(item is not None and item["media_type"].startswith("image/")
                                      for item in inputs)
                    bound = len(action["prompt"].encode("utf-8"))
                    complete = True
                    for item in inputs:
                        if item is None:
                            complete = False
                        elif item["media_type"].startswith("image/"):
                            bound += model_class["image_token_cost"]
                        elif (is_text_media_type(item["media_type"])
                              and item.get("size_bytes") is not None):
                            bound += item["size_bytes"]
                        else:
                            complete = False
                    models.append(ModelServiceSample(
                        sample_sha256=sample_id, model_class=model_class["capability_class"],
                        execution_surface_sha256=(surface_hash(execution["deployment_id"])
                                                  if execution.get("deployment_id") else None),
                        conservative_input_tokens=bound if complete else None,
                        actual_input_tokens=telemetry.get("input_tokens"), image_count=image_count,
                        output_budget=model_class["reserved_output_tokens"],
                        service_latency_ms=telemetry["service_latency_ms"],
                    ))
            else:
                operators.append(OperatorWorkSample(
                    sample_sha256=sample_id, operator=execution["operator"], input_bytes=size,
                    execution_surface_sha256=(surface_hash(*execution["agent_ids"])
                                              if execution.get("agent_ids") else None),
                    wrapper_latency_ms=execution["operator_latency_ms"],
                ))
            for index, transfer in enumerate(execution["transfers"]):
                if transfer["bytes_transferred"]:
                    transfers.append(TransferSample(
                        sample_sha256=_sample_id(run_id, identifier, f"transfer-{index}"),
                        network_category=network_category,
                        path_surface_sha256=surface_hash(
                            transfer["source_agent_id"], transfer["target_agent_id"],
                        ),
                        bytes_transferred=transfer["bytes_transferred"],
                        latency_ms=transfer["duration_ms"],
                    ))
    return CostHistory(models=tuple(models), operators=tuple(operators), transfers=tuple(transfers))


def _sample_id(run_id: str, action_id: str, kind: str) -> str:
    return sha256(f"{run_id}\n{action_id}\n{kind}".encode()).hexdigest()


def surface_hash(*identifiers: str) -> str:
    """Internal fit key only; never expose this physical-surface identity to an Agent."""
    return sha256(json.dumps(identifiers, ensure_ascii=True).encode()).hexdigest()
