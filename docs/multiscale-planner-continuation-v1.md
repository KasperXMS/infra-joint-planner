# Contended-host continuation, 2026-10-11

The initial run stopped after three executed Qwen3.5 4B cells because an unrelated
GPU process appeared during the third cell. The original stop record remains
immutable. The user explicitly prohibited pausing that process and authorized
continuing our experiment with the contention recorded.

The three existing task attempts are retained without inference retries. Their
outcomes are two noncompletions and one completed Video-MME task with score 1.
The third cell's reporting is recovered from its original result and cleanup
evidence; its independent Planner service work is unknown because the original
postprocessor did not persist the log offset. Full residency snapshots remain
private, including the foreign process. Historical results and No-Go decisions
remain unchanged.

Only the newly created 4B, 9B and Ministral 3 Planner services move to A28, using
the same verified weight files, Ollama version, parser, template, sampling and 32K
context preflight. The existing Executor services remain unchanged. The new A28
service uses its own model store, API port and tokenizer tunnel. No new model
capability tests are added. The original 60-hour deadline and 42-cell ceiling
remain in force.

At request boundaries, resource samples are refreshed at most every five seconds.
Both controller GPUs must retain at least 512 MiB free, and A28 must retain at
least 8 GiB available RAM. Original Executor identity, resident context, log-prefix,
reload, OOM, truncation, Worker cleanup and network restoration checks remain
active. The GPU process-set comparison now verifies the calibrated Executor/RPC
processes; foreign activity is recorded rather than treated as unauthorized drift.
Foreign processes are never paused, stopped or changed. The 512 MiB reserve is
declared before new benchmark calls: A28 Managers use its unified-memory GPU, so the
original 2,048 MiB new-GPU-model loading threshold no longer applies to their
deployment. Actual OOM still stops execution.

A brief GPU1 dip to 29 MiB after the first 9B task caused a stop before the next
cell. That task completed with score 0 and is retained. Continuation 004 keeps the
same resource limits and first waits for recovery: up to 240 seconds before a
request or 600 seconds between cells. Waiting consumes the original wall budget;
prolonged exhaustion, OOM or other system faults still stop. The Skills selection
remains the initial 9B/27B declaration; this later resource-only amendment does not
change it. Focused offline checks cover transient recovery and bounded exhaustion.

The first three 4B cells used controller GPU1; its remaining three use A28. Their
resource results therefore require placement stratification. To preserve a
matched Skills comparison, the two Skills models change from 4B/27B to **9B/27B**,
frozen before the first 9B benchmark result. This is a placement decision and does
not depend on scores. Every admitted plain model still receives six tasks; both
Skills models receive six additional tasks, with no selective reruns.

The nominal `qwen35-27b` deployment is verified as **Qwen3.8-27B Q4_K_M**, not
Qwen3.5-27B. Its existing weights are retained. Qwen3.5 size comparisons therefore
cover 4B and 9B only; comparisons involving 27B also differ in release, placement
and speculative decoding. No parameter-count-only causal claim is warranted.

Runtime amendments and continuation source hashes are written outside the
immutable experiment app. Startup failures (import path, missing log-path key and
an append-only tokenizer-log name collision) made no benchmark calls; all logs
and freezes remain. Only previously unexecuted conditions are dispatched by the
successful continuation. Raw evidence remains on the experiment hosts.
