import inspect
from typing import Any, cast

from fastapi import FastAPI, HTTPException
from pydantic import Field

from infra_joint.core.action import SemanticAction
from infra_joint.core.base import ContractModel
from infra_joint.operators.builtin import invoke_model_spec
from infra_joint.operators.registry import OperatorRegistry
from infra_joint.worker.model_backend import ModelBackend


class ExecuteOperatorRequest(ContractModel):
    action: SemanticAction
    deployment_id: str | None = None


class ExecuteOperatorResponse(ContractModel):
    operator: str
    output: dict[str, Any]


class WorkerStateResponse(ContractModel):
    agent_id: str = Field(min_length=1)
    available: bool
    in_flight: int = Field(ge=0)
    operators: tuple[str, ...]


def create_worker_app(agent_id: str, model_backend: ModelBackend) -> FastAPI:
    registry = OperatorRegistry()
    in_flight = 0

    async def invoke_model(action: SemanticAction) -> dict[str, str]:
        prompt = action.arguments.get("prompt")
        if not isinstance(prompt, str) or not prompt:
            raise ValueError("invoke_model requires a non-empty prompt")
        return {"text": await model_backend.complete(prompt)}

    registry.register(invoke_model_spec(), invoke_model)
    app = FastAPI(title=f"Infra Joint Worker: {agent_id}", version="0.1.0")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/state", response_model=WorkerStateResponse)
    async def state() -> WorkerStateResponse:
        return WorkerStateResponse(
            agent_id=agent_id,
            available=True,
            in_flight=in_flight,
            operators=tuple(sorted(registry)),
        )

    @app.post("/execute/operator", response_model=ExecuteOperatorResponse)
    async def execute(request: ExecuteOperatorRequest) -> ExecuteOperatorResponse:
        nonlocal in_flight
        try:
            binding = registry.binding(request.action.operator)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        in_flight += 1
        try:
            result = binding.handler(request.action)
            if inspect.isawaitable(result):
                result = await result
            if not isinstance(result, dict):
                raise TypeError("operator handler must return a dictionary")
            output = cast(dict[str, Any], result)
            return ExecuteOperatorResponse(operator=request.action.operator, output=output)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        finally:
            in_flight -= 1

    return app
