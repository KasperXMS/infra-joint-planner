# Quote-before-Commit decision audit v1

2026-10-04. Read-only analysis of the12 completed primary cells. No new Agent,
Planner, Verifier, evaluator or physical action is invoked. The Video block is
still live; this is not the final exploration report or a method recommendation.

Execution remains47fbe3b14196ea2b90c84597b75fa27f148b0b74. The source for the
current analysis is separately hashed:
`ffdde4d76b9a47cf704ce218cd9081c39206dc9c5d44c0f48da02329e658f5d7`.
It runs from remote `analysis-tools/quote-decisions-002`, outside the frozen
Agent/Worker code path. Per-cell `cost-consequence-analysis-003.json` is append-
only and records its source, original trace and result SHA256. Earlier001/002
analyses, gate reports and executions remain unchanged. Raw bodies/prompts and
private evaluator data stay remote; only numeric/structural receipts are exported.

## What was visible before a decision

The audit compares each created anonymous quote with parsed SDK function-call
outputs in the actual `logical.reasoning.input` record. The complete card must
match exactly; text/ID mentions, altered cards, specialist inputs and exposure
after commit/discard do not count. Input SHA256, decision ID and event ordering
are retained. Visibility is evidence of available feedback, **not causal use or
private chain-of-thought**. Provider-private reasoning is not recorded.

| Quote cell | Created | Consumed | Discarded | Pending | Exact visible cards | Known-infeasible commits |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| MultiHop Fast |8|7|0|1|8|0|
| MultiHop Slow |8|7|0|1|8|0|
| Academic Fast |7|5|2|0|7|1|
| Academic Slow |5|3|2|0|5|0|
| Financial Fast |6|2|4|0|6|0|
| Financial Slow |4|2|2|0|4|0|

Consumed quotes include failed physical attempts, not just inferences. All six
cells perform exactly one successful physical inference. Quote-only proposals,
discarded/pending models and context refusals are not counted as inference.
All38 cards are visible;26 consumed/10 discarded/2 pending. Thirteen cards expose
context_limit_exceeded; ten are discarded, two pending, one committed despite
that warning. This is genuine Agent behavior; no hidden rejection/repair policy
is added after observing it.

## Action-level paths and interpretation

MultiHop both networks:BM25x6(top_k5), then a model proposal with six retrieved
artifacts refuses context. Manager instead commits a model with only two of
those artifacts; the earlier proposal remains pending. Both terminal scores0.0.
Observed action bytes and operator pattern match between H. The reduction in
input count is real, but discarded supporting information/relevance needs the
separate private post-queue coverage audit. No inference repair or task rule is
derived from it.

Academic Fast:aggregate(217558 quoted remote bytes),BM25(top_k20),two infeasible
model quotes discarded,third infeasible model knowingly committed/refused,
BM25(top_k5),then artifact-backed inference. Final score1.0. Original Ledger has
the same prepared operator pattern and similar model service; Quote's extra
Manager work dominates its slowdown. The quote mechanism prevents some futile
attempts but does not prevent all, and is not free.

Academic Slow:BM25x2(top_k20),discard two infeasible model proposals with2/1
artifact inputs,then commit a model with **zero inputs** and819 prompt bytes.
Actual model input202 tokens/service6.391s;score1.0. Neither Manager nor specialist
uses read_artifact; retrieval output contains only ProducedArtifact metadata.
Thus artifact-backed document evidence consumption is not observed. A short,
correct prompt-only completion is not proof that a bounded evidence artifact
was generated or that the response is evidence-grounded. The first proposal
already differs before its first quote, so this comparison does not causally
attribute first-action choice to subsequent quote feedback.

Financial both networks:full aggregate,discard context-infeasible model proposals
(four Fast/two Slow),then prompt-only inference. No retrieval/read_artifact or
artifact-backed inference is performed by C; both scores0.0. Fast model input336
tokens/service8.370s,Slow727 tokens/15.334s. Ledger consumes retrieved evidence,
performs iterative context recovery and also scores0.0. Faster wrong answers do
not establish task utility. Slow C moves470494 bytes versus19116 A, highlighting
why minimum traffic is not minimum end-to-end cost or semantic adequacy.

The model evidence audit exports prompt byte counts/hashes, artifact IDs and
requirements only, never prompt/query text. Missing model-outcome receipts yield
unknown aggregate inference input counts rather than invented zeros. A terminal
model's zero declared inputs is a structural fact, not a claim about the origin
of all knowledge in its prompt or correctness of its answer.

## Estimator versus actual

Committed successful byte estimates match observed receipts in these C cells;
zero local transfers are known local zeros, not empirical predictor validation.
Unsupported historical transfer/model buckets remain unknown. Configured ideal
serialization is separate from observed transfer work; p50/p90 sums are not
joint quantiles, confidence bounds or wall-time critical paths.

| Successful model quote | Historical support | Actual service | Actual minus p50 | Actual minus p90 |
| --- | ---: | ---: | ---: | ---: |
| MultiHop Fast |10|127.532s|-50.285s|-192.608s|
| MultiHop Slow |10|125.679s|-52.137s|-194.460s|
| Academic Fast |15|71.302s|-28.002s|-56.348s|
| Academic Slow |0|6.391s|unknown|unknown|
| Financial Fast |0|8.370s|unknown|unknown|
| Financial Slow |6|15.334s|+4.356s|-0.194s|

Model profile uncertainty/cache effects remain substantial; no absent profile is
filled using the observed result. Context-fit agreement refers to the existing
conservative byte envelope/preflight, not tokenizer-perfect capacity or an OOM
prediction. Quote timing excludes cloud reasoning overhead; that overhead is
separately observed, not hidden in cost savings.

## Verification

Five additional synthetic tests cover exact pre-decision card visibility,
ignored infeasibility, pending-versus-executed accounting, false visibility from
text/altered/child/late inputs, prompt-only versus artifact-backed terminal paths,
unknown model-outcome receipts and preflight-versus-inference distinction.
The analyzer is read-only with respect to input trace/results and rejects duplicate
quote identity or lifecycle receipts without a creation event.

Full550 pytest passed; Ruff passed; strict Pyright0 errors/0 warnings using the
project virtualenv, plus explicit strict checking of the analysis script passed;
git diff check passed. No inference-time source changes accompany this audit.

The frozen native runtime, tools, instructions, Verifier, budget, scheduler and
benchmark/evaluator are unchanged. No cell is retried or replaced. Final route
ranking requires the Video block and private failure-path audit; do not promote
the Academic Slow result into a method win at this stage.
