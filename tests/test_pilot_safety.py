import asyncio
import json
from time import monotonic

import httpx
import pytest

from infra_joint.experiments.pilot_safety import (
    PilotBudgetExceeded,
    PilotRequestBudget,
    PilotStopped,
)


@pytest.mark.asyncio
async def test_shared_request_quota_is_atomic_before_any_network(tmp_path):
    budget = PilotRequestBudget(tmp_path / "STOP", monotonic() + 5, control_limit=2)
    sent = []

    async def transport(request):
        sent.append(request)
        return httpx.Response(200, json={})

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(transport), event_hooks={"request": [budget.control_hook]}
    ) as client:
        results = await asyncio.gather(
            *(client.post("http://example.test", json={}) for _ in range(8)),
            return_exceptions=True,
        )
    assert len(sent) == budget.control_requests == 2
    assert sum(isinstance(r, PilotBudgetExceeded) for r in results) == 6


@pytest.mark.asyncio
async def test_stop_deadline_bytes_and_physical_request_caps(tmp_path):
    stop = tmp_path / "STOP"
    budget = PilotRequestBudget(stop, monotonic() + 5, physical_limit=1, control_byte_limit=1)
    request = httpx.Request(
        "POST",
        "http://worker/execute/operator",
        content=json.dumps({"action": {"operator": "invoke_model"}}),
    )
    await budget.worker_hook(request)
    with pytest.raises(PilotBudgetExceeded):
        await budget.worker_hook(request)
    with pytest.raises(PilotBudgetExceeded):
        await budget.control_hook(request)
    assert budget.control_requests == 0
    stop.touch()
    with pytest.raises(PilotStopped):
        budget.check()
    stop.unlink()
    budget.deadline = monotonic() - 1
    with pytest.raises(PilotBudgetExceeded):
        budget.check()
