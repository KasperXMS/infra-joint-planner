# Harness v2 baseline requalification: frozen protocol

This branch evaluates the existing SDK-native Harness v2 under one unchanged
physical executor, scheduler, operator catalogue, specialist, verifier, task
evaluator and model pool. H1 uses the native SDK loop without the formal bridge.
H2 is a two-task, KEEP-only bridge feasibility check. Neither condition adds an
infrastructure-aware workflow adapter.

The controller-side Stage 0 receipt was written before formal model calls. It
attests the five resident Ollama deployments, actual 32K context, source
hashes, roles, frozen evaluator and task materialization, Worker isolation,
budgets, STOP and traffic control restoration. The local Planner is the
existing `qwen35-27b-resident-32k-v1` slot (digest prefix `9770c614`), whose
weight provenance was corrected in the prior multiscale study to
Qwen3.8-27B. This study retains that slot, its Q4_K_M weights, and the
existing cloud `qwen3.8-max` reference. The exact deployment attestation
remains on the experiment controller.

Stage 1 has six frozen tasks: positions 1 and 2 of MultiHop-RAG,
LongBench-v2 and Video-MME in the existing `task-freeze-002` manifest. Each
task runs local blind Planner twice and cloud blind Planner once, in that
order, for 18 formal cells. The network is 100 Mbps / 5 ms. Model errors,
invalid tool calls, incorrect answers and legal budget exhaustion count as
results. Only systemic integrity failures stop further cells.

Stage 1.5 uses the first frozen MultiHop-RAG and LongBench-v2 tasks for two
local H2 cells. The bridge records the actually proposed workflow,
dependencies, provenance and pending frontier. It may seal and KEEP a plan
after execution to test feasibility; it does not fabricate future actions or
claim that a post-run KEEP improved execution.

Stage 2 uses three previously studied anchors, frozen before its outcomes:

| Family | Source task ID |
| --- | --- |
| MultiHop-RAG | `multihop-rag-train-9bae0079038050a37a1ae583` |
| LongBench-v2 | `66f7c780bb02136c067c35e8` |
| Video-MME | `video_mme:795` |

For each anchor, each network (3 Mbps / 50 ms then 100 Mbps / 5 ms) and each
of two trials, Stage 2 runs H1 Blind, Raw Aware and Measured Ledger. The
method order rotates deterministically within each paired block, as frozen
in `harness_v2_stage2.py`; all 36 cells use the same local Planner and Worker
pool. Traffic control is applied once per network block, calibrated before
that block's first model call, and restored after it. Every cell has a fresh
Worker and artifact namespace. The formal bridge remains disabled.

Stage 3 is conditional. Its six-task selection rule is frozen in
`configs/experiments/harness-v2-heldout-selection-rule.json` before Stage 2
outcomes. Stage 3 runs only if Stage 2 shows a repeatable L2 logical workflow
change, paired measured-cost improvement, preserved evidence and acceptable
task quality. Otherwise the experiment stops with a No-Go decision. A Stage 3
run, if triggered, compares Blind with one selected method over six new
tasks, two network states and two trials (48 cells).

Raw prompts, traces, source assets and credentials stay on the controller.
Only source code, frozen public configuration, redacted receipts, aggregate
measurements and reports are committed. No cell is rerun because of its
score, schema validity or model failure.
