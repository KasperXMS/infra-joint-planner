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

## Node helper import isolation

Benchmark/trace imports are now lazy and limited to the4090-side full audit. The
owning-node `--scan-store` helper uses only the standard library, preventing the
shared historical virtualenv's editable-package path from selecting an unrelated
project install during a scan. A subprocess regression runs Python with `-S`
(no site packages) and proves the real confinement check is reached rather than
a project/dependency import failure. No Agent, Worker or model-serving source is
changed. The private audit still refuses any live owned queue handle and has not
yet scanned the real stores while Video runs.

Verification after this helper-only correction:full556 pytest passed,Ruff pass,
strict project Pyright0 errors/0 warnings; git diff check pass. Historical Agent
and isolation-manifest source hashes remain unchanged. No substantive cell is
rerun because the change is outside the execution path.
