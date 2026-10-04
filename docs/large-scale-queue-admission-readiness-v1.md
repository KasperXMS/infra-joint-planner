# Formal queue and recipient admission v1

2026-10-05. Execution revision: 5ca3fff16c66e6dafaf583d53e5d07dfc88a2a28.
**Phase I has started; this is not a completed-result report.**

## Changes outside the frozen control plane

- Append-only, fsynced, hash-linked attempt journal with exclusive queue ownership.
  A pending reservation cannot be interpreted as an observation timeout/retry.
  Completed nominal cells cannot be repeated or reordered. Ordinary wrong answers
  and logical/budget failures are retained as valid samples.
- One identical operational replacement is representable only for the declared
  operational failure classes. The queue stops for reconciliation rather than
  automatically repeating an excluded attempt. Confounders stop continuation.
- One common remote queue consumes the already frozen 168-cell balanced order.
  Every attempt has a new run ID, child process, fresh Worker processes/stores,
  network attestation, trace/result and append-only admission receipt.
- Existing Worker preparation/start/stop and tc implementation are reused. Partial
  startup PIDs are immediately persisted; shutdown verifies actual owned process
  exit before shared ports can be reused. Pre-run failures also retain result and
  JSONL evidence, without a fabricated answer or evaluator score.
- Recipient audit scans actual HTTP messages, including instructions and accumulated
  JSON tool results, and also checks native input provenance and feedback ordering.
  B1 alone receives root anonymous profiles; specialists/Verifier remain Blind.
  Cost feedback permissions are method-specific. Worker endpoints/deployment strings
  are compared privately; raw contexts never pass through the development PC.
- Raw provider usage/model identities/cost receipts are recomputed against frozen
  prices and FX, preserving unknown costs. Actual complete-run admission also
  checks trace chains, observer probes, artifact persistence, tc restoration and
  verified Worker cleanup. Unknown execution incidents require audit.
- Original MultiHop free-text answers are not forced into historical Yes/No labels.
  Wrong evaluator scores are not admission failures.

No Manager/Verifier instructions, stopping, native runtime, operator, scheduler,
model pool, benchmark/evaluator, task, method feedback, budget or physical substrate
was modified.

## Tests

56 new synthetic tests cover journal integrity/order/cap, lease ownership,
pending-attempt restart refusal, one operational replacement, recipient/method
isolation, nested accumulated tool results, exact pre-decision profiles, raw
usage/model/cost drift, provider versus protocol failures, full original free-text
admission, trace chains, queue retention/hard stops, pre-run evidence and partial
Worker cleanup. Existing all-seven-method real SDK integration now also exercises
the common effective-input audit.

Full pytest: **696 passed**. Ruff passed; strict Pyright zero errors/warnings;
git diff --check passed. Synthetic tests do not establish live benchmark quality.

## Remote execution receipts

- Source-only archive SHA-256:
  824fb1c270d28594981fb610906a1ab260b255bc1ba972f102451a241a4b7652.
- Identical source archive deployed to controller and A4/A5/A28, reusing their
  existing locked Python environments. No benchmark data passed through the PC.
- Execution freeze file SHA-256:
  38c9b72f641e22ddef770828221d4e4d41b7fa25a506f3e8b99bc7e337953133.
  Contains 362 source/config hashes plus existing task, price, history, rules,
  schedule and fixed-Verifier receipts.
- Remote root: /home/super/xiaoming/large-scale-cost-guidance-v1.
- Deployment receipt: readiness/queue-source-deployment-001.json.
- Freeze process receipt: readiness/queue-execution-freeze-process-001.json.
- Queue process receipt: queue-process-001.json; parent PID **1200364**.

Authoritative launch observation: parent owned/live; one durable reservation;
first child PID **1200650**; all four Workers started; zero settled cells.
First frozen cell: phase1-video_mme-1-7ea6434bc064f69c-p2-fast-B1.
This records an actual execution start, not admission or successful completion.
Later state must be checked against the specific process and append-only receipts.

Remaining: run/admit/audit all 168 cells, resolve genuine incidents without semantic
tuning, freeze justified Phase II pruning/schedule, complete its remaining block
within the 420 substantive-cell cap, and produce all requested final analyses.
Phase II has not started. No method is selected or promoted at this checkpoint.
