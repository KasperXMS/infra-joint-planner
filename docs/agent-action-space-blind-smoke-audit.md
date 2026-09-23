# Agent action-space contract and Blind Smoke audit

## Contract change

The contract is now:

`System finite operator vocabulary + WorkloadSpec + environment/model contracts -> per-agent feasible action space -> Planner selects/composes actions`

It is no longer:

`Planner declares allowed_operations + Planner selects actions`

`LogicalAgent` contains only its ID, role, objective, and fixed model-instance binding. The Planner schema and prompt contain no `allowed_operations`. For each binding, the system intersects `WorkloadSpec.available_operations` with registered operator requirements. Generic operators require at least one capable physical execution surface; model operators require the bound deployment host capability. Each `invoke_model` node is additionally checked against the media types of its actual input artifacts and the bound deployment modalities. The plan validator and `AgentManager` consume the same derived mapping and reject outside-workload, unknown, capability-infeasible, and modality-infeasible actions before execution.

The workflow remains open-ended over logical-agent count, roles, arguments, node count, DAG topology, dependencies, and handoffs, while operator IDs remain finite and system-owned.

## Changed implementation and tests

- `src/infra_joint/core/workflow.py`: removed Planner-owned capabilities and added system feasibility/modality validation.
- `src/infra_joint/workflow/planner.py`: removed the field from the output contract and exposes only the system-derived feasible operator list for each opaque model instance.
- `src/infra_joint/agents/manager.py`: enforces the derived map fail-closed.
- `src/infra_joint/workflow/orchestrator.py` and `runner.py`: pass the finite workload action space through validation and execution.
- `src/infra_joint/operators/registry.py`, `worker/server.py`, and `infrastructure/validation.py`: added deterministic operator-contract digests so a stale remote schema fails during startup/preflight.
- Tests cover legal selection, absent workload operators, unavailable capabilities, unsupported modalities, shared deployments, removal/rejection of `allowed_operations`, and remote operator-contract drift.

Validation on commit `6192e8cca417afe769d3ccb6635c9ff65bbe3be5`:

- full pytest: 179 passed
- Ruff: passed
- strict Pyright: 0 errors, 0 warnings

## Smoke audit

The first post-refactor attempt is preserved under `results/open-ended-mas-preliminary-v1/blind-baseline-smoke-v1-system-action-space`. It stopped fail-closed on `01-image-table-native`: the remote workers still exposed the pre-materialization `invoke_model` argument schema even though their operator IDs matched. This was a system/harness confounder, not a Planner failure. No retry occurred in that evidence directory. The worker code was synchronized, the processes on ports 9104/9105/9128/9212 were restarted, and exact operator-contract digest validation was added before a new one-shot smoke.

The clean rerun is under `results/open-ended-mas-preliminary-v1/blind-baseline-smoke-v2-system-action-space-synced`. Each task received one new Planner call; no completion or workflow was reused, and the Planner prompt was not tuned after observing results.

| Task | Frozen workflow SHA-256 | Natural workflow | Execution | Terminal/evaluator | Decision |
|---|---|---|---|---|---|
| image + table | `0a51f735332482580c7491c3a1188fe2059b903c2ebb94d8231894d91b68fa3a` | 3 active agents; 2 model agents; 2 cross-agent handoffs; model-output handoff; fan-in 2 | Completed on native/unshaped network; all nodes/agents done | `A sailing ship`; format valid; official score 0.0 | Valid semantic/model quality failure; not accepted/frozen |
| image + text | `68e707cd1a208a5ed60bb1c86ca9ff5f4a024830c82224d55dde9f1b96afa1d0` | 4 active roles but only the terminal agent invokes a model; no model-output handoff; fan-in 3 | Paused before execution by the predeclared trivial-workflow rule | Not evaluated | Recorded and paused; no forced MAS |

For the executed image + table workflow:

- benchmark-faithful adaptation: true
- privacy leakage in agent traces: none
- trace: 63 events, parent chain valid, all required events present, reconstructable
- actual model placements: visual agent on `strong-4090`; terminal synthesizer on `A28`
- transfer: 79,789 bytes in 288.064 ms, including real image transfer to `strong-4090` and model-output transfer back to `A28`
- workflow E2E: 45,043.625 ms; runner E2E: 67,306.724 ms
- critical path: 18,418.375 ms; maximum parallelism: 2; observed overlap: 110.350 ms
- model service: 17,912.893 ms total; calls finished with `stop`
- operator latency: 18,329.022 ms total
- terminal-agent output went directly to the original MultiModalQA evaluator

No accepted workflow freeze was created because neither task met all acceptance conditions. No 3/10/30 Mbps replay or method experiment was started.
