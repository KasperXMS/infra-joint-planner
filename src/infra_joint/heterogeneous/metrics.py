from statistics import fmean, median

from pydantic import Field, field_validator

from infra_joint.core.base import ContractModel


class ForcedPlacementMeasurements(ContractModel):
    agent_id: str = Field(min_length=1)
    costs_ms: tuple[float, ...] = Field(min_length=1)

    @field_validator("costs_ms")
    @classmethod
    def costs_are_nonnegative(cls, values: tuple[float, ...]) -> tuple[float, ...]:
        if any(value < 0 for value in values):
            raise ValueError("forced placement costs must be nonnegative")
        return values


class RoutingRegret(ContractModel):
    selected_agent_id: str = Field(min_length=1)
    oracle_agent_id: str = Field(min_length=1)
    selected_empirical_cost_ms: float = Field(ge=0)
    oracle_empirical_cost_ms: float = Field(ge=0)
    regret_ms: float = Field(ge=0)
    oracle_selected: bool


class RoutingRegretSummary(ContractModel):
    count: int = Field(gt=0)
    mean_regret_ms: float = Field(ge=0)
    median_regret_ms: float = Field(ge=0)
    p95_regret_ms: float = Field(ge=0)
    oracle_selection_accuracy: float = Field(ge=0, le=1)


def calculate_routing_regret(
    selected_agent_id: str,
    forced: tuple[ForcedPlacementMeasurements, ...],
) -> RoutingRegret:
    by_agent = {item.agent_id: item for item in forced}
    if len(by_agent) != len(forced) or len(by_agent) < 2:
        raise ValueError("oracle requires at least two unique forced placements")
    if selected_agent_id not in by_agent:
        raise ValueError("selected placement lacks forced-placement measurements")
    empirical = {
        agent_id: median(measurement.costs_ms) for agent_id, measurement in by_agent.items()
    }
    oracle_agent_id, oracle_cost = min(empirical.items(), key=lambda item: (item[1], item[0]))
    selected_cost = empirical[selected_agent_id]
    return RoutingRegret(
        selected_agent_id=selected_agent_id,
        oracle_agent_id=oracle_agent_id,
        selected_empirical_cost_ms=selected_cost,
        oracle_empirical_cost_ms=oracle_cost,
        regret_ms=max(0.0, selected_cost - oracle_cost),
        oracle_selected=selected_agent_id == oracle_agent_id,
    )


def summarize_routing_regret(values: tuple[RoutingRegret, ...]) -> RoutingRegretSummary:
    if not values:
        raise ValueError("routing regret summary requires at least one run")
    regrets = sorted(item.regret_ms for item in values)
    rank = max(0, min(len(regrets) - 1, -(-95 * len(regrets) // 100) - 1))
    return RoutingRegretSummary(
        count=len(values),
        mean_regret_ms=fmean(regrets),
        median_regret_ms=median(regrets),
        p95_regret_ms=regrets[rank],
        oracle_selection_accuracy=(sum(item.oracle_selected for item in values) / len(values)),
    )
