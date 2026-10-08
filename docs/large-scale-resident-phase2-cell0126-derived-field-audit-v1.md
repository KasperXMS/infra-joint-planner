# Phase II original126: typed-failure gate

Original `phase2-multihop_rag-4-fffab28c23fbdeaf-p2-slow-A`, attempt1, is preserved.
Queue020 exited1 at2026-10-08T10:43:52.249880UTC. Independent10:44:06UTC
readback confirms supervisor3735395/start197731107 and controller3735396/
start197731109 absent. No127 reservation, pending atomic action or replacement.
There are125 admitted cells,127 preserved/settled attempts, one unresolved126,
the sole original71 exclusion, and66 unstarted cells.

The original126 execution completed and has an evaluator result; answer/score
are not reviewed or aggregated here. Process3817143 exited0, all4Workers
verified exited, resident5 validation passed, tc cleanup_error isNone and
original qdisc equals restored qdisc. Actualconfigbytes/freeze match;
runtime0ff.../fixedBlindQwenVerifier/20-64-20/1200s remain unchanged.

Raw admission has exactly `typed_action_failure_requires_audit:validation_failed`.
Admission file SHA256:
`53e68f719ea113c93f56fb1304861cd1be6620713cd532f2b23fcae59fc8901f`.
Result SHA256:
`df195f75d82d0ac30dbd2d6ae0c228131637352f90d5ff1862d3a22d5deb1c9c`.
Trace SHA256 (427events):
`f80ef71acd2fbc39c5ae16b9cd1a350820aad967509e2781c718e5e18eca6eb3`.
Original journal SHA256:
`261ee83ab65f32aee7e89b6bb4764564f4f8c433d0d8b7e11ee4e9b160bc3ab7`.

## Narrow recorded failures

| Type | Recorded evidence |
| --- | --- |
| Synthesis guard | Six root Manager calls rejected before preparation: only invoke_model/final response allowed in synthesis |
| Context preflight | Three model actions: estimated inputs86240/82172/81732 plus reserved2048 exceed32768, before inference/transfer |
| Derived field misuse | article-analyzer BM25 requests `text_field=text` on all-search-results; recorded `document field must be text: text` |
| Read limit | article-analyzer read of all-search-results:85536B exceeds65536B |
| Output reservation collision | Manager reuses final-answer after an earlier context-failed model action reserved that output ID |

Existing frozen v3 pure proof and v2 source-bound reviewer cover these classes,
but this is not sufficient by itself for effective admission. An actual read-only
leaf and complete five-group preflight is running against the unchanged147-source
closure/currentmanifest. It must prove exact successful producer chain, public
schema/historical shape metadata, actual SDK selected-tool wires, closed graph,
Worker read-limit settings and every companion. Independent review is also
read-only. No sidecar, successor authority or new queue is created yet.

No Agent argument repair, field alias, retry, prompt/budget/operator change,
dataset/store body read or quality claim is authorized by this finding. Original
admission/journal/result/trace remain immutable. Full128 before129, all192/all193
and final inactive recipient/private/manual/retention/adoption/quality/Q1-Q10
audits and reports remain required.
