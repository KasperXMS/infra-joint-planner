# Infra-aware replanning preliminary v1

## Outcome

All 18 primary cells completed with valid runtime, evaluator, trace, visibility, and traffic-control evidence. No replanner changed G0 in any cell. Therefore this preliminary does **not** establish `H1 != H2 -> G(H1) != G(H2)`, and it provides no measurable system benefit attributable to workflow evolution.

The negative result is informative: infrastructure visibility alone did not make the LLM revise pending work, even when the prompt contained artifact locations, complete 3/10/30 Mbps link state, zero load, transfer estimates, and frozen measured A28/4090 service-cost profiles.

## Exact settings

- Cases: Video-MME 795-3, MultiHop multi-source, LongBench multi-document.
- Network: globally filtered worker traffic at 3, 10, or 30 Mbps; added RTT 0 ms.
- Arms: resource-blind semantic view versus the same replanner plus explicit physical state and cost view.
- Frozen G0, task/evaluator, model pool, operator vocabulary, initial placement, B0 scheduler, one replan, n=1, no retry or replacement.
- Checkpoint: after the deterministic tool prefix and before the first `invoke_model`; completed nodes/artifacts are immutable.
- Data were prepositioned once under unshaped networking; each runner E2E begins after tc is active. Every cell has before/after class counters and restored-qdisc evidence.

## Actual operator placements

Each task used the same B0-selected placement in all six cells:

- longbench-multidoc: `bm25-01` -> `A4`; `bm25-02` -> `A5`; `bm25-03` -> `A28`; `bm25-04` -> `A5`; `final-synthesis` -> `A28`; `notes-01` -> `A28`; `notes-02` -> `A28`; `notes-03` -> `strong-4090`; `notes-04` -> `strong-4090`.
- multihop-multisource: `final-synthesis` -> `A28`; `notes-barbarian` -> `strong-4090`; `notes-sorcerer` -> `strong-4090`; `retrieve-barbarian` -> `A5`; `retrieve-sorcerer` -> `A4`; `retrieve-sorcerer-3` -> `A28`.
- video-long-payload: `final-synthesis` -> `strong-4090`; `inspect-opening-evidence` -> `A28`; `make-opening-contact-sheet` -> `A4`; `sample-opening-frames` -> `A4`.

## Primary runs

| Run | Decision | G1 | Score | E2E ms | CP / overlap ms | Transfer B / ms | Sum op / model ms | Plan / replan ms |
|---|---|---|---:|---:|---:|---:|---:|---:|
| 01-video-long-payload-H_low-resource-blind | keep | `6ff35770` | 1.0 | 156825.4 | 153802.5 / 0.0 | 127578 / 497.2 | 153304.1 / 151329.4 | 0.1 / 2067.0 |
| 02-video-long-payload-H_low-infra-aware | keep | `6ff35770` | 1.0 | 106193.4 | 103668.0 / 0.0 | 127578 / 476.2 | 103190.8 / 101279.0 | 0.0 / 1919.9 |
| 03-video-long-payload-H_mid-resource-blind | keep | `6ff35770` | 1.0 | 104756.3 | 103282.5 / 0.0 | 127578 / 136.4 | 103144.4 / 101267.1 | 0.1 / 1030.5 |
| 04-video-long-payload-H_mid-infra-aware | keep | `6ff35770` | 1.0 | 105365.7 | 103342.5 / 0.0 | 127578 / 144.4 | 103196.9 / 101290.0 | 0.1 / 1286.6 |
| 05-video-long-payload-H_high-resource-blind | keep | `6ff35770` | 1.0 | 104947.7 | 103385.2 / 0.0 | 127578 / 138.9 | 103245.4 / 101278.1 | 0.1 / 1146.8 |
| 06-video-long-payload-H_high-infra-aware | keep | `6ff35770` | 1.0 | 105241.3 | 103383.7 / 0.0 | 127578 / 158.9 | 103223.8 / 101279.2 | 0.1 / 1300.2 |
| 07-multihop-multisource-H_low-resource-blind | keep | `9d139d96` | 0.0 | 22586.5 | 17010.2 / 0.0 | 9565 / 68.1 | 20183.5 / 19099.0 | 0.1 / 1415.3 |
| 08-multihop-multisource-H_low-infra-aware | keep | `9d139d96` | 0.0 | 11410.2 | 6172.8 / 0.0 | 9565 / 172.9 | 9153.5 / 7941.4 | 0.1 / 1152.4 |
| 09-multihop-multisource-H_mid-resource-blind | keep | `9d139d96` | 0.0 | 11290.7 | 5979.9 / 0.0 | 9565 / 91.4 | 8987.6 / 7915.8 | 0.1 / 1272.5 |
| 10-multihop-multisource-H_mid-infra-aware | keep | `9d139d96` | 0.0 | 11997.0 | 6164.7 / 0.0 | 9565 / 115.2 | 9243.5 / 7936.8 | 0.1 / 1526.1 |
| 11-multihop-multisource-H_high-resource-blind | keep | `9d139d96` | 0.0 | 11570.2 | 6140.8 / 0.0 | 9565 / 216.1 | 9129.5 / 7949.4 | 0.2 / 1476.6 |
| 12-multihop-multisource-H_high-infra-aware | keep | `9d139d96` | 0.0 | 11002.3 | 5960.8 / 0.0 | 9565 / 97.2 | 8979.2 / 7953.5 | 0.1 / 1197.3 |
| 13-longbench-multidoc-H_low-resource-blind | keep | `85d9cd7d` | 0.0 | 287848.7 | 166007.1 / 9947.9 | 41452 / 871.7 | 294758.8 / 294199.1 | 0.0 / 1341.9 |
| 14-longbench-multidoc-H_low-infra-aware | keep | `85d9cd7d` | 0.0 | 141256.4 | 70760.8 / 7519.0 | 41452 / 838.5 | 145205.9 / 144751.2 | 0.2 / 1495.2 |
| 15-longbench-multidoc-H_mid-resource-blind | keep | `85d9cd7d` | 0.0 | 141137.8 | 70632.9 / 7509.6 | 41452 / 966.6 | 145335.4 / 144724.0 | 0.2 / 1111.3 |
| 16-longbench-multidoc-H_mid-infra-aware | keep | `85d9cd7d` | 0.0 | 142336.0 | 70832.7 / 7429.3 | 41452 / 658.8 | 145254.5 / 144690.9 | 0.1 / 1131.8 |
| 17-longbench-multidoc-H_high-resource-blind | keep | `85d9cd7d` | 0.0 | 139986.9 | 70580.3 / 7379.5 | 41452 / 155.8 | 145075.6 / 144733.7 | 0.2 / 1416.7 |
| 18-longbench-multidoc-H_high-infra-aware | keep | `85d9cd7d` | 0.0 | 141129.5 | 70624.1 / 7313.6 | 41452 / 667.9 | 145071.1 / 144655.4 | 0.2 / 1394.0 |

## Blind versus aware

| Task / regime | Same G1 | Score blind/aware | Aware - blind E2E ms | Aware - blind traffic B |
|---|---|---:|---:|---:|
| longbench-multidoc / H_high | yes | 0.0/0.0 | 1142.5 | 0 |
| longbench-multidoc / H_low | yes | 0.0/0.0 | -146592.3 | 0 |
| longbench-multidoc / H_mid | yes | 0.0/0.0 | 1198.2 | 0 |
| multihop-multisource / H_high | yes | 0.0/0.0 | -567.9 | 0 |
| multihop-multisource / H_low | yes | 0.0/0.0 | -11176.3 | 0 |
| multihop-multisource / H_mid | yes | 0.0/0.0 | 706.3 | 0 |
| video-long-payload / H_high | yes | 1.0/1.0 | 293.6 | 0 |
| video-long-payload / H_low | yes | 1.0/1.0 | -50631.9 | 0 |
| video-long-payload / H_mid | yes | 1.0/1.0 | 609.4 | 0 |

Raw E2E deltas are not method effects because every paired comparison executed the same final workflow. The first run of each task also paid a repeatable model cold-start penalty:

| Task | First / later-median model ms | Ratio | Tokens identical |
|---|---:|---:|---|
| longbench-multidoc | 294199.1 / 144724.0 | 2.03x | yes |
| multihop-multisource | 19099.0 / 7941.4 | 2.40x | yes |
| video-long-payload | 151329.4 / 101279.0 | 1.49x | yes |

## Workflow evolution and failure modes

- Video: all six cells kept G0 (`6ff35770...`) and scored 1.0. Bandwidth changed measured transfer time, but neither arm changed the two-stage visual workflow.
- MultiHop: all six cells kept G0 (`9d139d96...`) and scored 0.0. At the early checkpoint the replanner accepted shard coverage without adding the evidence branch that the later terminal-checkpoint validation had needed. This is premature keep / insufficient semantic diagnosis, not a runtime failure.
- LongBench: all six cells kept G0 (`85d9cd7d...`) and scored 0.0. Infra-aware reasons repeatedly claimed no materially cheaper alternative despite explicit A28 versus 4090 service profiles. This is reproducible infra ignored / wrong cost reasoning. Four evidence-note calls also ended at the fixed output limit, preserving the known quality limitation of the frozen baseline.
- No over-reduction, new branch, deleted node, modified dependency, or model-binding change occurred. Consequently there is no traffic or latency gain caused by G0->G1.

## Validity audit

- Coverage: 18/18; invalid cells: [].
- Every trace has a valid parent chain, exactly one replanner start/end, one run end, and no run-failed event.
- Blind prompts contain no infrastructure snapshot or physical markers; aware prompts contain them. Neither arm contains serialized source/evaluator/gold/private evidence keys.
- Every tc attestation records all four HTB roots/classes, remote exit 0, successful cleanup, and restored roots A4/A5/A28=`mq`, strong-4090=`noqueue`.
- The pre-execution attempt-1 SSH-key failure is retained separately and excluded; it created no benchmark run. Attempt 2 contains all 18 primary runs.

## What this supports

The experiment supports method formalization around an explicit optimizer or validated cost-to-action mechanism: merely serializing infrastructure state into an LLM prompt did not produce joint workflow adaptation. It also shows that checkpoint placement controls which semantic deficiency is observable and must be part of the method contract.

It does not support a claim that infra-aware replanning improves latency, traffic, cost, or quality; it does not establish bandwidth-dependent workflow evolution; and n=1 plus cold-start ordering prevents causal interpretation of same-workflow E2E differences. No extra benchmark, repetition, RL, method, or sweep was run.
