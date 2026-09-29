# Resource-Blind SDK-Native Logical Adapter Audit

## Outcome

The formal resource-blind path now uses OpenAI Agents SDK native function tools and a
persistent Manager with bounded specialists exposed through `Agent.as_tool()`. The model no
longer emits the harness-owned `ManagerDecision`, `decision_type`, or `action_type`
discriminators. Every executable operator call is translated internally into a
`LogicalAction`, sent through the existing `ActionGateway`, and returned to the calling Agent
as a sanitized `LogicalObservation`.

The requested live validation did **not** produce three acceptable benchmark results. Video
and LongBench reached genuine native agent loops and ended in explainable semantic/stopping
failures. MultiHop exposed a pre-existing, global Worker artifact-state inconsistency and is an
invalid system/harness result. A final verification attempt stopped on that poisoned Worker
state before executing a physical action. No Aware run was started.

## Logical adapter changes

- Registered the frozen finite operator vocabulary as genuine SDK `FunctionTool` instances.
- Registered one bounded specialist template as an SDK agent-as-tool. The Manager retains the
  global task and final-answer ownership.
- Used the SDK's persistent native tool loop with `parallel_tool_calls=True`; graph snapshots
  are derived from actual calls and observations rather than model-authored future DAGs.
- Preserved the existing semantic validator, `ActionGateway`, scheduler,
  `PhysicalExecutionService`, `RuntimeExecutor`, Worker API, and benchmark/evaluator code.
- Returned execution, semantic, readiness, context, and capability failures as typed,
  sanitized observations. A malformed SDK argument payload is now a typed semantic failure
  rather than an SDK-level structured-output crash.
- Closed cancelled/in-flight actions as failed graph nodes, so a tool coroutine cancelled by
  the SDK cannot leave a terminal `running` node.
- Applied operator-schema defaults inside the adapter and preflighted the dynamic
  `sample_frames` output contract against a Planner-visible video duration.
- Added an opaque per-run namespace to derived artifact IDs. This prevents future runs from
  creating cross-run name collisions without exposing placement or infrastructure identity.
  Specialist results explicitly return the actual handed-off artifact IDs.
- Required the final answer to exactly equal a successful Manager-owned terminal
  `invoke_model` result.

The physical substrate was not modified.

## Contract and integration tests

`tests/test_native_agents.py` covers:

1. native function calls crossing `ActionGateway`;
2. typed tool failure followed by a legal next turn;
3. malformed tool arguments becoming a typed recoverable observation;
4. cancelled calls closing their graph nodes;
5. two independent BM25 calls executing concurrently;
6. a dependent model call failing readiness until its producer result exists;
7. Manager -> specialist-as-tool -> Manager continuation with explicit information handoff;
8. terminal-answer provenance from a successful Manager model action;
9. Blind logical-trace privacy and nested operator-schema compatibility.

An actual, dataset-free SDK/provider smoke also passed with the complete 12-tool schema and a
successful native terminal model action.

Final validation on the 4090 development host at `5e23ca57f3eb680b245c4fe3f855480daa814caa`:

| Check | Result |
|---|---:|
| Full pytest | 232 passed |
| Ruff | passed |
| Strict Pyright | 0 errors, 0 warnings |

## Frozen live settings

- Tasks: Video-MME 848-1, LongBench multi-document, MultiHop multi-source.
- Network: native/unshaped.
- Visibility: resource-blind; no `PhysicalProfileView` was injected.
- Manager: `deepseek-chat` through OpenAI Agents SDK.
- Budgets: 12 Manager turns, 8 specialist turns, 18 tool/model calls, 4 created
  specialists, 2 active specialists.
- Retry/replacement: disabled within every frozen attempt.
- Config SHA-256:
  `8f7d73b4208e01c1c7a3331e162cf0b2b6bb3388f6fecdeb8bd785f5e654c66b`.
- Public task bundle SHA-256 values:
  - Video: `713f6e1d945ca760d0080fd0dd4a74dc6a0dba1eaa4f44e09e4e157b677133ae`
  - LongBench: `6c22cd47f24cf3279fb317c752ff5c54ff49505aae9249251611ff0727bde341`
  - MultiHop: `54ef8ddbe4a3379254345f307b3f0ef6b95fe92e0b28ac4c89124bb6b7ebfe8e`

All benchmark datasets remained on the 4090 host. Only trace, result, progress, and public
freeze metadata were copied into the local ignored `results/` tree; no task contracts,
private evaluation records, or dataset payloads were copied locally.

## Three-case trace summary

The most complete three-case diagnostic attempt was frozen at
`9afa8aeca3b2412a26b487a4fb45faffddb1805c`. It predates only the subsequent run-scoped
artifact-name isolation change.

| Case | Native execution | Graph / Agents | Telemetry | Result and classification |
|---|---|---|---|---|
| Video-MME 848-1 | 18 accepted actions; 18 physical outcomes | 18 nodes, 141 edges; Manager plus `chapter-scout`, `sheet-reader-1`, `sheet-reader-2`; 12 succeeded, 6 failed | 21 reasoning completions; 408,228 transfer bytes / 64.10 ms; 478,309.61 aggregate operator ms; 275,551.28 model-service ms; 1,981/581 model input/output tokens; 486.20 s E2E | No terminal answer; Manager-turn budget exhausted. **Valid semantic/stopping failure**: it recovered from an oversized read and an infeasible specialist model request, performed additional sampling/clipping/contact-sheet analysis, then repeatedly requested infeasible model bindings and over-expanded to more specialists instead of stopping. |
| LongBench multi-document | 18 accepted actions; 18 physical outcomes | 18 nodes, 20 edges; Manager plus one `esg-analyst`; 12 succeeded, 6 failed | 13 reasoning completions; 64,048 transfer bytes / 240.70 ms; 470.99 aggregate operator ms; 32.56 s E2E | No terminal answer; tool/model-call budget exhausted. **Valid semantic planning failure**: four-way parallel retrieval and aggregation succeeded, but the specialist first attempted an oversized read, then issued five model calls that exceeded the advertised 16K context instead of reducing each retrieved artifact sufficiently. |
| MultiHop multi-source | 12 accepted actions before termination | 12 nodes, 14 edges; Manager only; 8 succeeded, 4 failed | 5 reasoning completions; 10 recorded physical outcomes; 3,024.99 aggregate operator ms; 9.20 s E2E | **Invalid system/harness result**. The Manager recovered from illegal multi-input `filter_records` calls by aggregating each three-shard branch, but a later action encountered globally inconsistent metadata for historical artifact `barb-poly-2`. A parallel sibling was cancelled and correctly closed as failed. No quality inference is permitted. |

No case reached the evaluator, so benchmark score and format validity are null rather than
zero. The traces nevertheless show real native continuation: Video changed from coarse
sampling to clipped/dense evidence acquisition and specialists; LongBench decomposed into
parallel retrieval and a specialist; MultiHop expanded across all three non-semantic corpus
shards and revised illegal filtering into aggregate-then-filter actions.

## Failure audit and stopping decision

Earlier shakedown evidence was retained rather than overwritten:

- a provider schema-reference incompatibility;
- malformed native tool JSON cancelling an in-flight sibling and leaving a stale graph state;
- an impossible `sample_frames` dynamic-output declaration;
- cross-run derived artifact name reuse.

Each adapter defect received a generic contract fix and regression test. The final attempt at
`5e23ca57f3eb680b245c4fe3f855480daa814caa` demonstrated the intended typed recovery from an
impossible sample request (`2040 s` requested coverage versus a known `2037.781 s` video), then
stopped because the observer still rejects the unrelated historical `barb-poly-2` metadata
conflict globally. Its graph correctly ends the attempted action as failed, and the new derived
ID is namespaced.

Removing that blocker requires an experimental-environment decision outside this task's
Logical-adapter-only scope: either start isolated fresh Worker processes/stores or change the
physical observer's global artifact-consistency policy. This audit therefore stops without
clearing Worker state, restarting services, changing physical code, running another attempt,
or starting Aware.

Live logical-event scans found none of `source_ref`, `evaluator_id`, worker/deployment
selection, IP address, bandwidth, RTT, queue depth, or placement fields. Physical selections
remain confined to physical telemetry.

## Evidence locations

- Complete diagnostic attempt: `results/resource-blind-live-validation-v1-sdk-native/v4/`
- Final stopped attempt with current adapter: `results/resource-blind-live-validation-v1-sdk-native/v5/`
- Remote immutable evidence roots:
  - `/home/super/xiaoming/resource_blind_live_validation_v1/evidence-sdk-native-v4`
  - `/home/super/xiaoming/resource_blind_live_validation_v1/evidence-sdk-native-v5`

The requested acceptance condition is therefore only partially met: the native SDK control
contract and natural continuation are demonstrated, but a clean three-case Blind validation
cannot be claimed until Worker artifact-state isolation is reviewed.
