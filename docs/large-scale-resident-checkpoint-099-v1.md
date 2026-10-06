# Resident checkpoint 99–102: continuation and non-executable D alternatives

2026-10-06. These are four first executions after the exact cell98review, not
retries/replacements. All use the unchanged execution002/revision955fe8f,
control009/external006, resident model pool, budgets, prompts, tasks and evaluators.
Each passes actual recipient privacy/residency/Worker exit checks. Old42remain
separate. Full168-cell/private audit/pruning/PhaseIIand finalQ1–Q10are unfinished.

## Completed individual outcomes

All four completed with canonical-valid terminal output and original evaluator
score1. These are individual results, not a pooled score or matched method ranking.
They vary in Planner/network/method; do not attribute their latency differences
to a single factor. M/S/Vare Manager/specialist/Verifier calls. Failed model
preparations and uncommitted quotes are not actual inference.

| Cell | Task / Planner / network / method | M / S / V | Physical / returned inference | E2E seconds | Frozen list-price API USD |
| --- | --- | --- | --- | ---: | ---: |
| 99 | MultiHop2 / P1 / Slow / B0 | 4 / 0 / 4 | 5 / 1 | 85.033 | 0.05331 |
| 100 | MultiHop2 / P2 / Fast / B1 | 6 / 0 / 6 | 8 / 1 | 173.376 | 0.09643 |
| 101 | LongBench1 / P2 / Fast / E | 9 / 0 / 9 | 13 / 1 | 99.392 | 0.22604 |
| 102 | LongBench1 / P1 / Slow / D | 19 / 0 / 3 | 3 / 1 | 129.062 | 0.12750 |

| Cell | Fixed initial bytes /seconds | Complete action-artifact bytes /seconds | Tool-only work seconds | Returned backend work seconds | Model input /output tokens |
| --- | --- | --- | ---: | ---: | --- |
| 99 | 7,696,522 /22.061 | 0 /0 | 1.206 | 21.076 | 7,222 /3 |
| 100 | 7,696,522 /0.796 | 18,058 /1.118 | 2.331 | 121.429 | 7,022 /3 |
| 101 | 514,789 /0.285 | 9,398 /0.079 | 0.806 | 13.275 | 4,645 /2 |
| 102 | 514,789 /1.602 | 0 /0 | 0.243 | 0.473 | 210 /2 |

Returned inferences finish-stop. Work sums can overlap and are not an E2E
decomposition; API USD is a frozen regional list-price estimate, not an invoice.
Zero action-artifact movement does not imply zero Cloud/tool communication.
Initial placement is fixed setup, not Agent-controlled movement. Fresh stores are
not cold inference cache; configured network delay is not measured symmetric RTT.

## Semantic continuation, not hidden repair

99/B0prepared two model actions; one failed context preflight and one entered
inference, after three successful tools. Its graph has5nodes/4edges/16snapshots.
Root reasoning27.155s and Verifier12.539s are separate from the21.076s backend.

100/B1prepared two model actions, with one context reject and one inference after
six tools. Graph8nodes/6edges/25snapshots. Root27.837s/Verifier18.770s are measured;
the121.429s backend dominates this particular trajectory, not a method-level claim.

101/Eissued ten BM25retrievals across the two documents and three prepared model
actions; two context preflights failed. The final inference actually consumed two
materialized bounded evidence artifacts and answered correctly. Its graph has
13nodes/10edges/40snapshots. Nine actual root inputs exposed frozen advisory rules
and optional estimate schemas, but raw provider responses contain no optional
query. Rule visibility/reduction/correctness do not prove internal rule use or
that E caused the trajectory. Root50.071s/Verifier32.576s exceed the13.275s backend
in this sample, without asserting an exact E2E partition.

102/Dcommitted only two BM25actions and one prompt-only terminal inference.
Graph3nodes/0explicit artifact edges/10snapshots. Nineteen Manager turns,
11quotes and14timed control calls/3.421s include substantial unexecuted control
work: quotes ended consumed3/discarded4/pending4. The actual114.695s root reasoning,
8.772s Verifier and0.473s backend are distinct scopes. Five raw `invoke_model`
calls are not five actual inferences. Prompt-only output does not establish
evidence discard or prior-knowledge provenance; private semantic audit is pending.

##102/D: actual comparison, but no executable alternatives or cost-saving choice

One actual `compare_ready_actions` call proposed two model candidates. Both returned
exact created consequence cards. The exact structured response appeared in five
later root SDK inputs. Thus a two-card consequence comparison was actually exposed;
do not claim that all resident D calls forever contain only one candidate/error.
There were zero physically feasible alternatives, selected member quotes,
post-comparison authorizations or executions. This is not successful alternatives
optimization, causal cost use or a reason for early pruning.

Both cards explicitly report `static_request_supported=true` and
`selection_failure_code=context_limit_exceeded`. The semantic model requirements
are supported; their artifact inputs violate the frozen **input envelope**.
The cards' movement/context/service/wrapper predictions remain null, rather than
invented numerical forecasts. No inference was performed for the query.

The source-bound offline replay uses actual artifact metadata and the exact frozen
resolver byte-upper-bound preflight, not benchmark bodies or a tokenizer guess:

| Candidate | JSON artifact bytes | Prompt bytes /conservative tokens | Conservative input | Deployment reserved output | Required envelope | Context limit | Excess |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| document1evidence | 63,089 | 544 | 63,633 | 2,048 | 65,681 | 32,768 | 32,913 |
| document2evidence | 63,385 | 544 | 63,929 | 2,048 | 65,977 | 32,768 | 33,209 |

All five frozen deployments share32K/2048. Each logical request declared reserved
output1, but the existing resolver consistently reserves the deployment2048;
neither setting was changed. This is input handling under an existing static
capability/preflight contract, not evidence of changing bandwidth, queue, placement
or deployment availability causing infeasibility. The conservative envelope is
not actual tokenizer input usage or the model artifact's architectural context
limit. Do not retune preflight/prompt/context to rescue these proposals.

The initial102metadata proof intentionally did not reconstruct token envelopes;
a second independent proof adds the exact source replay. Both remain immutable.

## Durable remote proofs

| Artifact | File SHA256 |
| --- | --- |
| `analysis/resident-completed-099-100-source-bound-001.json` | `a9ebe81ac04dead61b71892c4fa1cbc1f2c66f7a0d809a642c6173c1b0e0966d` |
| `analysis/resident-cell101-source-bound-001.json` | `4b7e6a0535392125598bf0f1dc0f73b70c8558274b6cdb8b37de5a60f776eabb` |
| `analysis/resident-cell102-source-bound-001.json` | `9b707f1f0bd47937255f15f7f4fd834ef6814258f0e3f5a927ea972027f4e65c` |
| `analysis/resident-cell102-comparison-infeasibility-001.json` | `7f7b3ab24505c12abb1b23cb3c82517c61400d7fe59a8b11e45fb8e357ae2dce` |
| `analysis/resident-cell102-comparison-static-envelope-002.json` | `9c8c7262cc5c0b4c2405b416bca37a47073dad2ff17d6dc26f3681f6e5e1599f` |

Replay binds frozen resolver SHA
`e046d18bb852c6cdef0be1694c67a59d1c70b4eb1f0705ed626a17a1efcddf21`
and exact pool/model-backend source hashes. Actual SDK context counts are
8/12/18/22for99/100/101/102respectively. No prompt, body, gold or full trace was
exported to the development PC. Every admission/source/trace/result linkage is
checked independently; no original evidence/admission/journal was overwritten.

At03:30:24Z Queue010PID3755889 and cell103atomic3807978 were live.
Cell103LongBench1/P2/Slow/C is pending, not part of the102completed outcomes.
No unresolved system finding, semantic retry, method pruning or PhaseII permission
is asserted by this checkpoint. The [optional-card helper](large-scale-resident-optional-card-audit-v1.md)
adds only source-isolated offline support for the eventual complete-block audit.
