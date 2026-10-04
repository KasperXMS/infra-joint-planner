# API list-price accounting readiness v1

2026-10-05. **Calculator and dated price/FX sources are frozen; full seven-method
runtime/transport integration remains pending. Formal benchmark runs = 0.**
Implementation `8278518`. This is external experiment telemetry, not a new Agent
objective, prompt, cost-guidance route or physical scheduling policy.

## Price basis

Both configured aliases are served through Alibaba Model Studio's existing Beijing
workspace. Use its published nonbatch alias list prices, not DeepSeek-direct API
rates, snapshot-specific peak/off-peak rates, explicit-cache creation or inferred
account discounts. No invoice or actually settled USD claim is made.

| Requested alias | Uncached input CNY / million | Implicit cached input | Output | Source |
|---|---:|---:|---:|---|
| `deepseek-v4-pro` | 12 | 1 | 24 | [Alibaba alias pricing](https://help.aliyun.com/zh/model-studio/deepseek-v4-pro) |
| `qwen3.8-max` | 12 | 1.5 | 36 | [Alibaba alias pricing](https://help.aliyun.com/zh/model-studio/qwen3-8-max) |

Shared fixed Qwen Verifier uses the second card in both Planner conditions.
Requested/response model and provider/region must match the card. A mismatch or
missing response identity yields unknown, never a borrowed price or fallback.
Underlying alias snapshot identity remains separately unverified.

USD uses the last published pre-freeze
[ECB reference feed](https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml),
dated **2026-10-02**, retrieved and preserved on4090: USD/EUR=1.1225,
CNY/EUR=7.5259. Thus reference USD cost is CNY cost ×1.1225/7.5259.
This fixed cross-rate is shared by every method/Planner; it is not a transaction
conversion rate. Decimal arithmetic uses40 significant digits, not binary floats.

Source YAML: `configs/experiments/large-scale-api-pricing-v1.yaml`.
Remote sources: `/home/super/xiaoming/large-scale-cost-guidance-v1/preparation/pricing-001`.

| Preserved material | SHA-256 |
|---|---|
| DeepSeek public pricing HTML | `f0dcf47598a782e3c9585539751d66fd9291e83a4d0dd24c21c5ed100835e381` |
| Qwen public pricing HTML | `834d42b4fc828d0c643cc32035b152c76129938ab06dbbc331080a36421e62bf` |
| ECB daily XML | `d16ef240d4d97a953b925cbf81451c812c559cd33f2ebe07b08b51e4085709e2` |
| Frozen YAML | `e4c03e0248798b5a786b5e5534f616b8a573add4f2ef6cf2ad5c8ed5e0ccb8ae` |
| `price-freeze.json` | `279d993cca0fd6b3206cbdb8eb5c1aab5008c3b35ed0424bec5d7587552122b6` |
| Existing-response monetary audit | `eb583cd14f1c3b0faa5df3471fa6aed617e8374d841ab7e6617ffa2067dc2e1f` |

## Measured versus unknown

The calculator accepts raw provider `prompt_tokens`, `completion_tokens`, cached
and reasoning detail fields. It does not accept the SDK Usage object's default
zeros as raw measurements. Explicit reported zero is retained as zero. Missing
usage/token counts, differentiated cache split, price or FX stay unknown.
Malformed/negative/boolean counts, cache counts above input, reasoning above output
and inconsistent total tokens are retained as invalid observations, not coerced.
Reasoning is a subset of reported output and is not charged twice.

Retain provider-currency cost and reference USD. Separate Manager, specialist and
Verifier totals. Any unknown call makes the complete total unknown, while a
labeled known subtotal remains available. Duplicate call IDs are rejected to avoid
double-counting. An empty recipient group has zero calls, not fabricated usage.
Do not let failed HTTP calls disappear from a future attempted-call ledger.

Neither metering nor monetary receipts are injected into B0/B1 logical contexts.
All methods must share pass-through collection, including nested/parallel
specialists and the independently constructed fixed Qwen Verifier. That complete
runtime invariant has **not yet been proven**, so no formal queue may start.

## Offline check against real provider receipts

Reused the six preserved nonbenchmark compatibility responses from readiness
001/002. No new API calls, Worker starts, tc or benchmark payloads were used.
Each raw response has explicit cache0, usage and a matching model alias. All six
produce known amounts under the frozen cards; original receipts remain unchanged.

| Recipient | Real diagnostic HTTP calls | Estimated reference USD |
|---|---:|---:|
| Manager | 4 | 0.003363070198 |
| Specialist | 0 | 0; none were called |
| Fixed Qwen Verifier | 2 | 0.004313464170 |
| Total | 6 | 0.007676534368 |

Total provider-currency list-price estimate is **CNY0.051468**. This verifies raw
receipt arithmetic and fixed-Verifier separation, not benchmark cost, semantic
quality or future specialist capture. The evidence is
`readiness/monetary-readiness-audit-001.json` under the new namespace.

Full **616 tests passed**, Ruff passed, strict Pyright0errors/0warnings and
diff-check passed. Fifteen new tests cover cache/FX arithmetic, reported versus
SDK-default zeros, malformed usage, reasoning non-double-billing, identity/region
mismatch, missing sources, per-recipient incomplete totals and frozen YAML parsing.
Next is pass-through native model/HTTP collector integration and mocked contract
tests for all methods, parallel specialists and fixed Verifier, before execution
freeze. No new cost-guidance mechanism is authorized by this readiness receipt.
