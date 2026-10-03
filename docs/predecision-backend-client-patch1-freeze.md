# Backend-client patch 1: execution freeze

Scope: genuine transport / experiment-admission defects only. No new method,
semantic tuning, model change or benchmark expansion.

## Incident and preserved evidence

795-2 Fast-Blind primary under `d43c3b3` contains one pending logical model action
but three Ollama requests: first two HTTP 500 at 600 s, third started by SDK retry.
The outer 1200 s request fails, SDK wraps it as UserError, no evaluator runs.
This is a system confounder, not valid semantic failure. Preserve the attempt,
append-only incident sidecars, server logs and all 20 earlier effective cells.

The audit-held suffix controller was terminated without resuming any later cell.
The atomic driver wrote result/trace/summary and restored tc; A28's owned Worker
needed a second shutdown signal to cancel its lingering SDK request. No Ollama
server, model tag, dataset or old evidence was deleted/restarted/overwritten.

## Minimal changes

- Implementation `3c3d3c8`: explicit backend retries=0; formal Worker config
  propagates the existing declared service read timeout=1200 s. Legacy non-formal
  default remains 600 s; connect5/write600/pool600 unchanged.
- Append-only run-bound external incident sidecars affect derived eligibility,
  never original historical validation/result files.
- Pre-run admission amendment `a5d1e80`: SDK exception wrapping cannot hide typed
  physical failures; unknown typed execution failures require audit. The five
  already-understood semantic/readiness/context failures remain admissible.
  Read-only audit includes explicitly named backend patch attempts.

Manager/Verifier prompts and qwen3.8-max, native control plane, 20/64/20 budgets,
specialist bounds, 32K/2048 models, tools, capabilities, task representation,
initial placements, scheduler, observer, evaluator and tc/network definitions
remain unchanged. The Worker HTTP idle-expiry patch remains 4 s.

## Manifest and provenance

New manifests: `infra-aware-predecision-v1-backend-client-patch1.yaml` and
`predecision-crossbenchmark-v1-backend-client-patch1.yaml`. Harness SHA-256:
`d9694f8adf80b554bbb9277f844d3534c22d9e0681e5f13ecede1784ae03b16e`.
Final deployed execution revision is recorded in its new `protocol-freeze.json`.
Earlier `66a6016` staging has diagnostics/protocol metadata only, **zero cells**;
do not mistake it for the final execution revision after the admission amendment.

Source packaging explicitly allowlists source/scripts/configs/tests and build
metadata, excluding historical results/evidence/datasets. No benchmark bodies
are routed through the development PC. All six frozen task/source/capability/
placement records must exactly match the original protocol before launch.

## Verification and run authorization

Old-policy regression: three actual requests for one simulated 500, timeout or
disconnect. New policy: one request, original typed error reaches caller.
Wrapped physical / unknown failure gate regressions fail against the old gate
and pass after the amendment. Full **459 pytest passed**, Ruff passed, strict
Pyright **0 errors / 0 warnings**.

Production constructor diagnostics on 4090 confirm both deployed model backends
use retry0/read1200/connect5/write600/pool600, 32768/2048, with no inference call.
Rerun only 795-2 Fast-Blind with fresh stores/new run ID and named
`backend-client-patch-1`; require clean audit, then exact remaining three cells
FA/SB/SA in frozen order. Do not rerun earlier tasks, replace semantic failures,
resume the old controller, increase the 1200 s limit or tune prompts.
