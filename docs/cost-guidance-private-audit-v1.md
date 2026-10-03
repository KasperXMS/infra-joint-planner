# Post-execution MultiHop evidence coverage audit v1

2026-10-04. Read-only private-evaluation analysis, not part of Agent execution or
the cost estimator. No additional model/Planner/Verifier call is made.

`scripts/cost_guidance_private_multihop_audit_v1.py` compares the retained
execution-grown paths with existing private supporting annotations after the live
queue is inactive. A live owned controller/child handle causes refusal, preventing
artifact scanning from adding experimental-period load. Artifact bodies stay on
their original storage node. Only scalar/structural coverage receipts return to4090;
no body/prompt/gold/private annotation is streamed to the development PC.

Corpus source SHA is checked against the original per-cell freeze. Each selected
stored artifact must match its recorded bytes/SHA; path confinement and symlink
checks prohibit escape from the exact existing experimental store. Results are
append-only, under the cell's private audit directory. No Worker/model process,
network configuration, task representation or historical result is modified.

Supporting-document identity is matched to original corpus document hashes by
the annotation's URL/title/source. Exact document IDs in retrieved records show
presence, not complete fact retention. Unknown mapping or projected/model notes
without document IDs stay unknown; they are not mislabeled absent. Literal fact
matching is only a lexical cue: absence is not semantic absence, and presence is
not answer correctness. The original evaluator score is retained unchanged.

The audit follows successful/failed tool/model paths, inputs, outputs and the
explicit terminal model source. Initial shards, retrieved evidence, reductions,
model notes and prompt-carried evidence remain distinguishable. It does not claim
a semantic quality oracle or automatically derive rules for the next Manager.
Private annotations never enter cost cards, SDK tools, Agent instructions or
live logical traces. Output contains support indices/coverage flags, not fact text.

Five synthetic tests cover exact corpus identity, literal normalization, unknown
identity after projection/paraphrase, unsafe/nonexperimental store rejection and
live-controller load isolation. Full545 pytest passed; Ruff pass; strict Pyright
0 errors/0 warnings; git diff check pass. This is analysis tooling only; the frozen
47fbe3b execution remains unchanged.
