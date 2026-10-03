# Cost-guidance exploration v1: intake and progress ledger

Status: work in progress, 2026-10-04 (Asia/Hong_Kong).
Branch: `cost-guidance-exploration-v1`, starting at `02518c7`.
This document records the new authorized exploration, not a completed method.

## Original scope and gates

Literature review -> method-space mapping -> prototype -> exploratory execution
-> failure analysis -> versioned generic refinement. The question is which
infrastructure/cost/consequence feedback helps an open-ended Agent make useful,
explainable cost-rational semantic decisions, not how to force Aware to win.

- Read all 21 specified original papers before method selection/implementation.
- Produce the literature map and novelty collision audit; distinguish verified
  facts from inference, inaccessible sources and unknown details.
- Design at least four routes. Prioritize spent-only Ledger and action-specific
  Cost Card / Quote-before-Commit; multicandidate and distilled heuristics are
  conditional later routes, not required additions to the executable primitive set.
- Cover existing MultiHop, LongBench and Video workloads; consider both Academic
  and Financial if affordable. Fast/Slow, n=1 per variant/task/regime.
- Maximum 36 substantive exploratory cells, including affected experimental
  reruns. No task-specific strategy, gold/private evaluation in cost estimation,
  silent repair, automatic truncation, or correctness predictions.
- Preserve model/tool/task/evaluator/scheduler/budget contracts; historical
  clean references are preferred to new controls. Explain any comparability gap.
- Quotes must not execute actions, infer with models, or materialize outputs.
  Unknown estimates stay unknown; report support and uncertainty.
- Assess actual versus predicted transfer/context/service consequences and
  cloud/control overhead, not just bytes or end-to-end speed.
- Preserve all failures and original evidence. Generic bugs require regression
  tests, full pytest/Ruff/strict Pyright, and separately identified affected reruns.
- Commit and push this independent branch; do not merge main.

Authorized stop conditions: cross-workload promising route(s), useful negative
results for simple routes, demonstrated major literature collision requiring a
new problem definition, persistent operational blocker, or the 36-cell cap.
Even at a stop condition, final documents and a bounded evidence-based ranking
are required; an abstract overlap is not proof of a major collision.

## Baseline evidence, not a new experiment

Project status and the eight requested storyline/family/audit reports were read
before method design. Their historical stop instructions are superseded by the
new exploration authorization; their empirical evidence is not rewritten.

The latest audited block contains 24 effective outcomes: 23 evaluator completions
and one valid no-answer Manager-budget failure. Historical MultiHop has nine
eligible runs of twelve; three leaked specialist-profile runs are excluded.
Use only admitted clean traces for service/transfer estimation. Do not pool
incompatible benchmark quality metrics or call the MultiHop block balanced n=3.

Frozen execution revision is `3c3bd95`; final reports revision is `02518c7`.
Raw-Aware quality-cost outcomes are mixed and n=1. They do not prove stable,
causal superiority or universal inadequacy of raw visibility. All completed
physical inferences selected A28; there is no observed model-device reversal.

Datasets and artifact bodies must remain on the 4090/Workers. The development
PC receives only bounded metadata. Existing evidence roots are not cleared.

## Current execution ledger

| Activity | Count / status |
| --- | --- |
| New substantive exploratory cells | 0 / 36 |
| New Planner/model inference calls for exploration | 0 |
| New Worker processes / tc shaping | 0 |
| Implemented variants | Ledger-only-v0 SDK adapter; synthetic contract tests only; no live cell |
| Historical Raw-Aware baseline reruns | 0 |

## Required final outputs

- `docs/method-literature-map-v1.md`
- `docs/method-novelty-collision-v1.md`
- `docs/cost-guidance-free-exploration-v1.md`
- `docs/next-method-recommendation-v1.md`
- `docs/cost-guidance-prototype-audit-v1.md` if prototypes are implemented

The final recommendation must answer Q1-Q10 in the original request and rank
routes by evidence, failures, literature overlap, complexity, novelty risk and
paper value. No winner is chosen at this intake checkpoint.

## Verified reading progress, 2026-10-04

Entries 1-21 now have original-body findings, with explicit residual visual or
published-version gaps in the reading ledger. The specified-original reading
gate is satisfied; this does not establish novelty or experimental success.
CostBench and Budget-Aware
reference/table gaps were closed. LLMCompiler/Flow/AFlow embedded prompts and
DynTaskMAS's full published paper were read, with representative visual checks.

Important corrections to simplistic related-work positioning:

- LLMCompiler already supports observation-driven replanning.
- Flow already changes semantic tasks/dependencies during execution.
- Murakkab is not physical-only: workload configuration can change enabled tasks.
- DynTaskMAS already combines dynamic task graphs with load/context-transfer
  feedback; absence of our exact quote interface is not proof of broad novelty.
- Budget Tracker includes strategy guidance; a spent-only Ledger is a narrower,
  explicitly attributed baseline rather than a reproduction of BATS.
- GPTSwarm already claims online graph improvement; MasRouter jointly selects
  collaboration/roles/models under quality-cost feedback. Neither is evidence
  that our distributed action-consequence interface is already demonstrated.
- ADAS searches whole agent code with validation before deployment; the read
  paper's primary objective is performance, not cost. Palimpzest executes sentinel
  samples rather than merely quoting. DocETL already rewrites semantic pipelines,
  but can substantially increase model/validation cost to improve accuracy.

Meta-tools, RouteLLM and the specified 2023 FrugalGPT original are fully read,
including appendices/references and representative visual checks. Meta-tools
has model-dependent latency/quality regressions; routing/cascade work does not
establish open-ended infrastructure-conditioned semantic evolution. Their
control/learning expense is relevant, not a reason to import quality oracles.

The complete AQP survey was located on its author's site, rather than replacing
it with a two-page tutorial: all70 physical / 140 printed pages are read.
Figure3.3 and Table8.1 were rendered and inspected. Specified original-body
coverage is complete; residual visual/version gaps are not silently closed.

AQP distinguishes response time from total work and
explicitly account for measurement/planning/actuation overhead. These concepts
are systems lineage, not novelty claims. They reinforce separately reporting
quote overhead, uncertainty and semantic quality rather than copying an
equivalence-preserving relational rewrite guarantee.

The novelty audit and five-route protocol are now written. Ledger-only-v0 is
implemented as a separate experimental adapter; original native source and all
historical manifests remain byte-for-byte unchanged. Full486 tests/Ruff/strict
Pyright pass at the prototype checkpoint. No candidate is declared effective
before actual cross-workload exploration. Quote/estimator and live runner
integration remain pending.

No exploratory cell, Planner call, Worker launch or shaping has been added.
Research-source PDF processing is read-only on the 4090; benchmark data remains
on its owning infrastructure. Small research page images only are copied for QA.
