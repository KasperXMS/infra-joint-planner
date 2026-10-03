# Recipient-level profile isolation patch v1

2026-10-03. The user authorized autonomous repair of genuine implementation
defects after the recorded privacy hard-stop. Historical incident evidence and
the exclusions in the [hard-stop audit](predecision-specialist-profile-isolation-hard-stop-v1.md)
remain unchanged.

## Minimal repair

`OpenAIAgentsNativeRuntime` now requests dynamic tool-result profiles only for
the Aware root Manager. It defensively strips a profile from any Blind recipient
observation before state, logical trace and SDK tool return. Actual accumulated
SDK input is checked before every Blind recipient model call; a profile-bearing
tool result or explicit profile message fails closed. Physical execution and
selection telemetry are retained separately.

The immediate cell gate and retrospective audit inspect actual SDK tool-result
context, not only `current_anonymous_profile`. An externally interrupted primary
is retained as a hash-validated external record, never a fabricated normal result;
a clean authorized implementation-patch attempt may complete that cell.

No Manager/specialist/Verifier instruction, model, tool schema, semantic strategy,
budget, static capability, task representation, scheduler or network regime was
changed. Aware Manager pre-decision freshness remains unchanged.

## Regression evidence

- The original wrapper fails the two Aware specialist tool-context tests; its
  corresponding two Blind controls pass.
- Success and typed-failure recovery both preserve Blind specialist isolation.
- An actual installed Agents SDK integration exercises Manager -> specialist
  function tools -> model output -> Manager continuation; only the deterministic
  provider response is mocked, not the SDK tool execution.
- Explicit-profile and accumulated tool-result injection fail before inference.
- Immediate and retrospective gates detect leakage with a null direct profile.
- External-stop hashes and completion without a fabricated primary are tested.

Full verification: **479 pytest tests passed**, Ruff passed, strict Pyright
**0 errors / 0 warnings**; `git diff --check` passed.

## Authorized affected-cell reruns

Use a separately frozen isolation-patch manifest and new fresh namespaces,
once per cell, in the original relative order:

1. LongBench Financial Fast-Aware.
2. LongBench News Fast-Aware.
3. Video-MME 795-2 Slow-Aware.

Retain the other 21 clean new cells. Preserve all 27 existing new attempts.
Do not rerun the existing MultiHop block: its three affected Aware repetitions
remain excluded, leaving unequal admissible counts (FB=3, FA=1, SB=3, SA=2).
No score or clean completion is promised by this implementation repair.
