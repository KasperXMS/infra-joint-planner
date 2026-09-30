# Blind harness v1.2 validation

## Decision

`blind-harness-v1.2` establishes a positive Blind execution baseline for the
`multihop-multisource` gate, but it does **not** pass the three-family completion
gate. MultiHop completed and scored `1.0`; LongBench terminated on an A28 model
service timeout after two typed context recoveries; Video produced the correct
semantic candidate but did not produce a contract-valid terminal choice. Therefore
v1.2 is not yet designated as the formal cross-benchmark Blind baseline, and the
Fast/Slow Blind/Aware preliminary was not started.

No run was retried or replaced. No prompt, Verifier, stopping rule, tool schema,
model/deployment, scheduler, benchmark adapter, evaluator, network setting, or task
representation was changed between cells. Dataset materialization and execution
stayed on strong-4090 and the Jetsons; no dataset bytes passed through the
development PC.

## Frozen harness

The new manifest is `configs/experiments/blind-harness-v1.2.yaml`, SHA-256
`b79ea82c12e251a4c88f23a88e0d11f6034c785a7693b3709aa9467548db7f28`.
It preserves the v1.1 behavior and changes only the generic limits:

| Limit | v1.1 | v1.2 |
|---|---:|---:|
| Manager turns | 12 | 20 |
| physical tool/model calls | 18 | 64 |
| Verifier calls | 12 | 20 |
| subagent turns | 8 | 8 |
| created subagents | 4 | 4 |
| active subagents | 2 | 2 |

The frozen runtime source hash is
`777ba219f80935f76b213c938c8933ee5f884354155f6eba736cdc5145d3c2eb`,
Manager-instruction hash is
`68b87058ba0a90549cd93a5e18a4a8def2f690e0df089545126a78718892a56e`,
Verifier source hash is
`6c7813735ceec02136008d74da99ae3e773ec93b95b5a50d8a8dd1fd992699e8`,
and static-capability hash is
`8d46d9b941a08380a00fdab1e7c151c25affd589ec4444864f3c5c925a2089a4`.
The anonymous deployments remained text+image, 32,768 context and 2,048 reserved
output. Visibility remained `BLIND`.

Each cell used new, previously absent Worker store roots and native/unshaped qdiscs.
Before each run, all four Worker surfaces were empty and matched the environment
contract. Raw qdisc inspection showed only the hosts' native `mq`, `fq_codel`, and
`noqueue` disciplines; no `htb`, `tbf`, or `netem` shaping was present.

## Results

| Task | Completed | Score / format | Manager / Verifier | Physical calls | Completed inference | E2E from trace | Transferred bytes | Primary class |
|---|---|---|---:|---:|---:|---:|---:|---|
| MultiHop `multihop-multisource` | yes | `1.0` / valid | 7 / 7 | 16 (14 tool, 2 model) | 1 | 171,824.720 ms | 7,708,104 | success |
| LongBench `longbench-multidoc` | no | evaluator not invoked | 8 / 7 | 15 (12 tool, 3 model) | 0; one backend request timed out | 929,909.142 ms | 1,081,150 | runtime/model-service timeout |
| Video-MME `video-long-payload` (`795-3`) | no | evaluator not invoked | 2 / 2 | 2 (1 tool, 1 model) | 1 | 388,154.451 ms | 282,885,553 | synthesis/output-contract failure |

All three logical privacy scans passed with no physical/private findings. None of
the runs reached the 20-turn, 64-call, or 20-Verifier ceiling.

## MultiHop gate

- Run: `07-multihop-blind-harness-v1.2-gate`
- Execution revision: `21b03b5b6fedf2845a69841144692e86d48ba6c3`
- Task/config hashes: task
  `54ef8ddbe4a3379254345f307b3f0ef6b95fe92e0b28ac4c89124bb6b7ebfe8e`,
  config `9a2e0505ab3c44776421fd0b2c329314cd458e1d9f8201d04d6b86096c458559`
- Initial placement: the three complete non-semantic corpus shards on A4, A5 and
  A28 respectively.
- First `READY_FOR_SYNTHESIS`: Verifier call 1.
- Graph: version 48, 16 nodes, 14 edges.

The first synthesis attempt was rejected before transfer at an estimated 86,055
input tokens plus 2,048 reserved output against the 32,768 window. The Manager then
performed narrower retrieval and aggregation, made a legal second model request,
reached real inference, and produced a non-empty `YES` terminal answer. Deterministic
format handling accepted it, and the private evaluator returned `1.0`.

This answers the first-stage question positively: with the 20-turn/64-call horizon,
the unchanged Blind Manager/Verifier loop can recover from a typed context failure,
synthesize, finalize, and invoke the evaluator normally.

## LongBench validation

- Run: `08-longbench-multidoc-blind-harness-v1.2`
- Execution revision: `b0dd1a51e3de790e759b3dc76b3a9807bddb6fd1`
- Task/config hashes: task
  `6c22cd47f24cf3279fb317c752ff5c54ff49505aae9249251611ff0727bde341`,
  config `7b2a460a583193fbc6350c837691e0d62f25338651d70f287232ff5c17457588`
- Initial placement: four faithful document artifacts on A4, A5, A28 and A5.
- Graph: version 45, 15 nodes, 12 edges.

The Manager retrieved from all four documents. Two synthesis requests failed typed
context preflight at 258,160 and 53,603 estimated input tokens. It recovered each
time by issuing smaller per-document retrievals. The third synthesis request used
four approximately 6.3--6.6 KB artifacts and was statically feasible. It was placed
on A28 and entered the actual backend, but the request did not return before the
fixed 900-second client deadline and ended as `physical_execution_failed: ReadTimeout`.
The trace records zero *completed* inference outcomes because no model response was
received. The evaluator was not invoked.

Primary failure: **runtime/model-service timeout**. Secondary behavior was
trial-and-error workflow composition around context sizing. This was not a budget
failure and was not retried or migrated to the other deployment.

## Video validation

- Run: `09-video-long-payload-blind-harness-v1.2`
- Execution revision: `36d570970f13a6012c6abed10408cc54de0fa328`
- Task/config hashes: task
  `d32c2823f8c86bf6afcce4ae4b3a7b80c76d5c2d589fcffadf03645f74f82c13`,
  config `3c12bd0ccca41bf1be8482273313cada759e55c129f46800f6b83258ca803b56`
- Initial placement: the complete 282,442,048-byte AV1 video on A4.
- Graph: version 6, 2 nodes, 5 information-flow edges.

A4 sampled 32 frames from the full 2,495.121-second timeline in 27,025.565 ms. The
Manager selected five frames; 443,505 bytes moved to A28. The A28 visual model
completed in 199,220.639 ms and explicitly concluded that the first magic used a
`String`, i.e. choice `A`. Verifier call 2 returned `complete`.

The candidate was nevertheless a prose explanation that mentioned every option
name and did not begin with an explicit choice label. The frozen deterministic
extractor intentionally accepts only an exact or unambiguous leading label, so it
failed closed with `terminal answer violates the choice output contract`. There was
no terminal answer and no evaluator call.

Primary failure: **synthesis/output formatting**; related stopping behavior allowed
the Verifier to declare the prose candidate complete before a contract-valid choice
was available. Semantic evidence selection and model reasoning were successful.
Per the freeze rule, this observation did not trigger a logic or prompt change.

## Gate and next experiment

The three-family criterion requires normal completion through terminal synthesis and
private evaluation for all three representative tasks. Only MultiHop met it.
Consequently:

- `blind-harness-v1.2` remains a frozen, reconstructable candidate harness, not the
  accepted formal cross-benchmark Blind baseline;
- the MultiHop result is a positive reusable Blind execution sample;
- no Fast/Slow Blind/Aware cell was run;
- no Aware evidence should be inferred from this stage.

Proceeding would require explicit review of the LongBench service-timeout policy and
the Video terminal-format/stopping behavior. This run deliberately makes no such
change.

## Evidence and verification

Durable private evidence and fresh stores remain on the experiment machines.
Sanitized freeze/result/trace/summary copies are retained locally under the ignored
directories:

- `results/blind-3family-validation-v1.2-multihop-gate`
- `results/blind-3family-validation-v1.2-longbench`
- `results/blind-3family-validation-v1.2-video`

No private task/evaluator file or dataset was copied locally. The exact trace
SHA-256 values are:

- MultiHop: `a2049e24de155828ace69476d6bc8dc666603cf8ea18032f9010150b0b526051`
- LongBench: `1417340cff9647a0895b40e8c6b9cdcd661a9c90d365163cb4f3954380b49a8d`
- Video: `a48ec9bce57811efb57c23e4ee605d8ff0732ec33a4fe9370a7c771ec8a156b0`

After adding only the v1.2 manifests/configs and freeze-contract tests: full pytest
passed all 311 collected tests, Ruff passed, and strict Pyright reported zero errors.
All experiment Worker processes were stopped after evidence capture; artifact stores
and historical evidence were retained.
