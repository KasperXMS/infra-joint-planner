# Cost-guidance live checkpoint v1

2026-10-04. Incomplete exploration, not a method recommendation or final result.
Execution source:47fbe3b14196ea2b90c84597b75fa27f148b0b74.
Source frozen under `/home/super/xiaoming/cost-guidance-exploration-v1-47fbe3b`.
Protocol-freeze SHA256:
`f18bfff202a0314c29bdd673158ddcd875a08b084118df6a2b9df109bf1eec66`.

## First admitted cell

MultiHop multisource/Fast/Ledger-only, one primary run, no retry/replacement.
Native SDK Manager+bounded Blind specialists; unchanged Blind Verifier, finite
tools, physical scheduler/models32K/2048,20/64/20 budget and task representation.
Initial fresh stores and original evaluator; no raw H injected into Manager.

| Metric | Observed |
| --- | ---: |
| Completion / original score | true /1.0 |
| E2E |250.012s|
| Action transfer bytes |57445|
| Action transfer work |0.636s|
| Manager / specialist reasoning turns |9 /8|
| Prepared tool / model actions |13 /3|
| Completed physical model inferences |1|
| Context preflight refusals |2|
| Execution-grown graph nodes / edges |16 /21|
| Actual input / metered reasoning receipts |17 /17|

Preflight refusals are not inferences. Initial placement is separate from action
traffic and included in runner E2E. No matched-control benefit or causal Ledger
effect is inferred from this single correct, low-traffic trajectory.

## Conservative gate stop and read-only adjudication

Controller1302023 terminated after the completed first cell because the original
operational gate treats `validation_failed` as requiring audit. This is not a
provider/runtime timeout. Exactly one such observation occurred: a specialist
requested BM25 `text_field=text` on a43094-byte aggregate of15 records. The owning
node's retained input has `body` and no `text`; all15 records lack a string `text`.
The frozen aggregate operator preserves input records; BM25 correctly rejects
the absent/non-string field; Worker transports ValueError as VALIDATION_FAILED.
This is recovered Agent argument/workflow misuse, not missing tool/capability,
artifact corruption, changed operator semantics or a harness workaround.

Actual retained input SHA256:
`23cfc5ad77abcba0a610676395014898c8fea1a02ee4e06834f57ecf424e55c8`.
Independent append-only `postrun-eligibility-audit-001.json` SHA256:
`354beb0d908718f662be8913e3f626712117118d7196aa6342de5f0e9655e9dc`.
Method recipient/input hashes, original observer/terminal/privacy checks, artifact
persistence, Worker shutdown and tc restoration have no other gate finding.
The initial gate report, trace, answer, result and queue stop remain unchanged;
the independent adjudication retains this effective sample, without rerun.

Only the next scheduled Fast/Quote cell was then launched as controller1335950,
using the same frozen execution/protocol/history and a different fresh cell.
Live handle was verified from `/proc/1335950`;102 trace events included3 quotes
and3 actual quoted receipts. This is a running snapshot, not completion evidence.
The remaining cells are not represented as finished or automatically restarted.

## Read-only analysis tooling

`scripts/cost_guidance_cell_analysis_v1.py` separates Manager/specialist token/work
receipts from Verifier/physical inference, retains unknown usage, and extracts
quote/control accounting and predicted-versus-observed consequences. Transfer
bytes errors are exact where measured. Supported marginal transfer p50/p90 work
estimates are compared with observed transfer work only when receipt counts
match; their sums are not joint quantiles or wall-time critical paths. Unsupported
profiles stay unknown. Context agreement concerns existing preflight, not true
tokenizer/OOM capacity. No model output size/quality is guessed.

Full verification after analysis tooling:538 pytest passed; Ruff pass; strict
Pyright0 errors/0 warnings; git diff check pass. Two extra analysis tests cover
unknown usage, supported/unsupported estimate errors, work-versus-wall semantics
and context preflight agreement. Analysis code does not alter the47fbe3b frozen
execution and is separately versioned. No new literature/novelty claim follows
from this checkpoint; exploration and final ranking remain incomplete.
