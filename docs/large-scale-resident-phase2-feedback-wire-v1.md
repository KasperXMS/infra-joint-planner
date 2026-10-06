# Held-out Phase II: actual feedback-wire audit

2026-10-07, Asia/Hong_Kong. This is a settled-request metadata audit, not final
semantic/adoption analysis. The real controller continued the frozen schedule.
No Agent code, instructions, budget, rule payload, scheduler or model was changed.

Audit001 covers snapshot005's six settled cells; audit002 extends the same checks
to snapshot006's seven cells, audit003 to snapshot007's eight cells and audit004
to snapshot008's nine cells; audit005 covers snapshot009's ten cells and audit006
covers snapshot010's eleven cells; audit007 covers snapshot011's twelve cells.
Actual persisted provider requests were read
only on their owner4090. No raw requests, benchmark artifacts, gold or supporting
evidence were exported through the development PC. The audits made zero model
calls and did not read support/corpus/store bodies.

| Check | Actual twelve-cell result |
| --- | --- |
| Manager / Verifier / specialist provider request contexts | 75 / 75 / 0 |
| B1 profile exactly matches corresponding pre-decision trace payload | 23 / 23 |
| A/E ledger exactly matches corresponding pre-decision trace payload | 38 / 38 |
| E rules exactly match frozen canonical rule payload | 20 / 20 |
| B0 profile/ledger/rule feedback messages | None |
| Non-Manager profile/ledger/rule message prefixes | None |
| Verifier model matches fixed frozen model | Every request |
| Original recipient and method scan findings | None |
| Semantic sufficiency / causal rule or profile adoption | Not established |

Actual root calls were aligned to reasoning-start timestamps and unique decision
IDs. Provider model identifiers matched the attempt freezes; no specialist
activity occurred. Equality checks inspect the messages actually sent, not just
events declaring that feedback was prepared. The original recipient scans remain
the broader privacy check; prefix absence alone is not a complete leakage proof.

The first derived audit invocation stopped before writing an output because its
assertion compared a canonical rule-payload SHA to the SHA of the enclosing JSON
file. This was a diagnostic assertion error, not rules drift or a failed cell.
Read-only diagnosis confirmed the distinction:

- Rule-manifest file SHA256:
  `36ba6e780bbf39b9509b70a98b80a8cd5478ce532420207070bdde9e7f2f0887`.
- Canonical rules SHA256, matching the manifest field and attempt freezes:
  `6b2152aaf9c3e1ba90deacd4031bddc8870e0ac01e32c72be68fb24dc0b43be9`.

Only the derived comparison was corrected. All exact request/trace/model checks
were retained; no experiment was retried, no frozen rule was modified, and no
runtime process was restarted.

Append-only owner-local receipts, under
`/home/super/xiaoming/large-scale-cost-guidance-resident-v1/analysis/`:

- `resident-phase2-feedback-wire-audit-001.json`, SHA256
  `a35c518dda67f761937608cf87661d44c12f3d85536b9c6d4c1253ea2aa2f7e8`.
- `resident-phase2-feedback-wire-audit-002.json`, SHA256
  `7d1ee33a2d8846f0914de6f36fe38add6637c21ca7a937625fa8de04ad7733de`.
- `resident-phase2-feedback-wire-audit-003.json`, SHA256
  `16a68ee56c944055ff0f2278086403e9b96db6f6abb1a3850e8d066acd552dbf`.
- `resident-phase2-feedback-wire-audit-004.json`, SHA256
  `0223640e8c48c4a67d7a01015b0bcf72ff9bdce37a0a73d908e5a92931c82a60`.
- `resident-phase2-feedback-wire-audit-005.json`, SHA256
  `2cca663e95ea0c5964308fd7c434cc79f74cf0dea11df28788ca443b986aca3b`.
- `resident-phase2-feedback-wire-audit-006.json`, SHA256
  `f2f75e4ba4f8f21d26e7ae061e570c1b7b7788a693061b4cead709e70639efd7`.
- `resident-phase2-feedback-wire-audit-007.json`, SHA256
  `baad36a2d0fcee6ddee95dfe5911f5e929b29dc178a92a96829641d624879924`.

Visibility does not prove internal adoption, correct cost reasoning or a
quality-preserving benefit. Complete held-out semantic/failure/adoption review
and Q1–Q10 remain outstanding. Private evidence-body auditing still requires the
unchanged global inactivity guard after the full block stops.
