# LongBench pre-decision Raw-Aware v1

## Current authorized recovery (2026-10-03)

Recipient-isolation repair is separately frozen as `3c3bd95` after 479 passing
tests, Ruff and strict Pyright. Only Financial and News Fast-Aware receive one
new `isolation-patch-1` attempt each with fresh stores. Admission remains 10/12
pending audits. Prompts, models, tools, budgets, task representations, scheduler
and network are unchanged. Old attempts below remain excluded and preserved.
See [patch audit](predecision-specialist-profile-isolation-patch-v1.md).

## Historical hard-stop snapshot

**HARD STOP: 10/12 ADMISSIBLE CELLS; FAMILY NOT CLEAN-COMPLETE.** Financial
Fast-Aware and News Fast-Aware were retrospectively invalidated by specialist
dynamic-profile leakage through tool results. Earlier complete-family claims and
quality totals below are preserved historical snapshots, not current eligibility.
See the [39-trace isolation audit](predecision-specialist-profile-isolation-hard-stop-v1.md).
No resumption, semantic tuning or replacement follows this privacy hard-stop.
The frozen protocol admits three distinct original multi-document
tasks, four conditions each. Selection, original context byte counts, natural
document boundaries and initial placement are in the
[protocol](predecision-crossbenchmark-v1-protocol.md).

Representation is byte-reconstructable ordered text records. Original questions,
choices/private gold and exact-choice evaluator remain unchanged; no workflow hints.

Original execution commit `90cea3261c1e21f7cb528025c64729741ccc8451`, unchanged Qwen
pre-decision harness. At the historical stopping boundary, three Financial cells
were clean; the fourth primary and its one identical replacement were confounded.
Both are retained and excluded. The separately frozen transport patch supplies
a clean Slow-Aware result; all remaining LongBench conditions completed in fixed
order. No third identical automatic
attempt is permitted.
See [live cross-benchmark report](predecision-crossbenchmark-v1.md).

The stopping boundary above is preserved as history. After user authorization,
transport patch `d43c3b3` was deployed separately (4 s idle Worker keepalive, no
retry), all six task freeze records verified identical, and Financial Slow-Aware
started as `transport-patch-1` with fresh stores. Only a clean audit permits the
unchanged remaining schedule. The three old clean cells remain retained; their
wrong answers are not tuned away.

## Financial task: completed effective comparison

The authorized `transport-patch-1` Slow-Aware run has now completed cleanly;
the historical confounded primary/replacement above remain excluded. All four
effective conditions are trace-reconstructable and completed/evaluated; all
score 0. The other eight LongBench cells have since completed in the original schedule.

| Condition | E2E s | Action bytes | Model service s | Manager / Verifier | Score |
| --- | ---: | ---: | ---: | --- | ---: |
| Fast-Blind (original revision) | 406.653 | 265938 | 113.943 | 20 / 20 | 0 |
| Fast-Aware (original revision; **excluded: profile leakage**) | 318.058 | 486264 | 117.735 | 10 / 10 | 0 |
| Slow-Blind (original revision) | 278.919 | 141047 | 51.549 | 14 / 14 | 0 |
| Slow-Aware (transport patch) | 251.831 | 486432 | 96.379 | 11 / 11 | 0 |

Patched Slow-Aware: aggregate first; aggregate_artifacts 2, BM25 5, model attempts
4 / actual inference 1 / context preflight rejects 3. No specialist; graph 11 nodes,
13 edges, peak 3 parallel actions / 0.699 s overlap. Terminal model input artifact
15938 bytes (1.47% of raw record representation), prompt 1310 bytes; actual input
tokens 4105, output tokens 2. Manager service work 93.553 s, Verifier work 47.222 s,
operator work 1.750 s, action transfer 1.912 s; initial placement separately 3.598 s.
All 132 probes, 11 Manager/profile and 11 Verifier hashes, terminal provenance,
12-artifact persistence, trace chain, tc restore and Worker shutdown pass.

Both Aware conditions aggregate before retrieval despite different network classes;
Slow-Aware traffic exceeds Slow-Blind by 244.9%, even though its E2E is 9.7% lower.
This is not a network benefit claim: service/reasoning paths differ, quality is zero
in all four conditions, and there is only one trajectory per condition. No semantic
quality failure is repaired or replaced. Remote `financial-four-cell-audit-001.json`
records the task audit and the disclosed transport revision difference.

Original context: 1,033,800 UTF-8 bytes, four natural documents. Lossless record
representation: 1,081,150 bytes, 344 chunks, initially on A4/A5/A28/A5.

| Condition | Status / score | First action | Graph N/E | BM25 / aggregate / read / reduction | Model attempts / inference / context rejects | Specialists / turns | E2E s / action bytes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Fast-Blind | clean evaluated / 0 | four parallel BM25 | 40/63 | 20/5/5/4 | 6/2/4 | 1/8 | 406.653 / 265,938 |
| Fast-Aware | **excluded: specialist profile leakage** / 0 | aggregate | 22/31 | 9/2/6/0 | 5/2/3 | 2/16 | 318.058 / 486,264 |
| Slow-Blind | clean evaluated / 0 | BM25 | 26/29 | 16/4/0/1 | 5/1/4 | 1/8 | 278.919 / 141,047 |
| Slow-Aware transport patch | clean evaluated / 0 | aggregate | 11/13 | 5/2/0/0 | 4/1/3 | 0/0 | 251.831 / 486,432 |

Reduction counts are generic top-k/projection attempts; model attempts are not
actual inference counts. Real action overlap peaks at four for both clean Blind
runs, one for Fast-Aware and three for patched Slow-Aware. Initial placement transfer
is separately 0.387 / 0.356 / 3.314 / 3.598 s and is included in E2E. The excluded
Slow-Aware primary/replacement remain in the historical exception audit, not in
this four-effective-cell comparison.

| Clean condition | Manager / specialist / Verifier work s | Physical model work s | Tool work s | Action transfer work s | Terminal artifact / prompt bytes |
| --- | --- | ---: | ---: | ---: | --- |
| Fast-Blind | 163.616 / 31.116 / 88.344 | 113.943 | 1.220 | 3.760 | 9,765 / 781 |
| Fast-Aware | 98.946 / 51.610 / 40.736 | 117.735 | 1.304 | 1.374 | 15,770 / 812 |
| Slow-Blind | 114.288 / 39.624 / 59.527 | 51.549 | 2.214 | 2.150 | 9,604 / 3,076 |
| Slow-Aware transport patch | 93.553 / 0 / 47.222 | 96.379 | 1.750 | 1.912 | 15,938 / 1,310 |

These are non-additive work sums, not a partition of wall time. Each terminal
answer is canonical A; the unchanged private gold label is C. No evaluator or
adapter repair, semantic retry, budget increase or prompt tuning follows these zeros.

### Evidence-path audit (preliminary attribution)

- Fast-Blind retrieves all four thematic branches across all four documents,
  then repeatedly encounters conservative context preflight. The terminal call
  uses only `top-supplier`: three records, document/chunk coordinates (3,3),
  (3,13), (4,19), 9,018 source-text bytes. The other three bounded branches are
  absent from terminal artifact inputs. Two actual model calls return A.
- Fast-Aware aggregates full documents, recovers through specialist retrieval,
  then narrows the terminal artifact to `search_negative_list`: five records
  from documents 1/2/3, including a duplicated (2,31) chunk; 15,130 text bytes.
  It answers A after three preflight failures. Less cloud work and fewer nodes
  accompany **more** transferred bytes than Fast-Blind, not improved quality.
- Slow-Blind searches/reduces all documents, but the terminal call consumes only
  `tiny-01`: three records from document 1, chunks 43/44/27, 9,094 text bytes.
  Its combined four-document bounded artifact still failed context preflight.

Artifact bodies were inspected only on the 4090 through retained Worker stores;
only byte/count/coordinate metadata reached the development workstation. These
paths establish narrow terminal artifact coverage and wrong synthesis; they do
not alone prove that decisive gold-consistent evidence was previously retrieved
and discarded. Primary attribution is evidence selection/answer synthesis, with
context-recovery inefficiency and Verifier readiness behavior as contributing
factors. Causal attribution between insufficient evidence and model reasoning
remains bounded by that evidence limitation.

Durable evidence audit: remote `financial-evidence-audit-primary-001.json`, SHA-256
`e0619dfec08b54dfba6a68e2fb6c9ddad1197b5784be261385eb288ef341f400`.
Independent original-task/choices/output-contract/private-gold/evaluator identity
checks all pass; retained terminal texts match original source chunk hashes.
The audit contains metadata and producer lineage, not a repair or revised answer.

First READY_FOR_SYNTHESIS occurs at Verifier calls 5/1/2 respectively. In
Fast-Aware, full-document aggregation metadata alone led the Blind Verifier to
declare readiness before a model could consume it. Phase-restricted attempts,
future-artifact references and within-run output-ID reuse remain recorded Agent
behavior under the frozen contract; they are not repaired as harness bugs.

## Academic task: completed effective comparison

Original GPT-4 report/system card and Chroma paper: 494456 source-text bytes,
514789 lossless record bytes, two natural documents initially on A4/A5.
All four conditions completed, emitted `C`, and scored 1.0 with the unchanged
private evaluator. No retry, replacement or task-specific modification.

| Condition | First action | E2E s | Action bytes / transfer s | Manager / Verifier | Tools / model attempts / actual inference | Context rejects | Graph N/E |
| --- | --- | ---: | --- | --- | --- | ---: | --- |
| Fast-Blind | BM25 | 126.426 | 63102 / 0.818 | 9 / 9 | 12 / 2 / 1 | 1 | 14 / 13 |
| Fast-Aware | aggregate | 175.840 | 243055 / 0.630 | 6 / 6 | 3 / 2 / 1 | 1 | 5 / 4 |
| Slow-Blind | BM25 | 176.759 | 25132 / 0.402 | 11 / 11 | 6 / 3 / 1 | 2 | 9 / 6 |
| Slow-Aware | BM25 | 156.410 | 18921 / 0.241 | 11 / 11 | 6 / 3 / 1 | 2 | 9 / 6 |

Fast-Blind uses one specialist (8 reasoning turns), seven BM25 calls, one aggregate
and four reads. Fast-Aware aggregates both documents, then retrieves twice.
Both Slow trajectories retrieve six times without full-document aggregation;
their two preflight failures and phase/readiness failures remain valid recovery
behavior. Peak physical action concurrency is one in all four conditions.

| Condition | Manager / specialist / Verifier work s | Physical model work s | Tool work s | Initial placement s | Terminal artifact / prompt bytes |
| --- | --- | ---: | ---: | ---: | --- |
| Fast-Blind | 45.807 / 23.778 / 41.113 | 10.947 | 0.465 | 0.165 | 0 / 2117 |
| Fast-Aware | 27.541 / 0 / 18.105 | 126.845 | 0.216 | 0.422 | 25497 / 1047 |
| Slow-Blind | 35.849 / 0 / 30.455 | 103.752 | 0.904 | 1.642 | 25132 / 933 |
| Slow-Aware | 30.907 / 0 / 33.058 | 83.875 | 0.883 | 1.604 | 18921 / 859 |

Zero terminal artifact bytes in Fast-Blind means a prompt-only terminal call;
it does not mean the Manager had no retrieved evidence. Include prompt bytes
when interpreting input reduction. Service-work sums are non-additive.

All 112/64/72/116 probes pass in fixed condition order, as do privacy, 9/6/11/11
Manager/Blind-Verifier input hashes, terminal provenance, trace chains, artifact
persistence, Worker shutdown and tc restore. Every Aware Manager input has a
fresh matching anonymous profile (6 Fast, 11 Slow). Remote evidence:
`academic-four-cell-audit-001.json` and merged `audit-progress-005.json` under
the new transport-patch root; eight clean effective cells, ten total attempts.

Observed Aware Fast→Slow change is aggregate-first→local BM25, unlike Financial
and existing MultiHop. Slow-Aware uses 24.7% fewer action bytes and 11.5% less
E2E than Slow-Blind while preserving this task's score. Fast-Aware is 39.1%
slower than Fast-Blind and moves more bytes. These are paired **n=1 trajectory
observations**, not stable/causal superiority: the Blind trajectories also change
between networks and the major E2E differences arise in model/reasoning work,
not the sub-second action transfers. No cost-guided mechanism is added.

## News task: completed effective comparison

Original Sanofi Q4/Q2 press releases: 228792 source-text bytes, 242295 lossless
record bytes, two natural documents initially on A4/A5. Every condition completed
and reached the unchanged private evaluator. Both Blind answers are `C` / score 1;
both Aware answers are `A` / score 0. The wrong answers are retained.

| Condition | First action | E2E s | Action bytes / transfer s | Manager / Verifier | Tools / model attempts / actual inference | Context rejects | Graph N/E |
| --- | --- | ---: | --- | --- | --- | ---: | --- |
| Fast-Blind | BM25 | 600.051 | 107471 / 1.652 | 14 / 14 | 16 / 8 / 5 | 3 | 24 / 26 |
| Fast-Aware (**excluded: specialist profile leakage**) | read (size reject) | 74.828 | 0 / 0 | 8 / 8 | 5 / 2 / 1 | 1 | 7 / 4 |
| Slow-Blind | aggregate | 507.576 | 191727 / 0.945 | 13 / 13 | 19 / 7 / 4 | 3 | 26 / 31 |
| Slow-Aware | read (size reject) | 189.024 | 19112 / 0.220 | 9 / 9 | 7 / 3 / 1 | 2 | 10 / 6 |

| Condition | Manager / specialist / Verifier work s | Physical model work s | Tool work s | Initial placement s | Terminal artifact / prompt bytes |
| --- | --- | ---: | ---: | ---: | --- |
| Fast-Blind | 60.914 / 26.026 / 54.215 | 449.079 | 3.059 | 0.146 | 19 / 1865 |
| Fast-Aware | 30.270 / 11.693 / 25.105 | 4.372 | 0.290 | 0.109 | 0 / 406 |
| Slow-Blind | 84.473 / 50.226 / 44.655 | 455.067 | 2.243 | 0.789 | 0 / 1343 |
| Slow-Aware | 49.800 / 0 / 29.645 | 103.674 | 0.628 | 0.827 | 19112 / 1747 |

Operator counts in fixed order: BM25 14/2/14/6; aggregate 2/0/3/0; read 0/3/2/1.
Specialist calls 1/1/4/0, specialist turns 8/3/15/0; peak action concurrency 2/1/4/2,
overlap wall time 3.052/0/111.120/1.355 s. Slow-Blind includes cross-owner overlap;
service sums are not additive wall time. Fewer Aware model calls accompany lower
E2E **and wrong quality**, not a quality-preserving system improvement.

### Semantic failure audit

Fast-Aware: initial full-artifact read fails its declared size limit; two BM25
outputs are materialized (32615 and 31738 bytes), but the first Verifier readiness
decision precedes successful plaintext evidence reads. The combined model request
fails context preflight. A specialist then reads both artifacts; the terminal call
is prompt-only (406 bytes, 94 actual input tokens) and returns the wrong label.
This establishes recovery followed by wrong synthesis and questionable readiness,
not proof that the specialist's retrieved facts were irrelevant.

Slow-Aware: read-size and two context failures are followed by legal bounded
retrieval. The terminal model consumes three records from **each** original document,
total 19112 artifact bytes plus a 1747-byte prompt (6014 actual input tokens), yet
returns the wrong label. Every retained record matches its original chunk hash;
this is not wrong-source placement, document loss, corruption, or evaluator mismatch.
Exact evidence-relevance versus reasoning attribution remains unproven.

Primary class for both zeros: **semantic evidence selection / answer synthesis**;
secondary: context-recovery composition and premature Verifier readiness. All
read-size, static context and phase restrictions are explicit; no silent truncation
or infrastructure failure is observed. Do not modify the frozen harness to fix them.

Remote audits: `news-fast-aware-semantic-audit-001.json` and
`longbench-zero-score-source-provenance-001.json`. The latter also checks the
patched Financial terminal's five supplier records from documents 1/3/4 against
original source hashes. Artifact bodies are read only on remote nodes; only
coordinates, byte counts and hashes are returned to the development PC.

## Family completion and bounded conclusions

**Retraction:** the historical twelve-cell audit below checked direct profile
fields but missed specialist tool-result context. It is not a current family
completion proof. `5dafc43/audit-progress-005.json` now admits ten LongBench cells,
with two unresolved Fast-Aware conditions. Their wrong answers remain preserved
but are not valid Agent-failure comparisons. The four Academic cells and Financial/
News Slow comparisons remain individually admissible under the retrospective scan.

`longbench-family-completion-audit-001.json` and
`longbench-family-runtime-integrity-001.json` verify:

- 12 clean effective completed/evaluated cells from 14 preserved attempts;
  the two old Financial transport incidents remain excluded, not deleted.
- Same task/public-bundle and capability hash within every task's four cells;
  48 unique effective Worker-store roots and 48 empty initial Worker states.
- 1844/1844 probes pass; 136 Manager and 136 Blind Verifier input hashes pass;
  all 55 Aware Manager turns have matching fresh pre-decision profiles.
- All 12 terminal answers originate from successful manager-owned physical model
  output; trace chains, persistence, privacy, tc restoration and shutdown pass.
- All 24 pre-run deployment states expose 32768/2048; all 21 completed physical
  inferences have finish_reason `stop`. All 48 finished-family Worker PIDs are inactive.

Selected-task quality: Financial 0/4, Academic 4/4, News 2/4 (6/12), **not** an
official LongBench population accuracy estimate. Blind 4/6 and Aware 2/6 are
descriptive counts on these three preregistered tasks, not a superiority test.

No universal network-class rule emerges: Financial Aware aggregates in both
networks; Academic Aware aggregates in Fast and retrieves locally in Slow;
News Aware tries local reads in both. Blind also changes workflow across networks.
Physical model service and cloud reasoning dominate these sampled E2Es, while
action transfers are seconds/sub-seconds. Cost and quality must be assessed jointly;
cheaper wrong answers and n=1 variations do not establish rational adaptation.
The first three Financial cells use the original transport revision; all others
use the disclosed transport-only patch, with logical behavior unchanged.
