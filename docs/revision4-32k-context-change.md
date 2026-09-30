# Revision-4 32K Context Change Record

## Motivation

The durable Revision-3 G0 was rejected before execution because its
`analyze-sorcerer` action had this conservative static envelope:

```text
required_context(analyze-sorcerer) = 27846
formal context_window              = 16384
```

The independent Ollama capability audit subsequently showed that the same
model and projector blobs, template, renderer, parser, and Q4_K_M quantization
pass the 28,672 and 32,768 formal envelopes on both A28 and `strong-4090` when
the model is instantiated with `num_ctx=32768`.

## Configuration inventory

| File or runtime surface | Field | Current value before Revision-4 | Role | Revision-4 action |
|---|---|---:|---|---|
| `configs/experiments/blind-baseline-environment-v2.yaml` | A28 `DeploymentSpec.context_window` | 16,384 | Environment loaded by the formal workflow runner through its frozen source benchmark config | Change to 32,768 |
| `configs/experiments/blind-baseline-environment-v2.yaml` | strong-4090 `DeploymentSpec.context_window` | 16,384 | Same formal environment contract | Change to 32,768 |
| A28 live Ollama tag `qwen3.8-27b-v1` | `PARAMETER num_ctx` | 16,384 | Backend runtime limit used by the formal Worker | Recreate the same tag from the same Modelfile with only `num_ctx=32768` |
| strong-4090 live Ollama tag `qwen3.8-27b-v1` | `PARAMETER num_ctx` | 16,384 | Backend runtime limit used by the formal Worker | Same one-line runtime change |
| Revision-4 fresh Worker configs | deployment `context_window` | not yet created | Worker `/state` surface must match the formal `EnvironmentSpec` | Create isolated evidence configs with 32,768 |
| `configs/experiments/blind-baseline-environment-v1.yaml` | `context_window` | 16,384 | Historical v1 baseline contract | No change |
| `configs/experiments/blind-budget-diagnostic-environment-v1.yaml` and its Worker configs | `context_window` | 16,384 | Separate completed budget diagnostic | No change |
| `scripts/heterogeneous_experiment_v1.py` | hard-coded 16,384 | 16,384 | Separate heterogeneous experiment | No change |
| tests containing 16K/other context fixtures | fixture values | varied | Unit-specific boundaries, not formal deployment configuration | No change |
| historical reports and calibration evidence | recorded 16K observations | 16,384 | Immutable evidence | No change |
| generic `DeploymentSpec`, capability projection, resolver, Worker, and preflight code | propagated `context_window` | configuration-driven | Enforcement and propagation logic | No code change |

The static capability model is derived from `EnvironmentSpec.deployments`, so
there is no separate static context constant to update. The Worker surface is
independently configured and is intentionally changed in the fresh replay
configuration so infrastructure consistency validation remains fail-closed.

## Approved change

Only the formal context deployment limit is approved:

```text
Ollama deployment num_ctx:
16384 -> 32768

DeploymentSpec.context_window:
16384 -> 32768
```

The prior attempt and `constructed-g0.json` remain immutable. A dedicated
replay harness may load that exact durable plan and exercise existing runner
APIs, but it may not call a Planner/Prior backend or alter the plan.

## Frozen variables

The following remain fixed:

```text
model blob
vision projector blob
model architecture
Q4_K_M quantization
template
renderer
parser
OLLAMA_KV_CACHE_TYPE=q8_0
OLLAMA_NUM_PARALLEL=1
OLLAMA_MAX_LOADED_MODELS=1
output reserve=1024
workflow definition
task
topology
model assignment requirements
network profiles
Planner logic
Prior logic and prior output
scheduler logic
tc profiles
evaluation logic
```

No cleanup, refactor, semantic tuning, retry, replacement, or matrix execution
is part of Revision-4 validation.
