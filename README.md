# Infra-Aware Joint Planner

Greenfield implementation of an online joint semantic-physical planner for dynamic,
heterogeneous agent networks.

The repository currently implements the M0 contracts and the first M1 execution slice:

- benchmark-facing task and output contracts;
- static environment and dynamic infrastructure state contracts;
- typed semantic actions, physical decisions, and finish decisions;
- a single-source operator registry for planner schemas and runtime handlers;
- deterministic physical binding with explicit infeasibility errors;
- a Blind Planner control graph with a mandatory finalization node;
- HTTP runtime-to-worker execution through FastAPI and httpx;
- a pluggable OpenAI-compatible model backend with explicit credential injection;
- worker-local artifact storage and checksum-verified worker-to-worker pulls;
- live infrastructure snapshots assembled from worker-reported state;
- deterministic BM25 retrieval and typed structured-data operators;
- capability-gated FFmpeg sampling/clip extraction and deterministic contact sheets;
- benchmark execution/evaluation isolation and a full-video Video-MME identity adapter;
- LongBench-v2 identity, multi-document, and audited fixed-width structured adapters;
- MultiHop-RAG full-corpus and explicitly derived fixed-candidate adapters;
- a strict JSON LLM Blind Planner with AUTO-only physical placement;
- tool-free contract-aware finalization over logical evidence only;
- artifact-aware text/image model invocation with fail-closed context preflight;
- concrete per-worker deployment-to-backend mappings and startup surface validation;
- paper-facing latency, token, operator, model-service, and transfer telemetry;
- a YAML-configured benchmark runner with persisted result and JSONL trace;
- an evaluator kept outside the planning/execution loop;
- an append-only JSONL trace writer;
- a persistent checksum-verifying artifact store and YAML-driven worker CLI;
- contract and runtime invariant tests.

## Development

Python 3.12 and [`uv`](https://docs.astral.sh/uv/) are expected.

```bash
uv sync --extra dev
uv run pytest
uv run ruff check .
uv run pyright
```

Start the example worker (the checked-in example uses a deterministic backend and no secret):

```bash
uv run infra-joint worker --config configs/example-worker.yaml
```

Request one real Blind Planner decision through an OpenAI-compatible cloud model:

```bash
uv run infra-joint blind-plan-once \
  --config configs/example-planner.yaml \
  --objective "Choose the next logical action for this task"
```

Set the environment variable named by `api_key_env` before running the command. The secret
itself must not be placed in YAML, command-line arguments, traces, or Git.

For an OpenAI-compatible deployment, set `model.backend` to `openai_compatible` and put only
the environment-variable name in `api_key_env`. The key value must remain outside YAML and Git.

Worker YAML maps every deployment ID to its own backend, modalities, and context/output budgets.
Experiment YAML keeps `EnvironmentSpec`, worker URLs, initial artifact placements, Planner
configuration, and local materialization sources outside `TaskContract`. Pass the loaded
`RunnerConfig` and an adapter-produced `AdaptationBundle` to `BenchmarkRunner.run()`; the runner
validates each live worker surface before materializing or executing a task.

## Architectural invariants

1. `TaskContract` contains no infrastructure placement or benchmark gold data.
2. Semantic actions and physical decisions remain separately typed.
3. `OperatorRegistry` is the only source for planner tools and runtime bindings.
4. Explicit physical intent is rejected when infeasible, never silently overridden.
5. Unknown infrastructure measurements remain `None` instead of fake precision.
6. Planning and finalization budgets are separate concerns.

Secrets and machine-local topology must be supplied outside the repository. Never add API
keys, host addresses, or local deployment credentials to tracked configuration.
