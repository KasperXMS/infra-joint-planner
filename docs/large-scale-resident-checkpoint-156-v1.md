# Resident checkpoint156: replacement completes, original score0 retained

2026-10-06. Cell
`phase1-multihop_rag-1-29e45040dce39dae-p1-fast-E`, attempt2, **completed,
terminal format-valid, original evaluator score0.0**. This is a valid quality
failure; no further retry, replacement or semantic tuning is authorized.
Nominal coverage is156/168, not156correct answers or successful executions.

## Original and replacement are separate evidence

Attempt1's actual mixed token-rate429 and policy400 failures remain immutable
and operationally excluded; no score is imputed. The sole replacement basis
was that independently proved429, not either policy refusal. See
[the complete original audit](large-scale-resident-cell156-mixed-provider-audit-v1.md).
Attempt2 preserves the same YAML except runID and four fresh store roots,
same model pool/prompts/tools/budgets/scheduler/task/evaluator/network and actual
APP004-only PYTHONPATH / explicit original archive revision. No model reload,
quota/configuration/concurrency change or per-request automatic retry occurred.

## Actual trajectory and telemetry

| Metric | Attempt2 |
|---|---:|
| Manager / Verifier turns |9 /9|
| Specialists / specialist turns |0 /0|
| Physical action attempts |21:18BM25 +3model actions|
| Reached model inference |1 A28 / qwen35 27.3B|
| Context preflight rejects |2, not inference|
| Other rejected observations |12phase-restricted +1semantic-validation|
| Cloud API requests |18:9Manager +9fixed Blind Verifier, allHTTP200|
| Graph nodes / information edges / snapshots |21 /18 /64|
| E2E |218.414075s|
| Complete action transfer |12,185bytes /0.113621s|
| Fixed initial placement, separate |7,696,522bytes /1.050882s|
| Model service / tool work |86.422320s /7.959879s|
| Model input / output tokens |4,961 /2|
| Manager / Verifier service work |97.045808s /29.919148s|
| API frozen list-price estimate |USD0.271733924181825, all18usage receipts known|

Actual root responses contain18BM25,4invoke_model,6read_artifact and6select_fields
function calls. Only3model requests became physical actions: one rejected
semantic call is not counted as inference. Phase-restricted calls likewise do
not become successful Worker operations.9rule inputs are observed, with0cost
queries/quotes/comparisons; visibility is not proof that the Agent used rules
cost-rationally. No model-output specialist handoff or MAS parallel-reasoning
claim is made. Service/work sums are non-additive wall time.

Independent original-admission reconstruction passed, as did all18actual SDK
recipient-context audits, four empty stores, Worker exits, five resident
identities and tc cleanup. The two failed context requests followed by a real
inference are natural continuation, not hidden repair. They do not establish
semantic recovery: the resulting original evaluator score is0.

Wrong evidence selection, incomplete aggregation, model reasoning and synthesis
remain possible primary quality causes. No private gold/supporting-body audit
has run yet, so this report does not guess which caused the answer error or
claim that E's cost rules caused evidence loss. Do not causally compare this
cell to155's different Planner/method/network.

## Immutable proof

Settlement/audit file
`analysis/resident-source004-cell156-replacement-settlement-audit-001.json`,
SHA256 `5a93980b189e16754a5edb0eb290b2cf20f646cc9757ec2de9a4fb6125847ef8`.
Live-start/config/residency proof SHA256:
`7a585eedfbda4cb05ff8cabd21278517ed62d6ee294ad9da311999cab9e9d9b8`.
Both proofs, actual Worker/backend outputs and full trace stay on4090/edges.
The development PC receives only bounded metadata/code/report text.

Queue023 remains owned/live. The remaining12original conditions continue in
the frozen balanced schedule; no new task/method/repetition is added. The full
168private/recipient/failure/adoption audit, pruning and actual held-out PhaseII
remain required. Old42remain unpooled and count toward the420cap.
