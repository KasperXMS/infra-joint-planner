# Complete experimental inventory

All selected inference is complete. 1,000 valid workflow episodes plus 2,316 one-step decision queries; no query is counted as workflow completion/TSR. Engineering-invalidated work remains included separately. Models are official BF16 Qwen3.5-4B/9B, Transformers/SDPA, greedy thinking-disabled. Frozen stage configs define context/turn/batch settings.

| Model stage | Engineering-only | Logical requests | Physical batches | Batch service wall, s | Generation span, s | Prompt tokens |
| --- | --- | --- | --- | --- | --- | --- |
| decision-context-probe-v1/Qwen3.5-4B | False | 144 | 36 | 59.420 | 59.892 | 186,040 |
| decision-context-probe-v1/Qwen3.5-9B | False | 144 | 36 | 57.143 | 57.611 | 186,040 |
| decision-generalization-v1/Qwen3.5-4B | False | 1,014 | 507 | 691.392 | 696.083 | 1,613,426 |
| decision-generalization-v1/Qwen3.5-9B | False | 1,014 | 507 | 691.076 | 695.707 | 1,613,426 |
| diagnostic-v1/Qwen3.5-4B | True | 404 | 101 | 138.566 | 142.835 | 865,925 |
| diagnostic-v2/Qwen3.5-4B | False | 647 | 176 | 364.933 | 371.932 | 1,527,834 |
| diagnostic-v2/Qwen3.5-9B | False | 430 | 108 | 255.987 | 259.902 | 759,661 |
| heldout-binding-v1/Qwen3.5-4B | False | 6,950 | 3,485 | 5312.476 | 5404.163 | 20,189,514 |
| heldout-binding-v1/Qwen3.5-9B | False | 5,852 | 2,938 | 5471.015 | 5545.196 | 16,142,848 |
| role-placement-v1/Qwen3.5-4B | False | 454 | 124 | 256.916 | 261.878 | 1,035,162 |
| role-placement-v1/Qwen3.5-9B | False | 322 | 88 | 182.792 | 185.915 | 551,358 |
| structural-transfer-v1/Qwen3.5-4B | False | 6,955 | 3,489 | 5169.943 | 5281.732 | 23,449,978 |
| structural-transfer-v1/Qwen3.5-9B | False | 5,778 | 2,903 | 5534.469 | 5621.841 | 17,927,743 |

Each physical batch is counted once. Generation span covers first through last recorded request for that model, not model-loading/setup/E2E or GPU kernel time; stages on different GPUs overlap. Unrecorded in-flight engineering work is unknown. Cloud calls are absent; local GPU USD stays unknown, not zero. Whole-instance lease accounting is separate in final-resource-work.json and the shutdown receipt.

| Workflow study | Model | Condition | Completion | Numeric success | Turns | Prompt tokens | Output tokens | Median E2E, s | Verify tool calls |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| diagnostic-v2 | Qwen3.5-4B | ledger | 5/8 | 1/8 | 195 | 516,253 | 5,779 | 23.86 | 47 |
| diagnostic-v2 | Qwen3.5-4B | local | 8/8 | 2/8 | 104 | 162,176 | 3,108 | 22.46 | 12 |
| diagnostic-v2 | Qwen3.5-4B | none | 8/8 | 2/8 | 108 | 159,014 | 2,488 | 22.70 | 12 |
| diagnostic-v2 | Qwen3.5-4B | static | 4/8 | 1/8 | 240 | 690,391 | 8,369 | 69.52 | 7 |
| diagnostic-v2 | Qwen3.5-9B | ledger | 8/8 | 2/8 | 107 | 230,049 | 4,833 | 28.00 | 12 |
| diagnostic-v2 | Qwen3.5-9B | local | 8/8 | 2/8 | 108 | 165,338 | 2,484 | 28.00 | 13 |
| diagnostic-v2 | Qwen3.5-9B | none | 8/8 | 2/8 | 107 | 156,466 | 2,470 | 28.00 | 12 |
| diagnostic-v2 | Qwen3.5-9B | static | 8/8 | 2/8 | 108 | 207,808 | 4,868 | 28.00 | 12 |
| role-placement-v1 | Qwen3.5-4B | none | 8/8 | 2/8 | 108 | 159,014 | 2,488 | 21.89 | 12 |
| role-placement-v1 | Qwen3.5-4B | static | 4/8 | 1/8 | 240 | 690,264 | 8,373 | 69.33 | 7 |
| role-placement-v1 | Qwen3.5-4B | static_system | 8/8 | 2/8 | 106 | 185,884 | 2,561 | 22.66 | 12 |
| role-placement-v1 | Qwen3.5-9B | none | 8/8 | 2/8 | 107 | 156,466 | 2,470 | 27.02 | 12 |
| role-placement-v1 | Qwen3.5-9B | static | 8/8 | 2/8 | 108 | 207,808 | 4,868 | 28.00 | 12 |
| role-placement-v1 | Qwen3.5-9B | static_system | 8/8 | 2/8 | 107 | 187,084 | 2,470 | 27.47 | 12 |
| heldout-binding-v1 | Qwen3.5-4B | binding_system | 36/36 | 5/36 | 639 | 1,790,113 | 17,972 | 22.91 | 60 |
| heldout-binding-v1 | Qwen3.5-4B | ledger_system | 29/36 | 0/36 | 999 | 3,380,976 | 31,327 | 27.29 | 105 |
| heldout-binding-v1 | Qwen3.5-4B | local | 26/36 | 1/36 | 1,112 | 2,818,144 | 30,782 | 26.71 | 407 |
| heldout-binding-v1 | Qwen3.5-4B | none | 36/36 | 0/36 | 700 | 1,290,103 | 16,842 | 21.21 | 60 |
| heldout-binding-v1 | Qwen3.5-4B | static | 6/36 | 0/36 | 2,018 | 6,848,330 | 57,539 | 96.74 | 815 |
| heldout-binding-v1 | Qwen3.5-4B | static_system | 36/36 | 1/36 | 701 | 1,547,191 | 21,775 | 22.55 | 60 |
| heldout-binding-v1 | Qwen3.5-4B | unbound_system | 33/36 | 2/36 | 781 | 2,514,657 | 21,448 | 25.24 | 57 |
| heldout-binding-v1 | Qwen3.5-9B | binding_system | 36/36 | 5/36 | 633 | 1,746,728 | 15,235 | 23.45 | 62 |
| heldout-binding-v1 | Qwen3.5-9B | ledger_system | 29/36 | 0/36 | 1,085 | 3,763,013 | 35,055 | 42.59 | 132 |
| heldout-binding-v1 | Qwen3.5-9B | local | 29/36 | 2/36 | 1,052 | 2,659,968 | 30,662 | 42.23 | 100 |
| heldout-binding-v1 | Qwen3.5-9B | none | 33/36 | 2/36 | 808 | 1,718,159 | 21,367 | 26.73 | 57 |
| heldout-binding-v1 | Qwen3.5-9B | static | 29/36 | 1/36 | 957 | 3,005,718 | 43,560 | 31.25 | 193 |
| heldout-binding-v1 | Qwen3.5-9B | static_system | 36/36 | 0/36 | 680 | 1,479,193 | 19,085 | 22.29 | 68 |
| heldout-binding-v1 | Qwen3.5-9B | unbound_system | 36/36 | 3/36 | 637 | 1,770,069 | 15,390 | 23.82 | 60 |
| structural-transfer-v1 | Qwen3.5-4B | binding_system | 42/48 | 2/48 | 1,298 | 4,809,681 | 31,851 | 26.27 | 73 |
| structural-transfer-v1 | Qwen3.5-4B | none | 24/48 | 0/48 | 2,151 | 6,259,550 | 54,722 | 82.19 | 41 |
| structural-transfer-v1 | Qwen3.5-4B | static_system | 30/48 | 1/48 | 1,941 | 6,122,834 | 49,995 | 60.72 | 54 |
| structural-transfer-v1 | Qwen3.5-4B | unbound_system | 38/48 | 2/48 | 1,565 | 6,257,913 | 40,028 | 31.93 | 67 |
| structural-transfer-v1 | Qwen3.5-9B | binding_system | 48/48 | 7/48 | 1,073 | 3,520,838 | 27,636 | 34.83 | 80 |
| structural-transfer-v1 | Qwen3.5-9B | none | 29/48 | 1/48 | 1,953 | 5,753,312 | 61,513 | 77.62 | 49 |
| structural-transfer-v1 | Qwen3.5-9B | static_system | 38/48 | 3/48 | 1,625 | 4,853,922 | 54,578 | 46.25 | 65 |
| structural-transfer-v1 | Qwen3.5-9B | unbound_system | 47/48 | 3/48 | 1,127 | 3,799,671 | 28,147 | 36.50 | 78 |

The verifier is an actual deterministic provenance/freshness tool, not an LLM; all measured model calls are planner calls. No Specialist/Physical Executor model is invoked in this synthetic study. This is not a resource-accounting substitution for historical InfraMAS. Tool/finish/error details are retained per group in workflow-condition-results.csv and each original summary; development errors include expected updates, while final-study errors explicitly exclude expected notices.

One-step accuracy/tokens are in the two decision-probe summaries. The final diagnostic publishes individual provider latencies in decision-results.csv; development request latencies remain in indexed private raw evidence. Development decisions reuse source tasks; the final diagnostic samples observed primary states and is post-hoc, not independent held-out performance validation. Placement, primary and transfer tables include every failed attempt and all its work. No inverse cost-per-success claim is made from tiny success denominators or mixed-condition batch work.
