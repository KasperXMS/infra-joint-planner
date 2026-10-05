# Exact root-owned corpus field misuse — offline audit

2026-10-05. The existing attempt is retained, not repeated or repaired. Its
independent full admission reproduces the original field-validation rejection;
the new exact sidecar proves all three findings and changes offline membership
only. Queue008 remains stopped. No new benchmark or Planner/model call occurs.

## Original execution

Cell: `phase1-multihop_rag-2-2d3129ed85c03f62-p1-slow-C`, attempt1.
Original formal implementation fa19e0bcf27fe1e09b1596a50d2a4af120432438,
execution-freeze003 canonical
`092f39fd278027eab324d4b0c5280bbd5024db9f23cc60de556c361f3901e749`.
Task, original evaluator, representation, model pool, budgets, scheduler,
operator vocabulary, Manager/Verifier instructions and privacy boundaries are
unchanged. The experiment uses the original single-artifact physical pool,
not the prospective diverse resident pool.

The root Manager actually receives the corpus schema declaring `body` as the
string field. It first requests `text` in three BM25 actions, one per initial
shard. Each selected Worker returns exactly
`document field must be text: text`; the three actions close as failed nodes.
The Manager subsequently selects `body`, succeeds on all three shards, and
performs one real model inference. There is no field alias, automatic argument
correction, schema injection, retry or prompt tuning. This is observable
semantic argument misuse and natural continuation, not missing operator,
dynamic deployment infeasibility, corpus corruption or a service outage.

The original evaluator runs: completion true, format valid, score1.0. This is
the unchanged MultiHop lowercase-whitespace-token-intersection score, not a
new semantic-quality judgment. Supporting-reference/body retention remains
pending the full Phase I private audit; correct score does not prove complete
grounding or quality-preserving cost optimization.

## Exact proof, not a blanket waiver

The new offline reviewer accepts **only** the sole original field-validation
finding, with no operational incident. It requires every failed action to be
root-owned BM25 on one original initial artifact, with a requested field absent
from both declared and actual record fields. Actual root input schema must
match the frozen source schema. Exact logical and physical failure messages,
execution-stage selection receipt, action completion and final failed graph
state must agree. Every physical field failure must have its logical proof;
duplicates, missing receipts, extra findings, unrelated operators, generated
inputs, hidden schema or specialist-owned actions fail closed.

All2,847 records (1,030 /898 /919) in the three frozen shards match the declared
body-string shape. Their hashes/bytes/media types and actual Worker metadata
match; four initial Worker stores are empty. All103 original evidence files,
the original admission and frozen operator/delegation sources are bound and
rechecked. The sidecar is new and exclusive; original evidence and journal
bytes are unchanged. It does not invent a provider-policy failure to reuse the
older compound field/policy reviewer. All20 cloud responses are HTTP200.

Implementation is outside the formal app:
[large_scale_field_only_review_v1.py](../scripts/large_scale_field_only_review_v1.py).
35 new tests cover exact success, additional findings, ownership/schema/field/
receipt/graph mismatch, missing or duplicate failures, all-three coverage,
source/evidence/proof drift, unchanged raw journal/admission and denied retry.
The membership projection checks the attempt population once per query rather
than once per scheduled cell. Existing stricter historical reviewers remain
unchanged. Full pytest959 passed in32.06s, Ruff/strict Pyright/diff check pass
before remote deployment; the additional asset-manifest test subsequently gives
960 passed in31.37s, with no reviewer source change.

## Recorded outcomes

| Metric | Original measured value |
|---|---:|
| E2E | 186.539 s |
| Initial placement | 7,696,522 bytes /22.321 s |
| Successful action-transfer subtotal | 14,697 bytes /0.119 s |
| Complete action-transfer total | unknown: three execution-stage failed outcomes |
| Manager / specialist / Verifier calls | 16 /0 /4 |
| Prepared physical tool / model actions | 6 /1 |
| Successful tool / model executions | 3 /1 |
| Actually returned model inference | 1 |
| Model service work | 65.625 s |
| Model input / output tokens | 3,742 /3, normal stop |
| Preflight/context failures | 0 |
| Graph | 7 nodes,1 information edge,22 snapshots,7 growth events |
| Final nodes | 4 succeeded /3 failed, all closed |
| Action owners / peak physical concurrency | 1 /3 |
| Observed overlap | 1.047 s, no cross-owner pair |
| API list-price estimate | USD0.124963, all20 usages known |
| Quotes | 8 created,7 consumed,1 discarded |

Additional observed SDK failure receipts include semantic_validation_failed6,
quote_already_consumed3 and phase_restricted5. Attempted calls are not all
executed physical operators. No model inference is inferred from a rejected
action. Quote discard is not proof of a cost-induced semantic revision. Action
work/critical path excludes Manager/Verifier and fixed setup; overlap does not
prove E2E benefit. Model service retains the old unstandardized residency timing
limitation; no invented loading-time subtraction is applied.

## Durable evidence and current gate

Remote root: `/home/super/xiaoming/large-scale-cost-guidance-v1`.

- New reviewer: `readiness/field-only-review-001/large_scale_field_only_review_v1.py`,
  SHA `3dbb9843b3cf50f38b34704542109b7562871b39c1b0a4777d816a979c8a7e4f`.
- Original admission canonical:
  `3757d5b0cd16c3cef45500b3a717bfaf1bcb8fbab5abf3d5122b7699518f2ae7`.
- New field-only sidecar canonical:
  `7b817c3c6139964313f89bc09eafbcf3762306680f3cff0374a1be191fb981b4`;
  file SHA `3e3cba6685153bbf3ff511fd7563854f7f2010e995b240b4ab1267fcfc59c702`.
- Reviewed admission canonical:
  `25268f814665694dcc436b6e693ebce1b91e0bcbb72f6b1c22e7997846abbc57`.
- `analysis/settled-case-audit-013.json`:
  `02939822399503fc7182c4e7688426ea295edc6b7d252bf1fbc602e898ca252b`.
- Local-test receipt:
  `ddbb31e099e4b36560b9f743ddcc8c0eb4d1ef1a6ffd00f1b6a4d1e60f76ef9b`.

The first ad-hoc bootstrap used a nonexistent compound-failure-review directory
and failed during import, before creating the audit process/lease or touching
original evidence. The corrected caller uses the actual `compound-review-002`
directory; this is not an experimental retry. Its owned offline audit process
2921018 completes and is verified gone. Queue008 parent2599603 and its atomic
child are gone; no new control freeze or queue resume is performed.

42/168 nominal cells are now independently classified:38 completed/evaluated,
four nominal unevaluated failures, plus the two separately preserved implementation
confounders. Original168 scope, full post-run privacy/supporting-evidence audit,
pruning and Phase II are still incomplete. The prospective pool's assets are
being prepared separately; no new deployment is activated. The old/new comparison
block cutover decision remains outstanding, not silently resolved by this audit.
