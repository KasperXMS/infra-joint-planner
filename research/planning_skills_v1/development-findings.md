# Development findings and why the held-out comparison changed

These are diagnosis and mechanism-selection results, not independent validation. All workflows use real local BF16 inference and actual deterministic tools. The eight development tasks are reused across the corrected diagnostic and placement studies; they must not be counted as sixteen independent tasks. Original traces and failed engineering work are retained.

## Execution inventory

| Stage | Recorded evidence | Interpretation |
| --- | --- | --- |
| diagnostic-v1 | 404 recorded requests, 101 generation batches, eight finished workflows plus interrupted traces | Entire run excluded from ability evidence because a chat-EOS framing mistake caused spurious JSON failures; all recorded work still costs resources |
| diagnostic-v2 | 64/64 finished workflows, 1,077 logical requests, 284 batches | Full corrected repeat, not selective rerunning |
| role-placement-v1 | 48/48 finished workflows, 776 logical requests, 212 batches | Same eight tasks and identical static bank, delivered in different message positions |
| decision-context-probe-v1 | 288/288 one-step queries, zero tool executions | Target node and ordered handles supplied; measures conditional operation choice, not workflow TSR |

The diagnostic's summed generation-batch wall is 620.920 seconds; the placement study's is 439.708 seconds. Each physical batch is counted once even when several workflows share it. These are model-service wall measurements, not kernel time, total batch E2E or a monetary allocation to conditions. Both stages batch up to four workflows per exclusive GPU. Later held-out studies use two and cannot establish a controlled cross-stage speed comparison.

## Static prompting changes completion more readily than correctness

The corrected diagnostic's 4B baseline completes 8/8 and succeeds 2/8; static/latest-user completes 4/8 and succeeds 1/8; local rules complete 8/8 and succeed 2/8; ledger plus static completes 5/8 and succeeds 1/8. All four 9B conditions complete 8/8 and succeed 2/8. There are no raw JSON/schema failures after the EOS correction. The 4B static and ledger arms instead incur dependency loops; ledger also incurs non-root verification attempts.

The placement ablation gives an actionable confound:

| Model | Condition | Completion | Numeric success | Turns | Prompt tokens | Output tokens | Median workflow E2E, s |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 4B | None | 8/8 | 2/8 | 108 | 159,014 | 2,488 | 21.89 |
| 4B | Static / latest user | 4/8 | 1/8 | 240 | 690,264 | 8,373 | 69.33 |
| 4B | Same static / system | 8/8 | 2/8 | 106 | 185,884 | 2,561 | 22.66 |
| 9B | None | 8/8 | 2/8 | 107 | 156,466 | 2,470 | 27.02 |
| 9B | Static / latest user | 8/8 | 2/8 | 108 | 207,808 | 4,868 | 28.00 |
| 9B | Same static / system | 8/8 | 2/8 | 107 | 187,084 | 2,470 | 27.47 |

The same bank's placement recovers 4B workflow completion and removes much of its excess work. It does not improve success beyond the no-skill baseline. Role, position and salience change together, so this is a delivery contrast rather than isolation of system-role authority alone. The eight tasks/two seeds do not support a capacity law or general harm prevalence. E2E also depends on the fixed mixed-condition batch schedule.

## Fresh evidence does not guarantee a fresh operation decision

On the development seed-11, depth-1 update task, the 9B baseline refetches an input changing from 16 to 38. Its recorded policy calls for `max` on the new observed values, but the model reuses `difference` and submits 68 instead of 76. The handles and final provenance are fresh. The verifier intentionally checks provenance/freshness rather than branch correctness, so successful verification is compatible with a wrong answer. This motivates separating state rebuilding from semantic re-decision, without asserting an internal cognitive mechanism from one trace.

The decision probe freezes all 48 valid non-root computations from the eight 9B baseline trajectories, including erroneous ones. Cards contain actual observed intermediate values and public policies, never the correct operator or reference answer.

| Model | Full history + supplied target: operator / joint | Full history + input-policy card: operator / joint | Isolated card: operator / joint |
| --- | --- | --- | --- |
| 4B | 28/48 / 28/48 | 45/48 / 45/48 | 39/48 / 39/48 |
| 9B | 26/48 / 26/48 | 44/48 / 42/48 | 39/48 / 39/48 |

The joint score requires the correct target and handles as well as operation. The 9B full-card arm has two target errors. Post-update operator correctness is 8/16, 16/16 and 13/16 for 4B, and 6/16, 12/16 and 13/16 for 9B. All 288 outputs pass schema validation. These correlated decisions are development observations, not 48 independent planning tasks or an estimate of autonomous TSR.

Across 48 queries per model, full-target prompts use 75,228 tokens, full-card prompts 79,713, and isolated-card prompts 31,099. Full-card's gain therefore is not explained simply by deleting history. Repetition, salience and easier value-policy association remain alternatives. The held-out design consequently compares joined and unjoined current facts with identical fact multiplicities and tokenizer-matched support, while leaving every action to the planner.

## Evidence and limits

The [diagnostic tables](results/diagnostic-v2/summary.json), [placement tables](results/role-placement-v1/summary.json) and [probe tables](results/decision-context-probe-v1/summary.json) retain all groups. Deterministic trace replay validates development workflow observations and evaluator outputs. An additional exact prompt/token/output replay validates all 776 placement calls without model inference. The final raw evidence index will identify private source traces and the excluded engineering namespace.

These experiments use a supplied dependency graph and deterministic provenance verifier. They do not measure open-ended decomposition, LLM Specialist/Verifier quality or transfer to the historical InfraMAS benchmark. Local GPU USD is unknown; cloud API calls are absent. Whole-instance rental, including setup and engineering errors, is accounted separately at the user-provided CNY rate.
