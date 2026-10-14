# Per-run pilot diagnostics

Manifest SHA-256: `415e8d63b3470d8baec6a4c1833918bf127f7a018caa53789baec0825b9bed03`. Officially scored: 16/16; complete without API rejection: 12/16. All times and energy values come from retained receipts.

| Cell | Status | Reward | Skill body | Agent s | Commands (failed) | Router errors | Compactions | Artifact changed | Receipt |
|---|---|---:|---|---:|---:|---:|---:|---|---|
| weighted-gdp-calculation-3-small-S0-r1 | valid-score | 0 | absent | 875.5 | 53 (3) | 64 | 16 | no | [JSON](../trials/weighted-gdp-calculation-3-small-S0-r1/result.json) |
| weighted-gdp-calculation-3-small-S1-r1 | valid-score | 0 | available, unread | 875.1 | 80 (6) | 46 | 25 | no | [JSON](../trials/weighted-gdp-calculation-3-small-S1-r1/result.json) |
| weighted-gdp-calculation-3-small-S2-r1 | valid-score | 0 | injected 137/137 requests | 875.2 | 95 (14) | 0 | 42 | no | [JSON](../trials/weighted-gdp-calculation-3-small-S2-r1/result.json) |
| weighted-gdp-calculation-4-small-S0-r1 | valid-score | 0 | absent | 874.5 | 41 (12) | 129 | 22 | no | [JSON](../trials/weighted-gdp-calculation-4-small-S0-r1/result.json) |
| weighted-gdp-calculation-4-small-S1-r1 | scored-context-rejection | 0 | available, unread | 52.3 | 6 (2) | 1 | 1 | no | [JSON](../trials/weighted-gdp-calculation-4-small-S1-r1/result.json) |
| weighted-gdp-calculation-4-small-S2-r1 | valid-score | 0 | injected 98/98 requests | 879.1 | 52 (4) | 0 | 46 | no | [JSON](../trials/weighted-gdp-calculation-4-small-S2-r1/result.json) |
| financial-analysis-2-small-S0-r1 | valid-score | 0 | absent | 145.2 | 30 (0) | 0 | 3 | yes | [JSON](../trials/financial-analysis-2-small-S0-r1/result.json) |
| financial-analysis-2-small-S1-r1 | valid-score | 0 | available, unread | 113.2 | 21 (0) | 0 | 2 | yes | [JSON](../trials/financial-analysis-2-small-S1-r1/result.json) |
| financial-analysis-2-small-S2-r1 | valid-score | 1 | injected 31/31 requests | 190.0 | 24 (3) | 0 | 5 | yes | [JSON](../trials/financial-analysis-2-small-S2-r1/result.json) |
| financial-analysis-3-small-S0-r1 | scored-context-rejection | 0 | absent | 236.6 | 58 (3) | 0 | 7 | no | [JSON](../trials/financial-analysis-3-small-S0-r1/result.json) |
| financial-analysis-3-small-S1-r1 | valid-score | 0 | available, unread | 130.0 | 30 (0) | 0 | 3 | yes | [JSON](../trials/financial-analysis-3-small-S1-r1/result.json) |
| financial-analysis-3-small-S2-r1 | valid-score | 1 | injected 47/47 requests | 232.9 | 38 (5) | 1 | 6 | yes | [JSON](../trials/financial-analysis-3-small-S2-r1/result.json) |
| weighted-gdp-calculation-3-strong-S1-r1 | scored-context-rejection | 0 | available, unread | 388.3 | 41 (6) | 0 | 10 | yes | [JSON](../trials/weighted-gdp-calculation-3-strong-S1-r1/result.json) |
| weighted-gdp-calculation-4-strong-S1-r1 | scored-context-rejection | 0 | available, unread | 275.7 | 28 (3) | 0 | 6 | yes | [JSON](../trials/weighted-gdp-calculation-4-strong-S1-r1/result.json) |
| financial-analysis-2-strong-S1-r1 | valid-score | 0 | available, unread | 425.1 | 93 (5) | 0 | 9 | yes | [JSON](../trials/financial-analysis-2-strong-S1-r1/result.json) |
| financial-analysis-3-strong-S1-r1 | valid-score | 0 | available, unread | 157.8 | 34 (0) | 0 | 3 | yes | [JSON](../trials/financial-analysis-3-strong-S1-r1/result.json) |

| Cell | Input / output tokens | Model calls | API / context rejects | First-byte / later response s | Peak GPU MiB | Sampled Wh |
|---|---:|---:|---:|---:|---:|---:|
| weighted-gdp-calculation-3-small-S0-r1 | 1581305 / 62401 | 133 | 0 / 0 | 132.147 / 699.563 | 27563.0 | 118.19 |
| weighted-gdp-calculation-3-small-S1-r1 | 1736170 / 58786 | 151 | 0 / 0 | 149.893 / 670.09 | 27563.0 | 109.95 |
| weighted-gdp-calculation-3-small-S2-r1 | 1780842 / 59543 | 137 | 0 / 0 | 138.078 / 668.95 | 27565.0 | 111.84 |
| weighted-gdp-calculation-4-small-S0-r1 | 2082487 / 54934 | 192 | 0 / 0 | 187.531 / 630.151 | 27565.0 | 107.79 |
| weighted-gdp-calculation-4-small-S1-r1 | 90451 / 3030 | 9 | 1 / 1 | 8.897 / 37.274 | 27565.0 | 6.03 |
| weighted-gdp-calculation-4-small-S2-r1 | 1218576 / 66936 | 98 | 0 / 0 | 95.206 / 752.082 | 27565.0 | 119.96 |
| financial-analysis-2-small-S0-r1 | 414634 / 5804 | 36 | 0 / 0 | 35.388 / 67.251 | 27565.0 | 12.62 |
| financial-analysis-2-small-S1-r1 | 271936 / 5645 | 24 | 0 / 0 | 24.356 / 63.675 | 27565.0 | 12.22 |
| financial-analysis-2-small-S2-r1 | 376921 / 9600 | 31 | 0 / 0 | 30.034 / 109.667 | 27565.0 | 18.89 |
| financial-analysis-3-small-S0-r1 | 708584 / 13815 | 63 | 1 / 1 | 61.78 / 159.569 | 27565.0 | 26.12 |
| financial-analysis-3-small-S1-r1 | 372119 / 6018 | 32 | 0 / 0 | 29.493 / 70.985 | 27565.0 | 13.75 |
| financial-analysis-3-small-S2-r1 | 568487 / 10594 | 47 | 0 / 0 | 42.741 / 123.473 | 27565.0 | 24.07 |
| weighted-gdp-calculation-3-strong-S1-r1 | 588525 / 22779 | 52 | 1 / 1 | 53.386 / 296.037 | 28067.0 | 76.65 |
| weighted-gdp-calculation-4-strong-S1-r1 | 386602 / 16370 | 35 | 1 / 1 | 35.557 / 207.402 | 28067.0 | 58.08 |
| financial-analysis-2-strong-S1-r1 | 1196200 / 19863 | 103 | 0 / 0 | 104.877 / 259.76 | 28067.0 | 75.19 |
| financial-analysis-3-strong-S1-r1 | 431075 / 6855 | 38 | 0 / 0 | 38.343 / 88.811 | 28067.0 | 26.81 |

First-byte and later-response sums are client-side latency proxies, not direct server-side prefill/decode measurements. Sampled Wh integrates selected GPU power over approximately five-second intervals and is not a billing amount. The context-rejected cells retain their official reward 0 but are excluded from the clean comparison denominator. `Skill body` measures actual appearance of the exact original text in model requests; it does not alone prove rule application.
