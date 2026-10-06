# Resident checkpoint151: Blind context recovery, normal completion

2026-10-06. Video representative2, task hash prefix `e48bef6f0e60e753`,
DeepSeek/Slow/B0, attempt1. Normal completion, valid terminal, original evaluator
score1.0. One run, no replacement, no manual recovery or semantic tuning.

The root Manager used6reasoning turns and6Blind Verifier calls, with no
specialist. Physical actions were sample_frames1and invoke_model2; the first
model attempt received `context_limit_exceeded` before inference, while the
second completed on A4/Qwen3-VL4B. The Manager continued after that typed
observation. Two semantic-validation observations and one phase-restricted
observation also occurred. They are not additional model inferences.

The actual provider responses contain2sample_frames,3invoke_model and
1make_contact_sheet calls; only3actions reached physical execution and only
1reached inference. SDK call attempts, physical calls and inference counts
therefore must remain separate. There was no infrastructure profile, ledger,
cost-query interface, rule input, quote or comparison in this B0run.

| Metric | Observed |
|---|---:|
| Manager / Verifier / specialist turns |6 /6 /0|
| Physical actions / actual inference |3 /1|
| Model input/output tokens |3,407 /2|
| E2E |113.093868s|
| Complete action transfer bytes/time |0 /0|
| Fixed initial placement |7,037,220bytes /19.711567s|
| Model service / tool work |19.124727s /1.638516s|
| Manager / Verifier work |51.881495s /18.931687s|
| Frozen list-price API USD estimate |0.121918304787|
| Graph nodes / information-flow edges / snapshots |3 /11 /10|
| Actual SDK recipient contexts audited |12|

No hidden summary/truncation, model substitution, retry, scheduler change or
manual answer repair was added. Static/capability preflight remained unchanged;
this trace demonstrates continuation after a context rejection, not that an
infra-aware method caused recovery. Correct completion and local action traffic
do not establish supporting-evidence retention or cost optimality.

The original admission was independently reconstructed, matched its canonical
settlement and had no admission/privacy/operational findings. Four initially
empty Worker stores, exited Workers, five resident instances and tc cleanup
passed. All12API costs were known,6Manager/6Verifier; monetary cost is the frozen
regional list-price estimate, not an invoice. Work sums are non-additive E2E.

Remote append-only proof:
`analysis/resident-source004-cell151-settlement-audit-001.json`, SHA256
`b9c44f4d5b54d4efdb1429b8b7b3a3582952e30fc07b06d9166b9d092ccd2812`,
captured14:14:15Z, under
`/home/super/xiaoming/large-scale-cost-guidance-resident-v1`.
No benchmark/API body was exported to the development PC.

Nominal admission count is now151/168, based on the147-cell immutable snapshot050
and four independently audited new settlements148–151. The remaining17nominal
cells retain the original schedule; old42remain closed/unpooled. All168/private
semantic/failure/recipient/adoption audits, frozen method pruning, actual held-out
PhaseII and finalQ1–Q10remain required. This successful Blind example is not
permission to skip that full scope or mark the goal complete.
