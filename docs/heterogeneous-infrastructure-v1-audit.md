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

All latency columns are milliseconds. `service distribution` is
mean / median / standard deviation / p90 / p95 across 30 measured requests.

| requested in/out | actual median in/out | service distribution | TTFT median | prefill median | decode median | output tok/s median |
|---:|---:|---:|---:|---:|---:|---:|
| 1024/128 | 1046/128 | 29,824.8 / 29,763.3 / 153.3 / 30,018.1 / 30,095.5 | 1,402.2 | 917.2 | 28,357.9 | 4.51 |
| 2048/128 | 2070/128 | 29,818.8 / 29,789.8 / 113.7 / 29,970.7 / 30,064.0 | 1,354.5 | 901.2 | 28,397.3 | 4.51 |
| 4096/256 | 4118/256 | 58,271.8 / 58,269.0 / 176.8 / 58,502.2 / 58,550.9 | 1,496.0 | 893.3 | 56,702.0 | 4.51 |
| 8192/256 | 8214/256 | 58,716.2 / 58,685.0 / 151.9 / 58,940.0 / 58,950.6 | 1,538.1 | 907.1 | 57,045.9 | 4.49 |

For completeness, each component below is also
mean / median / standard deviation / p90 / p95. Latencies are milliseconds.

| requested in/out | TTFT distribution | prefill distribution | decode distribution | output tok/s distribution |
|---:|---:|---:|---:|---:|
| 1024/128 | 1,455.3 / 1,402.2 / 150.0 / 1,628.8 / 1,731.2 | 917.3 / 917.2 / 1.7 / 919.4 / 920.8 | 28,356.5 / 28,357.9 / 10.9 / 28,370.4 / 28,373.6 | 4.5140 / 4.5137 / 0.0017 / 4.5165 / 4.5168 |
| 2048/128 | 1,391.4 / 1,354.5 / 117.1 / 1,552.6 / 1,647.5 | 898.2 / 901.2 / 7.3 / 903.9 / 907.4 | 28,398.7 / 28,397.3 / 10.4 / 28,411.3 / 28,419.2 | 4.5073 / 4.5075 / 0.0016 / 4.5092 / 4.5098 |
| 4096/256 | 1,517.2 / 1,496.0 / 176.9 / 1,747.0 / 1,791.1 | 893.6 / 893.3 / 1.0 / 894.4 / 896.3 | 56,703.3 / 56,702.0 / 10.4 / 56,719.3 / 56,721.6 | 4.5147 / 4.5148 / 0.0008 / 4.5158 / 4.5159 |
| 8192/256 | 1,580.5 / 1,538.1 / 148.0 / 1,790.9 / 1,824.8 | 912.5 / 907.1 / 10.7 / 931.7 / 938.7 | 57,047.4 / 57,045.9 / 14.8 / 57,065.2 / 57,072.1 | 4.4875 / 4.4876 / 0.0012 / 4.4888 / 4.4896 |

A28 remained in `MODE_30W`. Its CPU/GPU temperature moved from approximately
50/45°C before the two-hour profile to 54/49°C after it. `jetson_clocks --show`
returned the documented root-required error both before and after; no clock
change was made. No obvious thermal invalidity was observed.

### strong-4090 / dual RTX 4090

The same column definitions and 30-request sample size apply.

| requested in/out | actual median in/out | service distribution | TTFT median | prefill median | decode median | output tok/s median |
|---:|---:|---:|---:|---:|---:|---:|
| 1024/128 | 1046/128 | 1,615.2 / 1,607.2 / 39.3 / 1,641.4 / 1,737.1 | 550.5 | 282.9 | 1,042.1 | 122.83 |
| 2048/128 | 2070/128 | 1,646.0 / 1,629.5 / 50.4 / 1,682.0 / 1,734.3 | 570.9 | 291.1 | 1,052.1 | 121.66 |
| 4096/256 | 4118/256 | 2,804.8 / 2,766.2 / 105.4 / 2,881.7 / 3,147.3 | 649.3 | 313.0 | 2,091.8 | 122.38 |
| 8192/256 | 8214/256 | 3,025.8 / 3,023.7 / 81.8 / 3,123.7 / 3,146.5 | 858.7 | 356.1 | 2,120.9 | 120.70 |

| requested in/out | TTFT distribution | prefill distribution | decode distribution | output tok/s distribution |
|---:|---:|---:|---:|---:|
| 1024/128 | 560.7 / 550.5 / 39.9 / 593.3 / 682.5 | 283.0 / 282.9 / 3.0 / 286.9 / 287.3 | 1,042.8 / 1,042.1 / 4.9 / 1,049.5 / 1,050.8 | 122.7448 / 122.8328 / 0.5759 / 123.3923 / 123.4774 |
| 2048/128 | 584.4 / 570.9 / 53.2 / 650.2 / 687.9 | 291.4 / 291.1 / 2.1 / 294.3 / 295.5 | 1,052.4 / 1,052.1 / 3.0 / 1,056.1 / 1,056.4 | 121.6265 / 121.6584 / 0.3514 / 122.0769 / 122.0967 |
| 4096/256 | 689.0 / 649.3 / 104.3 / 730.3 / 1,037.6 | 313.2 / 313.0 / 1.4 / 315.0 / 315.7 | 2,092.9 / 2,091.8 / 7.0 / 2,101.9 / 2,108.8 | 122.3215 / 122.3818 / 0.4055 / 122.7453 / 122.7586 |
| 8192/256 | 851.1 / 858.7 / 74.7 / 939.2 / 960.7 | 356.4 / 356.1 / 2.0 / 358.7 / 359.7 | 2,120.5 / 2,120.9 / 4.5 / 2,124.9 / 2,127.3 | 120.7242 / 120.7022 / 0.2582 / 121.0192 / 121.2069 |

RTX telemetry moved from 43/38°C idle to 49/59°C after profiling; end power was
139/198 W and no obvious throttling condition was observed.

Ollama does not expose peak memory per request through this API, so
`peak_memory_bytes` is explicitly null rather than fabricated. Device-level
before/after memory telemetry is retained in the raw profile files. Scheduler
stage estimates are not taken directly from this microprofile: the v2 forced
pilot, once complete and audited, provides workload-specific median reduction
and model service costs.

## Controlled workload and information boundaries

The fixed fan-out/fan-in workload is derived deterministically from two real M4
MultiHop-RAG source documents. It is a controlled systems workload, not a formal
benchmark-quality claim. There is no random padding: size is produced by
documented replication of real document records while preserving canonical
evidence records.

The public TaskContract and artifact IDs use neutral shard names and contain no
Worker, device, deployment, placement, gold, or supporting-evidence identity.
Physical source placement exists only in the experiment harness sidecar. The
private evaluator remains separate.

The primary DAG is fixed: local BM25 on A4/A5, merge/package on A28, then a
co-located BM25 reduction, projection, and identical-model synthesis group on
either A28 or `strong-4090`. B0 uses locality only. B1 uses calibrated transfer
plus measured reduction/model compute with queue cost fixed to zero. Forced A28
and forced RTX runs provide the empirical placement oracle.

### Superseded v1 context freeze

The first freeze under `runs/heterogeneous-v1/workload-freeze-json/` used S/M/L
payloads of 8,385,059 / 33,552,190 / 134,213,826 bytes. Its final evidence
projection was approximately 2,018 bytes and produced only 610--616 actual
model-input tokens. This missed the declared approximately 2k--8k-token
meaningful synthesis-input target. The executions and telemetry remain
reconstructable, but this representation is not eligible as E5 regime-freeze
evidence or as a formal workload. It was not silently rewritten or deleted.

### Frozen v2 context representation

The replacement freeze is
`runs/heterogeneous-v1/workload-freeze-json-v2-6kb/manifest.json` (SHA-256
`a8479131b6638e67086e664fd5375769a0e5adaddf3a0228c9b9aa28f49667b9`).
It versions every public artifact ID with `heterogeneous-v2` and uses a
deterministic UTF-8, word-boundary prefix of at most 6,000 bytes from each real
source after the fixed field projection. The payload bytes are 8,390,183 (S),
33,551,977 (M), and 134,222,247 (L). The representation remains deterministic
semantic replication rather than random filler.

The frozen context preflight declares a 12,453-byte worst-case projected JSON
upper bound, a 15,616-byte reduced-artifact limit, a 512-token prompt upper
bound, 256 reserved output tokens, and the same 16,384-token model context. It
fails closed; no truncation or fallback is permitted.

The valid forced-RTX smoke
`hetero-v1-context-v2-smoke-rtx-audit2` exercised the real S payload at the
30 Mbps + 20 ms condition. Its projected context artifact was 12,441 bytes and
the model consumed 3,201 input tokens, emitted 188 output tokens, and stopped
with `finish_reason=stop`. Model service latency was 18,543.0 ms, workflow E2E
was 71,142.6 ms, runner E2E was 78,099.7 ms, and 16,813,463 transferred bytes
took 4,712.9 ms. The result was format-valid with score 1.0; its 35-event trace
is reconstructable. This validates the v2 execution contract and input scale,
not placement superiority or a benchmark claim.

## Crossover pilot

### Exploratory v1 pilot retained but excluded

The superseded representation completed 108 otherwise valid forced-placement
executions over six nominal bandwidths, three payloads, two placements, and
three repetitions. Its machine-readable exploratory summary is
`results/heterogeneous-v1-pilot-analysis.json`. It suggested the following
crossovers, but these are not used to freeze E6 regimes because every run used
the under-scale 610--616-token synthesis input.

| payload | predicted break-even Mbps | exploratory observed preference |
|---|---:|---|
| S | 0.906 | RTX was already faster at the lowest tested 3 Mbps; crossover, if any, was below the sweep |
| M | 3.636 | A28 at 3 Mbps, RTX at 10 Mbps; bracket 3--10 Mbps |
| L | 14.430 | A28 at 10 Mbps, RTX at 30 Mbps; bracket 10--30 Mbps |

There is also a provenance limitation in this old result tree. After 74 valid
runs, `hetero-v1-pilot-bw10-l-forced-a28-r03` completed its workflow, result,
and 34-event reconstructable trace, but A5 SSH timed out during post-run
generated-artifact cleanup. The then-current driver raised before writing the
metadata sidecar. Therefore the directory has a result and trace but no
experiment metadata and is excluded, even though its semantic score was 1.0.
The exact generated artifacts were subsequently removed, the cleanup error was
made persistent, and the cell was rerun only under the new ID
`hetero-v1-pilot-bw10-l-forced-a28-r03-replacement-audit1`. Consequently the
old tree contains 109 result/trace directories but only 108 eligible metadata
sidecars; the exploratory analyzer counts the 108 sidecar-backed runs. Neither
the original cleanup-failed run nor the 108-run exploratory analysis is formal
evidence.

### E5 v2 pilot status

E5 is being rerun from the v2 freeze with new run IDs. The frozen randomized
schedule is `results/heterogeneous-v1-pilot-v2-schedule.json`: seed 20260922,
six calibrated bandwidths x three payloads x two forced placements x three
repetitions = 108 scheduled runs. The live resume ledger is
`results/heterogeneous-v1-pilot-v2-schedule-progress.json`. Because the matrix
is still running, partial cells are not analyzed here and no v2 crossover or
regime-selection conclusion is claimed.

E6 (freeze H_low/H_mid/H_high) remains pending completion and audit of E5 v2.

## Formal B0/B1 and oracle matrix

E7 is pending E6. No formal B0/B1, forced-oracle, routing-regret, or
oracle-selection result is claimed. E8 remains optional and has not started.
E9 must follow successful controlled results and has not started. Queue/load
experiments and M5 have not started.

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
| pilot entrypoint import | system/harness confounder | no | direct script execution could not import the package-qualified sibling module and failed before argument parsing, schedule creation, `tc`, or any run; repository-root import bootstrap was scoped to direct execution |
| `hetero-v1-pilot-bw10-l-forced-a28-r03` | system/harness confounder | no | workflow/result/trace completed, but A5 SSH timed out during generated-artifact cleanup before metadata persistence; exact artifacts were later removed, cleanup failure persistence was patched, and replacement used the new `-replacement-audit1` ID |
| old 108-run context-scale pilot | experimental-design confounder | no (exploratory only) | all executions used only 610--616 model-input tokens instead of the declared approximately 2k--8k target; data are retained, but cannot select E6 regimes or support formal conclusions; v2 representation and new run IDs were frozen |
| `hetero-v1-context-v2-smoke-rtx-audit1` | system/harness confounder | no | explicit v2 input preload was missing, causing a prepositioned-artifact mismatch; the finish-reason validator also masked the primary failure; result/trace/metadata were retained, validation was fixed, inputs were preloaded, and audit2 used a new ID |

No failed attempt above is used as calibration, compute-profile, v2 pilot,
oracle, or scheduler evidence. The old 108-run pilot is retained only as
explicitly labelled exploratory evidence. Detailed machine-readable records,
including the missing-import, cleanup-timeout, context-scale, and missing-preload
provenance, are under `results/invalid-runs/`.

## Verification

Pending final post-experiment pytest, Ruff, strict Pyright, trace reconstruction,
and clean-worktree verification.

## Conclusions

E1--E4 establish the real heterogeneous substrate, calibrated `tc` network
conditions, equivalent 27.3B model replicas, and repeated device profiles. The
first 108-run forced-placement sweep is reproducible but is excluded from E5/E6
because its synthesis context was below the declared input scale. The versioned
v2 representation has passed a 3,201-input-token real-Worker smoke, and E5 v2 is
in progress. No v2 crossover, formal routing-regret, oracle-selection, or
scheduler-superiority claim is made before E5--E7 finish and are audited.
