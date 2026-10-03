# Cost-guidance prototype audit v1

Date:2026-10-04. Branch:cost-guidance-exploration-v1.
Scope: **Ledger-only-v0, empirical profiles, ready-action consequences and
SDK-native Quote-before-Commit-v0 implemented;16 live exploratory cells audited**.
Earlier implementation checkpoints below are historical. Current live results and
limitations:[final results](cost-guidance-final-results-v1.md).

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

## Historical implementation checkpoint

Clean historical metadata is now frozen on4090:33 eligible runs,62 model/255
operator/245 transfer samples, all198 source evidence hashes checked. Internal
deployment/directional-surface keys prevent A28/4090 or route pooling. Numeric
consequence cards preserve unsupported unknowns and perform no execution; see
[estimator and freeze audit](cost-history-estimator-v0.md). This is support
coverage, not estimator accuracy or observed method benefit.

SDK-native Quote/Commit is now implemented in isolated modules, with exact action,
ownership/single-use/staleness guards, Blind specialist/Verifier isolation and
shared A/C usage accounting. See [quote audit](quote-before-commit-v0-audit.md).
Eleven new protocol/real-SDK tests pass; no live positive result is claimed.

Integrate a versioned live runner/manifest; verify fresh stores and
recipient isolation; then perform the bounded cross-workload exploration.
Latest full verification:526 pytest passed, Ruff passed, strictPyright0 errors/0
warnings. The original native source and isolation manifest hashes are unchanged.
Current new substantive cells0/36; cloud/model calls0; Worker launches0; tc0.
No route ranking/effectiveness/novelty claim is promoted from these tests.

## Final implementation and execution audit

The versioned live runner/manifests,fresh store/process controller,tc attestation,
durable36-cell reservation guard and no-overwrite resumer are implemented.16 cells
use unchanged47fbe3b cell execution;analysis-only updates do not alter completed
evidence or trigger substantive reruns. All16 complete/evaluate;one original gate
stop is independently adjudicated recovered Agent schema misuse,not an auto-repair.

Additional read-only tooling:actual-input quote visibility/model-evidence analyzer,
private owning-node MultiHop document-coverage scanner and whole-matrix admission/
freeze/trace auditor. Private scanner is postqueue only;remote node helper imports
are lazy/stdlib-only. No model/evaluator invocation is performed by these audits.
Source helper updates on stopped Workers do not change the frozen execution path.

Final matrix evidence:16 cells,64 distinct initially empty stores,zero audit findings;
all49 quotes visible;36 successful quoted actions,one committed preflight refusal.
Worker shutdown/tc restoration/source parity/pass-through telemetry/isolation are
checked across every cell. No failed answer is replaced or counted as quality success.
Actual model-service prediction support remains partial;future outputs/queue/cache
remain unknown. The prototype does not estimate answer correctness.

Latest full verification before final documentation:556 pytest passed,Ruff pass,
strict Pyright0 errors/0 warnings. The documented Python virtualenv command is
required;an unrelated standalone pyright interpreter's missing-package reports are
not project failures. Final rerun results are recorded in the completion audit.
Native source and historical isolation manifest hashes above remain unchanged.
See [route ranking](next-method-recommendation-v1.md);no tested method is promoted.
