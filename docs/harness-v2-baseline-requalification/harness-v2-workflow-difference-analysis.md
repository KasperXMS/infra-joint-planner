# Workflow difference analysis method

The Stage 2 comparison pairs each Raw Aware or Ledger run with Blind on the
same source task, network and trial. All three use the same H1 execution
contract and Physical Scheduler. Comparisons use the ordered logical actions,
operators, normalized specialist ownership, declared dependencies, artifact
input flow, output semantic/media types and model requirements. Physical
binding uses the actual selected agent and deployment from each execution
receipt. Anonymous specialist IDs and physical completion order are
normalized before comparison.

The levels are:

- **L0:** the compared logical signature and physical binding are equal.
- **L1:** logical signature is equal, but physical binding differs.
- **L2:** logical operation, dependency, information flow, output semantic
  type, ownership or model requirement differs.

The redacted export also carries SHA256 fingerprints of tool arguments and
model prompts. A hash difference alone is called *textual content change*;
it is not proof of a meaningful semantic change, since stochastic sampling
can change wording under the same policy. L2 is therefore a conservative
structural signal. A useful infrastructure-aware mechanism additionally
requires cross-trial repetition, preserved task evidence and quality, and a
paired resource improvement. A lower-cost failure or early stop is not a
workflow optimization.

H2 is reported separately. Its post-run KEEP attempt cannot be interpreted
as a pre-execution planning decision or an L2 improvement.

## Observed Stage 2 differences

Of the 24 matched Aware/Blind and Ledger/Blind comparisons, 21 have an L2
structural difference and three are L0. None are placement-only L1. Raw Aware
has L2 in 10/12 pairs and Cost Ledger in 11/12. Seventeen L2 pairs change the
operator sequence; four retain the same operators but change action input
flow, output structure or model-action requirements. Physical placement
receipts differ in 9/12 Aware and 8/12 Ledger pairs, but those runs also
usually have changed logical structure, so placement alone explains none of
the classified L2 cases. The Physical Scheduler itself was unchanged.

Examples make the distinction concrete. In the LongBench runs, Blind often
introduced `aggregate_artifacts` before retrieval and model calls, while both
aware methods generally used repeated `bm25_retrieve`/`invoke_model` cycles.
On MultiHop, one Fast Aware trial introduced `select_fields` and
`top_k_records`; its paired Blind trial used repeated retrieval/model cycles.
On Video-MME, all methods started from `sample_frames`, but some changed the
number of frames passed into successive model calls; Slow Aware trial 1 also
used `read_artifact` and `extract_clip`, and Fast Ledger trial 2 used a
`make_contact_sheet`. The redacted export retains ordered actions, normalized
artifact flow, semantic/media types, model requirements and actual placement
for every cell without publishing prompts or answers.

Nine of the 12 task/network/method combinations show an L2 difference in
both trials. That is repeatability of a *classification*, not proof that the
same useful transformation recurred: action counts and information flow vary
between samples. None of the nine preserved score 1 for both Blind and the
candidate method in both trials. In the sole individual pair where both
methods scored 1, Slow Video trial 2 Aware used four frames in its second
model call versus Blind's six and reduced E2E from 969.7 to 866.6 s,
physical work from 38.0 to 25.4 s, and known cloud spend from $0.0838 to
$0.0787. Slow Video trial 1 Aware scored 0 while Blind scored 1, so this
single favorable pair cannot establish a repeatable optimization.

The Fast Video pairs reverse which sample succeeds: Blind scored 1/0 across
trials, while Aware and Ledger scored 0/1. This is consistent with stochastic
workflow and answer variation under the frozen Planner. It cannot be
attributed to a reliable infrastructure-state response. The study lacks a
same-method variance estimate beyond two trials and makes no statistical
significance claim.
