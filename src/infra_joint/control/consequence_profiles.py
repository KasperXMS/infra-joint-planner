"""Empirical system-cost profiles without task text, quality labels or extrapolation."""

from math import ceil, floor
from typing import Literal

from pydantic import Field, model_validator

from infra_joint.core.base import ContractModel

NetworkCategory = Literal["fast", "moderate", "constrained", "unknown"]
_TOKEN_EDGES = (256, 1024, 4096, 8192, 16384, 24576, 32768, 65536)
_BYTE_EDGES = (65536, 262144, 1048576, 4194304, 16777216, 67108864, 268435456)


class ModelServiceSample(ContractModel):
    sample_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    model_class: str = Field(min_length=1)
    execution_surface_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    conservative_input_tokens: int | None = Field(default=None, ge=0)
    actual_input_tokens: int | None = Field(default=None, ge=0)
    image_count: int = Field(ge=0)
    output_budget: int = Field(gt=0)
    service_latency_ms: float = Field(ge=0, allow_inf_nan=False)


class OperatorWorkSample(ContractModel):
    sample_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    operator: str = Field(min_length=1)
    execution_surface_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    input_bytes: int | None = Field(default=None, ge=0)
    wrapper_latency_ms: float = Field(ge=0, allow_inf_nan=False)


class TransferSample(ContractModel):
    sample_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    network_category: NetworkCategory
    path_surface_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    bytes_transferred: int = Field(gt=0)
    latency_ms: float = Field(ge=0, allow_inf_nan=False)


class CostHistory(ContractModel):
    schema_version: Literal["cost-history-v0"] = "cost-history-v0"
    service_bucket_basis: Literal["conservative_input_tokens"] = "conservative_input_tokens"
    models: tuple[ModelServiceSample, ...] = ()
    operators: tuple[OperatorWorkSample, ...] = ()
    transfers: tuple[TransferSample, ...] = ()

    @model_validator(mode="after")
    def samples_are_unique(self) -> "CostHistory":
        ids = [item.sample_sha256 for item in (*self.models, *self.operators, *self.transfers)]
        if len(set(ids)) != len(ids):
            raise ValueError("historical sample IDs must be unique")
        return self


class EmpiricalLatency(ContractModel):
    source: Literal["empirical", "unknown"]
    sample_count: int = Field(ge=0)
    minimum_support: int = Field(gt=0)
    p50_ms: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    p90_ms: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    unknown_reason: str | None = None

    @model_validator(mode="after")
    def support_and_values_agree(self) -> "EmpiricalLatency":
        if self.source == "unknown":
            if self.p50_ms is not None or self.p90_ms is not None or not self.unknown_reason:
                raise ValueError("unknown estimate must not invent numeric latency")
        elif (self.sample_count < self.minimum_support or self.p50_ms is None
              or self.p90_ms is None or self.p50_ms > self.p90_ms
              or self.unknown_reason is not None):
            raise ValueError("empirical estimate requires support and ordered quantiles")
        return self


class EmpiricalConsequenceProfiles:
    def __init__(self, history: CostHistory, *, minimum_support: int = 3) -> None:
        if minimum_support < 1:
            raise ValueError("minimum support must be positive")
        self.history = history
        self.minimum_support = minimum_support

    def model_service(
        self,
        *,
        model_class: str,
        execution_surface_sha256: str | None,
        conservative_input_tokens: int | None,
        image_count: int,
        output_budget: int,
    ) -> EmpiricalLatency:
        if image_count < 0 or output_budget < 1:
            raise ValueError("invalid model cost features")
        if conservative_input_tokens is None:
            return self._unknown("input envelope unknown")
        if conservative_input_tokens < 0:
            raise ValueError("input envelope must be nonnegative")
        if execution_surface_sha256 is None:
            return self._unknown("model execution surface unknown")
        if conservative_input_tokens > _TOKEN_EDGES[-1]:
            return self._unknown("input envelope outside supported bucket range")
        values = tuple(item.service_latency_ms for item in self.history.models
                       if item.model_class == model_class
                       and item.execution_surface_sha256 == execution_surface_sha256
                       and item.conservative_input_tokens is not None
                       and _bucket(item.conservative_input_tokens, _TOKEN_EDGES)
                       == _bucket(conservative_input_tokens, _TOKEN_EDGES)
                       and item.image_count == image_count and item.output_budget == output_budget)
        return self._estimate(values)

    def operator_work(
        self, operator: str, input_bytes: int | None, *, execution_surface_sha256: str | None,
    ) -> EmpiricalLatency:
        if input_bytes is None:
            return self._unknown("input size unknown")
        if execution_surface_sha256 is None:
            return self._unknown("operator execution surface unknown")
        if input_bytes < 0:
            raise ValueError("input size must be nonnegative")
        if input_bytes > _BYTE_EDGES[-1]:
            return self._unknown("input size outside supported bucket range")
        values = tuple(item.wrapper_latency_ms for item in self.history.operators
                       if item.operator == operator and item.input_bytes is not None
                       and item.execution_surface_sha256 == execution_surface_sha256
                       and _bucket(item.input_bytes, _BYTE_EDGES)
                       == _bucket(input_bytes, _BYTE_EDGES))
        return self._estimate(values)

    def transfer(
        self, category: NetworkCategory, size_bytes: int, *, path_surface_sha256: str | None,
    ) -> EmpiricalLatency:
        if size_bytes < 1:
            raise ValueError("transfer size must be positive")
        if category == "unknown":
            return self._unknown("link category unknown")
        if path_surface_sha256 is None:
            return self._unknown("transfer path surface unknown")
        if size_bytes > _BYTE_EDGES[-1]:
            return self._unknown("transfer size outside supported bucket range")
        values = tuple(item.latency_ms for item in self.history.transfers
                       if item.network_category == category
                       and item.path_surface_sha256 == path_surface_sha256
                       and _bucket(item.bytes_transferred, _BYTE_EDGES)
                       == _bucket(size_bytes, _BYTE_EDGES))
        return self._estimate(values)

    def _unknown(self, reason: str) -> EmpiricalLatency:
        return EmpiricalLatency(source="unknown", sample_count=0,
                                minimum_support=self.minimum_support, unknown_reason=reason)

    def _estimate(self, values: tuple[float, ...]) -> EmpiricalLatency:
        if len(values) < self.minimum_support:
            return EmpiricalLatency(source="unknown", sample_count=len(values),
                                    minimum_support=self.minimum_support,
                                    unknown_reason="insufficient matching clean receipts")
        ordered = sorted(values)
        return EmpiricalLatency(source="empirical", sample_count=len(values),
                                minimum_support=self.minimum_support,
                                p50_ms=_quantile(ordered, 0.5), p90_ms=_quantile(ordered, 0.9))


def _bucket(value: int, edges: tuple[int, ...]) -> int:
    return next((edge for edge in edges if value <= edge), edges[-1] + 1)


def _quantile(values: list[float], q: float) -> float:
    position = (len(values) - 1) * q
    lower, upper = floor(position), ceil(position)
    return values[lower] + (values[upper] - values[lower]) * (position - lower)
