# Cost-guidance exploration runner v1

2026-10-04. An isolated experimental controller, not a physical-substrate rewrite.
Primary scope:4 existing workloads × Fast/Slow × Ledger-only/Ledger+Quote =16
cells,n=1,no automatic retries/replacements. Method effectiveness is not established
by controller tests. Historical evidence remains immutable.

## Freeze and exposure

`scripts/cost_guidance_exploration_v1.py` imports the frozen benchmark adapters,
Worker config/start/stop helpers, tc transaction, original evaluator/runner,
privacy/observer/terminal audit and artifact persistence audit. It does not edit
those modules. Manager instructions, Qwen model, Blind Verifier, static32K/2048
contract,20/64/20 budgets and B0 scheduler remain unchanged.

The existing cross-benchmark protocol supplies exact Academic, Financial and
Video848-1 source IDs, document boundaries, video bytes and placement. MultiHop
uses the existing609-document/three nonsemantic-shard adaptation and the same
prospective canonical Yes/No serialization. Before execution, public bundle,
capability and placement hashes must match the historical admitted task records.
Neither quality nor answer is used to choose/admit a task or cost sample.

Only Manager receives the Ledger; C additionally receives anonymous quotes.
Both use `ProfileVisibility.BLIND`: no raw current H, concrete identity, physical
route, gold or evaluator-private metadata. Specialists execute their unchanged
Blind tools directly. Verifier remains Blind. The existing SDK on-model-start
provenance hook sees the actual post-filter input; no extra duplicate hook is
needed. A/C share pass-through Manager/specialist token/work accounting.

## Environment and control

All data access and execution are restricted to Linux under the4090-owned
`/home/super/xiaoming/cost-guidance-exploration-v1-*` namespace. Existing dataset
bodies and raw evidence do not transit the development PC. Source/config-only
deployment is allowed. Existing unrelated Workers/processes must not be stopped.

Fast100Mbps/configured5ms; Slow3Mbps/configured50ms. Reuse the existing tc
implementation and its Jetson HTB-without-netem limitation; do not describe
settings as measured symmetric RTT. Fixed cell order is Fast Ledger, Fast Quote,
Slow Ledger, Slow Quote per task. Fresh stores do not imply cold Ollama caches.

Each cell uses four unique, initially absent Worker roots/processes. Only those
owned processes are stopped. Network restoration executes in the existing tc
wrapper's finally path. Per-run configs, freezes, source/private evaluation,
before/after Worker state, PIDs, shutdown, tc attestation, result, JSONL trace,
summary and method/privacy/persistence audits remain on4090, append-only.

A Linux `flock` prevents concurrent experimental controllers from sharing these
ports/tc. A durable global cell-reservation journal counts primary and affected
revision runs against the36-cell cap. Failed/aborted reservations are not erased;
the cap is conservative. Re-entering an existing evidence cell refuses overwrite.
The controller does not implement automatic affected reruns; these require a
versioned generic repair and separately audited launch.

## Gates and interpretation

Original operational validation checks actual SDK inputs, observer probes,
terminal/evaluator behavior and typed failures. Method audit additionally checks
actual input hashes, exactly one fresh Manager Ledger, no Ledger/Quote in child
contexts, no cost feedback in Verifier contexts, reasoning-usage records, unique
quote IDs and run accounting. Actual retained artifact metadata is checked after
execution. Any confounder stops the queue, preserving evidence.

Wrong answers and legitimate stopping/budget failures are results, not reasons
for prompt tuning or replacement. Quote proposal/control-only turns do not invoke
Verifier; real observations use the frozen Verifier callback. Extra proposal and
commit turns consume the same20-turn reasoning horizon and their overhead must
be reported rather than hidden. Quotes never materialize or infer until explicit
commit. Unknown profiles stay unknown; the history is fixed, not updated from
evaluation outcomes or new cells during this initial matrix.

The SDK-native loop follows the [official Agents SDK running-agents contract](https://developers.openai.com/api/docs/guides/agents/running-agents).
No SDK upgrade or foundation-model substitution is made.

## Verification checkpoint

Full pytest536 passed; Ruff pass; strict Pyright0 errors/0 warnings;
`git diff --check` pass. Ten new controller contract tests cover16-cell/64-store
factorization, frozen tool space/placement/network/no-retry settings, remote-only
admission, real-input hash/Manager Ledger requirements, specialist/Verifier cost
isolation, historical representation/placement drift and durable36-cell cap.
These supplement the earlier real installed-SDK proposal/parallel commit/recovery/
specialist/terminal tests. No live cells are claimed by these tests.
