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
- an evaluator kept outside the planning/execution loop;
- an append-only JSONL trace writer;
- contract and runtime invariant tests.

## Development

Python 3.12 and [`uv`](https://docs.astral.sh/uv/) are expected.

```bash
uv sync --extra dev
uv run pytest
uv run ruff check .
uv run pyright
```

## Architectural invariants

1. `TaskContract` contains no infrastructure placement or benchmark gold data.
2. Semantic actions and physical decisions remain separately typed.
3. `OperatorRegistry` is the only source for planner tools and runtime bindings.
4. Explicit physical intent is rejected when infeasible, never silently overridden.
5. Unknown infrastructure measurements remain `None` instead of fake precision.
6. Planning and finalization budgets are separate concerns.

Secrets and machine-local topology must be supplied outside the repository. Never add API
keys, host addresses, or local deployment credentials to tracked configuration.
