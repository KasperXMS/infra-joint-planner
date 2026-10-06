# Held-out control preparation: physical JSONL boundaries

2026-10-07. Prelaunch inspection found the historical held-out controller and
its quote-admission wrapper using string `splitlines()` to parse trace JSONL.
Legal model-generated strings may contain U+2028/U+2029/U+0085; string splitting
would treat them as record boundaries and falsely reject a completed run.
No actual Phase II cell was launched before this correction.

Minimal control-only fix, commit `87b71d7`:

- `scripts/large_scale_resident_phase2_queue_v1.py` reuses the existing
  `JsonlTraceWriter.read_all()` for its E surface scan and a held-out admission
  wrapper. Base `frozen.admit` and the exact `quoted_action_mutated` rejection
  are preserved; no historical controller is edited remotely.
- `tests/test_resident_phase2_queue.py` covers all three separators for normal
  and quote-mutation admissions, E isolation pass/reject, and malformed JSON
  remaining fail-closed. Existing atomic-child/no-retry/current-gate tests remain.

No measured execution004 source, Agent behavior, prompts, semantic tools,
benchmark/evaluator, model pool, budget, placement or scheduler changes. The
atomic child remains selected from source004 only. Test runs make zero cloud or
physical model calls and do not instantiate real experimental Workers.

## Validation

- Full pytest:1694 passed,7 Windows platform/symlink skips, exit0.
- Ruff:pass. Project strict Pyright and explicit new controller check:
  0errors/0warnings. `git diff --check`:pass.
- Actual4090 controller integration:42passed in1.35s, no warnings in log002.
  The first log001 passed but had a pytest cache permission warning due
  `/dev/null` config rooting the cache in `/dev`; it is preserved. Log002 merely
  disables cacheprovider; no code, model or experimental condition changed.

Separate remote namespace:
`audit-tools/resident-phase2-jsonl-control-001`, under the resident4090 root.

| Proof | SHA256 |
| --- | --- |
| Code-only archive | `decc67fa04e674344f5a8700459138f1b6c748880063738d4c816032d97401f8` |
| Corrected controller source | `5f33604551fa75cac89d940373ff8ac8e0e2890d1aeea754785aabd0a48f66b4` |
| Linux tests log002 | `a1b4cec9e5b1f8dd2d88fe7664d3230ac995a793b5aba09dd470f3cc84ab4f9b` |
| Actual validation receipt001 | `b3970396ae0adf86de95392f04ac951abc655fce29088e8f95b036ce27900a83` |

All archive members were checked before extraction into a new empty namespace.
No dataset/model/fulltrace/APIbody transits the development PC. Historical
evidence/controllers and Phase I journal remain immutable. Actual Phase II gate
and control persistence, source closures and process launch must be verified
separately; these tests do not authorize a fake completion or imply a live queue.
