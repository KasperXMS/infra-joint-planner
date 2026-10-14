# Bounded environment feasibility results

This was a deterministic source/transport/evaluator integration check, **not** an LLM Planner trial or benchmark task-success result. Four MultiHop and four MultiModalQA Development questions were exercised once on physical Workers. Source-a ran on AGX Orin A4 and source-b on the workstation; each source store was persistent. The [final redacted receipt](feasibility-public.json) includes task IDs, operation types, output hashes, source/consumer, representation, bytes, latency and null model-cost fields.

| Check | Observed result |
|---|---|
| Base source identity/version | The initial 675-entry manifest was verified before the first probes (428/247 by node). The corrected 686-entry manifest was verified before the replacement probe (438/248). No undeclared base cross-node copy at either start. |
| Local operations | MultiHop BM25 ran separately on both resident shards for four questions. MultiModalQA text and table reads ran on their respective owners for four questions. |
| Remote data movement | 8/8 probe paths transferred source-a evidence/data to source-b via HTTP pull; 128,169 application bytes with matching size and SHA256. |
| Access control | Unauthenticated direct GET returned 403 on both Workers; protected semantic calls required action IDs. |
| Independent evaluation | 8/8 retained task answer contracts accepted their own gold in a **smoke check only**. Native evaluator parity on all 12 retained single-answer candidates: 36 prediction comparisons, 0 mismatches. No model answer was scored. |
| Calibration | Hslow/Hfast had distinct achieved rates on the same Worker-pull path; see [network accounting](network-and-cost-accounting.md). |
| Cleanup | 4 source-a and 12 source-b initial probe artifacts removed; one correction replica removed. Base 438/248 artifacts remained; all study Worker/proxy ports closed. |

An initial probe included a MultiModalQA three-answer task. Its short-text evaluator smoke was insufficient for the original list-answer contract. The [initial receipt](feasibility-initial-public.json) is retained; the case appears in [exclusions](manifests/excluded-candidates.jsonl). A different original single-answer task was checked after adding its benchmark-advertised candidate contexts to both source stores in a [separate correction receipt](feasibility-correction-public.json). The final eight-task receipt records both manifest sizes and explicitly names the correction. The added contexts do not alter the original MultiHop corpus or the earlier MMQA read probes. No answer-driven model rerun occurred.

Focused local validation covered public schema and Planner-view separation, deterministic placement, protected source reads, receipted operations, Worker-to-Worker pull/hash rejection, and restoration of base residency. Existing Worker/artifact tests also passed. The following are **not** established: full physical Controller isolation from source-b local files, image/video processing, end-to-end model answer quality, full corpus MultiModalQA retrieval, persistent index behavior, semantic equivalence of reduced evidence, or complete monetary/serving-state cost attribution.
