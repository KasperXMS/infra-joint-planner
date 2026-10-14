# Quality-preservation criterion

The original Video-MME private evaluator accepts only an exact declared
choice label and scores it against held-out gold. The fixed experiment uses
the same `795-3` question, original video, eight sampling timestamps, choice
set, model requirements and task prompt for both logical workflows. The
`frames` condition submits eight individual JPEGs; `sheet` submits their
resized 4×2 composite. Both lose most of the 41.6-minute source timeline;
the composite additionally trades pixel detail for a smaller evidence
payload. Structural validity therefore cannot establish semantic
equivalence.

Both pairs completed with exact valid output and original score 1 for both
workflows: **both correct** fast and **both correct** slow. No run was
incomplete, and there was no model or tool failure. The sampled evidence
hashes match across all four runs, and the two sheet artifact digests match
across network states. This establishes an observed quality-acceptable pair
of genuinely different logical workflows on the real task under both tested
states. It does not prove the sheet consistently preserves fine-grained
evidence or either strategy is reliable over repeated model draws.

For every matched network regime, the analysis classifies the pair as
**both correct**, **both incorrect**, **only frames correct**, **only sheet
correct**, or **one/both incomplete**. Only both-correct comparisons support
a quality-acceptable cost preference for this task. A syntactically valid
label with score zero is a quality failure. A cheap early failure or missing
evidence is retained in the denominator and never counted as a saving.

One stochastic physical model call was made per completed workflow. With only
one execution per cell, these successes are mechanism observations, not a
statistical reliability claim. The frozen design does not
selectively rerun a wrong answer. Gold and scores are never fed to the
fixed-policy choices; they are read only after terminal execution. All
quality conclusions in the final decision should be conditioned on the
[per-cell original scores](../../results/infra-workflow-opportunity-v1/controlled-public.json).
