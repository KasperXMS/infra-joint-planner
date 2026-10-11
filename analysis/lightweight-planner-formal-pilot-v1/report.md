# Lightweight Planner Competence Pilot — formal results

Completed matrix: 18/18 cells. Base `41d034d`; no selective model reruns or additional capability gates. Prior No-Go reports remain historical evidence.
Matrix wall: 2915.404 s, including setup, cleanup and documented repair pauses. Per-task E2E below excludes those intervals.

| Group | Completion | TSR | Raw schema failures | Cloud API USD (known) | Full cost |
|---|---:|---:|---:|---:|---|
| B0 | 6/6 | 4/6 | 0 | 0.6770080455493695106233141550 | unknown |
| B1 | 1/6 | 1/6 | 40 | 0.5853746741253537782856535431 | unknown |
| B2 | 0/6 | 0/6 | 20 | 0.1475151051701457632974129340 | unknown |

B0 = strong Manager without Skills; B1 = local 8B without Skills; B2 = same local 8B with frozen Skills. Specialist and Verifier remain strong. All groups use identical raw-call validation.

## Cells and workflow

| Cell | Task | Group | Completion | Score | Outcome | M/S/V turns | Schema failures | Physical successes/admissions | E2E s |
|---|---|---|---|---|---|---|---:|---|---:|
| LPC-01 | multihop_rag/1 | B0 | True | 0.0 | incorrect_answer | 4/0/4 | 0 | 1/1 | 160.061 |
| LPC-02 | multihop_rag/1 | B1 | False | unknown | turn_budget_exhausted | 20/8/20 | 19 | 0/0 | 137.333 |
| LPC-03 | multihop_rag/1 | B2 | False | unknown | provider_json_parse_error | 1/0/0 | 0 | 0/0 | 4.614 |
| LPC-04 | multihop_rag/2 | B1 | False | unknown | turn_budget_exhausted | 20/8/20 | 19 | 0/0 | 109.242 |
| LPC-05 | multihop_rag/2 | B2 | False | unknown | turn_budget_exhausted | 20/8/20 | 19 | 0/0 | 99.716 |
| LPC-06 | multihop_rag/2 | B0 | True | 1.0 | success | 3/0/3 | 0 | 1/1 | 160.639 |
| LPC-07 | longbench_v2/1 | B2 | False | unknown | provider_json_parse_error | 1/0/0 | 0 | 0/0 | 2.842 |
| LPC-08 | longbench_v2/1 | B0 | True | 1.0 | success | 8/0/8 | 0 | 1/1 | 69.854 |
| LPC-09 | longbench_v2/1 | B1 | False | unknown | provider_json_parse_error | 1/0/0 | 0 | 0/0 | 3.205 |
| LPC-10 | longbench_v2/2 | B0 | True | 0.0 | incorrect_answer | 5/2/5 | 0 | 1/1 | 88.823 |
| LPC-11 | longbench_v2/2 | B2 | False | unknown | provider_json_parse_error | 1/0/0 | 0 | 0/0 | 3.182 |
| LPC-12 | longbench_v2/2 | B1 | False | unknown | provider_json_parse_error | 1/0/0 | 0 | 0/0 | 2.473 |
| LPC-13 | video_mme/1 | B2 | False | unknown | provider_json_parse_error | 1/0/0 | 0 | 0/0 | 21.56 |
| LPC-14 | video_mme/1 | B1 | False | unknown | terminal_contract_failed | 13/3/12 | 1 | 1/1 | 165.429 |
| LPC-15 | video_mme/1 | B0 | True | 1.0 | success | 5/0/5 | 0 | 1/1 | 146.917 |
| LPC-16 | video_mme/2 | B1 | True | 1.0 | success | 5/0/5 | 1 | 1/1 | 47.136 |
| LPC-17 | video_mme/2 | B0 | True | 1.0 | success | 4/0/4 | 0 | 1/1 | 74.306 |
| LPC-18 | video_mme/2 | B2 | False | unknown | provider_json_parse_error | 3/0/2 | 1 | 0/0 | 28.762 |

## Control and physical resources

| Group/role | Turns | Input tokens | Output tokens | Cached input | API USD known subtotal |
|---|---:|---:|---:|---:|---:|
| B0/manager | 29 | 311120 | 11828 | 250752 | 0.2276578376008185067566669768 |
| B0/specialist | 2 | 29351 | 1005 | 9984 | 0.04229342669979670205556810481 |
| B0/verifier | 29 | 269006 | 4397 | 62592 | 0.4070567812487543018110790736 |
| B1/manager | 60 | ≥709565; 2 requests unknown | ≥12335; 2 requests unknown | ≥664331; 2 requests unknown | 0 |
| B1/specialist | 19 | 159970 | 3813 | 130432 | 0.1025226311803239479663561833 |
| B1/verifier | 57 | 620414 | 9569 | 433536 | 0.4828520429450298303192973598 |
| B2/manager | 27 | ≥226813; 5 requests unknown | ≥1991; 5 requests unknown | ≥215788; 5 requests unknown | 0 |
| B2/specialist | 8 | 60867 | 910 | 53376 | 0.03023541503341793008145205225 |
| B2/verifier | 22 | 147298 | 4140 | 107648 | 0.1172796901367278332159608818 |

Missing usage remains unknown (JSON null); zero recorded requests yields zero measured usage. Cloud API estimates use the frozen provider price card and FX reference, not billing statements. Local Planner GPU/energy/monetary cost and physical GPU cost remain unknown. Known cloud subtotals cannot establish a total-cost advantage.

| Group | Physical successes/admissions | Physical service s (known) | Runner starts | Runner reported service s | E2E s | Initial/action bytes |
|---|---|---:|---:|---:|---:|---|
| B0 | 6/6 | 369.996 | 6 | 364.487 | 700.599 | 238804668/10626750 |
| B1 | 2/2 | 13.939 | 62 | 132.249 | 464.818 | 238804668/10409192 |
| B2 | 0/0 | 0.000 | 27 | 38.797 | 160.676 | 238804668/5204596 |

Successful physical calls have backend telemetry. Admissions may fail before inference and are not all actual model calls. Failed/cancelled calls can have unmeasured work. Runner log starts include both the local Planner and Executor; runner timing sums are partial service proxies, never GPU busy time. Service sums can overlap and must not be added to E2E. Transfer counts are application artifact bytes, not wire traffic. Per-cell worker setup, tc, SSH and cleanup sit outside task E2E.

## Paired behavior and Skills effect

| Task | B0 workflow | B1 workflow | B2 workflow |
|---|---|---|---|
| 1 | aggregate_artifacts → bm25_retrieve → bm25_retrieve → invoke_model; specialists=0; edges=4; incorrect_answer | aggregate_artifacts → bm25_retrieve → bm25_retrieve → select_fields → select_fields → read_artifact → read_artifact; specialists=1; edges=6; turn_budget_exhausted | no executed graph nodes; specialists=0; edges=0; provider_json_parse_error |
| 2 | aggregate_artifacts → bm25_retrieve → invoke_model; specialists=0; edges=2; success | aggregate_artifacts → bm25_retrieve → read_artifact → read_artifact → bm25_retrieve → bm25_retrieve; specialists=1; edges=4; turn_budget_exhausted | aggregate_artifacts → bm25_retrieve → read_artifact → select_fields → filter_records → bm25_retrieve → invoke_model → top_k_records; specialists=1; edges=7; turn_budget_exhausted |
| 3 | aggregate_artifacts → bm25_retrieve → invoke_model → bm25_retrieve → invoke_model → bm25_retrieve → invoke_model; specialists=0; edges=6; success | no executed graph nodes; specialists=0; edges=0; provider_json_parse_error | no executed graph nodes; specialists=0; edges=0; provider_json_parse_error |
| 4 | bm25_retrieve → invoke_model → read_artifact → bm25_retrieve → invoke_model; specialists=1; edges=3; incorrect_answer | no executed graph nodes; specialists=0; edges=0; provider_json_parse_error | no executed graph nodes; specialists=0; edges=0; provider_json_parse_error |
| 5 | sample_frames → invoke_model → invoke_model; specialists=0; edges=37; success | sample_frames → invoke_model → sample_frames → make_contact_sheet → invoke_model; specialists=1; edges=25; terminal_contract_failed | no executed graph nodes; specialists=0; edges=0; provider_json_parse_error |
| 6 | sample_frames → invoke_model; specialists=0; edges=6; success | sample_frames → invoke_model; specialists=0; edges=1; success | sample_frames; specialists=0; edges=0; provider_json_parse_error |

B1→B2 paired Skills difference: completion -1/6; TSR -1/6; schema failures -20. B0→B2 quality difference: TSR -4/6. The machine-readable artifact provides the full turns, tokens, calls, service work, E2E and transfer vector for both comparisons. GPU prices remain unknown, so no complete monetary cost ratio is identified.

These are six previously examined tasks with one execution per group, a descriptive feasibility pilot. No significance, non-inferiority, held-out generalization or causal adapter-effect claim is supported. Execution order is frozen and balanced across tasks; cache and sequential residency effects remain possible.

## Infra-aware Workflow Adapter decision

NO-GO for adding the Infra-aware Workflow Adapter now. B2 completed 0/6 and succeeded on 0/6, compared with B0 completion 6/6 and success 4/6, and B1 completion/success 1/6. Most lightweight runs fail on raw-call schema or provider JSON parsing before useful terminal workflows. These observations give no evidence that infrastructure adaptation addresses the dominant failures. First investigate protocol and planning reliability in the current stack. This is a descriptive judgment on six examined tasks, not a new admission gate or significance claim. No further experiment starts automatically.

## Evidence and execution safety

The adjacent `pilot-results.json` contains each sanitized cell, numeric resources, workflow structure, schema recovery counters and SHA-256 links to remote raw evidence. Raw API payloads, traces, artifact bodies, evaluator details and logs stay on experiment machines. `execution-freeze.json` preserves deployed source hashes; append-only journal preserves order. Zero-model initialization corrections are separate from the competence matrix. The final integrity receipt records source/history/Skills consistency, tc restoration, Worker termination and context checks. Benchmark, evaluator, frozen Skills, semantic instructions, Physical Scheduler and Executor were not modified.
