import httpx
import pytest

from infra_joint.operators.catalog import build_operator_catalog
from infra_joint.worker.model_backend import StaticModelBackend
from infra_joint.worker.server import create_worker_app


@pytest.mark.asyncio
async def test_planner_catalog_matches_worker_operator_surface() -> None:
    catalog = build_operator_catalog()
    app = create_worker_app("worker", StaticModelBackend("A"))
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://worker"
    ) as client:
        state = (await client.get("/state")).json()

    planner_operators = {tool["function"]["name"] for tool in catalog.planner_tools()}
    assert set(state["operators"]) <= planner_operators
    assert planner_operators == set(catalog)
