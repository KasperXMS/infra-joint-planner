# Resident Phase I: source-bound post-block audit and screening

2026-10-07, Asia/Hong_Kong. This report concerns the new resident, diverse-pool
block only. The old 42 substantive cells remain immutable and unpooled.

## Execution and review scope

All 168 effective nominal cells are resolved; 188 attempts are preserved,
including 18 historical confounded attempts and two operational exclusions.
Queue025 and its final atomic process are inactive. The original four execution
epochs remain attached to their attempts, not retroactively relabeled source004.

All 168 recorded action paths, terminal outcomes, typed failures, recipient checks
and interface receipts have been reviewed. This means the observable review is
complete, **not** that every causal semantic explanation is known. Evidence
retention, sampling adequacy and method-induced evidence loss remain unknown
where annotations or provenance cannot establish them. No extra model calls,
semantic finalizer, prompt tuning, task replacement or historical rerun was used.

| Benchmark | Completed / 56 | Original score 1 | Score 0 | Unevaluated |
| --- | ---: | ---: | ---: | ---: |
| MultiHop-RAG | 47 | 32 | 15 | 9 |
| LongBench-v2 | 50 | 22 | 28 | 6 |
| Video-MME | 56 | 51 | 5 | 0 |

These are per-benchmark descriptive counts, not pooled accuracy or statistical
significance. Missing evaluation is not zero. Each task-condition has n=1.
Cost claims must remain conditional on matched correct completion.

## Terminal provenance and failure classification

All 153 completed answers are bound to successful terminal model outputs:
47 MultiHop outputs were evaluated directly; 106 LongBench/Video outputs used
deterministic canonical-choice extraction. All have normal stop receipts. There
is no post-workflow semantic answer generation.

The 15 unevaluated trajectories comprise:

- Six provider input-policy HTTP400 refusals, not outages or balance failures;
  they remain nominal and are not retried. They are not Planner reasoning errors.
- Eight exact 20-Manager-turn ceiling failures. Six are LongBench C/D trajectories;
  two are MultiHop C/D trajectories.
- One model-generated invalid SpecialistRequest JSON. Its serialization failure
  concerns argument composition; the evaluator never ran.

Among completed wrong answers, six MultiHop terminal outputs begin with an
explicit boolean contradicting the private answer. Five have both annotated
literal groups in their terminal inputs/prompt. That establishes an incorrect
terminal conclusion, but not complete semantic sufficiency or causal evidence
loss. The other 42 wrong-answer causes are explicitly mixed/unknown-subtype:
retrieval/sampling/reduction versus model reasoning cannot be isolated from the
available annotations. Do not silently convert this uncertainty into reasoning
failure, evidence loss or evaluator bug.

MultiHop's original evaluator uses token intersection, not a semantic oracle.
Literal overlap is not semantic retention; literal absence can reflect paraphrase
or inline evidence. All completed MultiHop representative2 runs passing does not
prove all four annotated facts were retained or necessary. LongBench
representative2 completed outputs all score0 after different legal paths. Video
has no reliable frame-level annotation to isolate sampling from VL reasoning.

The first offline MultiHop polarity helper overescaped its regex. Output001 is
preserved; output002 tests Yes/No/Yesterday and equality-checks all other fields.
The correction changes only derived audit fields, never original model output,
evaluator, runtime or experiment result. Its receipt is included below.

## Actual interface adoption and frozen screening

| Method | Phase II status | Evidence-based rationale |
| --- | --- | --- |
| B0 Blind | Retain | Core resource-blind reference, unchanged physical scheduler. |
| B1 raw profile | Retain | All 24 cells' actual root API inputs exactly matched fresh anonymous views; Verifier stayed Blind. Visibility is not useful adoption. |
| A ledger | Retain | Core spent-cost reference, no future-action cost. |
| B optional query | Drop expansion | DeepSeek 0/68 observed eligible decisions; Qwen 1/58. One valid query at LongBench1/Qwen/Slow/B; 23/24 cells had no query, not 24/24. |
| C mandatory quote | Diagnostic only | Retain existing 24 diagnostic/negative-control results. Higher root turn work in both Planners and four DeepSeek C turn-ceiling failures; not universally dominated in API dollars. |
| D comparison | Drop expansion | All 24 cells have zero multi-feasible comparisons. Four multi-candidate submissions exist, but only one real two-quote comparison; both cards context-rejected and unselected. Singleton choices do not exercise alternative comparison. |
| E frozen heuristics | Retain | Distinct no-query experience variant for held-out characterization, not a winner. Unknown semantic retention cannot support cross-task causal evidence-loss pruning; old-pool failures are not new-pool evidence. |

For the real two-card D comparison, LongBench1/DeepSeek/Slow/D trace
`b536001eae540e8ebe4573df1889889432d52151eb743fedde02edd46ef39627`
has both `invoke_model` cards reporting `context_limit_exceeded`, no selected
member. It is not two feasible alternatives and not dynamic device unavailability.

C/D root Manager turn totals across their 12 cells per Planner are respectively
180/187 for DeepSeek and 147/128 for Qwen; B0 is85/80. Verifier cadence, token/cache
pricing and specialist use differ: higher turn work is not universal higher API
USD. Quote-local control work is not the complete cloud-protocol overhead;
discard/staleness is not a proven quote-induced semantic revision. E advisory
visibility is not observable internal rule adherence.

Frozen survivors B0/B1/A/E imply 192 held-out cells:
2 Planners × 3 benchmarks × 4 remaining frozen tasks × 2 networks × 4 methods.
Global substantive count would be 42 + 168 + 192 =402, within420. There are no new
tasks, repetitions, prompt changes or extra B/C/D cells. This screening is not
an E2E winner selection.

## Immutable evidence

Remote root: `/home/super/xiaoming/large-scale-cost-guidance-resident-v1`.
All artifacts below are in its `analysis/` directory and exclusively created.
No dataset/model/full API or trace body passes through the development PC.

| Artifact | SHA256 |
| --- | --- |
| resident-current-snapshot-053.json | `018ecc49a42043165893b6f3214493ad5f3c51bec483bdd0c6687b52f4850c48` |
| Final Phase I journal | `7658930c1216dd0a4bfa921e80e06ab9b73bd5dd9e249bf3eff2ee962547a360` |
| resident-current-private-evidence-001.json | `f38938203de609e068fc63975fe12317a36271128a1c3fa9bea40e08130efb9c` |
| resident-phase1-adoption-review-001.json | `4185b6d763bf12c356dba74e0680a7cf8b69f4b0829300163fcdfb1ecaaf1ef8` |
| resident-phase1-review-cards-001.json | `c94d51027704c00d6b022fab0fb2b22fc5d171336603fa869641b4d03f0cf33a` |
| resident-phase1-terminal-failure-review-001.json | `d832eab9c2c1cc4ac0ed2b3c616a3980f26924d22b9ec8f1bd728fd9b9d0facd` |
| resident-multihop-terminal-alignment-002.json | `d4227a9db5dc4bc14c8bcf8c9c87d96c559dede7cc232ee69940f5ed8c3dbf2c` |
| resident-choice-terminal-alignment-001.json | `d5f010160c9d1c056303022a096a9664d3e9ed93191c8d90c6880a9710ca20d3` |
| resident-terminal-polarity-correction-001.json | `707f062b91cca56201ea570aaf5e93e3d06062491082179359bc9646b4a2beb4` |
| resident-comprehensive-phase1-audit-001.json | `f9a7f25e9ca737b95c201735c346d8cf8099f4fa4959f97a1a689ac55612a036` |
| resident-phase1-method-pruning-001.json | `6dfa23e926ce72a002ccfe703ff2c27b5122c29909c4f5f00d972ea3df7f4c80` |

Six real remote Markdown reports include per-cell result/failure/semantic/adoption
tables and screening/pruning, each hash-bound in the comprehensive bundle:

| Report | SHA256 |
| --- | --- |
| resident-phase1-results-review-001.md | `2550e6274907ad6d71a8b144ea5eff6f4bcde7cfd624fed9a09736773c3b8a12` |
| resident-phase1-failure-audit-review-001.md | `0d2d625579cb0ec4ade2ded6c87b7ef13f990d3a5475525bec1e17ed9817ca09` |
| resident-phase1-semantic-audit-review-001.md | `32b7502d0f4ff75bf97cc23f5d985f00d8c6ec9cf31638745cb9f0a0409403dd` |
| resident-phase1-adoption-audit-review-001.md | `4a33532ae0dbfed2f316a9116c77ce5146ede6739b12f621610b93892d0ec928` |
| resident-phase1-method-screening-review-001.md | `4240530fdb2ed57a608897847e07a3ad50b870ac4dd381c9c022e254e42395ac` |
| resident-phase1-method-pruning-review-001.md | `6e9644814a65631f883f6e16057463f483c86b3f171dfcbc261180eeb83fb5c5` |

## Gate and remaining work

Actual read-only gate verification succeeded: original journal/source projection,
all original report-file hashes, exact per-cell four-file evidence bindings,
recipient counts, all18 task identities, pruning and192-cell schedule were
revalidated. This is not a persisted gate/control receipt or launched queue.

Before activation, the held-out controller's Unicode JSONL parsing is being
minimally corrected and retested in a separate control namespace. Historical
controllers and measured source004 stay unchanged. Actual frozen gate/control,
held-out execution, final audits and Q1–Q10 remain required. The active research
goal is not complete.
