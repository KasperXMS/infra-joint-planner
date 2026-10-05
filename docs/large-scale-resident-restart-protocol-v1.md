# Resident, diverse-pool restart protocol v1

2026-10-05, Asia/Hong_Kong. User decision: restart with the new experiment.
The predecessor 42-cell block is closed to further scheduled runs, not deleted,
overwritten, retroactively warmed, or combined with this environment.

## Scope and budget

Keep the same 18 frozen tasks, benchmark representations, original private
evaluators, initial placements, two cloud Planners, fixed Blind Qwen Verifier,
Manager/Verifier instructions, finite operators, 20/64/20 budgets, existing
physical scheduler and privacy contracts. The approved change is the physical
model pool and explicitly resident execution protocol, not a new routing method.

New Phase I: 2 Planners × 3 families × 2 representative tasks × 2 networks ×
7 methods = **168 cells**, n=1, new run IDs and balanced preregistered schedule.
All B0/B1/A/B/C/D/E remain; there is no mid-Phase-I pruning.

Previous 42 substantive cells remain in the global counter. Therefore the new
Phase I brings cumulative substantive cells to 210. New Phase II contributes
48m cells after full new-block audit and frozen method selection. Within the
unchanged 420 ceiling, at most four complete Phase II methods fit: totals are
354 for m=3 and 402 for m=4; m=5 would total450 and is prohibited. The method
list is not selected now. Core B0/B1/A remain the intended baseline set;
additional candidates require the original quality/adoption/overhead criteria.
Operationally excluded attempts remain separately recorded and immutable.

Authoritative new root:
`/home/super/xiaoming/large-scale-cost-guidance-resident-v1`.
Models/runtimes remain in the separate remote resident-model-pool-v1 preparation
roots. Benchmark and model/runtime payloads never transit the development PC.

## Calibration before experiment activation

The candidate pool remains three artifacts/five instances: A4 4B Instruct,
A5 8B Instruct, A28 27.3B qwen35, GPU0 the same27.3B, GPU1 the same8B Instruct.
Do not call them five different models or invent quality classes from scale.

Start separate localhost Ollama0.34.0 servers with isolated stores. GPU0/GPU1
are separately bound by the observed GPU UUIDs. Preserve source tags, weights,
quantization, template and sampling parameters; create new derived tags only,
changing num_ctx to32768. Freeze q8_0 KV cache, flash attention, one parallel
request/one loaded model per server, and infinite keep-alive. Verify actual
parameters/weight hashes after creation; reject unexpected changes.

Use deterministic nonbenchmark synthetic text/images through the existing
OpenAI-compatible backend and runtime preflight, retries0, timeout1200s.
Separate setup loading/warm-up from measured warm requests. Record actual
input/output tokens, finish reason, service latency, actual server context,
memory/GPU placement, errors and log truncation findings. Byte-based conservative
preflight context estimates are not backend tokenizer counts. Never claim a
32K actual-token test from a32K-byte payload.

Verify five instances simultaneously resident, true GPU offload, no OOM or
silent truncation, text/image capability and32K/2048 agreement. Measure new
service/concurrency profiles or preserve unknown; never transfer a27B profile
to4B/8B. Calibrated anonymous static capability is shared by all methods.

No benchmark execution before new environment/harness/schedule/source/pricing/
profile freezes, fresh-Worker surface validation, and full tests. Retain pre/post
residency attestations on every cell. An unexpected eviction/reload or external
GPU conflict is a measurement confounder, not a startup constant to subtract.

## Evidence boundaries

The predecessor snapshot027 remains immutable at42/168,38 evaluated/four
unevaluated/two separate implementation-confounded attempts. Its SHA-256 is
`4f479383fa0e2e6a4ca041bd842a1615302046ece27166ccc55fb367bb2fbe5d`.
Its admission reviews do not authorize replacements or add old samples to the
new matched matrix. Old-pool evidence is historical/environment-specific.
No old/full-block supporting-evidence audit is fed to the new Agent.

New block initially has **zero benchmark cells**. Calibration permission does
not assert a validated deployment or grant an unrecorded schedule change.
See [cutover config](../configs/preparation/resident-model-pool-v1-cutover.yaml)
and [preparation audit](resident-model-pool-preparation-audit-v1.md).

Cutover receipt SHA-256:
`45d4f16ba36e194b0c4b3c03468183f0dd0c86153cd6738b683b51f1f0045b23`,
in the new root's `protocol/block-cutover-001.json`. Old journal SHA-256 remains
`bddc83d7ef5230d3aca3c440602cea25bfd8be34bea6ceba47c3ce8746c0fb86`.

Bootstrap tests cover separate GPU/store/port bindings, explicit noninherited
resident settings, path rejection, source identity/parameter preservation, and
the retained-old-cell budget. Full local regression:972 tests pass in35.12s,
Ruff/strictPyright/diff checks pass. No core runtime or logical instructions are
modified by this bootstrap.

Service-setting references: [derived model creation](https://docs.ollama.com/api/create),
[residency/KV/concurrency settings](https://docs.ollama.com/faq), and
[GPU binding](https://docs.ollama.com/gpu). Actual installed0.34.0 behavior must
still pass live verification; documentation is not a calibration result.
