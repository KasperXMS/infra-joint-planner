import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.lightweight_planner_roles_v1 import (
    gate_decision,
    manager_instructions,
    role_isolated_sdk,
)


def test_constructor_isolates_models_and_cost_identity_without_changing_sdk_or_settings():
    local, strong, settings, tools, runner = (object() for _ in range(5))
    receipts = []

    class Meter:
        def model(self, delegate, **metadata):
            receipts.append((delegate, metadata))
            return delegate

    sdk = SimpleNamespace(Agent=lambda **kwargs: SimpleNamespace(**kwargs), Runner=runner)
    facade = role_isolated_sdk(
        sdk,
        manager_model=local,
        specialist_model=strong,
        manager_model_id="local-8b",
        specialist_model_id="strong-cloud",
        manager_meter=Meter(),
        specialist_meter=Meter(),
    )
    assert facade.Runner is sdk.Runner
    for name, expected, expected_id in (
        ("manager", local, "local-8b"),
        ("bounded_specialist", strong, "strong-cloud"),
    ):
        agent = facade.Agent(
            name=name, model=local, instructions="original", tools=tools, model_settings=settings
        )
        assert agent.model is expected
        assert agent.tools is tools
        assert agent.model_settings is settings
        assert agent.instructions == "original"
        assert receipts[-1][1]["requested_model"] == expected_id
    with pytest.raises(ValueError, match="unrecognized"):
        facade.Agent(name="unexpected", model=strong)


def test_b1_has_exact_base_instructions_and_only_b2_gets_skills():
    base, skills = "original\n", "frozen procedural text\n"
    assert manager_instructions(base) == base
    assert manager_instructions(base, skills=skills) == base + "\n\n" + skills
    with pytest.raises(ValueError):
        manager_instructions(base, skills=" ")


def test_legal_alternative_terminal_does_not_retroactively_pass_strict_gate():
    decision = gate_decision(
        {
            "error": None,
            "final_answer": "A",
            "passed_native_smoke": False,
            "context_full_envelope_validated": False,
            "parallel_call_execution_validated": False,
        }
    )
    assert decision["native_terminal_observed"]
    assert not decision["formal_execution_allowed"]
    assert "frozen_recovery_smoke_not_passed" in decision["gaps"]
    assert not gate_decision({})["formal_execution_allowed"]


def test_http_200_with_logged_context_truncation_blocks_even_successful_smoke():
    decision = gate_decision(
        {"error": None, "final_answer": "A", "passed_native_smoke": True},
        context_receipt={"status": 200, "server_truncation_lines": ["truncating input prompt"]},
    )
    assert decision["strict_smoke_accepted"]
    assert "silent_context_truncation" in decision["gaps"]
    assert not decision["formal_execution_allowed"]
    assert not decision["model_must_choose_parallel_tools"]
    assert not decision["full_context_stress_required"]


def test_frozen_matrix_and_report_preserve_unexecuted_missing_values():
    root = Path(__file__).resolve().parents[1]
    config_path = root / "configs/experiments/lightweight-planner-competence-v1.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    results = json.loads(
        (root / "analysis/lightweight-planner-competence-v1/pilot-results-v1.json").read_text(
            encoding="utf-8"
        )
    )
    assert hashlib.sha256(config_path.read_bytes()).hexdigest() == results["config_sha256"]
    assert not config["formal_execution_allowed"]
    assert config["execution_entrypoint"] is None
    assert len(results["cells"]) == 18
    assert len({cell["cell_id"] for cell in results["cells"]}) == 18
    assert {cell["status"] for cell in results["cells"]} == {"not_run_gate1"}
    for cell in results["cells"]:
        for key in (
            "execution_completed",
            "terminal_format_valid",
            "evaluation_reached",
            "original_score",
            "end_to_end_success",
            "control_plane",
            "physical_inference",
            "total_resource_footprint",
            "workflow",
            "failure_class",
        ):
            assert cell[key] is None
    for group in ("B0", "B1", "B2"):
        assert sum(cell["group"] == group for cell in results["cells"]) == 6
        assert results["aggregate"][group]["end_to_end_tsr"] is None
    assert (
        hashlib.sha256((root / config["skills"]["path"]).read_bytes()).hexdigest()
        == config["skills"]["sha256"]
    )
