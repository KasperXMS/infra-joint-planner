# Multi-scale Planner preregistration v1

Frozen before benchmark inference on 2026-10-11, based on `70a75ae`.
The prior 18-cell pilot and its No-Go decisions remain historical observations.
This experiment neither resumes Phase II nor implements an Infra-aware Adapter.

## Finite execution

The [execution configuration](../configs/experiments/multiscale-planner-execution-v1.json)
preselects Qwen3.5 4B, 9B, the existing 27B deployment, and Ministral 3 3B.
Selection uses size, family and available memory before new benchmark scores.
There are no alternate candidates, parameter searches or score-based retries.
Downloads and earlier compatibility checks may overlap; inference remains sequential.

Each candidate receives one compatibility scenario set: complete native rendering
and token counting at 8K, 16K, 24K, 30K and overflow; a near-budget inference with
exact provider-usage comparison; and up to six native SDK turns covering calls,
strict schema validation, typed failure, continuation and terminal output.
Missing required fields are observable `schema_validation_failed` outcomes;
invalid actions cannot execute. Recovery uses the original turn budget.
Incorrect sentinel echoes measure recall ability; full rendering, exact token usage
and absence of truncation establish transport integrity. Recall errors alone do
not exclude a candidate. Only safety/context failures exclude affected candidates.

Screening uses frozen task indices 1, 3, 5: first MultiHop-RAG, LongBench-v2 and
Video-MME positions. Those exact no-Skills attempts carry into the six-task matrix;
indices 2, 4, 6 complete it. This avoids duplicate attempts and is explicitly **not
independent validation**. Every admitted candidate continues regardless of scores.
The new matched strong-cloud B0 runs all six tasks. Historical B0 remains descriptive.

The Skills ablation preselects 4B and 27B, conditional only on safety admission and
at least one schema-valid native call in compatibility or the no-Skills matrix.
It runs all six tasks once with the unchanged complete frozen Skills text.
No-Skills results supply the matched comparison; Skills token overhead is counted.
Maximum benchmark cells: 24 local plain + 6 B0 + 12 Skills = **42**.

## Fixed conditions and budgets

Manager-only substitution preserves the semantic prompt, operator schemas,
Specialist and Verifier (`qwen3.8-max`), evaluator, Physical Scheduler, physical
model pool and original execution budgets. Local Managers use 32,768 context,
2,048 output tokens, temperature 1 and top-p 0.95. Qwen thinking is disabled via
Ollama's standard `reasoning_effort:"none"`, mirrored as native `think:false` only
for render/count. No semantic `/nothink` prompt is appended. Provider-native parser
and template identities are pinned separately for each deployed model.

Each cell allows 72 control requests, 64 physical requests, 4,096 helper requests,
128 MiB control input, 3,600 seconds of execution and 1,260 seconds of cleanup.
The outer cell ceiling is 5,100 seconds; the complete finite run ceiling is
216,000 seconds. `STOP` is checked at request and cell boundaries; SDK retries are
zero. Compatibility allows at most eight inference and 512 helper requests per
candidate, with a 900-second deadline. Each official download has a 1,800-second
timeout; only three frozen artifact sets are requested.

A separate Ollama endpoint and model store on GPU1 hold at most one new Planner.
Only models owned by that endpoint may be unloaded. The existing 27B endpoint is
reused without changing its deployment or weights. All five Executor runners
must retain their identities, 32K contexts and idle boundaries. Independent
endpoint ownership does not imply GPU isolation: Planner and Executor contention
is part of the measured conditions. A minimum 2,048 MiB free GPU1 headroom is
checked after loading new Managers. Fresh Worker stores and ports isolate cells;
owned Workers must drain and exit, and traffic control must restore exactly.

## Interpretation and evidence

Schema failures, bad answers, provider/model errors and legal budget exhaustion
remain valid outcomes. Silent truncation, evaluator drift, historical/source drift,
resource boundary violations or failed cleanup stop the affected execution.
There is one attempt per model/task/Skills condition, with no selective reruns.

Private requests, outputs, task evidence, configurations and service logs remain
on the experiment machines. Exports contain numeric results, version identifiers
and opaque evidence hashes. Missing usage and GPU prices remain unknown; known
subtotals are labeled. Early failures are not treated as efficiency wins.
Results are descriptive for six previously examined tasks, with no significance,
noninferiority, held-out generalization or parameter-count-only causal claims.
