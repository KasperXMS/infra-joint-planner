# Resident checkpoints 161–166: original scheduled outcomes

2026-10-07, Asia/Hong_Kong. Same resident diverse pool, execution APP004
(`0ff0e9b`), task set, SDK-native control plane, prompts, budgets, methods,
scheduler and evaluators. Each cell is its original attempt1; no retry,
replacement, prompt tuning or model reload. These are descriptive outcomes,
not a cross-method causal comparison or completed PhaseI semantic audit.

| Cell | Task / Planner / network / method | Completion / score | Manager / specialist / Verifier turns | Physical actions / actual inference | E2E | Complete action bytes / transfer work |
| --- | --- | --- | --- | --- | --- | --- |
|161|LongBench1 / Qwen / Fast / B1|yes /1|8 /0 /8|16 /1|108.313794s|217,558 /0.698214s|
|162|LongBench1 / DeepSeek / Slow / B0|yes /1|9 /16 /9|21 /1|230.220681s|unknown /unknown|
|163|LongBench1 / Qwen / Slow / E|yes /1|9 /8 /9|25 /1|168.599983s|75,799 /0.903110s|
|164|LongBench1 / DeepSeek / Fast / D|no /unknown|20 /0 /3|4 /0|134.826582s|unknown /unknown|
|165|LongBench2 / DeepSeek / Fast / E|yes /0|8 /8 /8|27 /1|204.574563s|0 /0s|
|166|LongBench2 / Qwen / Slow / B0|yes /0|9 /0 /9|9 /1|111.992818s|0 /0s|

All completed answers are format-valid and evaluated by the original evaluator.
164 has no terminal completion/evaluation: score and format validity remain
unknown, not zero. All six original admissions were independently rebuilt,
matched journal receipts and are valid nominal outcomes. Wrong answers and
budget exhaustion are preserved, not rescued. Specific semantic primary causes
for wrong answers await the post168 private audit.

## Work and telemetry

| Cell | Fixed initial bytes / work | Tool / model backend work | Manager / specialist / Verifier work | API list-price estimate | Model input / output tokens | Nodes / information-flow edges / snapshots |
| --- | --- | --- | --- | --- | --- | --- |
|161|514,789 /0.134199s|1.912594s /19.351654s|57.347343s /0s /27.922005s|USD0.199844047888|6,752 /2|16 /24 /49|
|162|514,789 /1.562873s|unknown /0.746096s|99.819043s /112.006147s /46.910647s|USD1.035586381695|763 /2|21 /17 /64|
|163|514,789 /1.607388s|2.549681s /19.537610s|81.656975s /22.933939s /33.710936s|USD0.369581547722|6,853 /2|25 /27 /76|
|164|514,789 /0.160065s|unknown /0s|124.807255s /0s /7.893180s|USD0.133218626344|no inference|4 /0 /13|
|165|2,119,778 /0.212788s|4.056138s /13.079435s|80.270063s /69.168404s /35.077579s|USD0.705666629905|1,043 /1,293|27 /28 /82|
|166|2,119,778 /5.996695s|2.690872s /14.535948s|56.815149s /0s /29.423713s|USD0.139358899268|5,097 /2|9 /6 /28|

Work sums overlap and are not additive E2E components. API prices are frozen
regional list-price estimates, not invoices; all listed role receipts are known.
162/164 each have two failed read_artifact executions lacking complete transfer
receipts: successful transfer subtotal is zero but full traffic remains unknown.
Their successful tool-work subtotals are2.709093s and0.090048s, respectively.
164's zero model service is observed zero actual inference, not imputed missing
telemetry. Fixed initial materialization is separate from Agent-controlled movement.

## Interface and failure observations

-161:12BM25,1aggregate,3model attempts;2context rejections then successful
  A4/VL4B text inference. Each of eight actual root API requests contains exactly
  one fresh profile matching its corresponding trace view; all eight actual
  Verifier requests contain none. Visibility is proven, adoption/benefit is not.
-162:9reads,7BM25,4model attempts,1aggregate;3context rejections and2oversized
  reads, followed by GPU0/Qwen3.5 inference. Two specialists are created with
  peak2 and two InformationObject handoffs. Both specialist results name terminal
  action IDs;8turns each alone does not prove specialist budget exhaustion.
  Peak physical concurrency2, five overlapping action pairs, three cross-owner
  pairs,2.068338s overlap; this does not establish causal E2E speedup.
-163:14BM25,5model attempts,2aggregates,4select_fields;4context rejections then
  A4 inference. Nine E rule views, no query/quote/comparison; internal adherence
  is unobservable. One specialist is created.
-164:two oversized reads and two successful BM25 executions. Exact terminal
  AgentLoopError is `manager turn budget exhausted`. Nine quotes created, four
  consumed, five discarded; the five proposed model quotes are not inference
  calls or physical context rejections. All five model cards report selection
  failure `context_limit_exceeded`; four have a supported abstract static request,
  one has `static_request_supported=false`. Actual artifact-context feasibility
  is distinct from the abstract class-envelope flag; these facts alone do not
  establish dynamic deployment unavailability.17control-only batches, six quote-level
  phase-restricted rejections,2.353740s quote-control work. One singleton
  comparison is visible but produces no selected/executed member. No real
  multi-alternative comparison. Immediate cause is the20-turn ceiling;
  contributing protocol/workflow and semantic sufficiency await full review.
-165:12BM25,4model attempts,7reads,1aggregate,3select_fields;3context rejections
  then GPU0 inference. One specialist, eight E views; quality0 is retained.
-166:6BM25 and3model attempts;2context rejections then A4 inference, with one
  additional semantic validation and phase-restricted observation. Quality0 is
  retained. Different task/method/Planner settings prohibit an E-versus-B0 claim.

## Evidence and continuity

All six cells: four initially empty stores, verified Worker exits, tc cleanup,
full actual SDK recipient/privacy scans and residency validation pass. Actual
SDK contexts161–166:16,34,26,23,24,18. Five runner identities match each preceding
cell's after-state and current before/after states: no loading-time correction,
restart or warm-up substitution. Benchmark bodies/gold/support are not exported
or read by these metadata audits. Separate live-start proofs are not fabricated
for cells already completed when inspected.

Remote root:`/home/super/xiaoming/large-scale-cost-guidance-resident-v1`.
Append-only files under`analysis/resident-source004-cellNNN-*`:

| Proof | SHA256 |
| --- | --- |
|161settlement|`313b5c1b4adc22db7c30800f7c31bfc4c557c4fbd5ce2148b97143ee7b010604`|
|161actual profile delivery|`8b671726ab34624f3f32fdd7b9e4b1b313296a3d9b019f65dcb45f24f3a9459d`|
|162settlement|`55bb7a7d18cc53bc16f1df1d31be4ca95f63711c62fd4089da7c1680d2260d99`|
|163settlement|`f1fab5cf0d7801ba6a4dd673c6b1928af4aaab67e63de2786cad680d98384230`|
|164settlement|`22deb88c8ec360c2363b138f9ae1b4ab9569e159aea38df96ea03261cd8f4f61`|
|164budget/comparison|`a9d97f55472b79548ecf9d20eb240c8cd32613416922e06abd4820b34850fa2b`|
|164quote feasibility|`3b663702ab4db716f9747635e707ab616ce6230aeaca588c3f178af4c815790d`|
|165settlement|`815f47fd9bbf7450898125876ddaffc3ee644d9799ea1514440f261b030b0648`|
|166settlement|`958a85933dde38fca99d87bb59c16cb2ebed56c374726d4fd2dcef9a69b702c1`|

166completed at17:27Z, Queue025 remains owned/live and two original cells remain.
Count166 is snapshot052's158 plus eight independent settlements, not a relabeled
snapshot. Old42remain unpooled. Full168/private semantic/failure/recipient/adoption
audit, method pruning, actual held-out PhaseII and finalQ1–Q10 remain outstanding.
