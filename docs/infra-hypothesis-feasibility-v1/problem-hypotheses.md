# Frozen H1/H2 feasibility protocol

Frozen before any new model task run. Parent: `infra-evaluation-workload-v0.1` at `8c5bcce`. This study does not test H3 or implement a Planner/Adapter.

## Hypotheses and decisions

H1: Two quality-acceptable executions of the same original distributed task can use substantively different logical information-processing graphs and have different measured resource demands. A logical difference changes acquisition, selection, representation, retention, or downstream evidence dependencies; moving identical retrieval to a different machine alone is a physical control. One qualifying task supports feasibility only, not population prevalence.

H2: The controlled network state changes the relative resident-task E2E latency of quality-acceptable logical workflows materially and interpretably. A preference reversal is strong but optional evidence. Stable dominance, small/noisy differences, or service-state confounding are negative or inconclusive results. H3: An infrastructure-conditioned logical Planner improves quality-constrained efficiency beyond task-aware planning plus physical scheduling; H3 is reserved for later.

`L0` means visibility of measured infrastructure. `L1` means an interpretable logical choice changes with it. `L2` means that choice improves independently evaluated, quality-constrained performance over an appropriately matched infrastructure-blind choice. This phase can estimate potential L1 value; it cannot establish L2 Planner performance.

## Variables and cost boundary

For original task `x`, semantic state `s`, network state `h`, and workflow `G`, record native evaluator quality `Q(G,x,h)` and measured resident E2E latency `C(G,x,h)`. The primary objective is minimum resident-data task E2E latency subject to task success on the original evaluator. Completion and format validity are separate from success. Early failure is never a cost improvement. Report source-local time, model service/queue time, calls/tokens, application transfer bytes and time, controller overhead, setup/staging, known API USD, and unknown GPU cost separately. Overlapping intervals are not added to E2E.

Actively vary only the metered Worker data-path profile: `Hslow` nominal 3 Mbps plus 50 ms additional RTT, `Hfast` nominal 100 Mbps plus 5 ms. Measure achieved rates; prior 2.94/64.77 Mbps are references, not assumed rates. Hold task, source placement, operator, final model and prompt, evaluator, budgets and scheduler fixed. Record concurrent load, model revision, deployment identity, queue/service time, tokens, GPU utilization and observable cache state; unavailable telemetry is `unknown`.

H1 starts with one D2 MultiHop-RAG and one D2 text+table MultiModalQA Development task, each G0/G1 at Hfast (four cells maximum). Task IDs and workflows are frozen after P1 and before runs. If a task is invalid, replace it with the first remaining D2 Development task in the same family in the parent manifest order, recording the reason; never replace on wrong answer. A genuine pair requires both alternatives to pass original quality scoring, not just return plausible text. If no such pair exists, stop before H2.

For these single-answer Development cases, preregistered task success is a format-valid, completed original-evaluator score of exactly `1.0`; intermediate token overlap/F1 remains reported but is not called success. This strict threshold is identical for G0/G1 and both network profiles.

H2, conditional on P1 Go and H1 feasibility, is at most 2 tasks × 2 workflows × 2 profiles × 2 repetitions = 16 real task executions including qualifying H1 cells. Conditions are counterbalanced; outcomes are never selectively rerun. Compare directly paired costs and observed ranges before any retrospective oracle estimate. Equal profile weights are preregistered. The static quality-feasible set must pass across profiles; an infrastructure-conditioned oracle is only retrospective potential, subject to in-sample winner bias and planning overhead. If quality or serving-state controls fail, mark the value unidentified.

P1 requires an actual Controller runtime identity with no direct filesystem/mount/inherited-descriptor route to either source or private evaluator labels, and positive receipted, hashed remote reads over the metered path. If P1 fails, no H1/H2 live model runs occur. If H1 fails, no H2 expansion occurs. Historical results, benchmark semantics, gold, Skills, default model pool and Scheduler remain untouched.
