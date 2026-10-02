# LongBench pre-decision Raw-Aware v1

**IN PROGRESS.** The frozen protocol admits three distinct original multi-document
tasks, four conditions each. Selection, original context byte counts, natural
document boundaries and initial placement are in the
[protocol](predecision-crossbenchmark-v1-protocol.md).

Representation is byte-reconstructable ordered text records. Original questions,
choices/private gold and exact-choice evaluator remain unchanged; no workflow hints.

Execution commit `90cea3261c1e21f7cb528025c64729741ccc8451`, unchanged Qwen pre-decision
harness. First Financial Fast-Blind run completed with canonical A / score 0.0;
E2E 406.653 s, 265,938 action bytes, two actual inferences, no operational gate
failure. Family is **not complete**; remaining 11 cells and full semantic audits
are pending. See [live cross-benchmark report](predecision-crossbenchmark-v1.md).
