# Blind baseline semantic competence cleanup v1

## Frozen contract

Each of the six original tasks received exactly one Cloud Blind Planner call. Five valid G0 plans were executed once in the accepted clean attempt under the original benchmark/evaluator contracts, native networking, fixed model/operator pool, and B0 scheduler. The LongBench multi-document G0 failed context validation before execution and was not retried.

One resource-blind replan was allowed only after all currently executable non-terminal evidence/model nodes had materialized. Completed nodes and artifacts were immutable and were not replayed. Model instances were exposed to both Planner and replanner only as `reasoner-alpha` and `reasoner-beta`.

Both deployments used the generic configured 1024-token output limit. Context preflight remained fail-closed, and every call retained output-token and finish-reason telemetry. All accepted model calls ended with `stop`; the largest materialized evidence-note output was 293 tokens. No critic, hidden summarization, memory, RL, task-specific rule, or infrastructure visibility was added.

Two predecessor attempts are preserved but excluded:

- Attempt 1 contained the forbidden field name `source_ref` in fixed replanner instructions. No private value leaked.
- Attempt 2 exposed physical deployment IDs instead of opaque model aliases.

Only those privacy boundaries were corrected. Frozen G0 plans, actions, model pool, benchmark inputs, and evaluator were unchanged. The accepted attempt used no retry or replacement.

## Outcomes

| Task | Replan | G0 -> Gfinal | Answer | Score | E2E ms | Transfer B / ms | Model calls | Finish reasons |
|---|---|---|---|---:|---:|---:|---:|---|
| video-long-payload | keep | `9b0c22bd` -> `9b0c22bd` | A | 1.0 | 90494.5 | 105968 / 563.8 | 2 | stop |
| video-cross-temporal | keep | `d64e60c1` -> `d64e60c1` | B | 0.0 | 79864.9 | 422142 / 74.1 | 1 | stop |
| longbench-multidoc | planning_failed | - | - | - | - | - | 0 | - |
| longbench-structured | keep | `cd612478` -> `cd612478` | D | 1.0 | 3852.0 | 294 / 13.1 | 1 | stop |
| multihop-multisource | keep | `ae47b236` -> `ae47b236` | Yes, both guides explicitly state they have "gathered and simplified" the best builds for Season 2 and link to more detailed external sources for complex information. | 0.0 | 99522.0 | 13919 / 129.1 | 3 | stop |
| multihop-reasoning | keep | `82c94efd` -> `82c94efd` | Will Smith and Jada Pinkett Smith | 1.0 | 5533.6 | 5915 / 36.3 | 1 | stop |

## Workflow revisions and telemetry

### video-long-payload

- Decision: `keep`; trigger: none; G0 unchanged.
- Reason: the materialized visual evidence note identified String, so the pending terminal path had sufficient consistent evidence.
- Model input/output/finish: `inspect-early-sheet=654/196/stop`, `final-answer=424/2/stop`.
- Replanner input/output/finish/wall-ms: `5529/75/stop/1176.5`.

### video-cross-temporal

- Decision: `keep`; trigger: none; G0 unchanged.
- Reason: the materialized full-timeline contact sheet was judged sufficient for the pending chapter-order model node.
- Model input/output/finish: `analyze-chapters=2248/2/stop`.
- Replanner input/output/finish/wall-ms: `7948/85/stop/1102.8`.

### longbench-multidoc

- Decision: `planning_failed`.
- Typed failure: `WorkflowPlanningError` - node `note-02` had `estimated_input=15468`, `reserved_output=1024`, and `context_window=16384`.
- The Planner saw these bounds. Validation failed before execution, and the one-shot plan was not retried or repaired.

### longbench-structured

- Decision: `keep`; trigger: none; G0 unchanged.
- Reason: the completed deterministic chain had filtered, derived, selected, and ranked the bounded evidence needed by the terminal node.
- Model input/output/finish: `final-answer=587/2/stop`.
- Replanner input/output/finish/wall-ms: `4933/85/stop/1052.3`.

### multihop-multisource

- Decision: `keep`; trigger: none; G0 unchanged.
- Reason: two materialized evidence notes were judged consistent and sufficient for final synthesis.
- Model input/output/finish: `barb-evidence=2416/271/stop`, `sorc-evidence=2375/293/stop`, `final-answer=850/33/stop`.
- Replanner input/output/finish/wall-ms: `7711/48/stop/829.8`.

### multihop-reasoning

- Decision: `keep`; trigger: none; G0 unchanged.
- Reason: all three non-semantic corpus partitions had materialized bounded BM25 evidence for the pending synthesis node.
- Model input/output/finish: `synthesize-answer=2744/9/stop`.
- Replanner input/output/finish/wall-ms: `6004/97/stop/1190.5`.

## Trace and privacy audit

Every accepted execution contains exactly one replanner checkpoint. Every workflow node has exactly one `workflow.node.start`, so no completed node was replayed. All five replanner decisions were `keep`, hence every G0 hash equals Gfinal.

Planner/replanner prompt scans found none of the private field names/values, network addresses, or real deployment IDs. The JSONL traces, result, audit, replanner request/completion, workflow versions, transfers, placements, operator/model latency, and evaluator result are retained for every executed task. The pre-execution LongBench failure is retained in the planner-attempt evidence.

## Freeze

The accepted evidence is under `results/blind-baseline-6task-semantic-cleanup-v1/clean-attempt3`; excluded predecessors are retained beside it. The final manifest is `freeze/blind-baseline-final.json` with status `frozen_no_further_semantic_tuning`.

This resource-blind semantic baseline is now frozen. No further semantic Planner tuning is authorized.
