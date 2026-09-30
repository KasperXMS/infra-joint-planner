# Context Capability Calibration v1

## Scope

This diagnostic used the durable Revision-3 attempt
`20260929T222546551722Z-f19f3017aed8`. It made zero Planner calls, did not edit
the rejected G0, and did not start formal Workers, apply `tc`, materialize
benchmark artifacts for execution, or run any KEEP/PATCH matrix cell.

The reproducible diagnostic/calibration script is
`scripts/context_capability_calibration_v1.py` at commit `ea5f9dc`. All dataset
reads and model calibration occurred on the 4090/A28 hosts; no benchmark data
was transferred through the development machine.

## Rejected G0 diagnosis

Failing action: `analyze-sorcerer`.

The formal static preflight deliberately treats each UTF-8 byte of text as one
conservative token. The exact envelope is:

| Component | Media type | Static bound / contribution |
|---|---|---:|
| Action prompt | text | 212 bytes = 212 conservative tokens |
| `sorcerer-docs` | `application/json` | 26,610 bytes = 26,610 conservative tokens |
| Action-requested output minimum | — | 512 tokens |
| Deployment/static-class reserved output used by preflight | — | 1,024 tokens |
| **Total conservative context requirement** | — | **27,846 tokens** |

Both deployments collapse into the same anonymous static model class because
their semantic capabilities are identical. That class has a 16,384-token
context window and a 1,024-token reserved-output contract.

```ini
required_context = 27846
current_context_window = 16384
excess = 11462
```

No component of this envelope is unknown.

### Evidence path

```text
full-corpus-shard-0001 (2,772,674 bytes)
full-corpus-shard-0002 (2,431,922 bytes)
full-corpus-shard-0003 (2,491,926 bytes)
  -> aggregate-corpus / aggregate_artifacts
full-corpus (7,696,522 bytes; size preserved)
  -> retrieve-sorcerer / bm25_retrieve(top_k=8)
sorcerer-docs (26,610-byte static upper bound; size reduction)
  -> analyze-sorcerer / invoke_model
```

| Artifact | Producer | Static bound | Consumer | Change |
|---|---|---:|---|---|
| `full-corpus-shard-0001` | task source | 2,772,674 B | `aggregate-corpus` | source |
| `full-corpus-shard-0002` | task source | 2,431,922 B | `aggregate-corpus` | source |
| `full-corpus-shard-0003` | task source | 2,491,926 B | `aggregate-corpus` | source |
| `full-corpus` | `aggregate-corpus` | 7,696,522 B | `retrieve-sorcerer` | preserved |
| `sorcerer-docs` | `retrieve-sorcerer` | 26,610 B | `analyze-sorcerer` | reduced by 7,669,912 B |

The failure is therefore not caused by feeding the raw corpus directly to the
model, an intermediate model output, multiple accumulated artifacts, or the
212-byte prompt. BM25 reduces the 7.70 MB aggregate to a bounded top-8 result,
but the conservative 26,610-byte result plus prompt and output reserve still
exceeds 16K.

## Actual deployment contract

Both formal deployments use the same Qwen3.8 27B Q4_K model blobs and local
Ollama 0.34.0 OpenAI-compatible server. Their live Modelfiles explicitly contain:

```text
PARAMETER num_ctx 16384
```

Both services use `OLLAMA_KV_CACHE_TYPE=q8_0`, `OLLAMA_NUM_PARALLEL=1`, and
`OLLAMA_MAX_LOADED_MODELS=1`. The formal deployment and Worker configuration
also declare `context_window=16384` and `reserved_output_tokens=1024`.

Consequently, 20K--48K are outside the current model-build/runtime contract.
They were not forced, as required. This diagnostic does not claim that the
underlying model architecture could never be rebuilt for a larger context; it
only measures the actual deployments used by the formal experiment.

## Deployment calibration

Each supported 16K cell used a deterministic 15,360-byte synthetic text input
plus the unchanged 1,024-token output reserve. The exact formal preflight passed
at 15,360 conservative input tokens. The same OpenAI-compatible backend,
model, quantization/build, inference server, and `reasoning_effort=none` were
used. No benchmark gold or private evaluator data was used.

| Deployment | 16K | 20K | 24K | 28K | 32K | 40K | 48K | Recommended |
|---|---|---|---|---|---|---|---|---|
| A28 | PASS | NOT TESTED: runtime hard limit | NOT TESTED | NOT TESTED | NOT TESTED | NOT TESTED | NOT TESTED | 16,384 |
| strong-4090 | PASS | NOT TESTED: runtime hard limit | NOT TESTED | NOT TESTED | NOT TESTED | NOT TESTED | NOT TESTED | 16,384 |

Detailed 16K observations:

| Deployment | Preflight | Backend input/output | Output | Finish | OOM | Uncached TTFT | Uncached total | Initial clean-run total |
|---|---|---:|---|---|---|---:|---:|---:|
| A28 | PASS | 10,535 / 2 tokens | `OK` | `stop` | no | 181,229 ms | 182,363 ms | 204,497 ms |
| strong-4090 | PASS | 10,534 / 2 tokens | `OK` | `stop` | no | 22,372 ms | 22,769 ms | 75,437 ms |

The backend tokenizer counted fewer tokens than the byte-conservative preflight,
as expected. Output was non-empty and no truncation was observed. The initial
clean-run totals include model loading. Exact-prompt cached TTFT probes were
retained in evidence but excluded from the table. Peak memory is unknown because
the existing formal backend telemetry does not expose it; no value was guessed.

For each deployment:

- largest tested supported context window: 16,384;
- first inference failure: not observed inside the supported range;
- first larger requested tier: 20,480, not tested because the live Modelfile
  hard limit is 16,384;
- conservative recommended context window: 16,384.

## Decision

**B. Rejected G0 genuinely exceeds real model capacity.**

In the units enforced by the formal static/runtime contract:

```text
C_required(analyze-sorcerer) = 27,846
C_actual(A28 deployment)     = 16,384
C_actual(4090 deployment)    = 16,384
```

The declared `context_window=16384` matches both live model builds and is not
merely a conservative metadata value. Raising only `DeploymentSpec` or Worker
configuration would misrepresent the current runtime. No context configuration
was changed. Addressing this G0 would require a later, separately authorized
workflow-reduction constraint or a separately rebuilt and recalibrated model
deployment; neither was performed here.

## Stop attestation

- Planner backend calls: **0**
- New prior calls: **0**
- Formal Workers started: **no**
- `tc` shaping applied: **no**
- Matrix cells executed: **0**
- Deployment/context configuration changes: **none**
