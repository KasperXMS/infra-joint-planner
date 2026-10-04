# Large-scale cost-guidance characterization v1

2026-10-05. Branch `large-scale-cost-guidance-v1`, derived from `420d196`.
Status: **prospective design; not an execution freeze; zero formal cells launched**.
Task identities, provider compatibility, monetary metering and runtime admission
must all be frozen before the queue can start. This document does not authorize
running an incomplete substitute for the requested study.

## Question and scope

Characterize Method × Planner × Workload × Infrastructure, rather than select
a winner or introduce a new optimizer. Preserve the SDK-native persistent
Manager, bounded specialists-as-tools, finite operators, ActionGateway, physical
scheduler, observer, benchmark adaptation and original private evaluators.
No formal DAG revival, RL, semantic coverage guard, new heuristic, prompt tuning,
task replacement, budget increase, third Planner or additional benchmark.

The ten requested research documents have been read in full. Latest B/D/E
evidence supersedes historical statements that those routes were untested.
Raw visibility has mixed outcomes, A is a low-overhead control, B/D adoption is
weak, C adds overhead, and E has an audited evidence-discard quality regression.
None is a validated winner. These facts do not permit mid-screening pruning.

## Control-plane models

Inspect the actual configured endpoint and credentials privately on 4090, then
freeze exact provider/model/request settings and test native SDK compatibility.
Never print keys or silently fall back to another model. The existing Alibaba
Beijing workspace endpoint returned HTTP 200 from `/models` on 2026-10-05 and
advertised **both `deepseek-v4-pro` and `qwen3.8-max`**. A model-list response is
not an inference/function-call compatibility proof.

Candidate model configuration, pending compatibility admission:

| Role | Exact identifier | Provider | Context | Thinking | Temperature | Client timeout / retries |
|---|---|---|---:|---|---|---|
| P1 Manager and specialists | `deepseek-v4-pro` | Alibaba Model Studio Beijing | 1,000,000 documented | disabled | provider default | 180 s / 0 |
| P2 Manager and specialists | `qwen3.8-max` | same existing workspace | 1,000,000 documented | disabled | provider default | 180 s / 0 |
| Verifier in every cell | `qwen3.8-max` | same existing workspace | same Qwen contract | disabled | 0 | 180 s / 0 |

Both listed models document function calling and structured output. Provider
parameters are injected using the existing request-body adapter; Manager,
specialist and Verifier instructions/schema/output handling remain unchanged.
SDK supports explicit per-agent model selection; current runtime already accepts
an independently constructed Blind Verifier. Compatibility must still be tested,
including tool-result continuation, before claiming the comparison is feasible.
[SDK model/provider contract](https://developers.openai.com/api/docs/guides/agents/models),
[Alibaba DeepSeek API](https://help.aliyun.com/zh/model-studio/deepseek-api),
[DeepSeek provider model](https://help.aliyun.com/zh/model-studio/deepseek-v4-pro),
[Qwen provider model](https://help.aliyun.com/zh/model-studio/qwen3-8-max).

If fixed Qwen Verifier cannot work with P1, stop: do not substitute a DeepSeek
Verifier and mislabel a control-plane-stack comparison as a Planner comparison.
Record request and response model identities to detect alias drift. Do not enable
provider search or substitute a snapshot identifier without an explicit freeze.

## Frozen physical substrate and shared horizon

A4/A5/A28/strong-4090, same inference servers and model/projector blobs,
`qwen3.8-27b-v1` deployment tag (artifact metadata `qwen35`, 27.3B, Q4_K_M).
The tag is not independent proof of an official release name. Context 32768,
reserved output ceiling 2048; service timeout 1200 s, backend retries 0, Worker
HTTP idle expiry 4 s. Keep modality/context preflight, real materialization,
worker-to-worker movement and locality-aware physical resolution unchanged.

All cells: 20 Manager turns, 64 physical tool/model calls, 20 Verifier calls;
8 specialist turns, 4 created / 2 active specialists. No added semantic recovery,
hidden finalizer, truncation, model substitution or task-specific strategy.
Answer provenance remains a successful terminal physical-model output followed
by deterministic contract extraction and original private evaluation.

## Tasks and independence

Select **all 18 distinct task identities before method outcomes**: six each
MultiHop-RAG, LongBench-v2, Video-MME. Family order/representative positions are
part of the task freeze; first two per family enter Phase I, other four Phase II.
Selection is based on workload strata, not observed correctness or latency.

- MultiHop: varied source/evidence counts, nonsemantic shard distribution, size,
  context pressure, comparison/temporal/inference patterns and retrieval difficulty;
  a majority should naturally require cross-source/shard support.
- LongBench: two/many documents, medium/very-long context, cross-document reasoning
  and local-evidence/globally-large inputs, varied original task patterns.
- Video: prefer six different original videos, short/medium/long, object/temporal/
  event questions and localized/dispersed evidence. Disclose any unavoidable shared
  video; do not label six questions as six independent videos.

Keep original task/question/options/data/gold/evaluator; document lossless text
partition reconstruction and provenance. Full original videos remain available;
Agent-generated frames/sheets are lossy runtime evidence, not equivalent sources.
Task-visible collection/partition schemas remain semantic; private supporting
annotations may inform offline strata only and never enter Agent context.

Reuse one independently distilled E rule set identically for both Planners,
frozen before the entire formal block. Its historical source task IDs must be
disjoint from **all 18** evaluation task IDs, not merely Phase I. Existing E used
Financial `66f7c780bb02136c067c35e8`, News `66faa8efbb02136c067c7357`, and Video
`795-3`; these cannot silently become new held-out evaluation tasks. Numeric
service history is separately frozen and never refit on formal outcomes.

`large-scale-task-selection-v1.md` and its remote manifest must record source
size/count, modality, duration/document count, artifact count, initial placement,
rationale, task/evaluator/source hashes, semantic schemas, distributed locality,
context pressure and candidate reduction ratio. Unknown values stay unknown.
No benchmark payloads, private annotations or raw traces through the local PC.
Any download, scan, preparation or distribution takes place on 4090/Workers.

## Seven methods and recipients

| ID | Root Manager feedback | Prospective interface |
|---|---|---|
| B0 | task + semantic state + static capabilities only | none |
| B1 | B0 + fresh anonymous raw profile before each reasoning call | no ledger/cards |
| A | measured spent-cost/budget ledger | no future costs |
| B | A | optional `estimate_<ready_action>`; direct execution allowed |
| C | A | mandatory propose → quote → commit/revise, diagnostic control |
| D | A plus existing quote protocol | ≤3 Agent-proposed ready actions compared; system never picks |
| E | B plus identical frozen cost-only advisory rules | optional, not forced |

Only root Manager receives method feedback. Specialists and Verifier are Blind
in every method. Scan full effective SDK recipient contexts, including accumulated
tool results, not only profile construction. No worker/deployment/IP/route, gold,
source_ref or evaluator-private metadata in logical context. Never expose predicted
E2E as an online objective. Unknown/unsupported profile values remain unknown.

Measure B eligible high-impact decisions/query attempts/valid cards/adoption;
C quotes/commit/revision/pending/quote-induced revision; D proposed candidate
counts/actual ≥2 comparisons/adoption/post-choice; E exact visible rules, without
claiming private internal use. Failure and repeated calls retain real costs.

## Phase design and cap

Phase I = 2 Planners × 3 families × 2 frozen tasks × 2 networks × 7 methods
= **168 cells**, n=1. No outcome-driven removal during screening.

Only after every nominal cell has a classified durable result and all confounders
are resolved: write screening/failure/pruning audits and freeze Phase II methods.
Pruning requires cross-Planner/workload evidence of non-use, dominant intrinsic
overhead without benefit, systematic quality/evidence loss, unexercised mechanism,
or diagnostic-only status; mean E2E alone is insufficient.

Phase II = 2 Planners × 3 families × 4 remaining tasks × 2 networks × m methods
= **48m** cells. Prefer retaining B0/B1/A plus justified candidates. With this
complete expansion, m=3/4/5 gives **312/360/408** total formal cells. m=6 would
give 456 and is prohibited by the **420** cap. Do not drop arbitrary candidates
just to finish: document evidence-based pruning and cap-constrained allocation
before Phase II. Do not prune based on the historical exploratory block alone.
Freeze Phase II method set, schedule and exact cap before launch; no new user
approval is required after the complete Phase I gate passes.

Pre-generate a deterministic, balanced block schedule using seed **20261005**.
Alternate Planner/network within blocks, rotate method assignments and family/task
order, save ordered cell/run IDs and schedule hash before results. Do not run all
DeepSeek, all Fast or all one method first. One nominal run per cell, no semantic
retry/replacement. Actual execution is serial because tc/models/ports are shared.

## Network, stores and operational attempts

Reuse Fast 100 Mbps/configured 5 ms and Slow 3 Mbps/configured 50 ms, existing
peer-port scoping and transactional tc attestation/restoration. Jetson HTB lacks
netem; 4090 uses HTB+netem. Configured delay is not measured symmetric RTT.
Cloud HTTPS/SSH stay unshaped. Keep source representation and initial placement
identical across all methods/Planners/networks for a task.

Every attempt has fresh empty stores and Worker processes, new run ID, pre-run
state/operator/deployment consistency checks, network receipt, complete trace,
result even on failure, post-run artifact/provenance/privacy audit and cleanup.
Fresh stores do not imply cold Ollama/model cache. Never clear history/global stores.
Separate fixed initial-placement bytes/time from Agent-induced movement.

Use a new `large-scale-cost-guidance-v1` evidence namespace and reservation ledger;
never reuse the previous 36-cell budget. Operational attempts remain append-only.
Only provider outage/reset, Worker crash, tc pre-run failure or unexpected external
service failure permit one identical operational replacement. Repeated same-class
failure stops the affected block. Count semantic cells once, retain every attempt
and its exclusion/admission reason; never recast a wrong answer as infrastructure.

## Monetary accounting and outcome analysis

Capture each Manager, specialist and Verifier API request/response usage, including
cached/reasoning tokens where available, timestamp, latency, provider/model and
error. Freeze dated, region/model-specific provider price sources and any supported
currency-conversion source. Preserve raw provider-currency cost as well as USD.
Missing usage/pricing/FX stays unknown, not zero. List-price estimate is not an
invoice claim; do not apply DeepSeek-direct pricing to Alibaba-hosted inference.
Metering must pass responses unchanged and never enter logical feedback for B0/B1.

Cost vector: API USD, Manager/specialist turns, Verifier calls, physical inferences,
tool calls, tokens, action transfer bytes/time, context rejects. Do not reduce it
to one weighted scalar. E2E is an external outcome, not an online optimization
target. Work counters can overlap and are not an additive E2E decomposition.

Report completion, canonical terminal validity and original evaluator separately.
Missing evaluation is unknown, never 0. Do not pool incompatible benchmark scores.
Compare quality-conditioned resource footprints; cheap/wrong is not success.
Keep per-task/family/Planner/method results and descriptive interaction tables.
n=1 is diversity, not statistical significance; do not run automatic repetitions.

After execution, private-only evidence audit distinguishes retrieved, preserved
after reduction and terminal-path evidence. Where annotations are reliable, report
retention = required evidence groups reaching terminal path / groups previously
retrieved. A zero denominator or unverifiable generated prose is unknown. Never
feed this annotation, score or hindsight analysis to Agent/rules/profile estimator.

## Failure, repair and hard stops

Classify primary/contributing causes: semantic reasoning, retrieval, evidence
selection, coverage loss, Verifier, stopping/over-expansion, context recovery,
budget exhaustion, provider, physical runtime, observer, serialization/evaluator,
privacy or mixed. Wrong answers, ignored cards, single-candidate D, slower Aware,
E evidence loss and excessive analysis are valid behavior, not automatically bugs.

Genuine bug: preserve attempt → diagnose → regression test → minimal generic fix
→ full tests → new patch freeze → affected-only rerun → audit. No semantic tuning.
Each freeze requires full pytest, Ruff, strict Pyright, git diff --check.
Separate protocol/implementation/results/audit/report commits; do not merge main.

Stop the entire queue for unresolved privacy, unverifiable dataset/evaluator
integrity, failed tc restoration, repeated persistent provider outage, unfixable
generic bug, unrecoverable model/config drift, unfair method comparison or cap.
Do not fill missing cells with alternate tasks/methods or invented values.

## Required deliverables and completion gate

Under `docs/`: task-selection, Phase I results, Phase I failure audit, method
screening/pruning, Phase II results, cross-Planner analysis, full failure audit,
final recommendation, all with `large-scale-...-v1.md` filenames from the request.
Root Chinese `LARGE-SCALE-COST-GUIDANCE-RESULTS-2026-10-XX.md`.
Every run retains commit/config/harness/price/task hashes, fresh-store roots,
network/deployment contract, JSONL trace/result/summary, graph evolution, recipient
inputs, method exposure/adoption and cleanup receipts remotely.

Answer Q1–Q10 on adoption, Planner specificity, H-dependent workflow changes,
quality-cost conflict, API/control overhead, reduction-friendly workloads,
communication versus model/API dominance, quality-preserving savings,
representation versus decision-policy failures and evidence for a future separate
workflow optimizer. Any architecture recommendation is **not implemented here**.
Stop after the frozen Phase II block and audit; no new method/model/benchmark/N.

## Readiness at this design revision

- Full requested research reading: complete.
- Existing endpoint model-list check: complete; exact identifiers advertised.
- New experiment branch: created; old evidence and code untouched.
- Fixed-Qwen/DeepSeek native tool compatibility: synthetic live chain admitted;
  original DeepSeek toy-format failure preserved separately. See
  [provider readiness](large-scale-provider-readiness-v1.md). Full native-method
  runtime integration/admission is still pending.
- Eighteen task identities/representations/placement: frozen remotely, with complete
  original sources and six distinct videos; task preparation audit has no findings.
  See [task selection](large-scale-task-selection-v1.md) for unknown original
  LongBench source counts and evidence-span proxies; do not invent those values.
- Historical E holdout mapping: actual rule-source labels/hash verified; all eighteen
  identities are disjoint, and the historical source video is also excluded.
- Regional alias prices, dated ECB FX and raw-provider monetary arithmetic are
  frozen and checked against the six existing synthetic responses; see
  [accounting readiness](large-scale-api-accounting-readiness-v1.md). Pass-through
  collection across every formal method/recipient remains pending admission.
- Deterministic schedule/Phase II guards: tested; actual 168-cell ordered schedule
  frozen with all eighteen task identities. Remote reservation/full recipient audit/
  runner integration: pending verification; no formal execution admission yet.
- Formal execution permission gate: **not passed; cells = 0**.
