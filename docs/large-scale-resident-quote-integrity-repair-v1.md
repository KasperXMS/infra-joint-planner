# Resident Quote integrity audit and minimal repair

2026-10-06, 08:32 Hong Kong. This is an implementation-confounder audit, not
method pruning or a completed Phase I report. No Planner/model calls were made
by the audit, no task was replaced, and no prompt/budget/scheduler was tuned.

## Finding

The frozen `action_sha256()` hashes Pydantic JSON arrays originating from
`ExecutionRequirements.modalities` and `required_capabilities`, both frozensets.
Sorting dictionary keys does not canonicalize these unordered arrays.
`model_copy(deep=True)` can change their iteration order while preserving exact
typed equality. The stored quote then rejects its own unchanged action as
`quoted_action_mutated` before authorization/preflight/inference.

The unmodified deployed source reproduces this on Python 3.12 with
`PYTHONHASHSEED=33`: text/image requirements are semantically equal before and
after deepcopy, but their hashes differ. This also reproduces on the development
PC. This is not a model context limitation or Planner action mutation.

All 84 settled traces were read with an unchanged, hash-linked journal prefix.
Exactly two attempts contain the false mutation code:

| Original cell | Condition | False mutation rejections | Actual protocol final states | Experimental status |
| --- | --- | ---: | --- | --- |
| 4 | Video602-2 / P1 / Fast / D | 6 | consumed2, rejected6 | System confounder; retain, exclude pending repaired rerun |
| 84 | Video602-2 / P2 / Fast / C | 4 | consumed3, rejected4, pending1 | System confounder despite terminal completion/score1 |

For all ten calls, actual provider responses contain `commit_quote` with exactly
one argument, `quote_id`, matching the preceding failed authorization receipt.
The originally created action's raw JSON hash matches the stored quote hash.
The model supplied no altered prompt/inputs/requirements to the commit. No
benchmark artifact bodies, gold, evaluator contents or full prompts were exported
for this audit. This evidence does not assert that their hypothetical repaired
trajectories would be correct, faster, or otherwise beneficial.

Original admission/journal records and snapshot020 remain immutable. Their
nominal acceptance is superseded by this exact runtime finding: the 84 settled
attempts are not 84 clean comparative results. Snapshot020's original 64-admission
proof includes cell4 and must not be treated as proof that every run is free of
this subsequently identified defect. No unaffected sample is silently rerun.

## Offline lifecycle correction

The earlier `quote_decision_audit` labels quotes with no authorization/discard as
pending and does not account for rejected authorization. Its first81 model-quote
`pending14` includes cell4's six rejected quotes. Actual protocol summaries have
pending8/rejected6, not pending14. First84 all-quote summaries have consumed77,
discarded33, pending9, rejected10. These are historical trajectory accounting,
not adoption/quality rankings. The old projections are retained, not overwritten.
In particular D's observed lack of execution after candidate selection cannot
all be attributed to Planner choice when a false runtime guard intervened.

## Minimal code repair and validation

Commit `e8c42b5` sorts only the two set-valued requirement fields before hashing.
Ordered inputs, dependencies, outputs, prompts, identities and tool arguments
remain integrity-sensitive. No guard is disabled, no hidden action repair occurs,
and a genuinely modified stored action still fails closed.

Seven new regression cases cover unmodified quote authorization/execution under
three hash seeds, hash stability across processes, ordered-field mutations, and
real pending prompt/requirement mutation rejection. Before the fix, the original
five-case regression suite produced two failures; after the fix the full suite
passes. Independent audit script commit: `7c76101`.

| Check | Result |
| --- | --- |
| Full pytest | 1102 passed, 53.76s |
| Ruff, entire repository | passed |
| Strict Pyright with project virtualenv | 0 errors, 0 warnings |
| git diff --check | passed |

This local repair has **not yet been copied into the measured frozen app**.
Execution001 / control007 source and model configurations remain unchanged.
The measured cell85 continues under its original freeze; it is method B, not the
affected Quote path. No model reload, tc change, extra inference or new formal
cell was triggered by the audit/repair.

## Queue containment and next required gate

At 00:23:23Z, the exact queue parent PID2678456 was held with SIGSTOP; its active
atomic child PID3104875 was left running. At 00:29:29Z the parent was resumed
only to wait for and settle the same atomic run. The newly preserved exact bug
reviews change the review-file set bound by control007. Its existing fail-closed
check therefore stops before reserving the next scheduled cell. This is a real
new finding, not a fake source drift, rewritten freeze or admission waiver.
Verify the actual stop and child settlement; do not infer them from this intent.

**Verified drain, 00:33:51Z:** cell85settled valid at00:32:58Z, terminal format
valid/originalscore0. Parent2678456 and atomic3104875 are absent, queue lease is
released, and no86reservation exists. The controller console ends with the
expected `continuation source/evidence freeze drift` gate. The atomic run was
not killed, duplicated or replaced. Settled coverage is now85, with two known
runtime-confounded attempts still excluded from clean comparison.

Before any further formal cell: reconcile the drained attempt, freeze the generic
patch separately, add exact retrospective confounder accounting and authorize
only the two affected repair reruns. Preserve every original attempt and review;
do not silently promote either original result. Then resume only legitimate
never-started cells under a new source-bound execution/control freeze. All168
cells plus comprehensive private audit still precede pruning and Phase II.

## Append-only provenance

Remote root: `/home/super/xiaoming/large-scale-cost-guidance-resident-v1`.

- `analysis/resident-quote-hash-queue-hold-001.json`: fileSHA
  `5fdbd6d1883289e7224f31f8ad58e7cf160953382e6b9d3606f87907c9e83839`.
- `analysis/resident-quote-hash-safe-drain-001.json`: fileSHA
  `e8bae0950b02942749e182227f82fd0aa4e746e8c5ce95f1aa23704f18e20495`.
- `adjudications/quote-hash-confounder-001.json`: original exact proof fileSHA
  `65ac8392f37a731ab80fa84418b44a49b1b1d121ab9e864d9825b74e9a0bf390`.
- `adjudications/quote-hash-confounder-002.json`: adds correctly named protocol
  summary receipts, fileSHA
  `46407834f038507051b3a02cf205a424bc9e8d995e1dd7c249ec143c7217d37d`.
  Captured00:31:12Z; journalSHA
  `0f9e3c4c9df8420b41813da866b3f0b0c4748b9c630e4c550879acadfe0ba04d`.
- Frozen quote sourceSHA:
  `87bf876bd10c46993f0be8263f4b7fabf5545c2204ce586a1549430764184591`.
- Final independent auditor sourceSHA:
  `510088f0580aad03e46c947451f50224d4090ee267142871953c65f480c6e720`.
- `analysis/resident-quote-hash-drain-completed-001.json`: fileSHA
  `af992c6734ea5823c4cc334ca8a01745b0ea0a3abdfc7ee2aeef3637f7e3c4e7`.
  Last settlementSHA
  `78f0fbf3ee20b2039e69b5f4dce66825e04e508c12633cd99aa8afbe20e6e7f1`.

No replacement or new execution freeze is claimed in these receipts.
