import importlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
audit = importlib.import_module("large_scale_provider_audit_v1")


def test_provider_diagnostic_is_synthetic_and_verifier_context_is_blind() -> None:
    value = audit.synthetic_context().model_dump(mode="json")
    assert value["task"]["benchmark_id"] == "synthetic"
    assert value["task"]["artifacts"] == []
    assert value["observations"] == [] and value["actions"] == []
    assert audit.MODELS == ("deepseek-v4-pro", "qwen3.8-max")
    assert "maas.aliyuncs.com" in audit.BASE_URL
    assert not {"source_ref", "gold", "evaluator_id", "physical_profile"} & value.keys()


@pytest.mark.asyncio
async def test_local_or_old_namespace_is_rejected_before_credentials_and_calls(
    tmp_path: Path,
) -> None:
    with pytest.raises(RuntimeError, match="new 4090 namespace"):
        await audit.probe(tmp_path / "probe", tmp_path / "missing-key")
    assert not (tmp_path / "probe").exists()


def test_native_compatibility_is_not_toy_answer_format_compliance() -> None:
    assert audit.continuation_compatible([7], ["continue"], "The recorded value is 7.")
    assert not audit.continuation_compatible([], ["continue"], "7")
    assert not audit.continuation_compatible([7], [], "7")
    assert not audit.continuation_compatible([7], ["continue"], "")
