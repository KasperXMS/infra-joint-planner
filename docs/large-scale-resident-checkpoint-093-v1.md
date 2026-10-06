# Resident checkpoint 93–98: exact record-field audit, no semantic retry

2026-10-06. This is an intermediate, source-bound report, not Phase I screening.
All cells use execution002/revision955fe8f; Manager, Verifier, budgets, model pool,
resident services, scheduler, tools, benchmark/evaluator and task set are unchanged.
Old42 remain CLOSED/unpooled. No prompt tuning, new method or forced model routing.

## Actual completed cells

Every row completed, had canonical-valid output and invoked its original private
evaluator. Scores are individual outcomes, not pooled benchmark accuracy. M/S/V
denote Manager/specialist/Verifier reasoning calls; physical calls include failed
preflight/tool actions and are not identical to actual inference calls.

| Cell | Task / Planner / network / method | Score | M / S / V | Physical / returned inference | E2E seconds |
| --- | --- | ---: | --- | --- | ---: |
| 93 | Video131-3 / P2 / Fast / D | 1 | 9 / 8 / 3 | 9 / 3 | 209.346 |
| 94 | Video131-3 / P1 / Slow / C | 1 | 17 / 0 / 5 | 5 / 1 | 138.581 |
| 95 | Video131-3 / P2 / Slow / B | 1 | 6 / 0 / 6 | 3 / 1 | 125.095 |
| 96 | Video131-3 / P1 / Fast / A | 1 | 4 / 0 / 4 | 2 / 1 | 85.152 |
| 97 | MultiHop2 / P1 / Fast / D | 1 | 9 / 0 / 2 | 4 / 1 | 77.154 |
| 98 | MultiHop2 / P2 / Slow / E | 1 | 5 / 4 / 5 | 8 / 1 | 112.754 |

| Cell | Fixed initial bytes / seconds | Complete action-artifact bytes / seconds | Successful tool work seconds | Returned model backend work seconds | Model input / output tokens | Frozen list-price API USD |
| --- | --- | --- | ---: | ---: | --- | ---: |
| 93 | 7,037,220 / 0.660 | UNKNOWN / UNKNOWN; successful subtotal0 | 2.106; complete UNKNOWN | 116.639 | 4,139 / 1,010 | 0.25479 |
| 94 | 7,037,220 / 19.710 | UNKNOWN / UNKNOWN; successful subtotal0 | 0.712; complete UNKNOWN | 30.882 | 5,527 / 2 | 0.11649 |
| 95 | 7,037,220 / 19.705 | 0 / 0 | 1.313 | 37.773 | 6,704 / 2 | 0.15057 |
| 96 | 7,037,220 / 0.777 | 0 / 0 | 1.517 | 37.726 | 6,659 / 2 | 0.07985 |
| 97 | 7,696,522 / 0.895 | 0 / 0 | 1.084 | 21.823 | 7,509 / 3 | 0.06923 |
| 98 | 7,696,522 / 22.085 | UNKNOWN / UNKNOWN; successful subtotal30,058bytes /0.808s | 1.493; complete UNKNOWN | 0.405 | 62 / 3 | 0.19827 |

Failed tool execution can lack a complete movement/work receipt. Preserve the
original result's successful subtotal, but do not label it the complete total.
Context preflight is not inference. Returned models all finished-stop. Work sums
can overlap and are not an E2E decomposition; list-price USD is not an invoice.
Fresh Worker stores are not cold inference cache. Configured delay is not measured
symmetric RTT. All selected cells pass residency, Worker exit and actual recipient
privacy checks; cell98 additionally needs the exact offline proof below.

## Interface and continuation observations

93/D made three actual `compare_ready_actions` calls, each with one candidate.
One returned an exact created consequence card, but it was physically infeasible;
the other two returned typed failures. All three responses were visible in later
actual root SDK inputs. There was no multi-candidate comparison, feasible alternative
comparison, selected member quote or post-comparison execution. Correct completion
does not prove D's comparison mechanism was exercised. Its specialist used three
real visual inferences, and the graph has9nodes/36edges/28snapshots, actual concurrency1.
One overlarge read failed; the tool/model observations supported subsequent actions.

94/C has6quotes,5consumed/1discarded,11timed control calls/2.690s and17Manager turns.
An overlarge read failed; three successful tools and one inference eventually
completed the five-node graph. This is an observed trajectory, not proof of
quote-induced improvement or a cross-method cost ranking.

95/B exposed optional estimate tools in all6actual root requests, but made zero
optional query calls. One model context failure preceded the successful inference.
This does not negate cell90's independently proved optional-card adoption; both
observations must survive into the eventual complete-block audit.

96/A used one tool and one inference, with no failed physical graph nodes.
97/D used three tools and one inference, with no actual comparison call. Its four
graph nodes reached actual concurrency3/overlap0.529s; it has5quotes,4consumed/1discarded.
Graph width/edge counts do not by themselves establish semantic parallelism or savings.

98/E retrieved from the three shards, attempted a context-overlarge model action,
then delegated aggregation, retrieval and a read to one specialist. That specialist
requested an absent record field; it continued after the typed failure and read
the materialized artifact. A prompt-only root terminal model then returned a valid
answer. Its8-node/8-edge/25-snapshot graph has6succeeded/2failed nodes and actual
concurrency3/overlap0.713s. Five root inputs exposed the frozen rules. Visibility
does not prove internal rule use; prompt-only synthesis does not prove evidence
discard or prior-knowledge provenance. Semantic adequacy remains a private audit task.

## Why queue009 stopped at98, and why98 is retained without a rerun

The frozen admission gate treats arbitrary `validation_failed` as unresolved until
audited. Queue009 exited normally through that fail-closed gate at03:09:22Z; the
atomic process exited0 and every owned Worker was verified exited. No live run
was killed. The original confounder admission and205-record journal are immutable.

The exact failure is `bm25_retrieve(text_field="text")` over a materialized
44,823-byte/15-record JSON array on A28. An owning-device hash/size/metadata-checked
shape inspection proves every record has string `body`, but `text` is absent.
Only field names, counts and hashes returned; no dataset body or gold traversed
the development PC. Whole-record-preserving retrieval/aggregate ancestry links
the array to the correctly declared initial corpus schema. Specialist receipt of
that full schema is not assumed. The exact logical and physical failure messages,
operator selection, source hashes and all86original evidence files are bound.

Independent full admission reproduction matches the original receipt. The unchanged
existing field reviewer accepts this one exact argument misuse as a valid workflow-
composition failure, not a runtime bug. All relevant operator/delegation source
hashes are identical in execution001 and execution002. A new append-only sidecar
records that proof; it authorizes no replacement, alias, online correction or retry.
The terminal quality1 remains unchanged. This review is not the run's private
semantic primary-cause audit and not a blanket waiver of validation failures.

## Durable evidence and continuation freeze

All artifacts below remain under the resident remote root. Full traces and private
payloads were not exported. Earlier snapshots/proofs were not overwritten.

| Artifact | File SHA256 |
| --- | --- |
| `analysis/resident-snapshot-025.json` | `3e43389d68676b1a072351c8b0c2a9623bf1c7bc4df759da1377353eda209beb` |
| `analysis/resident-completed-093-095-boundary-001.json` | `ecdf38f5c9fc29a6221f489d410825c73d87451b02285aaac298f95ce8a31c06` |
| `analysis/resident-cell093-comparison-adoption-proof-001.json` | `68c7be51230833a80674012d103807258243a771db04ddb62abc1202204952a8` |
| Exact cell98 record-field sidecar | `878a4fd01ee61e8f9d8f670469a8a336236cf59028c657667ec84c2ae85434b9` |
| `readiness/cell098-record-review-validation-001.json` | `60adc73be353382b7389ed9f5058a815b8a8690b6ba749b617a20ecc33c5921d` |
| `readiness/cell098-continuation-full-validation-001.json` | `f5a83ff8159bbf13c6395fdc754e301860a1ba6217ff4e9bb99f36ef801b21ab` |
| `queue-control-freeze-009.json` | `d9d959cd1c04f7866b825fac0b47052be0e70f2bc7211029d5593393ef60c2d0` |

Snapshot025captured03:13:57Z with journalSHA
`e91c130a19b78619ff726588b7c039ba2a6eff2363e30ff99fe33ea9781cffc1`.
It verifies98effective cells/100settled attempts/0pending, two preserved Quote-
confounded originals, all scoped sidecars,18tasks and both source freezes. No
unresolved confounder remains. No benchmark/model/tc call was made during this audit.

Fullpytest passed exit0, with1,154collected tests; Ruff passed, strictPyright0errors/
0warnings and diffcheck passed. There are no code changes since the previously
validated source. One preliminary stdin audit omitted the archive revision env
and failed before evidence writes; the corrected launch supplied the actual
955fe8f revision. This was preparation, not a benchmark attempt or replacement.

Control009canonicalSHA is
`51dd4202cee844c5aada2073a95d3742d692b231651dc692d6d5a81547576544`.
Its only difference from control008 is the new exact cell98 record-field sidecar;
formal execution002 stays unchanged. Queue010 uses the same external006entrypoint,
not a script directory that shadows the reviewer. Its launcherPID3755888 was
created03:16:28Z; actual queue/first reservation must be independently verified.
Only never-started cells99onward may continue; cell98 is not repeated.

Actual03:17:39Z inspection confirmed Queue010PID3755889 alive, argv resolving the
external006controller and control009. Cell99 MultiHop2/P1/Slow/B0 was reserved
03:17:27Z, journalsequence205/SHA
`faf7337040062db08bef8b092c235294d45ad7ac2734630c3151dd67363fdd23`.
Its atomicPID3759367 was live. This is pending execution, not a completed outcome;
snapshot025remains its earlier98settled-cell scope. No automatic semantic retry.

All168cells, complete private/failure/recipient/adoption audit, frozen pruning,
actual PhaseII and finalQ1–Q10remain unfinished. No quality aggregate or winner,
early pruning, PhaseII authorization, new model/routing method or semantic tuning.
