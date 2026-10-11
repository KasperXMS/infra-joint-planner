# Historical evidence inventory v1

2026-10-11 (Asia/Hong_Kong). Retrospective analysis only. Base HEAD:
`9b9fc548d2329cfc8c9b913558f13be8d0711ccc`; working branch:
`avoidable-work-analysis-v1`. Historical execution sources are unchanged.

## Population and available evidence

| Source | Effective population | Available locally | Limits |
| --- | --- | --- | --- |
| Resident Phase I | 168 cells, 188 attempts: 168 valid, 18 confounded, 2 operational exclusions | User-requested trace export ZIP, manifest and 188 original traces | No original result/admission bodies, provider request/usage files, Worker stores or complete freeze closure |
| Resident Phase II, termination | 136 executed cells, 137 attempts, 135 admissions, 133 evaluated, 2 incomplete Agent failures; cell 136 unresolved; 56 unstarted | Final repository report | Full terminated-block raw evidence unavailable locally |
| Phase II local export through cell 89 | 89 cells, 90 preserved attempts, including excluded original 71 and replacement | Latest ZIP manifest and traces; older ZIP through 71 overlaps | A historical subset, not the 135-admission terminated population; analyze separately |
| Earlier cost-guidance | Closed 16 A/C + 18 B/D/E cells; earlier substantive 42 remain unpooled | Repository reports with numeric tables and source hashes | Different pool/epochs; no new per-operation raw reanalysis claimed |
| Earlier semantic replanning / budget diagnostic / predecision | Separate contract-development, exploratory and diagnostic populations | Repository reports and some previously exported failure traces | Never substitute these for resident samples or pool their scores |

Inputs reside in the workspace parent: `phase1-traces-2026-10-08-cells001-168.zip`
and `phase2-traces-2026-10-08-cells001-089.zip`. These are already-present,
previously user-requested exports. This analysis reads them in memory and writes
only metadata and hashes; it neither extracts their private contents nor obtains
additional raw evidence from an experiment machine. The older Phase II archive
is inventoried but excluded from the analysis to prevent duplicate counting.

Phase I manifest journal binding:
`7658930c1216dd0a4bfa921e80e06ab9b73bd5dd9e249bf3eff2ee962547a360`.
Latest local Phase II export journal binding:
`cc40962584f8f358b2461c4c445b0376852865c05d692c08bf799834d7101086`.
Terminated Phase II journal in the final report:
`e8e796e0b9bb2e3ebf1c2492c96138a20e05fca246bcb029c205f799339fa3a9`.
These are different checkpoints. Manifest membership is evidence of an exported
admission view, not an independent replay of owner-local sidecars or journal.

Final Phase I: MultiHop 47 evaluated (32 score1, 15 score0), 9 unevaluated;
LongBench 50 (22/28), 6 unevaluated; Video 56 (51/5), 0 unevaluated.
Terminated Phase II: MultiHop 48 admitted / 47 evaluated / 31 score1;
LongBench 44 / 43 / 20; Video 43 / 43 / 30. Cell 136's score1 remains outside
these denominators. Reported score1 is evaluator success, not semantic proof.

## Reused analysis and telemetry boundaries

Reuse `large_scale_snapshot_v1.event_metrics` for prepared/model/control counts,
failed inference missingness and SDK receipt deduplication; reuse
`trace_cost_receipts` for initial/action movement, execution failures and explicit
E2E; reuse `large_scale_graph_audit_v1.graph_audit` and its existing interval
analysis for graph integrity, dependencies and actual overlap. The older
`evaluation.trace_audit.summarize_cost` is useful historically but some token
defaults use zero, so it is not used for unknown-aware complete totals here.
Existing provider and quote/adoption audits distinguish actual API usage from
SDK history lower bounds. No new admission or experiment audit framework is added.

| Quantity | Evidence / interpretation |
| --- | --- |
| Manager / specialist starts | Explicit role-separated reasoning-start events, not HTTP counts |
| Verifier calls | Started/completed/input events; completed latency/tokens are receipts |
| Manager / specialist API tokens and USD | Raw provider usage absent; method-usage events can describe SDK usage but do not prove billing completeness; USD unknown locally |
| Physical actions / inference | Prepared actions, selection and typed model outcomes; returned service/token receipts are a subtotal; post-inference parse failure may lose telemetry |
| GPU-seconds | No trustworthy GPU utilization/dedicated-resource model: unknown |
| Movement | Payload bytes and transfer work, initial setup separate; failed execution may make totals unknown; prompt/HTTP/RPC wire traffic excluded |
| Graph | Artifact/control edges and closed action intervals; SDK/prompt-carried semantic influence is not a complete DAG |
| Fingerprints | Ordered content hashes where available, effective arguments, execution lineage; historical implementation/config/default/determinism closure may be missing |

Exact result reuse requires more than same operator, query or artifact ID.
Original inputs often have only logical IDs in traces. Produced artifact hashes
can be recovered from prior successful receipts. That does not establish an
operator-specific historical configuration or safe rebinding contract. Missing
proof remains Unknown rather than Exact. A model output lacking a graph consumer
can still influence Manager/Verifier through tool observations or prompts.

## Evidence levels and unavailable owner-local material

1. Original exported trace bytes: hash-checked against the manifest on every run.
2. Export manifest: effective membership and execution epoch as recorded at export.
3. Repository reports: reviewed derived aggregates with owner-local source hashes;
   not independently rederived when the underlying inputs are absent.
4. This analysis: offline resource projections and observable candidate signals.
5. Research judgment: intervention hypotheses, not causal or semantic findings.

The resident root is `/home/super/xiaoming/large-scale-cost-guidance-resident-v1`.
Original admissions, reviewed sidecars, frozen source closures, provider usage,
private evaluators and Worker artifact bodies remain owner-local. Phase II cells
90–135 and unresolved136 have no local trace coverage in the selected archive.
The closed Phase I quality-footprint report already records incomplete movement
in 37/168 cells. No complete-population cost is inferred from a measured subset.

All ten requested Stage 0 reports were inspected, including the historical
definitions, cost-guidance final/BDE, predecision, minimal replanning and budget
diagnostic. Their earlier continuation statements are historical; the termination
notice at the top of `large-scale-phase2-results-v1.md` takes precedence.
