# Specialist profile isolation: hard-stop audit v1

2026-10-03, UTC. **Experiment stopped; the 24-clean-cell objective is not achieved.**
No runtime fix, prompt change, replacement, extra benchmark run or new method was
introduced after detection. This note overrides earlier clean-family declarations.

## Defect and authoritative proof

The intended frozen contract gives dynamic infrastructure profiles only to Aware
Manager reasoning. Specialists and the Verifier must remain Blind.

The current native tool wrapper in
[native_agents.py](../src/infra_joint/control/native_agents.py) obtains `owner`,
but calls the gateway with `expose_profile=state.visibility == AWARE`, using
run-level rather than recipient-level visibility. It then returns the complete
`LogicalObservation` JSON. In an Aware run, a specialist's tool result can therefore
contain a non-null `physical_profile`; the SDK appends that result to the
specialist's persistent context.

The interrupted 795-2 Slow-Aware trace proves this happened. Specialist
`video-event-analyzer:native-turn:2`, 10:52:27.701601 UTC, received
`tool_output/physical_profile/network_class = constrained`, together with abstract
transfer/queue ranges. Input SHA-256:
`cb0ed5f662589fbad5491c13ffb80d6d2e6f0787fcce51db5ac5d9f2d8475018`.
The direct `current_anonymous_profile` field was null, which did **not** prevent
the tool-result route. Checking only that direct field was insufficient.

This is an infrastructure-visibility contract breach, not evidence of gold, IP,
worker or deployment identity disclosure. The focused scan found no dynamic
profile in Blind Manager inputs or Verifier contexts. It does not turn a focused
scan into a proof about every conceivable leakage route.

## Retrospective scope: 39 traces, no reruns

Audit all 26 completed new attempts, the interrupted 27th, and the 12 existing
MultiHop traces. Affected entries below are excluded from clean comparisons.
Counts are distinct tool calls whose profile-bearing result entered a specialist
input, not inference counts; repeated historical context can repeat a result.

| Block / task | Condition / attempt | Distinct leaking tool calls | Effect |
| --- | --- | ---: | --- |
| LongBench Financial | Fast-Aware primary | 14 | Previously admitted; now excluded |
| LongBench Financial | Slow-Aware old primary | 20 | Already excluded for observer incident; additional defect |
| LongBench Financial | Slow-Aware old operational replacement | 6 | Already excluded for observer incident; additional defect |
| LongBench News | Fast-Aware primary | 2 | Previously admitted; now excluded |
| Video 795-2 | Slow-Aware primary | 7 | Interrupted at privacy hard-stop; invalid |
| Existing MultiHop | Fast-Aware r2 | 5 | Previously admitted; now excluded from clean comparison |
| Existing MultiHop | Fast-Aware r3 | 20 | Previously admitted; now excluded from clean comparison |
| Existing MultiHop | Slow-Aware r1 | 2 | Previously admitted; now excluded from clean comparison |

Corrected new coverage: **21/24**: LongBench 10/12 and Video 11/12. Retain all
27 attempts: 21 admitted, five completed/excluded, one externally aborted.
Unresolved conditions are Financial Fast-Aware, News Fast-Aware and 795-2
Slow-Aware. The old transport/backend incidents remain excluded independently.

Existing MultiHop is not rerun or overwritten. Nine of its twelve traces remain
admissible under this focused audit; condition counts become FB=3, FA=1, SB=3,
SA=2. The historical full-block averages and n=3 claims are not clean balanced
Blind/Aware evidence. Do not silently replace missing repetitions or pool scores.

## Stop and preservation

At 11:19:45.791355 UTC, write an append-only incident record, ownership-check the
exact controller/driver commands, then send controller PID 3305975 SIGTERM and
driver PID 3485183 SIGINT. Four owned Workers subsequently exited; tc original
and restored qdisc agree, cleanup error is null, shutdown errors are empty.
No Ollama server or unrelated process was killed/restarted; no evidence was deleted.

The interrupted trace has 195 events, four Manager inputs, eight specialist
inputs, six completed normal-stop physical inferences (1577.898 s service work).
It ends at `logical.verification.input`, 11:19:43.483535 UTC, before the stop
record; there is no terminal answer or evaluator outcome. All 41 expected initial
and produced artifacts remain present; stored blob sizes/hashes and trace parent
chain pass. Artifact bodies were checked remotely, not transferred through the PC.

Cancellation bypassed the runner's normal `except Exception` finalization: no
normal `result.json`, summary or `run.end` was emitted. Preserve the original
trace unchanged and save an explicitly typed **external** `hard-stop-result.json`,
not a manufactured benchmark result or semantic failure. Completed inference
counts are six, not seven: the seventh model outcome was a context rejection.

The backend completion window contains exactly six HTTP-200 requests matching
those six inferences. Durable `private/hard-stop-backend-request-audit.json`,
SHA-256 `99b5fb95081f789ef219873e3ac30949b156b05ac7d4401a04852186956b8693`.
There is no observed timeout/retry/billing failure in this final attempt;
successful physical execution does not negate the isolation breach.

## Durable evidence

Remote root: `/home/super/xiaoming/predecision-crossbenchmark-v1-5dafc43`.

| Artifact | SHA-256 / scope |
| --- | --- |
| `specialist-profile-leakage-crosscell-audit-002.json` | `875a07016c530e67a330461f39c141c0e9484ca44b69cba3bcb7d1f43b0f4276`; all 39 traces |
| `audit-progress-005.json` | `9c66695abe6978291ace75c81fdf931fa3f3df6e29e09ebd4c4c5b9bed55e135`; 26 completed attempts, 21 effective cells |
| `specialist-profile-leakage-hard-stop-001.json` | Detection, exact process ownership and signals |
| `evidence/video-mme-795-2-slow-aware/primary/hard-stop-result.json` | `8696b99bc5809e40bf7244d6a01d6a19ee8302043275ecb4a5c19c735dd4402c`; external interrupted-run record |
| Same attempt's `private/hard-stop-artifact-and-cleanup-audit.json` | All four owned Workers inactive, tc restored, 41 expected artifacts preserved |
| `execution-source-integrity-audit-002.json` | `0fbd3acb191b81ab1200101c6b381c6198e8d3ac1b49a5ff94b46d3866aa8595`; 141 tracked source/scripts per node equal execution freeze |
| `hard-stop-original-evidence-preservation-audit-001.json` | `10dea09412243641234778a232aec90cde93cbb53baa716832668fcad3cdba74`; all 156 originally hashed files for 26 new completed attempts unchanged |
| `hard-stop-existing-multihop-evidence-preservation-audit-001.json` | `ee33a8bf0d37c0c52496d20a40ba4cfa1d7c381f3a74175ebe858de222a84784`; all 72 originally hashed files for twelve MultiHop runs unchanged |

Append-only incident sidecars invalidate the two newly affected completed cells
in the derived ledger. Original results, traces and old audit snapshots are not
rewritten. The existing MultiHop defect is recorded in the new retrospective
audit without changing its historical evidence.

## Claim boundary and next authorization

The [requirement-by-requirement completion audit](predecision-crossbenchmark-completion-audit-v1.md)
records which requirements are proved, contradicted or still unmet; it does not
claim that the 24-clean-cell objective was achieved.

The unchanged execution code still passes full pytest (459 tests), Ruff and strict
Pyright. Those checks did not cover this recipient-level tool-result isolation
invariant and do not certify experimental privacy. No green test result overrides
the live trace evidence.

Academic and the unaffected Video comparisons can still be described individually.
Financial/News Fast-Aware and the affected MultiHop repetitions cannot support
clean comparative claims. No complete cross-benchmark Raw-Aware conclusion,
stable infrastructure effect or cost-guided method is established by this stop.

Stop under the objective's explicit privacy hard-stop; do not automatically repair
and resume. The next decision requires review of a minimal recipient-aware
tool-result isolation fix, regression coverage, a new freeze and the appropriate
affected-run scope. Existing MultiHop reruns remain prohibited absent new authority.
