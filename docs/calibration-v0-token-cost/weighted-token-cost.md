# calibration_v0: method-level weighted token cost

This is a post-hoc reconstruction of the original calibration_v0 reference-workflow experiment. It makes no new inference calls and does not modify historical runs. The main raw file contains 24 completed runs (12 per method), one failed run before model selection, and one orphan trace directory also with no model selection. Early attempt1/2/3 and profiling runs are outside this scope. All 60 recorded model completions reconcile exactly with the per-run input/output token totals.

The values are backend-reported OpenAI-compatible `usage.prompt_tokens` and `usage.completion_tokens`, joined from `executor.selected` and `worker.execution.end` by action ID. They are not text-length estimates. The configured local tag was `qwen3-vl-edge-8k:latest`, across A4/A5/A28; the configured strong tag was `qwen3.8:27b`, on the 4090 host. These historical configuration tags do not establish a weight digest or a calibrated cost ratio between models. There is no paid Planner call in these fixed reference workflows.

| Method | Completed runs | Local calls | Local input | Local output | Strong calls | Strong input | Strong output |
|---|---:|---:|---:|---:|---:|---:|---:|
| centralized_raw | 12 | 0 | 0 | 0 | 12 | 37,740 | 408 |
| local_reduction | 12 | 36 | 138,132 | 13,850 | 12 | 19,004 | 480 |

Let the independent per-token weights be `s_in`, `s_out`, `l_in`, and `l_out`. The measured-token cost expressions for all 12 runs per method are:

```text
C_central = 37740*s_in + 408*s_out
C_local   = 19004*s_in + 480*s_out + 138132*l_in + 13850*l_out
```

For a normalized weighted-token sensitivity analysis, set strong input weight to 1, local input weight to `r`, and the output/input multiplier to `k` for both models. This assumption is illustrative, not a measured GPU price:

```text
C_central(r,k) = 37740 + 408*k
C_local(r,k)   = 19004 + 480*k + r*(138132 + 13850*k)
mean per completed run = C / 12
```

For equal input/output weights (`k=1`), `C_central=38148` and `C_local=19484+151982*r`:

| Local/strong per-token weight r | Central total | Local total | Central mean/run | Local mean/run | Local relative change |
|---:|---:|---:|---:|---:|---:|
| 0.10 | 38,148 | 34,682.20 | 3,179.00 | 2,890.18 | -9.09% |
| 0.125 | 38,148 | 38,481.75 | 3,179.00 | 3,206.81 | +0.87% |
| 0.25 | 38,148 | 57,479.50 | 3,179.00 | 4,789.96 | +50.68% |
| 1.00 | 38,148 | 171,466.00 | 3,179.00 | 14,288.83 | +349.48% |

For positive weights, local_reduction has a lower weighted-token cost exactly when:

```text
r < (18736 - 72*k) / (138132 + 13850*k)
```

At `k=1`, the threshold is `r<0.122804`: the local model must cost less than about 12.28% of the strong model per token. At `k=3`, it is `r<0.103071`, about 10.31%. A larger output weight penalizes the many locally generated evidence tokens. If `r=0.10,k=3`, costs are 38,964 versus 38,412.20, only about 1.42% lower for local reduction.

These are token-weighted accounting proxies, not measured dollar costs, FLOPs, energy, task E2E, or complete infrastructure costs. Prefill/decode differences, multimodal encoder work, model/hardware differences, sampling, network transfers and preprocessing are not calibrated by this proxy. Do not infer prices from parameter count. Historical local `api_cost_usd=0` does not establish zero monetary cost; local GPU monetary cost remains unknown. The method comparison is an equal-run average across the original two tasks, two infrastructure conditions and three repeats, not a success-normalized cost or a general task-distribution estimate.

Reconstruction evidence: [recovered-usage.json](recovered-usage.json) contains redacted per-call counters, exact method/model totals and SHA256 hashes of the source run file, trace files and Worker configurations. The [read-only extraction script](../../scripts/recover_calibration_v0_token_cost.py) reads the original files on the workstation and emits only audit metadata. Validation consists of duplicate/completeness checks and exact per-run token reconciliation; Ruff check/format pass. Original benchmark content, model responses and credentials are not exported.

## Task 795 only

Filtering the same recovered completed-run calls to task 795 yields six runs per method (two infrastructure conditions times three repeats). No new inference or failed-attempt substitution is involved.

| Method | Local calls | Local input | Local output | Strong calls | Strong input | Strong output |
|---|---:|---:|---:|---:|---:|---:|
| centralized_raw | 0 | 0 | 0 | 6 | 18,930 | 222 |
| local_reduction | 18 | 69,246 | 6,855 | 6 | 9,500 | 240 |

```text
C_central_795(r,k) = 18930 + 222*k
C_local_795(r,k)   = 9500 + 240*k + r*(69246 + 6855*k)
mean per completed run = C / 6
```

For `k=1`, the totals are `19152` and `9740+76101*r`:

| Local/strong per-token weight r | Central mean/run | Local mean/run | Local relative change |
|---:|---:|---:|---:|
| 0.10 | 3,192.00 | 2,891.68 | -9.41% |
| 0.125 | 3,192.00 | 3,208.77 | +0.53% |
| 0.25 | 3,192.00 | 4,794.21 | +50.19% |
| 1.00 | 3,192.00 | 14,306.83 | +348.21% |

The task-795 break-even condition is `r<(9430-18*k)/(69246+6855*k)`: 12.37% at `k=1` and 10.44% at `k=3`. The same uncalibrated-weight and monetary-cost limitations apply.
