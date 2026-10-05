# Resident-provider refusals: exact offline review

This is an admission/failure audit checkpoint, not a completed PhaseI analysis,
method-pruning decision or system workaround. No original attempt was rerun,
prompt-edited, input-censored or overwritten. The measured execution app and
fixed Blind Qwen Verifier remain frozen.

## Two different recipients, the same exact HTTP error

| Frozen cell | Condition | Failed recipient /request | Actual API outcome | Terminal/evaluator | E2E s | Known API USD subtotal /complete total |
| --- | --- | --- | --- | --- | ---: | --- |
| 29 | MultiHop1/P1/Fast/B1 | Manager #4 | HTTP400 `data_inspection_failed` | absent/unevaluated | 41.213 | 0.2193035584/unknown |
| 31 | MultiHop1/P1/Slow/B | Blind Verifier #5 | HTTP400 `data_inspection_failed` | absent/unevaluated | 92.020 | 0.1005979790/unknown |

Both use frozen task `multihop-rag-train-4b6de4acbde051fee1f727f3`, P1
`deepseek-v4-pro` Manager and fixed `qwen3.8-max` Verifier. The provider returned
the exact code/type `data_inspection_failed` and input-policy error text. Each
failed request/response is retained with file hashes. The triggering content is
not identified; no keyword, outage, balance exhaustion or method-induced policy
causality is inferred. These are **provider input-policy failures**, not semantic
wrong answers or replacement-eligible transient outages.

Cell29 had3successful Manager and3successful Verifier calls, then the failed
fourth Manager request. Cell31 had5successful Manager calls and4successful
Verifier calls, then the failed fifth Verifier request. Effective SDK context
audits covered all7and10requests respectively. Method/privacy gates reported
no other finding. Both cells independently passed5-instance resident-model
attestation and verified exit of all4owned Workers; tc/runtime gates had no
additional finding. Failed-call usage is unreported, never treated as0or a
complete invoice. Missing evaluation is never scored0.

## Execution and evidence preserved

Cell29's graph had12physical actions before the Manager refusal; no physical
model invocation occurred. Cell31 prepared17actions:6BM25,6filters,4reads and
1model action. The model action failed explicit context preflight, so it is not
an inference. Manager continued afterward; the terminal failure was the later
Verifier policy refusal, not that context rejection or a budget ceiling. Two
specialist function-call attempts were phase-restricted; no specialist actually
ran. None of these trajectory choices was automatically repaired.

Cell31 initial setup was7,696,522bytes/22.137s. Complete measured action artifact
transfer was0bytes/0s, complete tool work4.344s, backend model work0. These are
receipt scopes, not an E2E decomposition or a claim of zero cloud/context traffic.

Separate sidecars preserve both original rejected receipts:

| Cell | Original admission canonical SHA | Exact review canonical SHA | Original files bound |
| --- | --- | --- | ---: |
| 29 | `0c1f3a8c2e4d60fc91572b7690b90caf17b8d4e93722e89b69d2bd5c75ca68c7` | `ecd26e7453bcccc659d88812cc50eea47c18fa4aa456bea867d89cc060e5ad68` | 58 |
| 31 | `34236442f9c9fbf50a69d6006d344ef4d8b9304784d1d6c5692b7ef57608121b` | `6a3ead14c1050ec3048b50e23777b7290b80ce284ac878e3c3040a86f3c9860f` | 70 |

Cell29 lives under `resident-provider-policy-adjudications/<run-id>.json`; its
two-gate `control_plane_failed` case uses a new narrowly validated offline
review. Cell31 lives under `provider-policy-adjudications/<run-id>.json`; its
single-gate `logical_loop_failed` case uses the **unchanged existing** exact
provider-policy reviewer. All full run IDs/evidence remain on4090. Neither review
waives arbitrary errors, edits the journal, authorizes replacement or feeds
private information to any Agent. Both retained failures count as nominal
outcomes, not successful completions or resource-saving wins.

## Intervening valid semantic failure: cell30

MultiHop1/P2/Slow/A completed normally, returned a canonical terminal answer and
ran the original evaluator, score0.0. Manager4/Verifier4, physical4, actual model
inference1, no context rejection. Its physical sequence was aggregate, BM25,
BM25, model. Initial setup7,696,522bytes/21.811s; complete action transfer
5,204,596bytes/14.842s; complete tool work3.165s; backend model work226.595s;
E2E290.323s; frozen-list-price API USD0.0515664798.

This is a preserved valid semantic sample, not a runtime confounder or reason to
tune. Distinguishing retrieval/evidence-selection/model reasoning requires the
later private evidence-path audit; that primary semantic cause is not asserted
here. Lower API cost plus a wrong answer is not optimization success.

## Verified continuation, not a new execution freeze

Snapshot014 captured2026-10-05T19:29:29.906781Z:31nominal outcomes,0pending,
0unresolved confounders,4original findings with preserved reviews (JSON,
record-field and2policy),0operational replacements. Snapshot file SHA:
`1cde1ea8da47383ec0b6ae8f2135b5ac340a05dcb3f4ced6101bbd16d29cbcaf`.
Snapshot013 was refused because the journal advanced during collection; its
console is retained. Only the read-only collection was repeated, not any cell.

External control commit `3a5fb4a` reuses the unchanged single-gate reviewer,
binds both policy-sidecar namespaces and exposes their provenance offline.
1077full pytest passed (34.06s); Ruff/strictPyright/diff checks passed. Sources
were deployed only to `audit-tools/resident-policy-control-003`, never over the
frozen app or prior audit sources. Original cell29 proof/source binding remains
unchanged. Measured execution canonical SHA remains
`4090d46e5f3e7c3b25ae56355c830160c6688b1ca1c9e61ed5ca3ad93ba43e2c`.

New continuation control freeze004 canonical SHA:
`dbbc9d0a4752e31e07b0428cf911da3bcafccbf0d20b65c8f69a8af8e5bac6e4`;
file SHA `3dd0c4c400c6f7f27ef49ac14403cd56c2d97bbecb3c1a0e1105fdac8c628148`.
Queue005 PID1997584 and cell32atomic PID2003793 verified live19:29:49Z;
cell32is MultiHop1/P2/Fast/C. Re-read later process/journal state. Only never-started
scheduled cells continue; already-started31cells cannot be repeated. New
unresolved findings stop execution again.

The old42 remain closed/unpooled. Continue all168primary cells, then full private
evidence/recipient/failure/adoption audit before pruning. No PhaseII method set,
new method, architectural change, semantic tuning or pooled winner is authorized
by this checkpoint. The entire study and final Q1–Q10 reports remain unfinished.
