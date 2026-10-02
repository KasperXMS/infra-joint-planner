# SDK-native Infra-Aware Preliminary — Qwen3.8-Max v1

Date: 2026-10-02
Branch: `open-ended-mas-preliminary-v1`

## Scope

This experiment block evaluates one frozen Qwen cloud control plane on:

```text
MultiHop multihop-multisource
× Fast / Slow
× Blind / Aware
× n=3
```

The existing DeepSeek runs remain a separate pilot. No DeepSeek result is mixed
into the Qwen statistics below. The earlier `qwen-plus-2025-12-01` diagnostic was
the wrong candidate model; its evidence remains preserved, but it is excluded
from this Qwen3.8-Max block.

## Qwen control-plane configuration

Both cloud roles used exactly:

| Setting | Value |
|---|---|
| Manager | `qwen3.8-max` |
| Blind Verifier | `qwen3.8-max` |
| Provider | Alibaba Cloud Model Studio |
| API | existing OpenAI-compatible Beijing endpoint |
| Thinking mode | disabled with `enable_thinking=false` |
| Manager temperature | provider default |
| Verifier temperature | `0` |
| Client timeout / retries | 180 seconds / 0 |

The physical inference plane was not changed. A28 and strong-4090 continued to
serve `qwen3.8-27b-q4km-v1` through Ollama with the frozen 32K/2048 contract.
A4 and A5 remained operator-only Workers.

The endpoint's model listing contained `qwen3.8-max`. Synthetic compatibility
probes established:

- ordinary native function calling succeeded (`finish_reason=tool_calls`);
- required Verifier tool selection is rejected by Qwen thinking mode; and
- the same required tool call succeeds when `enable_thinking=false`.

The only provider adapter therefore injects that frozen request option. It does
not change Manager/Verifier instructions, task policy, tool schemas, budgets, or
physical scheduling.

## Sanity validation

The first deployment attempt at `b1d4e08` stopped before turn 1 because the
provider adapter did not subclass the Agents SDK `Model` interface. It recorded
zero Manager, tool, or model calls and is classified as an operational harness
failure. The attempt is preserved and was not counted as a semantic result.

The one permitted identical operational replacement used revision `b951ada` and
completed the full control path:

| Run | Completion | Score | Manager / Verifier | Tool / model / inference | E2E | Action bytes |
|---|---:|---:|---:|---:|---:|---:|
| `qwen38max-sanity-multihop-fast-blind-replacement-1` | yes | 0 | 16 / 16 | 24 / 5 / 3 | 527.995 s | 5,204,596 |

The terminal answer was format-valid and the private evaluator ran. The score of
zero is a valid semantic result, not a sanity-gate failure. Blind privacy passed.

Sanity provenance:

- code revision: `b951adaa1c1f37648b277b0b25bbee06d0568088`;
- sanity config SHA-256: `70a1a01c137b1e789581d9d84dd69f35c1b9b35c3126d8cfbb04b4b66989a829`;
- sanity harness SHA-256: `3ee816c167495c8d669a53b7eea348218183b078af4931ee1200827acddcb322`;
- task bundle SHA-256: `54ef8ddbe4a3379254345f307b3f0ef6b95fe92e0b28ac4c89124bb6b7ebfe8e`.

## Frozen protocol

After sanity, `qwen-infra-preliminary-v1` was frozen with SHA-256:

```text
23523cb2d8342b222df46af1cfdad1a43bc518eb5e9a7078b3a9dda4f2515c01
```

Shared settings for all formal runs:

- SDK-native persistent Manager and bounded specialists-as-tools;
- Blind Verifier;
- budgets `20 Manager / 64 tool-model / 20 Verifier`;
- identical task bundle, tool space, 32K/2048 physical deployments, scheduler,
  benchmark adapter, evaluator, and initial placement;
- Fast = 100 Mbps + 5 ms;
- Slow = 3 Mbps + 50 ms;
- fresh isolated Worker stores, one run, no retry/replacement per cell.

Blind received no physical profile. Aware received only anonymous
`PhysicalProfileView`; raw worker, device, deployment, address, route, and private
benchmark metadata remained unavailable to the logical layer.

## MultiHop matrix

`M/V` is Manager turns / Verifier calls. `T/M/I` is tool actions / declared model
actions / model actions that actually reached inference. Transfer excludes the
fixed 7,696,522-byte initial materialization.

| Condition | r | Completed | Score | E2E (s) | Action bytes | Transfer (s) | M/V | T/M/I | Graph N/E | Context failures |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Fast-Blind | 1 | yes | 0 | 166.909 | 5,204,596 | 1.821 | 14/14 | 25/2/1 | 27/16 | 1 |
| Fast-Blind | 2 | yes | 0 | 238.937 | 5,204,596 | 3.067 | 4/4 | 3/1/1 | 4/4 | 0 |
| Fast-Blind | 3 | yes | 0 | 99.892 | 5,204,596 | 1.632 | 7/7 | 8/2/1 | 10/9 | 1 |
| Fast-Aware | 1 | yes | 0 | 228.002 | 112,712 | 0.473 | 9/9 | 19/2/1 | 21/29 | 1 |
| Fast-Aware | 2 | yes | 0 | 194.482 | 5,204,596 | 1.428 | 5/5 | 3/1/1 | 4/4 | 0 |
| Fast-Aware | 3 | yes | 0 | 123.737 | 57,351 | 0.182 | 5/5 | 14/2/1 | 16/18 | 1 |
| Slow-Blind | 1 | yes | 0 | 1007.161 | 79,650 | 1.174 | 15/15 | 23/7/6 | 30/18 | 1 |
| Slow-Blind | 2 | yes | 1 | 186.445 | 5,204,596 | 14.842 | 8/8 | 8/2/1 | 10/10 | 1 |
| Slow-Blind | 3 | yes | 0 | 310.232 | 5,204,596 | 14.945 | 11/11 | 7/2/1 | 9/10 | 1 |
| Slow-Aware | 1 | yes | 0 | 193.064 | 5,204,596 | 15.044 | 7/7 | 5/2/1 | 7/8 | 1 |
| Slow-Aware | 2 | no | — | 654.509 | 171,085 | 3.284 | 20/20 | 33/6/4 | 39/37 | 2 |
| Slow-Aware | 3 | yes | 0 | 232.591 | 5,204,596 | 14.817 | 4/4 | 3/1/1 | 4/4 | 0 |

Slow-Aware r2 exhausted the frozen 20-turn Manager budget after extensive legal
retrieval/reduction/model activity. It is an eligible workflow/stopping failure,
not an operational failure, and was neither retried nor replaced.

## Aggregate results

| Condition | Completion | Scores | Mean / median E2E | Mean / median action bytes |
|---|---:|---|---:|---:|
| Fast-Blind | 3/3 | 0, 0, 0 | 168.579 / 166.909 s | 5,204,596 / 5,204,596 |
| Fast-Aware | 3/3 | 0, 0, 0 | 182.073 / 194.482 s | 1,791,553 / 112,712 |
| Slow-Blind | 3/3 | 0, 1, 0 | 501.279 / 310.232 s | 3,496,281 / 5,204,596 |
| Slow-Aware | 2/3 | 0, —, 0 | 360.055 / 232.591 s | 3,526,759 / 5,204,596 |

Relative to Blind:

- Fast-Aware reduced mean action traffic by 65.6% and median traffic by 97.8%,
  but mean E2E was 8.0% higher and median E2E was 16.5% higher.
- Slow-Aware mean E2E was 28.2% lower and median E2E was 25.0% lower, while mean
  traffic was 0.9% higher and median traffic was unchanged. Completion fell from
  3/3 to 2/3.

These n=3 values are descriptive only. The long-tail trajectories and the one
Aware budget failure preclude a claim that Aware improves end-to-end performance
while preserving completion/quality.

## Workflow signatures

All formal runs used sequential native action batches (`parallel_batches=0`).
Compact final-graph operator counts were:

| Condition | r | Workflow signature |
|---|---:|---|
| Fast-Blind | 1 | BM25 18, read 6, aggregate 1, model 2 |
| Fast-Blind | 2 | BM25 2, aggregate 1, model 1 |
| Fast-Blind | 3 | BM25 4, read 3, aggregate 1, model 2 |
| Fast-Aware | 1 | BM25 8, filter 6, select 2, read 1, aggregate 2, model 2 |
| Fast-Aware | 2 | BM25 2, aggregate 1, model 1 |
| Fast-Aware | 3 | BM25 9, read 3, aggregate 2, model 2 |
| Slow-Blind | 1 | BM25 21, read 2, model 7 |
| Slow-Blind | 2 | BM25 6, aggregate 2, model 2 |
| Slow-Blind | 3 | BM25 4, select 2, aggregate 1, model 2 |
| Slow-Aware | 1 | BM25 4, aggregate 1, model 2 |
| Slow-Aware | 2 | BM25 20, select 6, top-k 2, filter 1, read 2, aggregate 2, model 6 |
| Slow-Aware | 3 | BM25 2, aggregate 1, model 1 |

The physical scheduler selected the A28 Qwen3.8-27B deployment for every model
action that reached inference. This is a physical-layer decision, not a deployment
identifier exposed to Blind/Aware logical prompts.

## Infrastructure-response observations

The Aware trajectories did receive and react within an anonymous profile-bearing
control loop. Successful Aware traces recorded `fast`, `local`, or `constrained`
network classes without identities. The raw Slow-Aware r2 trace also contains a
`constrained` profile on its logical observations. Its compact `summary.json`
reports zero profile observations because the summarizer reads the returned loop
object, which is absent on loop failure; this is a post-run summary undercount,
not missing Manager input. The reconstructable JSONL trace is authoritative.

Infrastructure visibility produced materially different workflows, but the
response was not systematic across replicates:

- low-traffic reduction appeared in Fast-Aware r1/r3 but not r2;
- it appeared in Slow-Aware r2, where over-expansion exhausted the turn budget,
  but not in Slow-Aware r1/r3;
- simple full-movement workflows occurred under both Fast and Slow; and
- within-condition workflow variance was comparable to or larger than the
  between-network difference.

Therefore the experiment does **not** establish a stable implication
`H_fast != H_slow -> W_aware,fast != W_aware,slow`. It does establish that the
open-ended Qwen control plane can produce both aggressive reduction and full-data
paths, and that those choices have large execution consequences.

## Quality

The original evaluator was used unchanged. One run scored 1.0; ten completed
runs scored 0.0; one run did not reach evaluation. Several zero-score terminal
answers were format-valid prose beginning with an affirmative answer, while the
only score-1 output was the short answer `Yes`. This observed evaluator sensitivity
means the scores are reported exactly as produced but should not be reinterpreted
as a calibrated measure of explanatory semantic quality. No post-hoc extraction,
gold access, or evaluator modification was applied.

## Operational and integrity audit

- Formal provider failures: 0/12.
- Formal tc cleanup failures: 0/12.
- Formal exact qdisc restorations: 12/12.
- Formal logical privacy passes: 12/12.
- Fresh store contamination: none observed.
- Retries/replacements in the formal matrix: 0.
- Worker processes were stopped after every cell and after the final run.
- Final native qdisc: A4/A5/A28 `mq`; strong-4090 `noqueue`.
- Full result and JSONL trace exist for every completed and failed formal run.

Durable evidence remains on strong-4090 at:

```text
# Wrong qwen-plus candidate, excluded
/home/super/xiaoming/sdk-native-infra-qwen-v1-603a8dd/

# Qwen3.8-Max sanity operational failure and replacement
/home/super/xiaoming/sdk-native-infra-qwen38max-v1-b1d4e08/evidence/sanity/
/home/super/xiaoming/sdk-native-infra-qwen38max-v1-b951ada/evidence/sanity-replacement-1/

# Formal Qwen3.8-Max matrix
/home/super/xiaoming/sdk-native-infra-qwen38max-v1-73a1250/evidence/matrix-r1/
/home/super/xiaoming/sdk-native-infra-qwen38max-v1-fd7acb6/evidence/matrix-r2/
/home/super/xiaoming/sdk-native-infra-qwen38max-v1-fd7acb6/evidence/matrix-r3/
```

Each formal cell contains its freeze manifest, private evaluator inputs, result,
full JSONL trace, summary, Worker-store provenance, and tc attestation. Benchmark
datasets remained on strong-4090 and were never relayed through the development
machine.

## Comparison with the DeepSeek pilot

The DeepSeek n=1 pilot previously showed lower E2E and traffic for Slow-Aware
than Slow-Blind. The independent Qwen block also has lower Slow-Aware mean/median
E2E, but it does not reproduce a stable traffic reduction and includes one Aware
budget failure. These are separate experiment blocks and are not pooled.

## Preliminary interpretation and stop decision

The corrected Qwen model is **`qwen3.8-max` for both cloud Manager and Verifier**.
It successfully drove the frozen SDK-native harness through the sanity gate and
the complete 12-run MultiHop preliminary.

The main finding is mixed:

1. infrastructure-aware observations can coincide with large workflow and traffic
   changes;
2. those changes are not consistently aligned with Fast versus Slow;
3. workflow stochasticity and local-model service latency dominate several cells;
4. Aware does not yet preserve completion and quality while consistently lowering
   cost.

The requested MultiHop n=3 block is complete. No LongBench, Video-MME, additional
provider, prompt tuning, or method change was started after this audit.

## Subsequent trace audit note — 2026-10-02

The original tables, raw scores and interpretations above are preserved as historical
analysis. [Qwen MultiHop Trace Audit v1](qwen-multihop-trace-audit-v1.md) corrects
the all-sequential interpretation, separates nine affirmative serialization/metric
mismatches from the wrong-negative trajectory, flags two physical-observer
confounders, and establishes that first Aware actions precede profile delivery.
Its canonical yes/no scores are secondary post-hoc audit metrics, not revised
original benchmark scores. No formal run was repeated or historical result overwritten.
