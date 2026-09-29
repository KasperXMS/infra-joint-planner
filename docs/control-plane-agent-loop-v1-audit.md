# Control Plane Agent Loop v1 — Architecture Audit

## Scope and status

This change replaces the formal control path, not the physical substrate. Existing benchmark
adapters/evaluators, operator implementations, artifact storage and transfer, worker APIs,
`RuntimeExecutor`, infrastructure observation/validation, traffic control, calibration, cost
profiles, and trace storage remain in place. No benchmark experiment was started.

The old complete-DAG `WorkflowBenchmarkRunner` and M4 iterative `BenchmarkRunner` are explicitly
marked **legacy historical-replay paths**. They remain unchanged apart from documentation so
frozen evidence can still be reproduced. New formal runs enter through
`ControlPlaneBenchmarkRunner`.

## Changed files

- New control plane: `src/infra_joint/control/{contracts,validation,physical,gateway,graph,loop,openai_agents,runner}.py`
- Compatibility annotations only: `src/infra_joint/core/workflow.py`,
  `src/infra_joint/{experiments,workflow}/runner.py`
- Packaging and developer entry points: `pyproject.toml`, `uv.lock`, `README.md`
- Tests: `tests/test_control_plane.py`
- This audit: `docs/control-plane-agent-loop-v1-audit.md`

```text
sanitized Task
    -> persistent Manager (optional bounded subagents-as-tools)
    -> LogicalToolAction | LogicalModelAction
    -> SemanticActionValidator
    -> ActionGateway
    -> PhysicalExecutionService
       -> InfrastructureObserver
       -> PhysicalFeasibilityValidator / AutoPhysicalScheduler
       -> RuntimeExecutor (existing transfer + execution substrate)
    -> LogicalObservation (+ optional abstract PhysicalProfileView)
    -> Manager state update / next decision
    -> execution-grown WorkflowGraph G0 -> G1 -> ...
    -> terminal model-action text
    -> original benchmark evaluator
```

## Boundary audit

### Logical layer

- `LogicalAgentSpec` contains only logical ID, role, and objective. It has no model instance or
  deployment binding.
- `LogicalToolAction` and `LogicalModelAction` have strict schemas. Unknown fields fail closed;
  physical directive keys and IP literals in action content are rejected.
- `LogicalModelAction` declares modality, minimum context, output reserve, capability, and optional
  quality-class requirements. It does not name a model deployment or device.
- `AgentTaskView` is the only task view admitted to manager/subagent context. `source_ref` and
  `evaluator_id` are absent.
- A manager may add bounded subagents, but their executable tool/model actions use the same
  gateway. One logical agent may have only one active action; independent subagents may run in
  parallel.
- Finish is deterministic: it must cite one successful model action owned by the finishing agent.
  The returned answer is exactly that action's `output.text`, checked against the declared output
  contract and then sent to the original evaluator. No finalizer model call exists.

### Physical layer

- `PhysicalFeasibilityValidator` consumes `EnvironmentSpec` and live `InfrastructureState`; the
  semantic validator does not.
- `AutoPhysicalScheduler` selects operator workers and model deployments from current availability,
  capabilities, modality/context preflight, requested quality class, and input locality.
- `PhysicalExecutionService` is the sole adapter above the unchanged `RuntimeExecutor`. It observes,
  selects, executes, re-observes materialized artifacts, and returns a sanitized logical
  observation plus physical telemetry for the trace.
- `PhysicalProfiler` reuses measured `ExecutionCostProfile` data and the existing transfer formula.
  Its logical-facing `PhysicalProfileView` contains only ranges/classes/counts—no worker,
  deployment, route, host, or IP identity.
- Blind mode passes no profile at all. Aware mode uses exactly the same `PhysicalProfileView`
  contract before decisions and on observations.

### Validation split

| Stage | Inputs | Checks |
| --- | --- | --- |
| Semantic | sanitized task, finite operator set, operator registry, grown graph | operator existence, JSON schema, known inputs, unique producers/actions, dependency readiness, model-output contract |
| Physical | environment and live infrastructure | worker/deployment availability, capability, modality, context/output budget, model request preflight, current reachability |

The semantic layer cannot import physical identity through either validation surface.

## OpenAI Agents SDK integration

`OpenAIAgentsManagerPolicy` and `OpenAIAgentsSubagentFactory` provide the SDK semantic adapter.
SDK agents return only structured next-step logical decisions. The application still owns state,
tool execution, deployment, and tracing; executable decisions always pass through `ActionGateway`.
Subagents are bounded tools returning results to the manager, which retains final-answer ownership.

The SDK is an optional `agents` dependency so substrate tests remain offline and deterministic.
This workstation had package metadata but not the wheel in its offline cache, so no network install
or real cloud call was attempted. The adapter invocation/schema path is covered with a contract
double. Before a live run, install the extra on an allowed host and exercise the configured API key.

## Minimal smoke results

No remote benchmark or infrastructure sweep was run. The local deterministic smoke exercised:

1. Manager creates an evidence-research subagent.
2. The subagent invokes `read_artifact`, observes the result, then invokes a model and materializes
   an `evidence` InformationObject.
3. The manager observes the subagent result, adds a terminal model action consuming `evidence`, and
   finishes from that exact model output.
4. All three physical actions (`tool`, subagent `model`, manager `model`) use one
   `RuntimeActionGateway`.
5. Trace events reconstruct logical decisions, subagent start/end, every graph snapshot from G0,
   logical observations, physical selections, deployments, transfer telemetry, and execution
   telemetry.
6. A runner-level smoke materializes a benchmark artifact, returns terminal answer `A`, and receives
   score `1.0` from the original private evaluator. Logical trace lines contain neither private
   benchmark metadata nor physical worker/deployment identity.
7. The same immutable `LogicalModelAction` was resolved to deployment A/device A when its input was
   on A and to deployment B/device B when the input was on B.

Tests added in `tests/test_control_plane.py` cover strict logical contracts, semantic/physical
validation separation, alternate physical bindings, abstract profile privacy, the optional SDK
adapter, persistent manager/subagent execution, terminal-answer provenance, original evaluator use,
and trace leakage.

## Verification

- Control-plane tests: `7 passed`
- Full pytest: passed (all existing and new tests)
- Ruff: passed
- Strict Pyright: passed
- `uv lock --check`: passed

The final formal workflow is:

`Task -> persistent Manager -> bounded subagent/tool decision -> ActionGateway -> PhysicalExecutionService -> RuntimeExecutor -> LogicalObservation -> next decision -> terminal model answer -> evaluator`
