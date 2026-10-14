# P0/P1 decision and final questions

**P0: Go for MultiHop-RAG and the text+table subset of MultiModalQA; CrossVid deferred.** Twelve original single-answer Development questions have authentic recoverable source data, publisher or modality-service identities, original scoring, two single-source controls and eight D2 cross-source candidates. The D2 count is an audit judgment, not a measured quality result. Three inspected candidates have explicit exclusion reasons. No final Validation/Test set was populated.

**P1: No-Go for a fully isolated distributed evaluation environment yet.** Persistent A4 and workstation source stores, genuine A4→workstation transfers, measured network profile effects, hashes, receipts, independent scoring and cleanup all worked. The workstation served simultaneously as `source-b` and Controller, and holds older raw benchmark copies accessible to the Controller OS account. The HTTP source guard cannot prevent direct local filesystem access. This is a material data-locality bypass; reporting P1 as fully passed would be misleading.

**P2 controlled fixed-workflow pilot: No-Go now.** W0 and W1 can be specified and their core data operations execute, and the original evaluator is usable. Before a quality/cost comparison, move the Controller to a host or OS boundary with no source mounts, verify source-b data/labels cannot be read except through receipted Worker RPC, and meter cold setup plus model-service state. Then run a small fixed-workflow quality check before any Planner adaptation. A workflow preference reversal is not a prerequisite; valid quality-constrained comparisons are.

| Final question | Answer from this v0.1 work |
|---|---|
| Q1: suitable originals? | MultiHop-RAG text and MultiModalQA text+table yes for bounded P1; CrossVid QA metadata yes, actual video deployment no. |
| Q2: genuine dependence? | D0 2, D1 2, D2 8 among retained 12; D2 rests on original cross-report/compositional questions and source inspection, not model failures. |
| Q3: partitions? | MultiHop original publisher identities with experimental physical hashing; MultiModalQA experimental text/table modality services; CrossVid not placed. |
| Q4: physical locality? | Distinct local ext4 volumes and a real LAN hop were verified. Controller/source-b OS co-location prevents strict no-bypass isolation. |
| Q5: Worker/operator compatibility? | Text BM25, text/table JSON read, artifact pull and hashes worked. Video/image/model contracts were not demonstrated. |
| Q6: communication vs initialization cost? | Resident payload transfer and two achieved network regimes were measured separately; compressed source staging is recorded. Full setup latency/package network bytes are unknown. |
| Q7: provenance? | Source artifact IDs/hashes, action receipts, output representations and producer→consumer transfers are traceable for probes. Semantic equivalence of reductions remains unproven. |
| Q8: native scoring without leakage? | Original evaluators retained; 36 single-answer parity checks matched. Planner projection excludes private labels. OS-level separation of private eval files on Controller is still needed. |
| Q9: distinct strategies? | W0/W1 are executable at transport/retrieval level for MultiHop and text+table tasks; neither has yet passed full task quality in this environment. |
| Q10: ready? | Not yet: fix Controller isolation, complete setup/serving observation, and perform one bounded original-quality W0/W1 validation. |

No Infra-aware advantage, Opportunity Coverage or Infrastructure Decision Sensitivity is claimed. No P2 experiment was started.
