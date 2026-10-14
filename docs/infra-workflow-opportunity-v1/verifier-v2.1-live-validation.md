# Verifier v2.1 live request validation

Eight saved historical failure *contexts* were submitted as new request-level
tests to the same cloud `qwen3.8-max` endpoint. The original sensitive context,
provider output and gold were kept on the controller. The frozen case manifest
and [redacted result](../../results/infra-workflow-opportunity-v1/verifier-live-public.json)
identify each request by hash and preserve only validity, usage and latency.
These are fresh stochastic outputs, not exact replays of the old failures and
not reruns of the 36-cell task matrix.

The eight original strict responses all failed raw schema validation. In the
fresh requests, four first attempts were raw-schema and semantically valid;
four produced the known `evidence_state_version` type error. The bounded
protocol made exactly one additional provider attempt for each of those four.
All four recovered to raw-schema and semantic validity, yielding **8/8 valid
final decisions in 12 provider attempts**. No string-to-integer coercion was
used. Six final decisions were `complete` and passed candidate/evidence-version
binding plus the terminal contract against their historical context; two were
`continue`, for which terminal binding is inapplicable.

Observed total provider latency was 48.254 s, including **14.377 s extra**
recovery latency. Total reported usage was 177,003 input and 2,675 output
tokens; the four recovery attempts added 62,603 input and 938 output tokens
(including 16,128 reported cached input tokens in one shown case). A frozen
non-batch list-price/Fx estimate using reported cache usage is **$0.2259**
for all new attempts, **$0.0223** attributable to recovery attempts. This is
an estimate, not a provider invoice. Request-level success does not establish
correct task answers, historical failure-rate reduction in full Agent runs,
or savings after system-level retries.

Condition: bounded protocol recovery, at most two provider attempts, unchanged
strict JSON Schema, terminal contract and candidate binding. This is an
engineering reliability result, not an InfraMAS method gain. The previous
No-Go conclusion is unchanged.
