# H2 KEEP-only formal bridge feasibility

Two preregistered local 27B cells ran with the SDK-native formal bridge
enabled. This was a feasibility observation, not part of the H1 method
comparison. The bridge recorded only Manager-proposed actions and their
declared dependencies; no future workflow action was synthesized for the
experiment.

| Task | Proposed actions | Declared dependencies | Pending actions | KEEP available | Task outcome |
| --- | ---: | ---: | ---: | --- | --- |
| MultiHop-RAG 1 | 6 | 0 | 0 | No | Manager turn budget exhausted |
| LongBench-v2 1 | 1 | 0 | 0 | No | Verifier raw verdict schema failure |

All recorded actions were dispatched as they were proposed. Neither cell
exposed a pending frontier or reached a sealed plan with a successful
KEEP operation. The two task failures remain the actual outcomes; they were
not rerun. The MultiHop cell observed 20 Manager turns and 20 Verifier calls;
the LongBench cell observed one Manager turn and a malformed Verifier call.

These observations do not establish that H2 can naturally present a
meaningful, dependency-rich pending workflow to a future adapter. They also
do not test PATCH or show an H2 quality or cost gain. Stage 2 therefore uses
H1 with the bridge disabled, as frozen in the protocol.
