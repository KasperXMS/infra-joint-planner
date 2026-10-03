# Cost-guidance prototype audit v1

Date:2026-10-04. Branch:cost-guidance-exploration-v1.
Scope: **Ledger-only-v0 implemented; no live exploration yet**.
This is an intermediate implementation audit, not the full goal's completion.

## Files and mechanism

- `src/infra_joint/control/ledger.py`: immutable numeric snapshots, receipt
  idempotency, unknown coverage, separate tool/model counts and remaining budgets.
- `src/infra_joint/control/ledger_native.py`: isolated experimental subclass of
  the existing OpenAIAgentsNativeRuntime, per-run receipt gateway and composed
  SDK predecision input filter. No new physical primitive or scheduling rule.
- `tests/test_cost_ledger.py`: accountant cases and real SDK parallel native
  tool -> observation -> Manager continuation checks with a synthetic provider.
- `tests/test_native_predecision.py`: existing real-SDK specialist test also
  exercises Ledger-only; base Raw-Aware control remains.
- Literature/protocol documents: all21 original-body entries, collision audit,
  five candidate routes, cap and pre-experiment gates.

Only Manager receives a current spent-cost snapshot. A trace event distinguishes
Ledger-only from original Blind even though dynamic-profile visibility remains
BLIND. Specialists/Verifier do not receive Ledger or raw physical profiles.
Manager/specialist/Verifier instructions, tool schemas, models, budgets and
terminal-source validation remain unchanged; no cost-specific semantic prompt
or preferred first action is added in v0.

## Preserved freeze and implementation correction

The first implementation edited the native runtime directly. Full regression
correctly rejected it at the historical source-hash gate. Those owned edits
were reversed with a patch; **no historical manifest/hash was updated**. The
working implementation is the separate Ledger adapter. This is a development
correction, not an experimental rerun or a positive method result.

Original native source SHA-256 remains:
`b6112f2fda45add527e54a5924c9a5693a94f4439e37785846bafbca32a15985`.
Original isolation manifest remains:
`444db21f3d7aa0db13af993854e77318a29bddee1aee438f27d4a4f7c25affbf`.
No changes to worker/runtime/scheduler/operator/evaluator source, historical
configs, source data, evidence roots or model server state.

## Tested behavior

| Requirement | Evidence |
| --- | --- |
| Duplicate receipt does not double count | Identical replay; conflicting/mismatching IDs rejected |
| Parallel work is not E2E |200ms tool work vs50ms loop wall; non-additive flag |
| Preflight is not inference | Context refusal counts failed model, zero confirmed inference |
| Backend failure not falsely zero work | Inference/service uncertainty explicitly retained |
| Missing transfer telemetry not zero | Observed sum plus unknown receipts; complete total=null |
| Ready tools still parallel | Installed real SDK, two BM25 tools, barrier proves overlap |
| Fresh feedback reaches actual next Manager input | H0 zero receipts; next turn two successful tools; trace matches input |
| Specialist retains Blind semantic continuation | Actual accumulated SDK specialist inputs scanned |
| Verifier not given cost feedback | Verification contexts scanned; existing transitions unchanged |
| Physical/private identity removed | Snapshot contains numeric counters, not receipt output/locations/IDs |
| Original baseline path unchanged | Adapter absent in control test; historical freeze regression passes |

Costs exclude initial placement; `logical_loop_elapsed_ms` is not benchmark
E2E. Model-wrapper duration is not added to model-service work. Failed actions
without detailed runtime receipts retain unknown movement/work; this prototype
does not reconstruct absent backend telemetry or claim a complete failed-cost
total. Confirmed inference uses actual model telemetry; backend uncertainty
is separate, not silently counted as a successful inference.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest -q -o addopts='' --tb=short
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\python.exe -m pyright --pythonpath .venv\Scripts\python.exe
git diff --check
```

Full pytest:486 passed. Ruff:pass. Strict Pyright:0 errors/0 warnings.
Tests use deterministic provider doubles and real SDK dispatch, not cloud or
remote benchmark execution. Official SDK overview:
[Running agents](https://developers.openai.com/api/docs/guides/agents/running-agents).
Exact input-filter behavior was also checked in installed `agents/run_config.py`;
no SDK/package upgrade was performed.

## Remaining work

Freeze clean historical metadata for empirical service/transfer estimation;
implement Quote-before-Commit with no-execution, exact-action and ownership
checks; integrate a versioned live runner/manifest; verify fresh stores and
recipient isolation; then perform the bounded cross-workload exploration.
Current new substantive cells0/36; cloud/model calls0; Worker launches0; tc0.
No route ranking/effectiveness/novelty claim is promoted from these tests.
