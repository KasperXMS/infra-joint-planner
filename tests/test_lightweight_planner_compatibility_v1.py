import asyncio

from infra_joint.control.contracts import LogicalModelAction, LogicalToolAction
from scripts.lightweight_planner_compatibility_v1 import SyntheticGateway


def test_model_actions_do_not_have_operator_and_synthetic_read_failure_is_recoverable():
    async def check():
        gateway = SyntheticGateway()
        read = LogicalToolAction(
            action_id="r",
            owner_agent_id="manager",
            inputs=("synthetic-source",),
            operator="read_artifact",
            arguments={},
        )
        first = await gateway.execute_batch((read,), expose_profile=False)
        assert first[0].observation.failure_code == "artifact_not_materialized"
        second = await gateway.execute_batch((read,), expose_profile=False)
        assert second[0].observation.succeeded
        model = LogicalModelAction(
            action_id="m",
            owner_agent_id="manager",
            inputs=("synthetic-source",),
            prompt="synthetic",
        )
        assert not hasattr(model, "operator")
        result = await gateway.execute_batch((model,), expose_profile=False)
        assert result[0].observation.output == {"text": "A"}
        assert gateway.calls == ["read_artifact", "read_artifact", "invoke_model"]

    asyncio.run(check())
