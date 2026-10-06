# Resident checkpoint147: malformed native specialist arguments

2026-10-06. This is the resident/diverse-pool block, not a restart or pooling of
the predecessor42. Cell `phase1-multihop_rag-2-2d3129ed85c03f62-p1-slow-A`,
attempt1, retains its original result, trace, admission and journal settlement.

## Exact failure and admission

The last DeepSeek Manager response was HTTP200, finish_reason `tool_calls`,
and contained three `consult_specialist` calls. Each405-byte argument string
was malformed JSON, rejected at line1/column92. The actual supplied schema
exactly matches the frozen strict `SpecialistRequest` schema. Replaying the
actual raw argument validation reproduces the terminal SDK `UserError`.
There is no provider outage, missing operator or mismatched specialist schema.

Primary cause: **workflow composition / malformed native tool-call JSON**.
Context, readiness and phase-restricted actions also occurred earlier, but the
run did not exhaust its budget. No specialist was allocated for the malformed
calls. This is a valid nominal failure, not a successful completion and not an
infra optimization benefit. No replacement or semantic retry is authorized.

The frozen SDK specialist parser aborts on malformed JSON rather than returning
a typed observation to the Manager. This is an explicit recovery limitation of
the measured harness. It has not been repaired, hidden or tuned for this cell.
The original confounder settlement remains immutable; an independently
reproducible sidecar supplies the effective admission only.

## Measured outcome

| Metric | Observed |
|---|---:|
| Execution completed | false |
| Answer / evaluator / format | absent / not invoked / unknown |
| Manager / Verifier calls | 10 / 9 |
| Created specialists | 0 |
| Physical actions | 12 |
| Tool actions / model attempts | 10 / 2 |
| Actually reached model inference | 0 |
| Model context rejections | 2 |
| Action graph | 12 nodes / 15 edges / 37 snapshots |
| E2E | 144.506543s |
| Complete action transfers | 66,763bytes / 1.115055s |
| Fixed initial placement | 7,696,522bytes / 22.234922s |
| Operator work / model service work | 1.866435s / 0s |
| Manager / Verifier service work | 86.163857s / 31.579553s |
| Frozen list-price API estimate | USD0.170260127028 |

The 10 tools comprise3BM25,3filter_records,3select_fields and1aggregate.
Zero model service work is justified by two pre-inference context rejections,
not imputed from missing usage. All19 actual SDK recipient contexts were
audited. Four empty Worker stores, exited Workers, five unchanged resident
model runners and successful tc cleanup were verified. Setup traffic is not
Agent-controlled traffic; overlapping work metrics must not be summed as E2E.
Missing evaluation remains unknown, never score0.

## Source and evidence binding

Measured execution remains004, revision
`0ff0e9b6d0799bd62e725a76b157e64cd9df5ccd`, canonical freeze
`16453c240789388fc54c1319334ddbfeca2f0878308b85e643afc2d6d509799c`.
No Agent, prompt, budget, schema, Worker, model, scheduler or tc behavior changed.

The actual4090 venv links SDK site-packages to a shared installation. External
audit code now binds the SDK's lexical import path, resolved shared target and
content hash, separately from the strictly root-owned native source. General
owned-file restrictions on evidence and native code remain intact. This fixes
an offline proof-path assumption, not the SDK parser or measured run.

The metadata collector also has a deterministic dependency closure: importing
an unrelated audit/gate module cannot change snapshot identity. Historical
collectors and their snapshots remain untouched. No private supporting-evidence
body audit or PhaseII pruning has been performed at this checkpoint.

Remote root: `/home/super/xiaoming/large-scale-cost-guidance-resident-v1`.
Evidence bodies and all API arguments/responses remain remote.

| Append-only receipt | File SHA256 |
|---|---|
| `analysis/resident-source004-cell147-native-specialist-json-diagnosis-001.json` | `81b59b055a7927075ae482be338845d8d0b58a5ff6c3485600f6afee47debdba` |
| `analysis/resident-source004-cell147-sdk-json-cost-audit-001.json` | `9649fb4847ef805b7ef80af411665f281da1cf47003bec26b16c4a9ed23d8ae6` |
| Native specialist admission sidecar | `d240e209996860e13fefa34c24f8ceab862c623bc91d8875e8da01bcd7223acc` |
| `queue-control-freeze-021.json` | `c983bc145764b49a8a4850d4728e7e50bbfb2025ae57a4a0bbb1845acdab00ad` |
| SDK audit002 actual Linux validation | `cc2cd20bd38915d8cd4f0d092c90b205f56c2b4cf8230024e83871a5ee3ef0c1` |
| Current coverage snapshot050 | `928e4855481aae28dbbdbe10f9228abdcf2ce24d33e1853dc9060c8091ef3d2c` |

External implementation commits: `411c7d8`, `f56ebce`. Full local regression:
1602passed,7directory-symlink tests skipped on Windows; Ruff, explicit-venv
strict Pyright and diff checks pass. The actual Linux suite passed57tests in
1.51s, including all seven shared-SDK regressions. Actual execution004 read-only
preflight and collector import-order stability passed, with unchanged journal,
zero Planner calls, zero model inferences, zero Worker starts and zero tc writes
during validation.

Snapshot050 independently confirms147valid nominal cells,166preserved attempts
and0pending. Eighteen historical confounded attempts and one operationally
excluded attempt remain separate. Valid here includes the audited model
failure147; it does not mean147successful completions. The remaining21nominal
cells retain their original balanced schedule.

Continuation021 is frozen, but a freeze alone is not a running queue. Verify
the owned process, exact child provenance and new atomic reservation before
claiming dispatch. Continue only the original unexecuted nominal cells; do not
rerun147, pool the old42, prune before all168 audits or start PhaseII early.
