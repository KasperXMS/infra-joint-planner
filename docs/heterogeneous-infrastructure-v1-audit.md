# Heterogeneous Infrastructure Experiment v1 Audit

## Scope and freeze

- Original M4 substrate: `main@bccef07`.
- Preserved v0 experiment base: `mas-workflow-orchestration@6a10595`.
- Development branch: `heterogeneous-infrastructure-v1`.
- v1 adds sidecar contracts, preflight, `tc` control/calibration, equivalent-replica
  placement, controlled-workload tooling, profiling, scheduling, analysis, tests,
  and result artifacts under `src/infra_joint/heterogeneous/`, `scripts/`,
  `tests/`, `results/`, and this report.
- The frozen RuntimeExecutor, Worker API, benchmark evaluators, benchmark
  adapters, artifact-validation semantics, and existing WorkflowPlan semantics
  were not reinterpreted. The primary v1 matrix freezes a scripted semantic DAG
  before placement selection.
- M5 was not started. There is no infrastructure-visible semantic planning,
  topology adaptation, dynamic replanning, RL, migration, prefetch, speculative
  execution, or model substitution.

## Hardware topology

| Worker | Address / isolated port | Device | Primary v1 role |
|---|---:|---|---|
| `A4` | `192.168.0.104:9104` | Jetson AGX Orin 32 GB | source-A data Worker |
| `A5` | `192.168.0.105:9105` | Jetson AGX Orin 32 GB | source-B data Worker |
| `A28` | `192.168.0.128:9128` | Jetson AGX Orin 64 GB | merge and AGX synthesis replica |
| `strong-4090` | `192.168.0.12:9212` | 2 × NVIDIA GeForce RTX 4090, 24 GB each | RTX synthesis replica |

The final post-fix unshaped hard preflight is
`results/heterogeneous-v1-hard-preflight-audit2.json`. It verifies all four
Worker identities, their exact twelve-operator surfaces, artifact endpoints,
deployments, replica metadata, both RTX 4090 UUIDs, and unshaped root qdiscs.

`A28` reported `MODE_30W`. `jetson_clocks --show` requires general root access,
which was not available and was not bypassed; no undocumented power or clock
change was made. Non-interactive `sudo tc` was available on the required hosts.

## Model configuration and replica equivalence

- Semantic model: custom Ollama tag `qwen3.8-27b-v1` / logical model
  `qwen3.8-27b-q4km-v1` (27.3B parameters).
- Quantization: `Q4_K_M`; the preferred >=14B requirement is satisfied, so the
  separately permitted 8B fallback was not used.
- Manifest/checkpoint fingerprint on both replicas:
  `sha256:b69fef4451445b2d5433388b20b9c03883521ca3f949b656e50d494cb29c2350`.
- Runtime: Ollama `0.34.0` on both replicas.
- Context window: 16,384 tokens; fixed maximum output: 256 tokens.
- Primary generation configuration: non-thinking, temperature 0, seed 42,
  `top_k=1`, `top_p=1`.
- Physical deployments: `a28-qwen3.8-27b-q4km-v1` and
  `strong-4090-qwen3.8-27b-q4km-v1`.

Preflight requires equality of checkpoint, fingerprint, quantization, runtime
version, context, output limit, prompt-template ID, and generation-config ID.
Mismatch is fail-closed; there is no deployment substitution or model downgrade.
The OpenAI-compatible backend keeps `reasoning_effort` optional and defaults it
to null, preserving frozen M4 behavior. Only the two v1 replica configurations
bind `reasoning_effort=none`. Post-fix forced RTX and A28 smokes both returned
visible content with `finish_reason=stop`.

## `tc` setup and safety

- A28 interface: `wlP1p1s0`; original root `mq`.
- RTX interface: `wlp6s0`; original root `noqueue`.
- Shaping: HTB rate/ceil class on both directions; NETEM adds the full 20 ms on
  RTX egress only because the Orin kernel lacks NETEM.
- Filters are restricted to the A28/RTX peer addresses plus experiment Worker,
  iperf3, and ICMP traffic. SSH/controller traffic is not intentionally shaped.
- The HTB burst is approximately 10 ms of rate credit with a 64 KiB floor. This
  avoids the earlier 4 MiB burst allowing small transfers to bypass low rates.
- Apply is transactional. Normal completion, failure, and controller cleanup
  restore the observed root kind and verify it. All six audit calibrations ended
  with A28 `mq` and RTX `noqueue`.

Primary v1 metadata requires `network_control_method=tc`; the v0 application
emulator remains intact but is not accepted for these measurements.

## Network calibration

The audit sweep holds added RTT at 20 ms and uses three iperf3 measurements plus
three real Worker-to-Worker artifact pulls at each payload size. Values below
are medians in Mbps except RTT, which is milliseconds.

| nominal BW | RTT median / p95 | iperf3 | 1 MiB | 8 MiB | 32 MiB | 128 MiB |
|---:|---:|---:|---:|---:|---:|---:|
| 3 | 22.20 / 25.50 | 2.935 | 2.821 | 2.856 | 2.863 | 2.864 |
| 10 | 22.40 / 25.50 | 10.063 | 8.787 | 9.305 | 9.473 | 9.500 |
| 30 | 22.30 / 26.20 | 30.609 | 24.682 | 27.662 | 27.829 | 28.131 |
| 100 | 22.30 / 25.80 | 92.051 | 59.093 | 81.363 | 71.781 | 86.921 |
| 300 | 23.05 / 29.80 | 128.305 | 33.623 | 83.421 | 98.356 | 123.466 |
| 1000 | 22.20 / 25.10 | 123.065 | 47.507 | 87.359 | 117.483 | 111.561 |

The 3/10/30 Mbps conditions closely enforce the configured bottleneck for large
artifacts. At 100 Mbps and above, shared Wi-Fi and fixed overhead dominate;
nominal 300/1000 Mbps must not be interpreted as achieved link speed. Formal
regime selection therefore uses measured artifact behavior and the forced pilot,
not the nominal label alone. Machine-readable files are under
`results/network_calibration/`; `*-audit1.json` is the n=3 audit sweep.

## Compute profiles

Both valid `audit2` profiles use the same prompt template and generation
configuration with 10 warmups and 30 measured requests per point. Every one of
the 240 measured samples ended with `done_reason=length` and a nonzero output.

### A28 / AGX Orin 64 GB

| requested in/out | actual median in/out | service median / p95 ms | TTFT median ms | prefill median ms | decode median ms | output tok/s median |
|---:|---:|---:|---:|---:|---:|---:|
| 1024/128 | 1046/128 | 29,763.3 / 30,095.5 | 1,402.2 | 917.2 | 28,357.9 | 4.51 |
| 2048/128 | 2070/128 | 29,789.8 / 30,064.0 | 1,354.5 | 901.2 | 28,397.3 | 4.51 |
| 4096/256 | 4118/256 | 58,269.0 / 58,550.9 | 1,496.0 | 893.3 | 56,702.0 | 4.51 |
| 8192/256 | 8214/256 | 58,685.0 / 58,950.6 | 1,538.1 | 907.1 | 57,045.9 | 4.49 |

A28 remained in `MODE_30W`. Its CPU/GPU temperature moved from approximately
50/45°C before the two-hour profile to 54/49°C after it. `jetson_clocks --show`
returned the documented root-required error both before and after; no clock
change was made. No obvious thermal invalidity was observed.

### strong-4090 / dual RTX 4090

| requested in/out | actual median in/out | service median / p95 ms | TTFT median ms | prefill median ms | decode median ms | output tok/s median |
|---:|---:|---:|---:|---:|---:|---:|
| 1024/128 | 1046/128 | 1,607.2 / 1,737.1 | 550.5 | 282.9 | 1,042.1 | 122.83 |
| 2048/128 | 2070/128 | 1,629.5 / 1,734.3 | 570.9 | 291.1 | 1,052.1 | 121.66 |
| 4096/256 | 4118/256 | 2,766.2 / 3,147.3 | 649.3 | 313.0 | 2,091.8 | 122.38 |
| 8192/256 | 8214/256 | 3,023.7 / 3,146.5 | 858.7 | 356.1 | 2,120.9 | 120.70 |

RTX telemetry moved from 43/38°C idle to 49/59°C after profiling; end power was
139/198 W and no obvious throttling condition was observed.

Ollama does not expose peak memory per request through this API, so
`peak_memory_bytes` is explicitly null rather than fabricated. Device-level
before/after memory telemetry is retained in the raw profile files. Scheduler
stage estimates are not taken directly from this microprofile: the forced pilot
provides workload-specific median reduction and model service costs.

## Controlled workload and information boundaries

The fixed fan-out/fan-in workload is derived deterministically from two real M4
MultiHop-RAG source documents. It is a controlled systems workload, not a formal
benchmark-quality claim. S/M/L contain 8,385,059 / 33,552,190 / 134,213,826
bytes respectively. There is no random padding: size is produced by documented
replication of real document records while preserving canonical evidence records.

The public TaskContract and artifact IDs use neutral shard names and contain no
Worker, device, deployment, placement, gold, or supporting-evidence identity.
Physical source placement exists only in the experiment harness sidecar. The
private evaluator remains separate. The model input projection is approximately
2,018 bytes for every payload and is context-preflighted without truncation.

The primary DAG is fixed: local BM25 on A4/A5, merge/package on A28, then a
co-located BM25 reduction, projection, and identical-model synthesis group on
either A28 or `strong-4090`. B0 uses locality only. B1 uses calibrated transfer
plus measured reduction/model compute with queue cost fixed to zero. Forced A28
and forced RTX runs provide the empirical placement oracle.

## Crossover pilot

Pending.

## Formal B0/B1 and oracle matrix

Pending.

## Statistical caution

Measured values, derived medians/break-even estimates, and interpretations are
reported separately. No significance claim is made without appropriate evidence.
Results are specific to the tested Workers, model, Wi-Fi path, fixed DAG, payloads,
and idle-state condition.

## Invalid-run audit

| Attempt | Classification | Counted? | Reason / response |
|---|---|---:|---|
| initial PRIO/TBF tc preflight | system/harness confounder | no | target qdisc path unsupported; transactional cleanup, then supported HTB |
| initial repeated-token compute prompt | system/harness confounder | no | Ollama stream lacked final telemetry on both replicas; deterministic integer-sequence prompt fixed telemetry collection |
| compute profile audit1 overlap | system/harness confounder | no | one-time artifact preload overlapped shared Wi-Fi; incomplete A28 stopped and RTX audit1 retained but excluded; isolated audit2 started |
| runner smoke audit1 | system/harness confounder | no | v1 Worker config declared non-thinking semantically but did not bind `reasoning_effort=none` into the OpenAI-compatible request; hidden reasoning consumed all 256 tokens and returned empty visible content; optional deployment-scoped binding added and verified on both replicas |

No failed attempt above is used as calibration, compute-profile, pilot, oracle,
or scheduler evidence. Detailed machine-readable records are under
`results/invalid-runs/`.

## Verification

Pending final post-experiment pytest, Ruff, strict Pyright, trace reconstruction,
and clean-worktree verification.

## Conclusions

Pending measured pilot and formal results. No crossover or scheduler-superiority
claim is made before those data exist.
