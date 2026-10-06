# Resident checkpoints149–150: exercised quote protocol, no D comparison

2026-10-06. Both original next scheduled cells ran once on execution004, without
replacement, tuning, altered budgets or new methods. Both completed normally,
passed terminal format and received original Video-MME evaluator score1.0.
The video representative is2, task hash prefix `e48bef6f0e60e753`.

| Metric |149: DeepSeek/Fast/D|150: Qwen/Slow/E|
|---|---:|---:|
| Manager / specialist / Verifier calls |13 / 6 / 3|4 / 0 / 4|
| Created specialists |1|0|
| Physical actions / returned inferences |7 / 3|2 / 1|
| Model deployment |A4/Qwen3-VL4B,3times|A4/Qwen3-VL4B,1time|
| Model input/output tokens, sum |11,153 / 6|6,627 / 2|
| E2E seconds |200.178980|114.269571|
| Complete Agent transfer bytes/time |0 / 0|0 / 0|
| Fixed initial bytes/time |7,037,220 /0.644797s|7,037,220 /19.708869s|
| Model service work seconds |63.018302|37.665085|
| Tool work seconds |1.369502|1.726008|
| Manager work seconds |81.147605|40.967236|
| Specialist work seconds |40.620888|0|
| Blind Verifier work seconds |10.003901|13.226304|
| Frozen list-price API USD estimate |0.198308979657|0.147212625732|
| Graph nodes / information-flow edges / snapshots |7 /29 /22|2 /6 /7|
| Actual SDK contexts audited |22|8|

Work sums overlap and are not an additive E2E decomposition. Input/output tokens
are actual backend receipts; graph edges include separate information-object
flows and are not a count of distinct node pairs. These rows differ in Planner,
network and method. Their latency/cost difference **cannot establish a causal
D-vs-E benefit**. No scores from other benchmarks are pooled with these scores.

##149: interface and natural continuation

Executed operator counts: extract_clip1, sample_frames1, make_contact_sheet2,
invoke_model3. One specialist performed its own finite-tool/model continuation.
No physical/logical execution failure was recorded, but there were6typed
`semantic_validation_failed` quote rejections during root planning. They were
observed by the Agent without manual repair; quote rejects are not inferences.

The actual quote lifecycle contains3quotes: one invoke_model quote discarded,
one extract_clip quote consumed and a later invoke_model quote consumed.
All3exact cards appeared in actual Manager input before first commit/discard:
respectively2,1,1input receipts. There were2authorized commits and2observed
executions. Visibility and lifecycle prove interface exposure/execution only;
they do not prove causal cost-rational revision or reveal private reasoning.
No known selection-failure quote was committed.

There were **zero real multi-candidate comparisons**, no candidate sets and no
post-comparison selections. D's distinguishing comparison mechanism therefore
was not exercised in this trajectory, despite its quote protocol being used.
Raw provider responses independently confirm2commit_quote calls; the replayed
SDK-input lower bound sees only1because the final response has no later input.
Actual-response counts, not that lower bound, are the complete call accounting.
This is not yet cross-Planner/workload evidence sufficient for pruning.

##150: no-query E and typed recovery

Physical sequence: sample_frames -> invoke_model. One semantic-validation
observation and one phase-restricted observation occurred, but only2actions
reached physical execution and1reached model inference. The Manager continued
to a valid terminal without retrying the experiment.

Frozen rules were visible in4root predecision inputs. Original E-isolation and
admission reconstruction passed: zero query-capable interfaces in actual
Manager requests, zero optional queries/cards/quotes/comparisons. No specialist
was created. Rule visibility does not establish internal adherence or causal
resource savings. Score1does not prove that all temporal evidence was retained.

## Provenance and continuation

Both original admissions independently reconstruct byte/canonical-equivalent
settlement evidence. Four empty Worker stores, verified Worker exits, all actual
SDK recipient-context/privacy scans, five resident model identities and tc
cleanup passed in each run. No inference/warm-up, Worker start or tc write was
introduced by the audits. Full JSONL/result/API bodies remain remote.

Remote root:`/home/super/xiaoming/large-scale-cost-guidance-resident-v1`.

| Append-only audit | SHA256 |
|---|---|
| `analysis/resident-source004-cell149-settlement-audit-001.json` | `b3be49e98868b76166b8ba9a7522b7a76efa2144e5477be2da8fe39520417fc9` |
| `analysis/resident-source004-cell149-quote-visibility-audit-001.json` | `3faa4bd0eabf959f043f1772cc180267517171d630e322ff4e8c8ddbf57998d0` |
| `analysis/resident-source004-cell150-settlement-audit-001.json` | `8deebdbaa9d5c05529e8620459dfdf7eaa741d30e2ed9434cd79fc6c5ab8e4d6` |

The independently audited new settlements bring the resident nominal count to
150/168, including prior valid failures. Snapshot050remains its original147/166
scope, not retrospectively rewritten. At14:11:19Z, Queue021 PID1114748and the
next Video2/DeepSeek/Slow/B0/attempt1atomic1155329were owned/live with four fresh
Worker starts and actual SDK-loop events. That151st cell was pending, not a
completed sample. Old42remain separate. Required all168/private semantic/
failure/recipient/adoption audits, frozen pruning, actual held-out PhaseII and
finalQ1–Q10remain outstanding. No PhaseII or new optimizer is authorized here.
