# SDK-native Infra-Aware Preliminary — Qwen v1

Date: 2026-10-02
Branch: `open-ended-mas-preliminary-v1`

## Scope

This block was opened to run a Qwen-cloud control plane independently from the
existing DeepSeek pilot. The DeepSeek runs, statistics, and conclusions were not
modified or combined with this block.

The required gate was one non-matrix Fast/Blind `multihop-multisource` sanity run.
The formal Fast/Slow × Blind/Aware matrix was permitted only after that run proved
the complete Manager → native tools → Verifier → synthesis → evaluator path.

## Qwen control-plane configuration

The strong-4090 host already contained a `DASHSCOPE_API_KEY` credential and the
following recorded OpenAI-compatible endpoint:

```text
https://llm-6tbxas81ayf65rd1.cn-beijing.maas.aliyuncs.com/compatible-mode/v1
```

A read-only `GET /models` returned HTTP 200 and included the pinned snapshot
`qwen-plus-2025-12-01`. That snapshot was selected instead of a moving alias. The
[Alibaba Cloud model page](https://docs.modelstudio.console.alibabacloud.com/en/model-studio/qwen-plus)
documents a 1,000,000-token context window and support for function calling and
structured outputs for the Beijing service. The actual endpoint was then probed
with synthetic, non-benchmark inputs:

| Probe | Outcome | Finish reason | Latency |
|---|---|---|---:|
| ordinary function call | valid `echo_probe({"value":"ok"})` | `tool_calls` | 1,234.640 ms |
| required Verifier-style function call | valid `submit_verification` JSON | `tool_calls` | 1,201.774 ms |

The candidate sanity manifest therefore used:

| Setting | Value |
|---|---|
| Provider | Alibaba Cloud Model Studio |
| Manager model | `qwen-plus-2025-12-01` |
| Verifier model | `qwen-plus-2025-12-01` |
| Manager temperature | provider default (the frozen runtime does not set it) |
| Verifier temperature | `0` |
| Tool transport | OpenAI-compatible function tools |
| Verifier transport | required function tool |
| Client timeout | 180 seconds |
| Client retries | 0 |

No key value was written to the repository or trace.

## Compatibility wiring

Commit `603a8dd70458ebe4f40bf8f6aecddcb894002cff` added only:

- a provider-neutral key-file loader keyed by the harness `api_key_env`;
- explicit admission of the Qwen sanity/future frozen harness IDs; and
- the candidate Qwen sanity manifest and pinned run configuration.

The Manager instructions, Verifier instructions/state machine, tool schemas,
20/64/20 budget, benchmark adapter/evaluator, physical scheduler, profile
abstraction, Worker implementation, and local Ollama deployments were unchanged.
Tests prove that the candidate manifest differs from `blind-harness-v1.3.1` only
in control-plane provenance/configuration fields.

Validation before deployment:

- full `pytest`: passed;
- Ruff: passed;
- targeted Qwen harness/config/key-loader tests: 23 passed;
- configured Pyright was also run, but the local environment lacks the pre-existing
  optional Pillow stubs and LangGraph dependency; its 21 diagnostics were confined
  to `operators/media.py` and `planning/graph.py`, not this change.

## Sanity validation

The only sanity attempt was:

| Field | Value |
|---|---|
| Run ID | `qwen-sanity-multihop-fast-blind-v1` |
| Code revision | `603a8dd70458ebe4f40bf8f6aecddcb894002cff` |
| Config SHA-256 | `3a8b7ad4dbf3e254481d355ef848989ed1a1e78051def4afa22ff4c82498e449` |
| Candidate harness SHA-256 | `c926f78c3813004e46c57dfee087e11319c91ef6844ef1f3e376cea5b4b3f1e9` |
| Task bundle SHA-256 | `54ef8ddbe4a3379254345f307b3f0ef6b95fe92e0b28ac4c89124bb6b7ebfe8e` |
| Static capability SHA-256 | `8d46d9b941a08380a00fdab1e7c151c25affd589ec4444864f3c5c925a2089a4` |
| Visibility | Blind |
| Network | Fast: 100 Mbps + 5 ms |
| Retry/replacement | none |

All four Worker stores were absent before startup and exposed zero artifacts at
the preflight `/state`. A4/A5/A28/strong-4090 retained the same operator and
deployment surfaces as the DeepSeek pilot. Benchmark files were read only on the
strong-4090 host; none were downloaded or relayed through the development machine.

### Result

| Completion | Score / format | Manager / Verifier calls | Tool / model calls | Local inference | E2E | Initial / action bytes |
|---|---|---:|---:|---:|---:|---:|
| no — Manager-turn exhaustion | evaluator not invoked | 20 / 20 | 7 / 0 | 0 | 170,254.048 ms | 7,696,522 / 0 |

The Qwen provider and SDK transport did work:

- all 20 Manager calls returned normally;
- all 20 Qwen Verifier calls returned schema-valid verdicts;
- seven native BM25 actions crossed the ActionGateway and physical execution
  service;
- six BM25 actions succeeded and produced real artifacts; and
- the Verifier returned `ready_for_synthesis` eight times, first at call 4.

The compact final graph contains seven BM25 nodes (six succeeded, one failed). It
contains no model node because no valid `invoke_model` action reached the graph.

## Failure analysis

The primary failure is **workflow composition / artifact-reference misuse**, with
hard Manager-turn exhaustion as the terminal condition. It is not a provider,
wire-format, physical-runtime, context, evaluator, or network failure.

The trajectory was:

1. Turn 1 used the invalid BM25 field `text`; the typed observation exposed that
   the declared corpus field is `body`.
2. Qwen recovered and produced successful Barbarian and Sorcerer retrievals.
3. The runtime canonicalized each Manager-declared output alias under the run
   namespace, for example:

   ```text
   requested alias: barbarian-guide-results-1
   materialized ID: derived/091ea0bab7914ff8be94c9656edb2167/barbarian-guide-results-1
   ```

4. On every synthesis attempt, Qwen supplied the short alias rather than the
   exact materialized ID returned by the tool observation. The runtime correctly
   rejected these calls as `artifact_not_materialized`.
5. Qwen expanded retrieval across all three shards, and the Verifier repeatedly
   confirmed that evidence was sufficient, but Qwen continued to reuse short
   aliases. It never submitted a valid terminal `invoke_model` action.
6. The unchanged 20-turn ceiling ended the run.

Observed typed failures were ten `artifact_not_materialized`, one BM25
`validation_failed`, one output-ID collision `semantic_validation_failed`, and one
`phase_restricted` call. None reached local model inference.

This is not safely repairable as a provider wire adapter. Making the run pass would
require at least one prohibited semantic/harness change, such as changing the
Manager instructions to emphasize canonical returned IDs or silently resolving
short aliases to namespaced artifacts. The latter would be hidden action repair
and would change the frozen harness semantics for all providers.

## Isolation and cleanup

- Blind logical privacy scan passed: no worker/device/deployment identity, IP,
  placement, `source_ref`, evaluator ID, gold, or supporting evidence appeared in
  logical events.
- `tc` applied the declared Fast regime and restored A4/A5/A28 to `mq` and
  strong-4090 to `noqueue`.
- `cleanup_error` is null.
- All four isolated Workers were stopped after evidence persistence.
- Fresh stores, Worker logs, full trace, result, freeze manifest, and tc
  attestation remain preserved on strong-4090 under
  `/home/super/xiaoming/sdk-native-infra-qwen-v1-603a8dd/`.

## Stop decision

The P0 sanity gate did **not** pass because synthesis and evaluator invocation were
not reached. This valid trajectory is not eligible for an operational replacement.
No prompt/model/budget/tool/runtime semantic setting was changed, and no second
sanity attempt was made.

Consequently:

- `qwen-infra-preliminary-v1` was not frozen;
- no formal MultiHop 4-cell run was started;
- no n=3 extension, LongBench, or Video-MME cell was started; and
- the DeepSeek pilot remains unchanged and statistically separate.

The current evidence supports only this conclusion: the selected Qwen cloud model
is transport-compatible and can drive native tools and the structured Blind
Verifier, but under the frozen v1.3.1 semantics this one sanity trajectory did not
complete because it repeatedly failed to reuse canonical materialized artifact
identifiers.
