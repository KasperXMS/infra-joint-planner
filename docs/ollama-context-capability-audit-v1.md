# Ollama Context Capability Audit v1

## Scope and controls

This audit only tested whether the existing Ollama model artifact used by A28
and `strong-4090` can operate beyond the current 16K deployment setting. It did
not regenerate or edit a prior, change a workflow or scheduler, start formal
Workers, apply `tc`, or execute a KEEP/PATCH matrix cell.

```text
Planner calls = 0
Prior calls   = 0
Matrix cells  = 0
tc shaping    = 0
```

The synthetic probes contain no benchmark, gold, supporting-evidence, or
evaluator-private data. Model calibration ran on the two experiment hosts; no
benchmark data passed through the development machine.

Raw evidence is retained at:

```text
/home/super/xiaoming/workflow_formal_preliminary_2x2_v1/evidence/
  ollama-context-capability-audit-v1/
```

## Three distinct context limits

Both nodes use the official experiment tag `qwen3.8-27b-v1`. `ollama show`,
`ollama show --modelfile`, and `/api/show` agree on the following distinction:

| Deployment | Model metadata context | Current Modelfile `num_ctx` | Formal `DeploymentSpec.context_window` |
|---|---:|---:|---:|
| A28 | 262,144 | 16,384 | 16,384 |
| strong-4090 | 262,144 | 16,384 | 16,384 |

The artifact is Qwen `qwen35`, 27.3B parameters, Q4_K_M quantization, embedding
length 5,120. Relevant metadata is:

```yaml
qwen35.context_length: 262144
qwen35.rope.dimension_count: 64
qwen35.rope.dimension_sections: null
qwen35.rope.freq_base: 10000000
```

The vision projector is CLIP, 460.73M parameters, embedding length 1,152 and
5,120 dimensions. Both endpoints reported Ollama 0.34.0. The two Modelfiles
refer to the same model and projector blob hashes; only their local blob-root
paths differ.

Therefore, the previously observed 16K boundary was not the model metadata
limit. It was simultaneously the official tag's `num_ctx` setting and the
frozen formal deployment contract.

## Isolated 32K calibration builds

Because the metadata limit exceeds 32K, an independent tag was created on each
node:

```text
qwen3.8-27b-v1-ctx32k-calibration
```

The tag reuses exactly the same two blobs, template, renderer, parser,
quantization, and other parameters. The retained unified Modelfile diffs contain
one change only:

```diff
-PARAMETER num_ctx 16384
+PARAMETER num_ctx 32768
```

The existing Ollama servers were not restarted, so their experiment settings
remained unchanged: `OLLAMA_KV_CACHE_TYPE=q8_0`, `OLLAMA_NUM_PARALLEL=1`, and
`OLLAMA_MAX_LOADED_MODELS=1`. The formal 1,024-token output reserve was also
unchanged. The official tag was not overwritten or rebuilt. A post-test
`ollama show --modelfile qwen3.8-27b-v1` still reports `num_ctx 16384` on both
nodes, and no formal configuration references the calibration tag.

## 24K / 28K / 32K probes

Each cell was one clean, uncached request. Before every call, the calibration
tag was unloaded and `/api/ps` returned an empty model list. Each prompt used a
different deterministic prefix. After every call, `/api/ps` reported the
calibration tag loaded with `context_length=32768`.

The `Envelope` column is the formal conservative context budget. Its input is
`Envelope - 1,024` ASCII bytes because the formal preflight deliberately counts
each UTF-8 byte as one conservative token. `Actual input` is the independent
token count returned by the Ollama/OpenAI-compatible backend. This distinction
matters: these results validate the rejected G0's 27,846-unit *formal
conservative envelope*; they do not pretend that a 28K envelope contained 28K
backend-tokenizer input tokens.

| Deployment | Envelope | Preflight | Actual input/output | Output / finish | TTFT | Total | OOM | Truncation signal |
|---|---:|---|---:|---|---:|---:|---|---|
| strong-4090 | 24,576 | PASS | 16,172 / 2 | `OK` / `stop` | 23,239 ms | 23,305 ms | no | none observed |
| strong-4090 | 28,672 | PASS | 18,988 / 2 | `OK` / `stop` | 23,906 ms | 23,965 ms | no | none observed |
| strong-4090 | 32,768 | PASS | 21,804 / 2 | `OK` / `stop` | 25,536 ms | 25,605 ms | no | none observed |
| A28 | 24,576 | PASS | 16,175 / 2 | `OK` / `stop` | 304,114 ms | 305,282 ms | no | none observed |
| A28 | 28,672 | PASS | 18,991 / 2 | `OK` / `stop` | 356,083 ms | 357,243 ms | no | none observed |
| A28 | 32,768 | PASS | 21,807 / 2 | `OK` / `stop` | 408,914 ms | 410,094 ms | no | none observed |

All calls completed normally with non-empty output and `finish_reason=stop`.
Backend-reported input tokens continued increasing at every tier rather than
being capped at the old 16K deployment setting. There was no Ollama rejection,
OOM, backend error, timeout, or observed truncation. The synthetic prompt's
expected answer was produced at all tiers.

`/api/ps` reported loaded VRAM allocation of 19,181,590,279 bytes on
`strong-4090` and 17,536,059,964 bytes on A28. These are loaded-allocation
observations, not peak-memory measurements; peak memory was unavailable and is
not guessed.

### Required-context coverage

The rejected action has the already reconstructed conservative requirement:

```ini
required_context(analyze-sorcerer) = 27846
current_official_num_ctx           = 16384
current_formal_context_window      = 16384
calibration_num_ctx                = 32768
```

The 28,672 envelope is 826 units above the rejected G0 requirement and passed
on both deployments. The 32,768 boundary also passed on both. This is direct
evidence that the same model artifacts can accommodate the required formal
envelope when instantiated with a separately validated 32K Ollama setting.

## Summary table

| Deployment | Model metadata context | Current `num_ctx` | Formal context | 32K temp build | 28K test | 32K test |
|---|---:|---:|---:|---|---|---|
| A28 | 262,144 | 16,384 | 16,384 | PASS | PASS | PASS |
| strong-4090 | 262,144 | 16,384 | 16,384 | PASS | PASS | PASS |

## Decision

**A. The current 16K limit is deployment-configured; the same model artifact
can support the required ~27.8K context under a validated 32K Ollama build.**

This supersedes the earlier capacity diagnosis that was intentionally limited
to the then-current 16K deployment build. It does not authorize or perform a
formal configuration change. `DeploymentSpec.context_window`, Worker
deployment configuration, the frozen static capability contract, the official
model tag, the prior, and the rejected G0 all remain unchanged.

The calibration tags and raw evidence are retained for review. No Revision-4
prior call or experiment matrix run was started.
