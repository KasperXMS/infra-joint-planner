# Resident Phase I checkpoint145: Blind field misuse, natural recovery

2026-10-06. `phase1-multihop_rag-2-2d3129ed85c03f62-p1-fast-B0`, original attempt1.
Reserved12:03:42.418902Z; conservative audit-gate settlement12:07:35.256716Z.
Queue018 stopped before dispatching another cell. The task itself completed,
terminal format valid, original MultiHop evaluator score1.0.

## Exact diagnosis, not a validation-error waiver

The root Manager submitted three BM25 actions with `text_field=text`, one per
initial corpus shard. The declared task schema uses string `body`. The unchanged
record reviewer checked actual metadata, content hashes and every record on its
owning device: all records have string `body`, none has `text`.

| Artifact | Records | Bytes | Owning node |
| --- | ---: | ---: | --- |
| full-corpus-shard-0001 | 1,030 | 2,772,674 | A4 |
| full-corpus-shard-0002 | 898 | 2,431,922 | A5 |
| full-corpus-shard-0003 | 919 | 2,491,926 | A28 |

All three exact receipts report `document field must be text: text`, execution
stage, matching action owner and real physical selection. The established root
input schema and initial-artifact ancestry were checked. This is ordinary legal
operator parameter misuse, not a missing artifact, schema drift or Worker defect.
No field alias, hint, hidden repair, prompt change or nominal retry was applied.
The Manager naturally continued and recovered within the same run.

## Actual footprint

| Metric | Actual value |
| --- | --- |
| Manager / specialist / Verifier calls | 7 / 0 / 7 |
| Prepared actions | 11:9 BM25,2 model attempts |
| Actual model inference | 1, resident A28 Qwen3.5-27B |
| Model input / output tokens | 7,074 / 3 |
| Failed observations | 3 absent-field,3 semantic validation,1 phase,1 context |
| E2E | 194.679s |
| Fixed initial distribution | 7,696,522bytes / 0.961s |
| Recorded action-transfer subtotal | 18,058bytes / 0.062s |
| Model service / successful tool work | 123.232s / 2.113s |
| Manager / Verifier work | 46.594s / 21.669s; non-additive wall-time work |
| Frozen API list-price estimate | USD0.109309028820; all14 calls known |
| Graph snapshots / nodes / edges | 34 / 11 / 6 |
| Maximum concurrent actions / measured overlap | 3 / 1.195s |

The context-rejected model attempt did not reach inference. Successful tool work
does not include failed-tool work, and recorded action bytes are not independently
proved complete traffic. Score1 alone does not establish evidence retention.
Full private semantic/failure/recipient/adoption audit remains required after168.

## Preserved original and exact source-bound sidecar

Original admission was independently reconstructed exactly. Its conservative
`confounder` disposition and original journal settlement are retained. An append-
only sidecar, reproduced by the unchanged source-bound reviewer, admits the
original attempt as valid in the effective ledger. No result or trace rewriting.
All14 actual SDK contexts, four empty starting stores, Worker exit, five model
residency and tc cleanup passed. Bodies stayed on4090/owning edges; only shape,
hash and bounded telemetry reached the development workspace.

Remote root: `/home/super/xiaoming/large-scale-cost-guidance-resident-v1`.

- Reservation SHA256: `af00c10cd5e26468701c262f52f7332e5636f39d3f0b7b9b648d7f7c63c76935`.
- Original settlement SHA256: `a068e19ac4480ebac27d0874544f263d756b567f020971ab68dc9d6b0611aa3f`.
- Original admission file SHA256: `6032480f70a41ed45dbe6bdd6f804fbb24adb91570bf33e8117e40a62522f18b`.
- Original admission canonical SHA256: `e7e1cee575216e04e347d2ed4fc03e09faaf06a392ad6daac184f93231173fe5`.
- Sidecar in `source-bound-record-field-adjudications`, SHA256:
  `0beb9d71b6c71371f683bcc2e7e6680319cb3bf0f8641f65ed7544e82a2e9735`.
- Reviewed admission canonical SHA256: `efbcaef49a04c37814fa2f6c2cc47217aa12f0dfa7f24ec4cd29591b4925624a`.
- Bounded proof `analysis/resident-source004-cell145-record-admission-001.json`,
  SHA256 `391da17646ed038cabc608a8e97e891051826039a2c0f39c33552698750a984d`.
- Metrics proof `analysis/resident-source004-cell145-record-settlement-audit-001.json`,
  SHA256 `1a2e88fbd57ae71dfa29d86efeb63e358af59f3c4b3555feda8a55d1af34f726`.
- Original journal unchanged by review, SHA256:
  `b6d86b0917999beefad1f1d4c833009224042e558386ba296d110f42e975af26`.

This is a partial checkpoint, not completed PhaseI, pruning or PhaseII approval.
Continuation must freeze the expanded proof scope separately without replacing
old control017 or rerunning this effective completed cell.
