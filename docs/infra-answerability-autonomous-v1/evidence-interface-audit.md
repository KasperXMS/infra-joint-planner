# Evidence interface audit

The audit reconstructed six task/workflow evidence sets from the frozen public task manifest and original source-a/source-b base and correction archives. It compared the original-data SHA256 values to the 686-entry residency manifest before using any article. The manifest hash is `33ccac887c5fcf52ac4b6f9104a21bc7319bbdb5af33ab60f27bd1063bbf020d`; all four archive hashes still match the [P1 closure](../infra-hypothesis-feasibility-v1/p1-isolation-closure.md). Reconstructed prompts and private evaluator labels remained in separate workstation audit directories. The Controller and model never received labels.

| Task | Workflow | Final records | Article-body characters | Rebuilt context tokens | Historical context tokens |
|---|---:|---:|---:|---:|---:|
| MultiHop a647 | G0 | 4 | 40,930 | 9,692 | 9,692 |
| MultiHop a647 | G1 | 8 | 129,103 | 29,175 | No model call (413) |
| MultiHop 667f | G0 | 6 | 96,427 | 25,175 | 25,175 |
| MultiHop 667f | G1 | 8 | 102,306 | 27,469 | 27,469 |
| MMQA 0ed6 | G0 | 4 | 0; text/table evidence | 2,802 | 2,802 |
| MMQA 0ed6 | G1 | 4 | 0; text/table evidence | 2,876 | 2,876 |

The independent offline label overlap check found both annotated support documents with full stored body text in both MultiHop evidence sets for each task. Their combined body lengths were 27,045 characters for a647 and 26,460 for 667f. This establishes content reachability, not that the model extracted the correct relation. MMQA selected one of two supporting text IDs in both workflows; the nested table retained four headers and 24 rows. Source-side MultiHop G1 selected records lacked original article IDs and exposed only `_origin_shard`. All eight records in each reconstructed G1 set could be mapped uniquely back to an original article by offline content fingerprint, but that mapping was absent from the live trace.

Question-scoped G0 and whole-shard G1 source candidate pools differ, so the historical transfer and latency differences cannot isolate selection placement. The new [provenance check](provenance-check-public.json) demonstrates a gold-blind, question-named-publisher source-local index on the archived originals: four producer/task checks, exact original hashes, article IDs and full bodies validated after BM25 selection. One producer has zero in-scope articles for a647; the index records that fact rather than silently widening scope. This is a prepared new condition, not a retroactive repair of historical G1.

Machine-readable, redacted per-record shapes and token counts are in [evidence-interface-public.json](evidence-interface-public.json); support overlap counts are in [gold-overlap-public.json](gold-overlap-public.json). Raw corpus, questions, answers and reconstructed prompts remain only on the experiment machine.
