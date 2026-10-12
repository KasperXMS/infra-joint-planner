# Failure decomposition

Descriptive partitions, not causal first-failure attribution. Wrong-answer branches concern submitted numeric results; rejected calls can coexist with policy errors. Zero valid compute is not evidence of correct operation choice. Original numeric evaluator and every outcome are unchanged.

| Observed outcome/history | Episodes |
| --- | --- |
| Numeric success; all executed policies correct | 14 |
| Numeric success; compliant submitted ancestry after an earlier policy error | 6 |
| Numeric success; retained policy violation | 2 |
| Wrong answer; no unexpected tool error | 333 |
| Wrong answer; unexpected tool error also observed | 75 |
| Turn exhaustion; no valid computation executed | 22 |
| Turn exhaustion; a valid computation chose a wrong policy | 52 |
| Turn exhaustion; valid partial computation, no observed policy error | 0 |

Total: 504 frozen episodes. Zero-valid-compute failures contain these rejected tool calls: `{"dependency_mismatch": 1342}`.

A valid computation means the tool accepted the declared ordered dependencies and produced an artifact; an invalid compute request is not counted as an executed policy decision. The all-executed-policies-correct field is vacuously true when this count is zero. Such failures belong to dependency execution, not demonstrated branch competence.

Policy-compliant submitted ancestry after an earlier wrong computation does not prove intentional recognition or repair; an update can invalidate and discard an old path. Unexpected errors exclude the task's expected source-update/transient notifications. No output is selectively rerun.

Per-model/condition, depth and per-episode identities are retained in the accompanying JSON; decisions, input values and raw generations are absent.
