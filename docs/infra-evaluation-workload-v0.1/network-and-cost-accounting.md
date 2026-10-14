# Network and cost accounting

Two profiles were applied through **study-owned paced HTTP proxies** on A4, not host `tc`: `Hslow=3 Mbps + 50 ms` on port `63105`, `Hfast=100 Mbps + 5 ms` on `63106`. `source-b` used its existing allowlisted Worker pull to fetch from those endpoints. Proxy requests forwarded to the protected source-a Worker, and transferred SHA256/byte counts matched the original artifact. The [eight calibration observations](network-calibration-public.json) are endpoint-to-endpoint pull measurements, including HTTP/Worker overhead:

| Profile | 3 small-payload median | 3,955,727-byte payload latency | Achieved large-payload throughput |
|---|---:|---:|---:|
| Hslow | 103.125 ms | 10,754.608 ms | 2.943 Mbps |
| Hfast | 57.931 ms | 488.611 ms | 64.767 Mbps |

The small-payload difference is 45.194 ms, close to the configured **additional RTT difference** of 45 ms; absolute small-payload latency also includes Worker/proxy/service overhead. Hfast did not reach nominal 100 Mbps, so future analysis must use measured rates, not the configuration label. These probes establish effect on the actual artifact-pull data path; they are not a complete task-method-network matrix. Calibration copies were deleted, and host traffic control was untouched.

The 8 valid resident-task operator probes transferred **128,169 payload bytes** (MultiHop 126,484; MultiModalQA 1,685), with median transfer latencies 13.065 / 5.047 ms on the unshaped LAN. [`feasibility-public.json`](feasibility-public.json) records per-probe bytes, transfer duration and total **probe** wall time. It does not call a Planner or complete a benchmark answer; its wall time is not task E2E. Byte counts are application payload, excluding HTTP framing/control traffic. A future run must collect network counters if wire-level totals are required.

Cold setup is separate. The initial compressed source bundles were 3,052,214 bytes (A4) and 2,115,911 bytes (workstation); the validity correction added 5,395 and 1,801 bytes. Thus **5,175,321 compressed source-package bytes** were staged before resident use, across multiple physical hops. Logical resident artifacts total 13,331,531 bytes because source documents and per-node BM25 shards coexist. The code archive was another 344,441 bytes, and A4 dependency installation downloaded packages separately. Exact SSH protocol traffic, package-install bytes and setup elapsed time were not metered, so complete setup cost is **unknown** rather than zero. No per-query amortization is reported.

For later trials, record `setup_bytes/latency`, `workflow_transfer_bytes/latency`, local operator latency, model-service latency, control latency, true task E2E, and unclassified time as separate nullable fields. Record model/deployment revision, request arrival/completion, queue delay, tokens, GPU utilization, cache telemetry or `unknown`, warm/cold label and concurrent workload. No model was invoked in P1, so model latency and GPU monetary cost are `null`; no GPU price is fabricated. The earlier fixed-workflow study found substantial serving-state variance, which remains a risk to any future network-conditioned cost comparison.
