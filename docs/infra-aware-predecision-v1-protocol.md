# Infra-Aware Pre-decision v1 — preregistration

Date: 2026-10-02. Implementation: `d533ece`; operational queue: `4709d7d`.
This is a new block, not replacement/scoring of the historical Reactive-Aware block.

## Frozen shared protocol

Task: `multihop-multisource`, original MultiHop query
`multihop-rag-train-9bae0079038050a37a1ae583`. Complete 609-document corpus, original
three non-semantic hash partitions and initial A4/A5/A28 placement. Original private
evaluator and gold are unchanged. No supporting evidence or gold enters planning.
Prospectively declared SHORT_TEXT terminal labels: exactly `Yes` or `No`.

Source hashes (checked on strong-4090, no local dataset transport):

- corpus: `20b61b5ab84de84a927420c5d265b7ec8d859ae49980699958a787ade9e4d28f`
- queries: `03cfb4926461f868684903aadc8024447bdda5bb3f6804741424cce338515bff`

Cloud Manager and Blind Verifier: `qwen3.8-max`, same provider endpoint, instructions,
non-thinking request option, no provider retries. Verifier temperature 0, required
function-tool transport, same semantic stopping/synthesis behavior.

Budgets: Manager 20; physical calls 64; Verifier 20; specialist turns 8;
created specialists 4; active specialists 2. Finite generic tool vocabulary and
physical locality-aware scheduler unchanged. A28 / strong-4090 physical Qwen3.8-27B
Q4_K_M Ollama, same model blob/tag/build, 32768 context / 2048 reserved output;
1200 s model-service client timeout. A4/A5 operator-only. No cost-guided mechanism.

Blind: task + static capability contract + semantic observations. No profile fetch.
PreDecisionAware: same plus existing anonymous `PhysicalProfileView` freshly fetched
through SDK input filter before every Manager model call, including turn 1.
Profiles expose no Worker/deployment/address/route identity. Verifier always Blind.
Profile schema remains `physical-profile-v1`; unavailable service estimates remain unknown.

Native loop and bounded specialists-as-tools remain the sole execution path.
No prior call, whole-plan DAG compiler, prompt tuning, model substitution or budget increase.

## Exact primary schedule

Fast: 100 Mbps + 5 ms added RTT. Slow: 3 Mbps + 50 ms added RTT.
Existing transactional tc mechanism/endpoints, including previously documented directional
netem support, are reused unchanged. Every cell gets fresh processes and an independent
artifact-store root. Fixed Worker ports are reused only after owned processes stop.

| Order | Replicate | Condition |
|---|---|---|
| 1 | r1 | Fast-Blind |
| 2 | r1 | Fast-Aware |
| 3 | r1 | Slow-Blind |
| 4 | r1 | Slow-Aware |
| 5 | r2 | Fast-Blind |
| 6 | r2 | Fast-Aware |
| 7 | r2 | Slow-Blind |
| 8 | r2 | Slow-Aware |
| 9 | r3 | Fast-Blind |
| 10 | r3 | Fast-Aware |
| 11 | r3 | Slow-Blind |
| 12 | r3 | Slow-Aware |

All 12 primary configs: `configs/experiments/infra-aware-predecision-v1-*-r*.yaml`.
Shared manifest: `configs/experiments/infra-aware-predecision-v1.yaml`.
n=1 per named cell; n=3 per condition. No semantic retries/replacements.

## Evidence and operational audit

Retain commit/config/component hashes, original private evaluator result, selected/effective
action arguments, model inputs and producer/reduction lineage, semantic SDK input provenance,
exact sanitized Verifier context/verdict, graph evolution, physical selection/service/transfer
telemetry, action intervals, private observer diagnostics, pre-run empty Worker states,
Worker configs/PIDs/logs and tc attestation. Provider-private reasoning is not saved.

Queue runs only on strong-4090; source datasets are materialized/distributed from there.
After each cell inspect tc restore, privacy, initial stores, terminal/run events, input/profile
timing and probe/provider/runtime errors. Valid wrong answers, retrieval/selection/context
recovery failures, stopping/budget exhaustion and Aware underperformance continue the queue.
Operational incidents stop it for audit, not semantic tuning. No automatic replacements.

Confirmed implementation defects require diagnosis/regression/minimal fix/full tests/new patch
freeze, then affected-cell-only reruns with new IDs and original evidence preserved.
Explicit transient external failures permit one identical, separately labeled replacement;
repeated same-class external failure hard-stops the block. tc cleanup/privacy failures hard-stop.

## Analysis and stopping

Audit failed/score-zero runs, latency/traffic outliers and unusual workflow signatures with
supporting trace IDs/confidence. Distinguish evidence existence/retrieval/preservation/selection,
Verifier knowledge, actual pre-decision Ht, observer incidents, model-service work and terminal
serialization. Do not treat valid semantic failures as engineering defects.

Report run-level and condition mean/median completion/original score/E2E/bytes/transfers/
physical model work/cloud work/tool calls/turns/concurrency/graph and first-action distribution.
Compare historical Reactive-Aware descriptively only; do not pool statistics or rewrite scores.
The hypothesis of stable Slow-local-first / Fast-movement is not an acceptance requirement.
If unsupported, report it and stop; do not implement marginal-cost guidance in this goal.

Tests before freeze: full pytest **412 passed**, Ruff passed, strict Pyright 0 errors/0 warnings.
The experiment result/failure audit will be separately committed to
`docs/infra-aware-predecision-qwen-v1.md` (and a failure-audit side report when needed).
