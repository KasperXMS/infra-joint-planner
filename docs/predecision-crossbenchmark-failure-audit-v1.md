# Cross-benchmark exception audit v1

## Pre-run JSONL diagnostic regression

Before formal runs, the source pool was audited on the 4090. A diagnostic using
`read_text().splitlines()` falsely appeared to show malformed JSONL. Physical-line
iteration verified **all 208 records parse**: embedded Unicode U+2028/U+2029 is legal
inside a JSON string but Python `splitlines()` splits it. Source bytes were neither
modified nor discarded. This was a diagnostic/parser defect, not dataset corruption.

The same concrete defect existed in the lightweight queue's trace parser. A synthetic
regression puts U+2028/U+2029 inside an observation and proves the old parser fails on
valid JSONL. The generic queue parser now splits only LF, and the new cross-benchmark
summary uses existing `JsonlTraceWriter.read_all()` (physical file iteration).
Native runtime, prompts, evaluator, actions and physical execution are unchanged.
Frozen MultiHop component sources/manifest and completed evidence are preserved.

No formal cell had started; no experimental retry or historical MultiHop rerun is
needed. The fix is an instrumentation correctness fix, not semantic tuning.

## Formal attempts

Pending. Preserve all primary and authorized operational replacement evidence.
