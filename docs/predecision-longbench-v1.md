# LongBench pre-decision Raw-Aware v1

**STOPPED AT OPERATIONAL GATE; FAMILY INCOMPLETE.** The frozen protocol admits three distinct original multi-document
tasks, four conditions each. Selection, original context byte counts, natural
document boundaries and initial placement are in the
[protocol](predecision-crossbenchmark-v1-protocol.md).

Representation is byte-reconstructable ordered text records. Original questions,
choices/private gold and exact-choice evaluator remain unchanged; no workflow hints.

Execution commit `90cea3261c1e21f7cb528025c64729741ccc8451`, unchanged Qwen pre-decision
harness. Three Financial cells are clean; the fourth primary is operationally
confounded and retained; its one identical replacement is also confounded. Family is
**not complete**; eight other primary cells remain unexecuted, and Slow-Aware has
no clean eligible result. No third identical automatic attempt is permitted.
See [live cross-benchmark report](predecision-crossbenchmark-v1.md).

## Financial task: partial comparison

Original context: 1,033,800 UTF-8 bytes, four natural documents. Lossless record
representation: 1,081,150 bytes, 344 chunks, initially on A4/A5/A28/A5.

| Condition | Status / score | First action | Graph N/E | BM25 / aggregate / read / reduction | Model attempts / inference / context rejects | Specialists / turns | E2E s / action bytes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Fast-Blind | clean evaluated / 0 | four parallel BM25 | 40/63 | 20/5/5/4 | 6/2/4 | 1/8 | 406.653 / 265,938 |
| Fast-Aware | clean evaluated / 0 | aggregate | 22/31 | 9/2/6/0 | 5/2/3 | 2/16 | 318.058 / 486,264 |
| Slow-Blind | clean evaluated / 0 | BM25 | 26/29 | 16/4/0/1 | 5/1/4 | 1/8 | 278.919 / 141,047 |
| Slow-Aware primary | excluded observer confounder / 0 | aggregate | 28/27 | 8/2/13/0 | 5/2/3 | 3/23 | 311.743 / 486,420 |

Reduction counts are generic top-k/projection attempts; model attempts are not
actual inference counts. Real action overlap peaks at four for both clean Blind
runs and one for Fast-Aware. Initial placement transfer is separately 0.387 /
0.356 / 3.314 s for the three clean runs and is included in E2E.

| Clean condition | Manager / specialist / Verifier work s | Physical model work s | Tool work s | Action transfer work s | Terminal artifact / prompt bytes |
| --- | --- | ---: | ---: | ---: | --- |
| Fast-Blind | 163.616 / 31.116 / 88.344 | 113.943 | 1.220 | 3.760 | 9,765 / 781 |
| Fast-Aware | 98.946 / 51.610 / 40.736 | 117.735 | 1.304 | 1.374 | 15,770 / 812 |
| Slow-Blind | 114.288 / 39.624 / 59.527 | 51.549 | 2.214 | 2.150 | 9,604 / 3,076 |

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
