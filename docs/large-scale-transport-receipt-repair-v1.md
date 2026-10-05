# Transport receipt audit and minimal repair

2026-10-05. **Queue stopped; 26 / 168 classified nominal cells.** No new
experimental attempt has been launched by this repair. Phase I remains incomplete;
there is no pruning, pooled accuracy, method ranking or Phase II authorization.

## Preserved affected attempt

Academic / DeepSeek V4 Pro / Slow / A, attempt1:
`large-scale-cost-guidance-v1-phase1-longbench_v2-1-233652563a5a9ff2-p1-slow-A-attempt1`.
Original execution94c9bac / execution-freeze-002 remains unchanged remotely.

| Measurement | Original evidence |
|---|---|
| Completion / format / original evaluator | completed / valid / score1.0 |
| Admission | confounder: typed_action_failure_requires_audit:physical_execution_failed |
| E2E | 1462.655675 s |
| Manager / specialist / Verifier turns | 10 / 15 / 10 |
| Created / peak-active specialists | 2 / 1 |
| Prepared tools / models | 33 / 10 |
| Successful tools | 28 |
| Model attempts | 5 context rejects; 3 returned inferences; 2 transport interruptions |
| Returned model service subtotal | 889.586659 s; complete total unknown |
| Returned physical input / output tokens | 9971 / 1892; interrupted-call usage unknown |
| Finish reasons for returned inferences | 3 stop |
| Initial placement | 514789 bytes / 1.563402 s |
| Successful action-transfer receipts | 94908 bytes / 1.237336 s; complete movement unknown |
| Cloud API calls / frozen-list-price estimate | 35 / USD0.823860918, not invoice cost |
| Action graph | 43 nodes / 41 information-flow edges; 130 status snapshots |

Two model actions start around2026-10-04T23:11:04Z and close around23:31:05Z,
roughly1200.6 s later. Their logical observation is exactly
`physical_execution_failed` / `unrecoverable physical execution error: ReadTimeout`.
The Agent continues naturally and reaches a correct terminal answer. The owned
queue parent1978333 and child1987511 are absent, not merely observation-timed-out.

Both interrupted actions have logical closure but **no physical.execution receipt**.
Do not classify the whole run as a wrong answer or promote score1 to valid cost
evidence. Neither failed inference/service time nor full movement can be recovered
from successful subtotals. Backend and Worker HTTP timeouts are both1200 s;
Worker log tail checks expose no ReadTimeout/OOM traceback. The precise inner
cause and failed-call inference status remain unproven. Do not attribute these
physical transport errors to cloud Planner failure.

Remote `analysis/transport-gate-audit-001.json` binds163 original evidence files;
all163 hashes are reverified without drift. Original receipt canonical SHA-256:
`f44b894dc8fde73774ce901192d94a2d8dfa353d695506563811fb1e49f1151a`.
Audit file SHA-256:
`2d6d05ce23d9500c3fe2213c4d55d2ed4ace9517391ede97b84a9414fd21d9cb`.
No original result, journal, admission, trace, artifact or prompt is edited.

## Two genuine measurement defects

1. The offline collector relied on `logical.model.outcome`. Interrupted actions
   lack that event as well as the physical receipt, so it falsely reported zero
   uncertain model outcomes and treated returned service subtotal as complete.
2. PhysicalExecutionService retains selection metadata only for its typed errors.
   Raw httpx transport exceptions escape; native runtime closes the logical node
   and rethrows, losing the already selected physical binding and action timing.

## Minimal repairs

- Offline commit3f95992 correlates prepared model actions, failed logical
  observations, model outcomes and physical receipts. Unknown failed inference
  work remains unknown; known context/preflight and selection-only failures do
  not invent inference. Duplicate observation/outcome evidence counts once.
- Transport repair commitfdefed6 attaches a physical-only receipt to the **same** httpx
  RequestError and rethrows it unchanged. It records frozen selection, action
  elapsed work, exception class and execution-stage failure. Native closure emits
  that receipt separately, retaining one logical observation and existing graph,
  batch completion, failure code/message and rethrow semantics.
- There is no retry, failover, model substitution, timeout extension, extra
  observer query or error-to-success conversion. Elapsed action work is not
  fabricated model-service latency. Request/exception text is not exported.
- Manager/specialist instructions, Manager input and terminal-source methods are
  AST-identical to94c9bac. Changed native methods only close/emit interrupted
  physical metadata. No prompt, budget, tool vocabulary, scheduler, evaluator or
  task change is made.
- The original historical harness manifests remain untouched and still reject
  a changed runtime. New local
  `infra-aware-predecision-v1-transport-receipts-patch2.yaml` explicitly pins the
  revised native/physical sources and the parent native source hash. Shared
  semantic/model/Verifier/tool/budget contracts are unchanged. This is **not** a
  deployed formal execution-freeze-003 or a queue-resume authorization.

## Verification and corrected remote snapshot

- Nine offline regressions cover missing receipts, interrupted/cancelled model
  actions, deduplication, no-inference preflight, selection-only errors, tool
  failures, privacy and missing outcomes.
- Nine transport regressions cover ReadTimeout/ConnectError/ReadError for model
  and tool actions, exception identity, one attempt, selection provenance,
  unknown inference, sanitized logical state, graph closure and no duplicate
  observation. Historical freeze regression checks old rejection and new pinning.
- Full pytest: **811 passed in20.33 s**. Ruff passes; strict Pyright0 errors /
  0 warnings; git diff --check passes. Before the explicit supplemental manifest
  was added, the full suite correctly rejected historical native-source drift;
  the strict validator was not weakened to bypass it.
- Source-only offline collectorv1-9 runs remotely, preserving older collectors.
  `analysis/settled-snapshot-023.json` verifies26 admitted /28 attempts /
  0 pending /2 effective confounders /5 original confounded attempts,
  2 JSON reviews /1 provider-policy review /0 operational exclusions.
- The affected row now reports **2 unmeasured failed model outcomes** and
  **2 missing model physical receipts**, with complete model-service total null.
  Its original successful service subtotal and evaluator outcome stay unchanged.

Snapshot023 file SHA-256:
`9ed65ee37e1acaf48ccc25719d0081365b6acba9c49e3886ad2b3351fba8e7ef`.
Collectorv1-9 source SHA-256:
`813b5b0269cedb97aa4f69fe2c4393cafdf0de9ba38293780f809642665ac84a`.

## Remaining gate

The formal remote app is still94c9bac and queue005 remains stopped. Preserve the
current failure, establish a new audited execution/control freeze and explicit
affected-cell repair provenance before any rerun or queue resumption. Do not
blanket-admit physical_execution_failed, retrofill failed measurements, replace
valid semantic failures or reinterpret successful completion as no runtime defect.
Complete all168 classified/audited Phase I cells before private evidence coverage
analysis, method pruning and the frozen Phase II expansion.
