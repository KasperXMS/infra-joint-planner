# Clean cost-history and empirical estimator v0

2026-10-04. This is an estimator implementation, not a live method result.

## Source eligibility

Use the final cross-benchmark audit's 24 effective cells, including the valid
Manager-budget failure, plus nine eligible historical MultiHop runs. Exclude the
three MultiHop recipient-profile violations. Selection never uses correctness,
answer text, gold, supporting evidence or evaluator score. All evidence hashes
in each admitted audit record are rechecked before extraction. Only new output
directories are allowed; no historical file is rewritten.

`scripts/build_cost_guidance_history_v1.py` runs on strong-4090. It reads raw
traces there and emits numeric cost samples and a source/hash manifest. It does
not start Workers, shape links, invoke models, materialize artifacts or evaluate
tasks. No raw trace, prompt, artifact content or answer is sent to the PC.

## Prediction basis and limitations

- Model features: anonymous model class, exact internal execution-surface hash,
  conservative ready-input envelope bucket, exact image count and actual backend
  output ceiling. The minimum requested output requirement is not `max_tokens`.
- The envelope matches the existing guard: prompt UTF-8 bytes plus ready text
  artifact sizes plus the static image cost. It is **not actual tokenizer usage**.
  Provider input tokens are retained as observed metadata, not used as if known
  before inference. Artifact labels/chat-template overhead are outside this guard;
  this is not a new proof of the backend's true token capacity.
- Operator profiles match operator, input-size bucket and execution surface.
  Wrapper latency includes RPC/serialization; it is not pure compute.
- Transfer profiles match exact internal directional route surface, configured
  network category and payload-size bucket. They report empirical latency,
  not configured-bandwidth arithmetic or measured universal throughput.
- Minimum support is three receipts; output is p50/p90 plus sample count.
  These quantiles are descriptive, **not confidence intervals**. Buckets larger
  than the finite supported ranges return unknown; modalities/image counts,
  deployments/routes and output budgets are not pooled to manufacture support.
- Physical-surface hashes are internal estimator keys only. A future Manager
  cost card may receive numeric consequences, never these identity keys.
- Failed actions without execution receipts do not become zero-cost samples.
  Unknown artifact sizes are not filled using future outputs. Duplicate actions
  or mixed run IDs fail closed. Initial materialization is not included.
- Historical Ollama cache/load and sequential run order were not controlled;
  these are coarse empirical work distributions, not stable causal predictions.
  Unsupported strong-4090 service cells remain unknown even if A28 has receipts.

## Verification

22 new tests cover support thresholds, quantiles, feature/surface isolation,
unknown/no extrapolation, finite numeric values, leakage-free extraction,
ready-input timing, actual output ceiling, preflight versus inference, Unicode
physical-line parsing, source hash mismatch and evidence path confinement.

Full pytest:508 passed. Ruff:pass. Strict Pyright:0 errors/0 warnings.
Historical baseline source/config hash tests still pass; no substrate changed.

## Actual remote freeze

Remote source revision `00ff980`; append-only output:
`/home/super/xiaoming/cost-guidance-history-v0-00ff980/freeze-001`.
All198 referenced evidence hashes were verified across33 eligible runs.
Source audits match the previously frozen hashes; three leaked MultiHop runs
are excluded. The final valid no-answer/budget run remains eligible.

| Receipt | Count | Matching bucket support >=3 | Unknown support |
| --- | ---: | ---: | ---: |
| Physical model service |62|54|8|
| Operator wrapper |255|236|19|
| Action transfer |245|238|7|

These are **training-receipt bucket coverage**, not unique-bin counts, accuracy,
validation or generalization estimates. All62 input envelopes are reconstructable;
all model samples use output ceiling2048 and one actual model execution surface.
No strong-4090 model inference sample exists in this freeze.

`cost-history.json` SHA-256:
`693f26bc8855f1712e22607e98ca4bc0571027e51d9db247dfe8f0012d3c392b`.
`manifest.json` SHA-256:
`bd10d6b146c42fe32e0888ca2138584c389d439e7e45aef186563e5bb7e15481`.
Strict sample-field allowlists and history hash were independently checked after
writing. The183836-byte numeric history stays on4090; only aggregate counts and
hashes were returned to the PC. Extraction launches no Worker/model/planner/tc.

## Read-only action-consequence layer

`control/consequence.py` consumes the existing scheduler's prepared action and
its exact infrastructure snapshot. It does not execute, reserve, read artifacts
or invoke an evaluator. It returns anonymous numeric consequences only:
ready-input movement, configured ideal serialization separately from empirical
transfer latency, existing context envelope and supported model/operator profiles.
Source choice follows RuntimeExecutor's first reachable lexicographic source,
not a new cheapest-route rule. No output-reduction ratio or future LLM artifact
size is guessed. Static-impossible requirement is distinguished from a current
binding failure; private failure messages/selection identity are not returned.

Seven synthetic tests additionally cover real scheduler preparation without
execution, source consistency, configured versus empirical cost, local/unknown
movement, image versus JPEG context, snapshot changes and typed static failure.
Latest full verification with this layer:515 pytest passed, Ruff passed, strict
Pyright0 errors/0 warnings and diff whitespace check passed. Original native
runtime and isolation manifest hashes remain unchanged.
This is not yet the SDK-native Quote/Commit protocol: ownership, proposal expiry,
commit/revise tools and live runner integration still remain. No live exploratory
cells have been launched; full exploratory objective is not complete.
