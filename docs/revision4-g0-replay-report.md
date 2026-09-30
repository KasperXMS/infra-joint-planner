# Revision-4 G0 32K Replay Report

## 1. Objective

Apply the independently calibrated 32K context setting to the formal A28 and
`strong-4090` deployments, then replay only the durable Revision-3 G0 that had
previously been rejected at its first context gate. The replay was permitted
only after complete static validation. No 2x2 matrix cell was authorized.

## 2. Previous G0 rejection

The immutable source is attempt
`20260929T222546551722Z-f19f3017aed8`, task
`multihop-rag-train-9bae0079038050a37a1ae583`, canonical G0 SHA-256:

```text
c964883c32fa4b144bffdf77a153e57c438d802adb361c6d9e3739c8617b459f
```

Its first rejected action was:

```text
required_context(analyze-sorcerer) = 27846
formal context_window              = 16384
```

The original attempt, raw completion, draft, constructed G0, and validation
result were not edited or overwritten.

## 3. Revision-4 configuration change

The audit was first committed independently as `7b1d5c1` (`docs: add Ollama
context capability audit`). The approved configuration change is commit
`cccfe30`; the immutable replay harness is commit `8ad3d96`.

Repository deployment diff:

```diff
 A28 DeploymentSpec.context_window:
-16384
+32768

 strong-4090 DeploymentSpec.context_window:
-16384
+32768
```

On each live Ollama endpoint, the official `qwen3.8-27b-v1` tag was rebuilt
from its saved Modelfile with exactly one parameter change:

```diff
-PARAMETER num_ctx 16384
+PARAMETER num_ctx 32768
```

Both official tags now resolve to manifest `0ae0a0db78e8`, the same manifest as
the already validated independent 32K calibration tag. The calibration tag was
not modified.

## 4. Frozen variables

The following remained unchanged:

- model blob: `f5f1dd8920d417aac2718b0bda3403da274301efdd6760b4f0f4b864ff2ad57d`;
- vision projector blob: `ac3714bfdddeca31351f2752bf1a63f266f4df87c0b68c895e44945ca704448e`;
- both blob contents independently matched those SHA-256 values on both nodes;
- Qwen `qwen35`, 27.3B, Q4_K_M, template, renderer, parser, and projector;
- `OLLAMA_KV_CACHE_TYPE=q8_0`, `OLLAMA_NUM_PARALLEL=1`, and
  `OLLAMA_MAX_LOADED_MODELS=1`; the Ollama services were not restarted;
- reserved output 1,024, task, G0 actions, dependencies, terminal action,
  Planner/Prior logic and output, scheduler, network/tc profiles, and evaluator.

No model re-quantization, workflow edit, prompt edit, parser edit, retry, or
replacement occurred.

## 5. Static validation

The targeted context diagnosis passed under the new contract:

```text
official deployment num_ctx        = 32768 (A28 and strong-4090)
DeploymentSpec.context_window      = 32768 (both deployments)
required_context(analyze-sorcerer) = 27846
remaining conservative capacity   = 4922
analyze-sorcerer failure           = null
```

Thus the original 16K context blocker is resolved and propagated correctly.

Complete-plan static validation then continued beyond the formerly failing
action and failed closed at a newly exposed downstream action:

```text
WorkflowValidationError
  caused by StaticFeasibilityError:
  invoke_model has no static model class fitting its actual prompt/artifact
  context envelope: action=compare-guides;
  unknown input bounds=['sorcerer-analysis', 'barbarian-analysis']
```

The relevant unchanged path is:

```text
retrieve-sorcerer -> analyze-sorcerer -> sorcerer-analysis --+
                                                               +-> compare-guides
retrieve-barbarian -> analyze-barbarian -> barbarian-analysis -+
```

Both intermediate artifacts are model outputs. The current formal contract
correctly leaves their byte upper bounds unknown. It does not guess a bound
from reserved tokens, silently truncate, or insert an implicit reduction.

Per the Phase-4 stop rule, this full-plan static failure terminated the run
before Worker startup, artifact materialization, or workflow execution.

## 6. G0 replay procedure

`scripts/revision4_g0_32k_replay.py` is a bounded validation/replay harness. It:

1. loads the exact durable `constructed-g0.json`;
2. checks its canonical hash against the recorded Revision-3 hash;
3. reconstructs the same benchmark task and public artifact bundle on the 4090;
4. reuses the recorded Prior provenance without a backend call;
5. invokes the existing semantic/static validator under the 32K environment;
6. would freeze and execute only after validation passes.

Step 5 failed, so steps 6 and all runtime setup were not entered. No fresh
Workers were started and no formal frozen-prior replay artifact was created.

## 7. Runtime evidence

There is no G0 runtime result because execution was correctly prevented.

- Planner calls: **0**
- Prior calls: **0**
- matrix cells: **0**
- tc shaping calls: **0**
- Workers started: **no**
- artifacts materialized: **no**
- model inference calls from G0: **0**
- evaluator calls: **0**

Read-only `tc qdisc show` snapshots were saved for A4, A5, A28, and
`strong-4090`. They show the native `mq`/`fq_codel`/`noqueue` state and no
Revision-4 shaping hierarchy. Post-change Ollama `/api/ps` was empty on both
model nodes.

## 8. Context and token observations

No G0 backend token telemetry exists because full-plan preflight rejected the
workflow. The preceding capability audit remains the applicable runtime
evidence: both nodes passed one clean 28,672-envelope and 32,768-envelope call
with the same model manifest, non-empty `OK`, and `finish_reason=stop`.

The targeted Revision-4 diagnostic computed 27,846 conservative units and a
32,768 model class. It made zero backend calls. The failure at `compare-guides`
is an unknown-bound failure, not a second 16K/32K comparison.

## 9. Memory observations

No G0 GPU memory sampling was started because the static gate failed before
execution. Consequently there is no G0 peak-memory observation and no value is
inferred from `/api/ps`. The earlier calibration's loaded allocations remain
separate calibration evidence, not a G0 peak measurement.

## 10. Workflow result

```text
execution_started = false
execution_completed = false
original context blocker = resolved
new full-plan static blocker = observed at compare-guides
```

The G0 remained byte-for-byte and semantically unchanged.

## 11. Quality and evaluator result

The original benchmark evaluator was not called. There is no terminal answer,
format-validity result, or benchmark score. Reporting a quality result would be
invalid because execution never began.

## 12. Interpretation

This is not runtime Case A: the formal 32K setting propagated and the original
`analyze-sorcerer` context gate now passes. It is also not Case B, C, or D,
because no backend or workflow execution was allowed.

It is a Phase-4 fail-closed result: resolving the first context blocker exposed
a separate latent static-feasibility defect in the same G0. The system cannot
prove that two materialized intermediate model outputs fit the terminal model
context because their output-size envelopes are unknown. Treating them as
bounded without an explicit contract would violate the experiment's no-guess
and no-silent-truncation rules.

## 13. Decision

Revision-4 validates the **32K deployment propagation and the formerly rejected
action**, but does **not** validate the complete G0 or authorize the formal
matrix.

```text
context issue at analyze-sorcerer: resolved
complete G0 static feasibility:    failed
G0 runtime validation:             not run
formal matrix prerequisites:       not satisfied
```

## 14. Exact next permitted action

Stop and request review. A subsequent authorization must choose how the formal
contract obtains a sound byte envelope for materialized model outputs (or how a
new Prior is constrained to create a statically bounded path). That would be a
new contract/Prior scope and was not attempted here. Until then, the only
permitted action is evidence review; no G0 retry or matrix cell should run.

## Evidence

Durable evidence, including pre/post Modelfiles, `/api/show`, `/api/ps`, blob
hashes, exact git diff, configuration snapshots, immutable G0 copies, context
diagnosis, typed static failure, tc state, and SHA-256 manifest:

```text
/home/super/xiaoming/workflow_formal_preliminary_2x2_v1/evidence/
  revision4-g0-32k-replay/
```
