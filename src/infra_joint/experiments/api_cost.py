"""External list-price accounting from raw provider usage, never Agent guidance.

SDK Usage objects are not input: their default zero fields cannot distinguish
unreported usage from a measured zero. Missing usage, pricing, cache split or
currency conversion remains unknown. This is not a billing invoice estimator.
"""

from collections.abc import Mapping, Sequence
from datetime import date
from decimal import Decimal, localcontext
from typing import Literal, cast

from pydantic import Field, model_validator

from infra_joint.core.base import ContractModel

Recipient = Literal["manager", "specialist", "verifier"]


class APIPriceCard(ContractModel):
    provider: str = Field(min_length=1)
    region: str = Field(min_length=1)
    model_id: str = Field(min_length=1)
    currency: str = Field(min_length=1)
    input_per_million: Decimal = Field(ge=0, allow_inf_nan=False)
    cached_input_per_million: Decimal = Field(ge=0, allow_inf_nan=False)
    output_per_million: Decimal = Field(ge=0, allow_inf_nan=False)
    observed_date: date
    source_url: str = Field(min_length=1)
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    pricing_kind: Literal["published_nonbatch_list_price"] = "published_nonbatch_list_price"


class FXReference(ContractModel):
    provider_currency: str = Field(min_length=1)
    reference_currency: Literal["EUR"] = "EUR"
    target_currency: Literal["USD"] = "USD"
    provider_units_per_reference: Decimal = Field(gt=0, allow_inf_nan=False)
    usd_per_reference: Decimal = Field(gt=0, allow_inf_nan=False)
    rate_date: date
    source_url: str = Field(min_length=1)
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class ProviderUsage(ContractModel):
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    cached_input_tokens: int | None = Field(default=None, ge=0)
    reasoning_output_tokens: int | None = Field(default=None, ge=0)
    reported_total_tokens: int | None = Field(default=None, ge=0)
    invalid_fields: tuple[str, ...] = ()


def _count(value: object) -> int | None:
    # bool is a subclass of int, but not a provider token measurement.
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def _detail(details: object, key: str) -> object:
    return cast(Mapping[str, object], details).get(key) if isinstance(details, Mapping) else None


def usage_from_raw(raw: Mapping[str, object] | None) -> ProviderUsage:
    if raw is None:
        return ProviderUsage()
    prompt_details = raw.get("prompt_tokens_details")
    completion_details = raw.get("completion_tokens_details")
    values: dict[str, object] = {
        "input_tokens": raw.get("prompt_tokens"),
        "output_tokens": raw.get("completion_tokens"),
        "reported_total_tokens": raw.get("total_tokens"),
        "cached_input_tokens": _detail(prompt_details, "cached_tokens"),
        "reasoning_output_tokens": _detail(completion_details, "reasoning_tokens"),
    }
    invalid = [key for key, value in values.items() if value is not None and _count(value) is None]
    counts = {key: _count(value) for key, value in values.items()}
    input_count, output_count = counts["input_tokens"], counts["output_tokens"]
    cached, reasoning, total = (counts["cached_input_tokens"], counts["reasoning_output_tokens"],
                                counts["reported_total_tokens"])
    if cached is not None and input_count is not None and cached > input_count:
        invalid.append("cached_input_tokens_exceed_input")
    if reasoning is not None and output_count is not None and reasoning > output_count:
        invalid.append("reasoning_tokens_exceed_output")
    if (total is not None and input_count is not None and output_count is not None
            and total != input_count + output_count):
        invalid.append("inconsistent_total_tokens")
    return ProviderUsage(**counts, invalid_fields=tuple(invalid))


class APICostEstimate(ContractModel):
    usage: ProviderUsage
    provider_currency: str | None = None
    provider_amount: Decimal | None = Field(default=None, ge=0, allow_inf_nan=False)
    usd_amount: Decimal | None = Field(default=None, ge=0, allow_inf_nan=False)
    unknown_reasons: tuple[str, ...] = ()
    invoice_amount: Literal[False] = False
    reasoning_already_in_output_total: Literal[True] = True


def estimate_api_cost(
    raw_usage: Mapping[str, object] | None,
    price: APIPriceCard | None,
    fx: FXReference | None,
    *,
    provider: str,
    region: str,
    requested_model: str,
    response_model: str | None,
) -> APICostEstimate:
    usage = usage_from_raw(raw_usage)
    reasons = list(usage.invalid_fields)
    if usage.input_tokens is None:
        reasons.append("input_tokens_unreported")
    if usage.output_tokens is None:
        reasons.append("output_tokens_unreported")
    if price is None:
        reasons.append("price_unavailable")
    elif (price.provider, price.region, price.model_id) != (provider, region, requested_model):
        reasons.append("price_provider_region_or_model_mismatch")
    if response_model is None:
        reasons.append("response_model_unreported")
    elif response_model != requested_model:
        reasons.append("response_model_mismatch")
    # The split is needed only if hit and miss have different prices.
    if (price is not None and usage.cached_input_tokens is None
            and price.cached_input_per_million != price.input_per_million):
        reasons.append("cache_split_unreported")
    currency = price.currency if price is not None else None
    if reasons or price is None or usage.input_tokens is None or usage.output_tokens is None:
        return APICostEstimate(usage=usage, provider_currency=currency,
                               unknown_reasons=tuple(reasons))
    # If both rates are identical, cache split does not affect this calculation.
    # The usage field remains None; this is not an invented zero measurement.
    cached = usage.cached_input_tokens if usage.cached_input_tokens is not None else 0
    with localcontext() as ctx:
        ctx.prec = 40
        amount = (
            Decimal(usage.input_tokens - cached) * price.input_per_million
            + Decimal(cached) * price.cached_input_per_million
            + Decimal(usage.output_tokens) * price.output_per_million
        ) / Decimal(1_000_000)
        usd = None
        if price.currency == "USD":
            usd = amount
        elif fx is None:
            reasons.append("fx_unavailable")
        elif fx.provider_currency != price.currency:
            reasons.append("fx_currency_mismatch")
        else:
            usd = amount * fx.usd_per_reference / fx.provider_units_per_reference
    return APICostEstimate(usage=usage, provider_currency=currency, provider_amount=amount,
                           usd_amount=usd, unknown_reasons=tuple(reasons))


class APICostReceipt(ContractModel):
    call_id: str = Field(min_length=1)
    recipient: Recipient
    cost: APICostEstimate


class APICostSummary(ContractModel):
    calls: int = Field(ge=0)
    known_usd_calls: int = Field(ge=0)
    unknown_usd_calls: int = Field(ge=0)
    known_usd_subtotal: Decimal = Field(ge=0, allow_inf_nan=False)
    complete_usd_total: Decimal | None = Field(default=None, ge=0, allow_inf_nan=False)

    @model_validator(mode="after")
    def complete_count_matches_total(self) -> "APICostSummary":
        if self.known_usd_calls + self.unknown_usd_calls != self.calls:
            raise ValueError("API call count mismatch")
        if (self.complete_usd_total is not None) != (self.unknown_usd_calls == 0):
            raise ValueError("Complete API amount requires every call cost")
        return self


def summarize_api_costs(receipts: Sequence[APICostReceipt]) -> dict[str, APICostSummary]:
    if len({receipt.call_id for receipt in receipts}) != len(receipts):
        raise ValueError("Duplicate API receipt would double-count a call")
    result: dict[str, APICostSummary] = {}
    for recipient in ("manager", "specialist", "verifier", "all"):
        selected = [row for row in receipts if recipient == "all" or row.recipient == recipient]
        amounts = [row.cost.usd_amount for row in selected if row.cost.usd_amount is not None]
        with localcontext() as ctx:
            # Each frozen per-call FX result has already been rounded once. Sum
            # those finite Decimal receipts exactly: a second fixed-precision
            # rounding made totals depend on HTTP completion versus audit order.
            # Align to the smallest exponent and reserve carry digits for N terms.
            # This changes no prices, FX, per-call charge or logical feedback.
            if amounts:
                smallest_exponent = min(cast(int, amount.as_tuple().exponent)
                                        for amount in amounts)
                largest_position = max(amount.adjusted() for amount in amounts)
                ctx.prec = max(40, largest_position - smallest_exponent + 1
                               + len(str(len(amounts))) + 1)
            else:
                ctx.prec = 40
            subtotal = sum(amounts, Decimal(0))
        unknown = len(selected) - len(amounts)
        result[recipient] = APICostSummary(
            calls=len(selected), known_usd_calls=len(amounts), unknown_usd_calls=unknown,
            known_usd_subtotal=subtotal, complete_usd_total=subtotal if unknown == 0 else None,
        )
    return result
