import json
from pathlib import Path

import httpx
import pytest
from jsonschema import Draft202012Validator

from infra_joint.worker.artifact_fetcher import HttpArtifactFetcher
from infra_joint.worker.artifact_store import InMemoryArtifactStore, StoredArtifact
from infra_joint.worker.server import create_worker_app
from scripts.prepare_infra_evaluation_workload_v01 import owner

MANIFEST_ROOT = Path("docs/infra-evaluation-workload-v0.1/manifests")


def _jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_public_manifests_validate_and_planner_view_excludes_evaluation_metadata() -> None:
    schema = json.loads(
        Path("docs/infra-evaluation-workload-v0.1/evaluation-schema.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator.check_schema(schema)
    instance = json.loads(
        Path("configs/experiments/infra-evaluation-instance-v01.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator(schema).validate(instance)
    tasks = _jsonl(MANIFEST_ROOT / "task-candidates.jsonl")
    sources = _jsonl(MANIFEST_ROOT / "source-residency.jsonl")
    views = _jsonl(MANIFEST_ROOT / "planner-view.jsonl")
    evaluation_definitions = _jsonl(MANIFEST_ROOT / "evaluation-definitions.jsonl")
    task_validator = Draft202012Validator(schema["$defs"]["task_candidate"])
    source_validator = Draft202012Validator(schema["$defs"]["source_residency"])
    assert len(tasks) == 12
    assert len(sources) == 686
    assert len(views) == len(tasks)
    assert len(evaluation_definitions) == len(tasks)
    for definition in evaluation_definitions:
        Draft202012Validator(schema["$defs"]["evaluation_definition"]).validate(definition)
        assert str(definition["evaluation_metadata_ref"]).startswith("private:")
    source_groups = {source["source_group"] for source in sources}
    for task in tasks:
        task_validator.validate(task)
        assert set(task["source_collection_refs"]) <= source_groups
    for source in sources:
        source_validator.validate(source)
        if str(source["source_group"]).startswith("publisher:"):
            assert source["resident_agent"] == owner(str(source["source_group"]))
    for view in views:
        assert set(view) == {
            "task_id", "question", "source_artifact_refs", "source_collection_refs",
            "answer_contract",
        }
        assert not {"answer", "answers", "supporting_context", "source_dependency_class"} & set(
            view
        )


def test_correction_and_cleanup_receipts_preserve_failure_provenance() -> None:
    root = Path("docs/infra-evaluation-workload-v0.1")
    final = json.loads((root / "feasibility-public.json").read_text(encoding="utf-8"))
    initial = json.loads((root / "feasibility-initial-public.json").read_text(encoding="utf-8"))
    assert final["task_probe_count"] == 8
    assert initial["task_probe_count"] == 8
    assert final["excluded_initial_probe"] in {row["task_id"] for row in initial["results"]}
    assert final["excluded_initial_probe"] not in {row["task_id"] for row in final["results"]}
    assert all(row["evaluator_smoke_passed"] for row in final["results"])
    assert all(row["gpu_monetary_cost"] is None for row in final["results"])
    assert all(
        json.loads((root / name).read_text(encoding="utf-8"))["base_residency_restored"]
        for name in ("cleanup-public.json", "cleanup-correction-public.json")
    )


def test_network_profiles_actually_changed_worker_pull_latency() -> None:
    schema = json.loads(
        Path("docs/infra-evaluation-workload-v0.1/evaluation-schema.json").read_text(
            encoding="utf-8"
        )
    )
    config = json.loads(
        Path("configs/experiments/infra-evaluation-network-v01.json").read_text(
            encoding="utf-8"
        )
    )
    validator = Draft202012Validator(schema["$defs"]["infrastructure_profile"])
    for profile in config["profiles"]:
        validator.validate(profile)
    assert config["host_tc_modified"] is False
    receipt = json.loads(
        Path("docs/infra-evaluation-workload-v0.1/network-calibration-public.json").read_text(
            encoding="utf-8"
        )
    )
    large = {
        row["profile"]: row
        for row in receipt["measurements"]
        if row["sample_kind"] == "large"
    }
    assert large["Hslow"]["payload_bytes"] == large["Hfast"]["payload_bytes"]
    assert large["Hslow"]["payload_sha256"] == large["Hfast"]["payload_sha256"]
    assert large["Hslow"]["elapsed_ms"] > large["Hfast"]["elapsed_ms"]


def test_source_assignment_is_stable_and_modality_services_are_separate() -> None:
    assert owner("publisher:The Verge") == owner("publisher:The Verge")
    assert owner("mmqa:text-service") == "source-a"
    assert owner("mmqa:table-service") == "source-b"


@pytest.mark.asyncio
async def test_protected_source_requires_token_and_receipted_operation() -> None:
    artifact = StoredArtifact.create("source/doc", "text/plain", b"real evidence")
    source = create_worker_app(
        "source-a",
        {},
        artifact_store=InMemoryArtifactStore((artifact,)),
        artifact_read_token="private-token",
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=source), base_url="http://source"
    ) as client:
        assert (await client.get("/artifact/source%2Fdoc")).status_code == 403
        valid = await client.get(
            "/artifact/source%2Fdoc", headers={"x-source-access-token": "private-token"}
        )
        assert valid.status_code == 200
        assert valid.content == artifact.content
        assert valid.headers["x-artifact-sha256"] == artifact.sha256_hex
        action = {"action": {"operator": "read_artifact", "inputs": [artifact.artifact_id]}}
        denied = await client.post("/execute/operator", json=action)
        assert denied.status_code == 422
        assert denied.json()["detail"]["code"] == "validation_failed"
        action["action_id"] = "receipt-1"
        read = await client.post("/execute/operator", json=action)
        assert read.status_code == 200
        receipt = await client.get("/execute/receipt/receipt-1")
        assert receipt.status_code == 200


@pytest.mark.asyncio
async def test_worker_pull_uses_authorized_measured_data_path() -> None:
    artifact = StoredArtifact.create("doc", "application/json", b'{"text":"evidence"}')
    source = create_worker_app(
        "source-a",
        {},
        artifact_store=InMemoryArtifactStore((artifact,)),
        artifact_read_token="private-token",
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=source), base_url="http://source"
    ) as source_client:
        destination_store = InMemoryArtifactStore()
        destination = create_worker_app(
            "source-b",
            {},
            artifact_store=destination_store,
            artifact_fetcher=HttpArtifactFetcher(
                source_client, frozenset({"source"}), access_token="private-token"
            ),
        )
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=destination), base_url="http://destination"
        ) as destination_client:
            response = await destination_client.post(
                "/artifact/pull",
                json={
                    "artifact_id": "doc",
                    "source_url": "http://source/artifact/doc",
                    "expected_sha256": artifact.sha256_hex,
                },
            )
            assert response.status_code == 200
            assert response.json()["size_bytes"] == len(artifact.content)
            assert destination_store.get("doc").sha256_hex == artifact.sha256_hex
            wrong = await destination_client.post(
                "/artifact/pull",
                json={
                    "artifact_id": "another",
                    "source_url": "http://source/artifact/doc",
                    "expected_sha256": "0" * 64,
                },
            )
            assert wrong.status_code == 409
            assert "another" not in destination_store.ids()
