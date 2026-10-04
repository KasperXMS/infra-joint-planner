from datetime import date
from decimal import Decimal, localcontext
from pathlib import Path

import pytest
import yaml

from infra_joint.experiments.api_cost import (
    APICostEstimate,
    APICostReceipt,
    APIPriceCard,
    FXReference,
    estimate_api_cost,
    summarize_api_costs,
    usage_from_raw,
)


def price(model: str = "qwen3.8-max") -> APIPriceCard:
    return APIPriceCard(
        provider="aliyun-model-studio", region="cn-beijing", model_id=model, currency="CNY",
        input_per_million=Decimal(12), cached_input_per_million=Decimal("1.5"),
        output_per_million=Decimal(36), observed_date=date(2026, 10, 5),
        source_url="https://help.aliyun.com/zh/model-studio/qwen3-8-max", source_sha256="a" * 64,
    )


def fx() -> FXReference:
    return FXReference(
        provider_currency="CNY", provider_units_per_reference=Decimal("7.5259"),
        usd_per_reference=Decimal("1.1225"), rate_date=date(2026, 10, 2),
        source_url="https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml",
        source_sha256="b" * 64,
    )


def raw_usage(cached: int = 200) -> dict[str, object]:
    return {"prompt_tokens": 1000, "completion_tokens": 50, "total_tokens": 1050,
            "prompt_tokens_details": {"cached_tokens": cached}}


def estimate(raw: dict[str, object] | None, **changes: object) -> APICostEstimate:
    # Keep fixtures explicit rather than turning unknown observations into SDK Usage.
    return estimate_api_cost(
        raw, price(), fx(), provider=str(changes.get("provider", "aliyun-model-studio")),
        region=str(changes.get("region", "cn-beijing")), requested_model="qwen3.8-max",
        response_model=str(changes.get("response_model", "qwen3.8-max")),
    )


def test_raw_cache_split_and_reference_currency_conversion_are_exact() -> None:
    result = estimate(raw_usage())
    assert result.provider_amount == Decimal("0.0117")
    with localcontext() as ctx:
        ctx.prec = 40
        assert result.usd_amount == Decimal("0.0117") * Decimal("1.1225") / Decimal("7.5259")
    assert result.usage.cached_input_tokens == 200
    assert result.usage.reasoning_output_tokens is None
    assert result.unknown_reasons == () and not result.invoice_amount


def test_explicit_reported_zero_is_not_missing_usage() -> None:
    result = estimate({"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0,
                       "prompt_tokens_details": {"cached_tokens": 0}})
    assert result.provider_amount == 0 and result.usd_amount == 0
    assert result.usage.input_tokens == 0
    missing = estimate(None)
    assert missing.provider_amount is None and missing.usd_amount is None
    assert "input_tokens_unreported" in missing.unknown_reasons


def test_missing_cache_split_is_unknown_not_assumed_cache_miss() -> None:
    result = estimate({"prompt_tokens": 1000, "completion_tokens": 50})
    assert result.provider_amount is None
    assert result.unknown_reasons == ("cache_split_unreported",)


def test_identically_priced_cache_split_can_be_costed_without_fabricating_usage() -> None:
    card = price().model_copy(update={"cached_input_per_million": Decimal(12)})
    result = estimate_api_cost(
        {"prompt_tokens": 1000, "completion_tokens": 50}, card, fx(),
        provider=card.provider, region=card.region, requested_model=card.model_id,
        response_model=card.model_id,
    )
    assert result.provider_amount == Decimal("0.0138")
    assert result.usage.cached_input_tokens is None


@pytest.mark.parametrize("field,value", [("prompt_tokens", True), ("completion_tokens", -1),
                                        ("total_tokens", "1050")])
def test_malformed_usage_cannot_be_coerced_to_a_charge(field: str, value: object) -> None:
    raw = raw_usage()
    raw[field] = value
    result = estimate(raw)
    assert result.provider_amount is None and field.replace("prompt", "input").replace(
        "completion", "output").replace("total_tokens", "reported_total_tokens"
    ) in result.unknown_reasons


def test_inconsistent_cache_reasoning_and_total_fields_are_retained_as_invalid() -> None:
    result = usage_from_raw({"prompt_tokens": 100, "completion_tokens": 10, "total_tokens": 111,
                             "prompt_tokens_details": {"cached_tokens": 101},
                             "completion_tokens_details": {"reasoning_tokens": 11}})
    assert result.invalid_fields == (
        "cached_input_tokens_exceed_input", "reasoning_tokens_exceed_output",
        "inconsistent_total_tokens",
    )


def test_reasoning_tokens_are_not_charged_twice() -> None:
    raw = raw_usage(0)
    raw["completion_tokens_details"] = {"reasoning_tokens": 40}
    result = estimate(raw)
    assert result.provider_amount == Decimal("0.0138")
    assert result.usage.reasoning_output_tokens == 40


@pytest.mark.parametrize("changes", [
    {"provider": "deepseek-direct"}, {"region": "singapore"},
    {"response_model": "qwen3.8-max-other-snapshot"},
])
def test_wrong_provider_region_or_model_never_borrows_an_alias_price(
    changes: dict[str, str],
) -> None:
    assert estimate(raw_usage(), **changes).provider_amount is None


def test_missing_price_or_fx_does_not_silently_zero_the_run_cost() -> None:
    args = {"provider": "aliyun-model-studio", "region": "cn-beijing",
            "requested_model": "qwen3.8-max", "response_model": "qwen3.8-max"}
    no_price = estimate_api_cost(raw_usage(), None, fx(), **args)
    assert no_price.provider_amount is None and no_price.usd_amount is None
    no_fx = estimate_api_cost(raw_usage(), price(), None, **args)
    assert no_fx.provider_amount == Decimal("0.0117") and no_fx.usd_amount is None
    assert no_fx.unknown_reasons == ("fx_unavailable",)


def test_per_recipient_partial_subtotals_never_masquerade_as_complete_totals() -> None:
    receipts = [APICostReceipt(call_id="m1", recipient="manager", cost=estimate(raw_usage())),
                APICostReceipt(call_id="v1", recipient="verifier", cost=estimate(None))]
    result = summarize_api_costs(receipts)
    assert result["manager"].complete_usd_total is not None
    assert result["specialist"].calls == 0 and result["specialist"].complete_usd_total == 0
    assert result["verifier"].complete_usd_total is None
    assert result["all"].calls == 2 and result["all"].unknown_usd_calls == 1
    assert result["all"].complete_usd_total is None
    with pytest.raises(ValueError, match="Duplicate"):
        summarize_api_costs([receipts[0], receipts[0]])


def test_frozen_price_cards_use_actual_aliases_same_region_and_fx() -> None:
    path = (Path(__file__).resolve().parents[1]
            / "configs/experiments/large-scale-api-pricing-v1.yaml")
    raw = yaml.safe_load(path.read_text())
    for model, values in raw["models"].items():
        card = APIPriceCard.model_validate({
            "model_id": model, "provider": raw["provider"], "region": raw["region"],
            "currency": raw["currency"], "observed_date": raw["observed_date"], **values,
        })
        assert card.model_id in {"deepseek-v4-pro", "qwen3.8-max"}
        assert card.region == "cn-beijing" and card.input_per_million == 12
    assert FXReference.model_validate(raw["fx"]).rate_date == date(2026, 10, 2)
