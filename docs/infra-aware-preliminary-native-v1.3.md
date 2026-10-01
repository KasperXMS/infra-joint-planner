# SDK-native Infra-Aware Preliminary v1.3

Date: 2026-10-02  
Branch: `open-ended-mas-preliminary-v1`  
Execution revision: `205de7d9607704bcf5efaaa56eed4da6bf7f4295`

## Scope and controls

This is the authorized one-task `Fast / Slow × Blind / Aware` preliminary. It uses
the frozen `multihop-multisource` task, SDK-native persistent Manager, shared Blind
Verifier, finite tool space, physical scheduler, 32K/2048 deployments, and the
20/64/20 budget. Every cell used a fresh Worker store, one repetition, and no retry
or replacement.

The task bundle SHA-256 is
`54ef8ddbe4a3379254345f307b3f0ef6b95fe92e0b28ac4c89124bb6b7ebfe8e`;
the static capability contract SHA-256 is
`8d46d9b941a08380a00fdab1e7c151c25affd589ec4444864f3c5c925a2089a4`.
All four counted cells use harness `blind-harness-v1.3.1`. This is the frozen v1.3
behavior plus only the control-plane compatibility fix that permits an Aware
Manager to share the unchanged Blind Verifier. The Verifier receives no physical
profile.

The network regimes were applied on all four machines using the existing
transactional `tc` harness:

- Fast: 100 Mbps, 5 ms added RTT.
- Slow: 3 Mbps, 50 ms added RTT.

Each cell's attestation records the applied qdisc and successful restoration.
Cleanup errors were null; A4/A5/A28 returned to their original `mq` roots and
strong-4090 returned to `noqueue`.

Blind receives no `PhysicalProfileView`. Aware receives only the anonymous view;
logical trace privacy checks passed in every cell and found no worker, deployment,
IP, placement, network-value, or private benchmark identity leakage.

## Four-cell result

Initial materialization was identical at 7,696,522 bytes. “Action bytes” below
exclude that fixed initial placement traffic; “total bytes” include it.

| Network | Method | Run | Completion | Score / format | Manager turns | Tool / model calls | Graph nodes / edges | E2E ms | Action bytes | Total bytes |
|---|---|---|---:|---|---:|---:|---:|---:|---:|---:|
| Fast | Blind | `16-multihop-fast-blind-v1.3.1` | no | n/a | 20 | 61 / 3 | 64 / 32 | 250,465.012 | 22,194 | 7,718,716 |
| Fast | Aware | `17-multihop-fast-aware-v1.3.1` | yes | 0.0 / valid | 13 | 18 / 4 | 22 / 16 | 214,865.608 | 10,006 | 7,706,528 |
| Slow | Blind | `18-multihop-slow-blind-v1.3.1` | yes | 0.0 / valid | 9 | 21 / 2 | 23 / 13 | 303,102.954 | 33,966 | 7,730,488 |
| Slow | Aware | `19-multihop-slow-aware-v1.3.1` | yes | 0.0 / valid | 13 | 41 / 2 | 43 / 33 | 217,485.620 | 5,598 | 7,702,120 |

The Fast-Blind run is a valid agent-trajectory failure, not a harness failure. It
reached one real model inference, accumulated evidence, and exhausted the frozen
20 Manager turns after 64 total tool/model calls. Its primary classification is
stopping/over-expansion plus hard budget exhaustion. No evaluator was invoked.

All three completed cells reached terminal synthesis and the private evaluator.
Their terminal outputs were format-valid but received score 0.0. The preliminary
therefore supplies no positive semantic-quality claim.

## Workflow evolution and physical execution

The final graph operator counts were:

| Cell | Operator composition |
|---|---|
| Fast Blind | `bm25_retrieve` 35, `read_artifact` 16, `select_fields` 10, `invoke_model` 3 |
| Fast Aware | `bm25_retrieve` 10, `select_fields` 4, `filter_records` 2, `read_artifact` 2, `invoke_model` 4 |
| Slow Blind | `bm25_retrieve` 9, `filter_records` 9, `aggregate_artifacts` 1, `select_fields` 1, `read_artifact` 1, `invoke_model` 2 |
| Slow Aware | `bm25_retrieve` 18, `top_k_records` 10, `filter_records` 5, `select_fields` 5, `read_artifact` 3, `invoke_model` 2 |

The Slow-Blind trajectory aggregated remote evidence on A28 before terminal model
execution and moved 33,966 action bytes. The Slow-Aware trajectory instead grew a
larger distributed reduction graph, including ten `top_k_records` actions, and
moved only 5,598 action bytes before the A28 model call.

For the same Slow condition, Aware versus Blind reduced:

- E2E by 85,617.334 ms (28.2%);
- action-transfer bytes by 28,368 bytes (83.5%); and
- action-transfer latency from 1,436.008 ms to 199.100 ms (86.1%).

The fixed initial materialization dominates total byte volume, so total bytes fell
only 0.37%. Both completed with the same score (0.0), meaning the system benefit did
not further reduce measured quality, but it also did not preserve a positive-quality
answer.

Aware workflow structure changed with infrastructure: Fast ended with 22 nodes and
Slow with 43 nodes. The Slow trajectory performed substantially more local bounded
reduction and transferred less action data. Thus the observed relation is
`H_fast != H_slow -> G_fast != G_slow`, and the direction is consistent with the
anonymous profile presented to the Manager.

## Predicted versus actual cost signal

The Aware Manager received one anonymous profile per physical action: 22 in Fast and
43 in Slow. Fast profiles classified actions as `fast` or `unknown`, with predicted
transfer upper bounds up to 226.814 ms. Slow profiles classified actions as
`constrained` or `local`, with upper bounds up to 7,443.797 ms. For representative
2.43–2.49 MB shard inputs, Slow predicted transfer upper bounds were approximately
6.54–6.70 seconds; comparable Fast full-shard inputs were bounded near 0.227 seconds.
The fast/slow ordering therefore agrees with the applied regimes and actual transfer
pressure.

No service-latency profile was available in either Aware run. All 65 corresponding
fields remained explicitly unknown; the system did not synthesize a guessed value.
This prevents a meaningful whole-workflow predicted-versus-actual latency accuracy
claim in this run.

## Invalid preflight attempt retained

Before the counted matrix, one Fast-Aware attempt failed before the Manager because
the harness incorrectly rejected `ProfileVisibility.AWARE` whenever the shared Blind
Verifier was enabled. It performed no logical trajectory and is excluded from the
four cells. The evidence remains preserved under the earlier `e41f39e` deployment.
The minimal fix removed only that erroneous construction-time coupling and added a
regression proving that the Aware Manager sees the profile while the Verifier does
not. No experiment evidence was overwritten.

## Decision

This preliminary shows a real, interpretable infrastructure-dependent workflow
change and a measurable Slow-network systems benefit at equal measured quality.
It does **not** establish a stable method advantage:

- `n=1` trajectories are stochastic;
- Blind Fast and Blind Slow also produced different workflows despite having no
  network visibility;
- Fast Blind did not complete, so the Fast method comparison is censored; and
- every completed cell scored 0.0.

The result is sufficient as a problem-validity signal for further controlled work,
but not for an accuracy, robustness, or causal performance claim. Per the stopping
rule, no additional task, repetition, bandwidth, prompt tuning, or Aware experiment
was run.

