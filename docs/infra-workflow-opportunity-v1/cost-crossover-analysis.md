# Cost-crossover analysis and measurement boundary

The primary comparison is paired E2E wall time for `frames` minus `sheet`
under each fixed network condition. A sign change is a time cost crossover;
it becomes a **quality-constrained** preference reversal only if both
workflows satisfy the original task evaluator in the compared conditions.
The result is not inferred from the historical 284.7/205.4/34.9/160.8 s
table, whose full provenance is unverified.

The fast 100 Mbps pair is quality-matched: both original scores are 1.
`frames` took 240.690 s E2E; `sheet` took 83.136 s, a 157.554 s sheet
advantage. The eight-frame model call used 7,512 input tokens and 210.982 s
of model service, while the sheet call used 1,943 input tokens and 54.513 s.
Workflow-triggered transfer fell from 1,230,240 to 452,899 bytes and from
0.904 to 0.264 s. The service-work difference (156.469 s) accounts for
nearly all observed E2E separation, while transfer saved under one second.
The smaller image-token count is consistent with lower model work, but the
fixed order did not independently control service warm/cache state. Both
conditions independently
staged the same 282,442,048-byte MP4 in 24.584/24.633 s, corresponding to
about 91.9/91.7 Mbps effective source transfer.

The subsequent slow `frames` cell used the **same sampled-artifact digest,
same prompt digest and same 7,512 reported input tokens** as fast `frames`,
but its physical model service fell from 210.982 to 3.416 s. This is
consistent with unmeasured serving cache/warm-state reuse; the OpenAI-compatible
response does not expose actual cache-hit work. The fixed order places fast
before slow, so model state is confounded with network state. The slow cell's
801.393 s E2E is dominated by 788.944 s mandatory source transfer, and its
1,230,240 workflow bytes took 4.815 s to move. A fast-versus-slow model-work
comparison cannot be interpreted as a bandwidth effect. No quality-constrained
**infrastructure-caused** preference reversal will be claimed from a sign
change unless this state confound can be ruled out; the package makes no
selective rerun to do so.

The final slow `sheet` cell also scored 1 and took 797.929 s, with 788.584 s
source staging, 1.411 s action transfer and 3.274 s model service. Both
slow model calls show short service times compared with their fast counterparts
despite identical within-workflow prompt/evidence hashes and token counts.
For the paired E2E cost function, the directly observed differences are

| Network state | `T(frames) − T(sheet)` | Preferred by measured E2E | Both correct? |
| --- | ---: | --- | --- |
| Fast 100 Mbps / configured 5 ms | +157.554 s | Sheet | Yes |
| Slow 3 Mbps / configured 50 ms | +3.464 s | Sheet | Yes |

There is **no observed preference reversal**; the sheet wins in both measured
states. The slow gain is small relative to its 789 s common staging cost and
to uncontrolled serving-state variation. It cannot establish a robust
break-even. The workflow image payload fell by 777,341 bytes (63.2%) under
either state. Observed transfer saving grew from 0.640 s fast to 3.404 s
slow, but model-service time fell by 156.469 s in the fast pair and only
0.142 s in the slow pair. This is a multi-component cost trade-off with
unknown GPU monetary cost, not a single calibrated dollar objective.

The measured task boundary starts at `ControlPlaneBenchmarkRunner.run()`:
mandatory original-video materialization from controller to A4, media
operations, workflow-triggered artifact transfers, physical inference and
terminal evaluation are included. `tc` setup and fresh Worker startup occur
before this task clock, and cleanup after it; those costs are recorded for
reproducibility but not mistaken for task execution. The original 282 MB
source is common to both workflow choices and dominates slow-condition
latency. The trace audit reports initial bytes/time separately from
action-triggered bytes/time. Image transfer time is a Worker/HTTP measurement,
not a pure link-service measurement; simultaneous stages and critical-path
overlap make service-work sums nonadditive with E2E.
The model's short terminal label returns in the Worker HTTP response; its
standalone byte count and latency are not separately instrumented and remain
unknown rather than being folded into a fabricated transfer component.

The fixed policy makes no cloud API calls, so observed cloud API spend is
zero **for this fixed condition**. Manager decision turns are deterministic
controller operations, with no LLM tokens. Specialist and Verifier calls are
absent under the frozen verification policy. Local A28 model requests, input
and output tokens, and service latency are real; GPU monetary cost is
**unknown**. A later adaptive selector would need to add its own
Manager/Verifier/quoting overhead before comparison with these fixed-workflow
opportunity measurements.

The sanitized scalar [result file](../../results/infra-workflow-opportunity-v1/controlled-public.json)
contains per-action and per-cell measurements plus network restoration
receipts. The separate [network calibration record](../../results/infra-workflow-opportunity-v1/network-calibration.json)
distinguishes prior same-link `iperf` measurements from this batch's effective
original-video transfer throughput. Effective throughput is computed as
`8 × initial_transfer_bytes / initial_transfer_seconds` and compared with
the configured 3/100 Mbps ceilings. This is an end-to-end transfer check,
not an independent `iperf` calibration or a measured symmetric RTT. The prior
[Stage 2 network audit](../../results/harness-v2-baseline-requalification/audit-summary.json)
on the same links/configuration measured controller-to-A4 throughput of
95.39 Mbps fast and 2.796 Mbps slow, with restoration receipts. Those are
historical calibration, not a fresh pre-run measurement for these four cells.
With only two configured bandwidths, any break-even interpolation is a model
estimate and is not independently validated. If either quality or cost
dimension is missing, no crossover claim is made.
