# Frozen held-out workflow study: heldout-binding-v1

The mechanisms were selected from development evidence, then frozen before any held-out model execution. Final generation uses seeds 43017/43033/43059 and relative/parity templates. Earlier 310xx cases were renderer/tokenizer structural fixtures only and are excluded from model evaluation. Static rule contents remain byte-for-byte the original `STATIC` bank; runtime support is explicitly a deterministic harness intervention, not a claim about static prompt granularity alone.

## Tasks and unit of analysis

Twelve independently generated graphs: two new policy templates × dependency depth 1/3 × three seeds, width three. Each has three paired variants: no update, a genuine source-value change with unchanged correct operation vector, and a genuine value change with a changed operation vector. Updated variants must change the correct root numeric result. The generator selects graphs admitting both update regimes before inference; this is a controlled stress distribution, not natural workload prevalence.

There are **36 task variants**, with **12 graph clusters**, not 36 independent natural tasks. Stable/flip variants have identical public task text and initial data. Task IDs, update regime, changed source, replacement value, seeds and reference operation vectors are hidden from the model until actual tool observations expose the relevant facts. The DAG is supplied in dependency order: the primary claim concerns binding, policy selection and recovery, not discovering an unknown task decomposition.

## Conditions

| Condition | Persistent rules | Dynamic content |
| --- | --- | --- |
| none | none beyond common API/task contract | none |
| static_system | complete generic bank in system instructions | none |
| static | none | identical complete bank as latest user message |
| local | none | last-observation-selected rule from the same bank |
| ledger_system | complete bank in system instructions | observation-only artifact/validity/receipt ledger |
| binding_system | complete bank in system instructions | every public node policy joined to observed ordered parent handles/values and current output |
| unbound_system | complete bank in system instructions | identical policies/current-output facts and repeated parent artifact facts, in separate tables |

Binding/unbound contain the same fact inventory and repetition counts, and their dynamic blocks are padded to exactly the same tokenizer length at the same state. This is per-state matching, not forcing divergent trajectories to have equal histories. Unbound tables retain explicit ordered parent names; they do not remove required knowledge. Padding may itself affect attention and remains a limitation. Both conditions represent every node, including missing inputs, without selecting a next action, operation or eligible-node subset. They prefer the latest observed valid artifact for each node, identically in both conditions; semantic correctness is never inferred by the adapter.

All three ledger/binding/unbound conditions use the same observed receipt/phase block after successful verification. No tool/action is automatically selected, completed, repaired, masked or executed by support. Source values come only from actual fetch results. There is no extra LLM, trained component, retrieval corpus or constrained decoding.

## Inference and safety

Two frozen official Qwen3.5 BF16 checkpoints; direct Transformers 5.19.0/PyTorch 2.8.0+cu128, SDPA, thinking disabled, greedy decoding, repetition penalty 1, 256 output tokens, exact 16,384-token context preflight. Both checkpoint endoftext and tokenizer chat EOS are stopping IDs. Backend, precision, generation, tools, evaluator and deployment are identical across conditions within a model.

Each GPU hosts one model, with **two** active workflows batched together. Longer held-out trajectories and dynamic blocks motivated a conservative batch size after measured development peak allocations of 14.83/22.31 GiB for 4B/9B at batch four. This setting is frozen for every held-out condition; it is not a backend search. Each cell has 64 turns, 300-second cooperative request deadline and a 3,600-second task deadline checked before action execution. The independent whole-instance 10-hour soft/20-hour hard resource guard includes setup time. A fixed seeded task order and rotated condition order are frozen in the config.

**504 full workflow episodes** (36 × 7 × 2) execute continuously. Schema/JSON errors, wrong answers, legal time/token exhaustion and recovery failures remain outcomes. Only system integrity failures justify interruption; no outcome-selected reruns or mid-study prompt/support changes are allowed. Historical experiments remain untouched.

## Evaluation and planned contrasts

Strict raw JSON Schema validation precedes real deterministic tools. Completion means a valid root/receipt submission; success additionally requires exact numeric correctness. The verifier checks provenance/freshness only and gives no semantic-answer feedback. Refactoring the private reference helper for task construction reproduced all 64 earlier diagnostic episodes exactly; scoring semantics were not relaxed.

Primary contrasts: binding versus matched unbound; binding versus system-static; identical static bank across role placement; ledger versus system-static; local versus system-static. Report completion, success, schema validity, dependency/phase/terminal failures, conditional operation accuracy, old-operation persistence after changed observed inputs, verification attempts, turns/tokens and failure-inclusive resource proxies. Stratify by update regime, model, depth and template. Compute paired differences and uncertainty over graph clusters; do not treat paired update variants or repeated model conditions as independent trials.

Measured batch service wall time is counted once. Per-request latency overlaps within a batch and is not GPU kernel time. Monetary GPU USD remains unknown; known whole-instance rental estimates are in CNY at ¥6.06/hour. No exchange rate or unsupported per-GPU allocation is invented. Tokens/calls are useful work proxies, not a complete monetary cost model. No inference about real InfraMAS benchmark success or universal scaling follows from this synthetic study alone.
