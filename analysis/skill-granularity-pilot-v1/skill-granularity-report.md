# Skill Granularity Pilot v1 — final results

All 30 frozen cells are included: three tasks per condition; 4B and 9B have S0/S1/S2/S3 and 27B has its two preregistered conditions. S0=no Skills; S1=unchanged abstract guidance; S2=procedure with real schemas; S3=conditional atomic SOP. These are different content/length treatments, not an isolated causal test of presentation granularity.

The frozen `qwen35-27b` slot uses the existing Qwen3.8-27B deployment; it is not a Qwen3.5-27B checkpoint. The 4B/9B Managers use the independent A28 service; 27B shares the existing resident endpoint. Specialist, Verifier, Executor and Physical Scheduler are fixed. Cross-scale latency comparisons therefore also reflect deployment differences.

## Completion, quality and protocol reliability

| Frozen candidate | Actual model | Model blob | Quantization | Context/output | Temperature/top-p | Thinking/effort | Backend | Manager placement |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| qwen35-4b | Qwen3.5-4B | sha256-a9d0a3e1d8c91732a3812becd31f8d4a8ff57414903f226306069f0437e2ac50 | Q4_K_M | 32768/2048 | 1/0.95 | False/none | Ollama 0.34.0 | A28 |
| qwen35-9b | Qwen3.5-9B | sha256-02d45dc1cf451ba2475ac33b301c2dd8f985abe4c182ce04a1f2f5bf0260278d | Q4_K_M | 32768/2048 | 1/0.95 | False/none | Ollama 0.34.0 | A28 |
| qwen35-27b | Qwen3.8-27B | sha256-f5f1dd8920d417aac2718b0bda3403da274301efdd6760b4f0f4b864ff2ad57d | Q4_K_M | 32768/2048 | 1/0.95 | False/none | Ollama 0.34.0 | strong-4090-gpu0 |

A recorded protocol amendment authorized up to three concurrent task pipelines on shared resources, with unchanged per-service request parallelism and model/Skill/runtime contracts. Existing serial cells were retained without rerun. TSR is the primary outcome; E2E and log service work are diagnostic under this policy. A dispatch ceiling of three does not imply three simultaneous model inferences.

| Cell | Cohort | Dispatch ceiling | Wave | Actual wave size | Serving request parallelism | Log intervals may overlap |
| --- | --- | --- | --- | --- | --- | --- |
| qwen35-4b-t1-S0 | serial_before_amendment | 1 | unknown | unknown | unknown | False |
| qwen35-4b-t1-S1 | serial_before_amendment | 1 | unknown | unknown | unknown | False |
| qwen35-4b-t1-S2 | shared_resource_wave | 3 | wave-001 | 3 | 1 | True |
| qwen35-4b-t1-S3 | shared_resource_wave | 3 | wave-001 | 3 | 1 | True |
| qwen35-4b-t2-S1 | shared_resource_wave | 3 | wave-001 | 3 | 1 | True |
| qwen35-4b-t2-S2 | shared_resource_wave | 3 | wave-002 | 3 | 1 | True |
| qwen35-4b-t2-S3 | shared_resource_wave | 3 | wave-002 | 3 | 1 | True |
| qwen35-4b-t2-S0 | shared_resource_wave | 3 | wave-002 | 3 | 1 | True |
| qwen35-4b-t3-S2 | shared_resource_wave | 3 | wave-003 | 3 | 1 | True |
| qwen35-4b-t3-S3 | shared_resource_wave | 3 | wave-003 | 3 | 1 | True |
| qwen35-4b-t3-S0 | shared_resource_wave | 3 | wave-003 | 3 | 1 | True |
| qwen35-4b-t3-S1 | shared_resource_wave | 3 | wave-004 | 1 | 1 | True |
| qwen35-9b-t1-S0 | shared_resource_wave | 3 | wave-005 | 3 | 1 | True |
| qwen35-9b-t1-S1 | shared_resource_wave | 3 | wave-005 | 3 | 1 | True |
| qwen35-9b-t1-S2 | shared_resource_wave | 3 | wave-005 | 3 | 1 | True |
| qwen35-9b-t1-S3 | shared_resource_wave | 3 | wave-006 | 3 | 1 | True |
| qwen35-9b-t2-S1 | shared_resource_wave | 3 | wave-006 | 3 | 1 | True |
| qwen35-9b-t2-S2 | shared_resource_wave | 3 | wave-006 | 3 | 1 | True |
| qwen35-9b-t2-S3 | shared_resource_wave | 3 | wave-007 | 3 | 1 | True |
| qwen35-9b-t2-S0 | shared_resource_wave | 3 | wave-007 | 3 | 1 | True |
| qwen35-9b-t3-S2 | shared_resource_wave | 3 | wave-007 | 3 | 1 | True |
| qwen35-9b-t3-S3 | shared_resource_wave | 3 | wave-008 | 3 | 1 | True |
| qwen35-9b-t3-S0 | shared_resource_wave | 3 | wave-008 | 3 | 1 | True |
| qwen35-9b-t3-S1 | shared_resource_wave | 3 | wave-008 | 3 | 1 | True |
| qwen35-27b-t1-S0 | shared_resource_wave | 3 | wave-009 | 3 | 1 | True |
| qwen35-27b-t1-S3 | shared_resource_wave | 3 | wave-009 | 3 | 1 | True |
| qwen35-27b-t2-S3 | shared_resource_wave | 3 | wave-009 | 3 | 1 | True |
| qwen35-27b-t2-S0 | shared_resource_wave | 3 | wave-010 | 3 | 1 | True |
| qwen35-27b-t3-S0 | shared_resource_wave | 3 | wave-010 | 3 | 1 | True |
| qwen35-27b-t3-S3 | shared_resource_wave | 3 | wave-010 | 3 | 1 | True |

Cells in the same wave can capture overlapping intervals from the same resident or independent Planner service log. Summed log times are therefore an overlapping reported proxy: they can double-count shared work and must not be interpreted as exclusive per-cell service work, GPU cost, or a causal cost effect of Skills. API usage and trace-recorded physical calls remain attributed to their own cells. The serial/shared cohort difference is preserved, including possible queue and timeout effects; latency deltas do not determine the TSR assessment.

| Condition | Completion | TSR | Raw valid/calls | Schema failures | Provider errors | Outcomes |
| --- | --- | --- | --- | --- | --- | --- |
| qwen35-27b__S0 | 3/3 | 1/3 | 33/34 | 1 | {} | {"incorrect_answer": 2, "success": 1} |
| qwen35-27b__S3 | 3/3 | 1/3 | 22/23 | 1 | {} | {"incorrect_answer": 2, "success": 1} |
| qwen35-4b__S0 | 0/3 | 0/3 | 20/28 | 8 | {"provider_timeout_error": 2} | {"provider_timeout_error": 2, "turn_budget_exhausted": 1} |
| qwen35-4b__S1 | 2/3 | 1/3 | 36/46 | 10 | {} | {"incorrect_answer": 1, "success": 1, "turn_budget_exhausted": 1} |
| qwen35-4b__S2 | 0/3 | 0/3 | 28/34 | 6 | {"provider_timeout_error": 1} | {"provider_timeout_error": 1, "terminal_contract_failed": 1, "turn_budget_exhausted": 1} |
| qwen35-4b__S3 | 1/3 | 1/3 | 30/34 | 4 | {"provider_timeout_error": 1} | {"provider_timeout_error": 1, "success": 1, "turn_budget_exhausted": 1} |
| qwen35-9b__S0 | 0/3 | 0/3 | 2/2 | 0 | {"provider_timeout_error": 3} | {"provider_timeout_error": 3} |
| qwen35-9b__S1 | 1/3 | 0/3 | 29/39 | 10 | {"provider_timeout_error": 1} | {"incorrect_answer": 1, "provider_timeout_error": 1, "turn_budget_exhausted": 1} |
| qwen35-9b__S2 | 1/3 | 0/3 | 20/29 | 9 | {"provider_timeout_error": 1} | {"context_budget_exceeded": 1, "incorrect_answer": 1, "provider_timeout_error": 1} |
| qwen35-9b__S3 | 1/3 | 0/3 | 7/16 | 9 | {"provider_timeout_error": 2} | {"incorrect_answer": 1, "provider_timeout_error": 2} |

Schema validity divides valid original parsed operator/delegation Function Calls by all such calls reaching the strict application validator, across Manager and Specialists. It excludes Verifier structured-output validation and provider responses that never yielded a parsed Function Call. One call with several schema defects counts once. HTTP 500 XML/JSON parser failures remain a separate protocol layer; they cannot establish pure task-reasoning failure.

## Recovery and workflow structure

| Condition | Manager valid/calls | Specialist valid/calls | Later-valid/invalid calls | Verifier invalid | Nodes/edges | Repeated calls | Specialists |
| --- | --- | --- | --- | --- | --- | --- | --- |
| qwen35-27b__S0 | 25/26 | 8/8 | 1/1 | 0 | 23/39 | 0 | 1 |
| qwen35-27b__S3 | 22/23 | 0/0 | 1/1 | 0 | 21/35 | 0 | 0 |
| qwen35-4b__S0 | 20/28 | 0/0 | 6/8 | 0 | 19/9 | 0 | 0 |
| qwen35-4b__S1 | 36/46 | 0/0 | 9/10 | 0 | 30/55 | 0 | 0 |
| qwen35-4b__S2 | 28/34 | 0/0 | 6/6 | 0 | 20/33 | 0 | 0 |
| qwen35-4b__S3 | 30/34 | 0/0 | 3/4 | 0 | 18/18 | 2 | 0 |
| qwen35-9b__S0 | 2/2 | 0/0 | 0/0 | 0 | 2/0 | 0 | 0 |
| qwen35-9b__S1 | 29/39 | 0/0 | 4/10 | 0 | 24/17 | 0 | 0 |
| qwen35-9b__S2 | 20/29 | 0/0 | 8/9 | 0 | 19/16 | 0 | 0 |
| qwen35-9b__S3 | 7/16 | 0/0 | 4/9 | 0 | 6/0 | 0 | 0 |

Recovery here means an invalid call is followed by a valid call to the same tool by the same owner. Several invalid calls can precede one valid call; this is a descriptive recovery signal, not proof of matching semantic intent or successful task completion. Repeated calls share identical selected arguments; this count does not by itself prove redundancy.

## Role turns, usage and API cost

| Condition/role | Requests/turns | Input tokens | Output tokens | Cached tokens | Unknown usage requests | Known input/output subtotal | API USD known | API USD complete |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| qwen35-27b__S0/manager | 20/20 | 179933 | 5732 | 147782 | 0 | 179933/5732 | 0 | 0 |
| qwen35-27b__S0/specialist | 8/8 | 66519 | 1424 | 53248 | 0 | 66519/1424 | 0.04331183380060856508856083658 | 0.04331183380060856508856083658 |
| qwen35-27b__S0/verifier | 20/20 | 149151 | 2803 | 46720 | 0 | 149151/2803 | 0.2088360993369563773103549077 | 0.2088360993369563773103549077 |
| qwen35-27b__S3/manager | 13/13 | 148561 | 4702 | 80892 | 0 | 148561/4702 | 0 | 0 |
| qwen35-27b__S3/specialist | 0/0 | 0 | 0 | 0 | 0 | 0/0 | 0 | 0 |
| qwen35-27b__S3/verifier | 13/13 | 96875 | 1837 | 16896 | 0 | 96875/1837 | 0.1567917378652387089916156207 | 0.1567917378652387089916156207 |
| qwen35-4b__S0/manager | 30/30 | unknown | unknown | unknown | 2 | 304225/6181 | 0 | 0 |
| qwen35-4b__S0/specialist | 0/0 | 0 | 0 | 0 | 0 | 0/0 | 0 | 0 |
| qwen35-4b__S0/verifier | 28/28 | 169535 | 5717 | 57856 | 0 | 169535/5717 | 0.2435263742542420175660053948 | 0.2435263742542420175660053948 |
| qwen35-4b__S1/manager | 46/46 | 567310 | 12739 | 509598 | 0 | 567310/12739 | 0 | 0 |
| qwen35-4b__S1/specialist | 0/0 | 0 | 0 | 0 | 0 | 0/0 | 0 | 0 |
| qwen35-4b__S1/verifier | 46/46 | 350689 | 8243 | 104192 | 0 | 350689/8243 | 0.5087560956164711197331880573 | 0.5087560956164711197331880573 |
| qwen35-4b__S2/manager | 35/35 | unknown | unknown | unknown | 1 | 455823/7767 | 0 | 0 |
| qwen35-4b__S2/specialist | 0/0 | 0 | 0 | 0 | 0 | 0/0 | 0 | 0 |
| qwen35-4b__S2/verifier | 33/33 | 192392 | 5680 | 65536 | 0 | 192392/5680 | 0.2722100160778112916727567467 | 0.2722100160778112916727567467 |
| qwen35-4b__S3/manager | 35/35 | unknown | unknown | unknown | 1 | 455174/7647 | 0 | 0 |
| qwen35-4b__S3/specialist | 0/0 | 0 | 0 | 0 | 0 | 0/0 | 0 | 0 |
| qwen35-4b__S3/verifier | 34/34 | 170010 | 5844 | 80384 | 0 | 170010/5844 | 0.2097775442139810521000810534 | 0.2097775442139810521000810534 |
| qwen35-9b__S0/manager | 5/5 | unknown | unknown | unknown | 3 | 11477/374 | 0 | 0 |
| qwen35-9b__S0/specialist | 0/0 | 0 | 0 | 0 | 0 | 0/0 | 0 | 0 |
| qwen35-9b__S0/verifier | 2/2 | 10502 | 338 | 1024 | 0 | 10502/338 | 0.01900787945627765449979404457 | 0.01900787945627765449979404457 |
| qwen35-9b__S1/manager | 34/34 | unknown | unknown | unknown | 1 | 399723/7454 | 0 | 0 |
| qwen35-9b__S1/specialist | 0/0 | 0 | 0 | 0 | 0 | 0/0 | 0 | 0 |
| qwen35-9b__S1/verifier | 33/33 | 213852 | 6284 | 68608 | 0 | 213852/6284 | 0.3090516536228225195657662207 | 0.3090516536228225195657662207 |
| qwen35-9b__S2/manager | 30/31 | unknown | unknown | unknown | 1 | 466373/5961 | 0 | 0 |
| qwen35-9b__S2/specialist | 0/0 | 0 | 0 | 0 | 0 | 0/0 | 0 | 0 |
| qwen35-9b__S2/verifier | 29/29 | 240572 | 5757 | 46464 | 0 | 240572/5757 | 0.3887254534341407672172099018 | 0.3887254534341407672172099018 |
| qwen35-9b__S3/manager | 13/13 | unknown | unknown | unknown | 2 | 130574/3605 | 0 | 0 |
| qwen35-9b__S3/specialist | 0/0 | 0 | 0 | 0 | 0 | 0/0 | 0 | 0 |
| qwen35-9b__S3/verifier | 11/11 | 47201 | 1677 | 23168 | 0 | 47201/1677 | 0.05720262028461712220465326407 | 0.05720262028461712220465326407 |

Missing usage remains unknown; known subtotals are lower bounds and do not replace complete totals. Zero requests legitimately yields zero usage. Cloud prices use the frozen accounting card and are estimates, not invoices. A local Manager's zero cloud charge excludes its unknown hardware/energy cost.

## Verifier amplification and cost per successful task

| Condition | V/M turns | V/M input tokens | V turns/success | V API USD/success complete | All cloud USD/success complete | E2E diagnostic s/success |
| --- | --- | --- | --- | --- | --- | --- |
| qwen35-27b__S0 | 1.000 | 0.829 | 20.000 | 0.2088360993369563773103549077 | 0.2521479331375649423989157443 | 514.932 |
| qwen35-27b__S3 | 1.000 | 0.652 | 13.000 | 0.1567917378652387089916156207 | 0.1567917378652387089916156207 | 304.546 |
| qwen35-4b__S0 | 0.933 | unknown | unknown | unknown | unknown | unknown |
| qwen35-4b__S1 | 1.000 | 0.618 | 46.000 | 0.5087560956164711197331880573 | 0.5087560956164711197331880573 | 3343.990 |
| qwen35-4b__S2 | 0.943 | unknown | unknown | unknown | unknown | unknown |
| qwen35-4b__S3 | 0.971 | unknown | 34.000 | 0.2097775442139810521000810534 | 0.2097775442139810521000810534 | 3018.066 |
| qwen35-9b__S0 | 0.400 | unknown | unknown | unknown | unknown | unknown |
| qwen35-9b__S1 | 0.971 | unknown | unknown | unknown | unknown | unknown |
| qwen35-9b__S2 | 0.935 | unknown | unknown | unknown | unknown | unknown |
| qwen35-9b__S3 | 0.846 | unknown | unknown | unknown | unknown | unknown |

Per-success numerators include all three attempts, including failures; the denominator is successful tasks. No successes gives unknown, not zero. V/M uses aggregate role totals, not the mean of cell ratios. More Verifier work can accompany repeated evidence batches and recovery; these traces do not isolate a causal Verifier effect.

## Physical work, service proxies and data transfer

| Condition | Physical successes/admissions | Known physical service s | Resident log interval proxy s | Independent Planner log interval proxy s | E2E diagnostic s | Initial/action artifact bytes | Cloud USD known/unknown calls | Full cost |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| qwen35-27b__S0 | 4/4 | 290.791 | 529.574 | not applicable (resident) | 514.932 | 29651569/11201 | 0.2521479331375649423989157443/0 | unknown |
| qwen35-27b__S3 | 3/3 | 135.434 | 318.235 | not applicable (resident) | 304.546 | 29651569/10466 | 0.1567917378652387089916156207/0 | unknown |
| qwen35-4b__S0 | 0/0 | 0.000 | 0.000 | 1350.517 | 1653.258 | 29651569/5204596 | 0.2435263742542420175660053948/0 | unknown |
| qwen35-4b__S1 | 3/3 | 604.107 | 601.551 | 2606.177 | 3343.990 | 29651569/3984 | 0.5087560956164711197331880573/0 | unknown |
| qwen35-4b__S2 | 2/2 | 31.399 | 61.653 | 2774.730 | 3050.814 | 29651569/0 | 0.2722100160778112916727567467/0 | unknown |
| qwen35-4b__S3 | 1/1 | 18.696 | 37.602 | 2730.136 | 3018.066 | 29651569/5204596 | 0.2097775442139810521000810534/0 | unknown |
| qwen35-9b__S0 | 0/0 | 0.000 | 0.000 | 472.634 | 758.540 | 29651569/0 | 0.01900787945627765449979404457/0 | unknown |
| qwen35-9b__S1 | 2/2 | 246.045 | 244.412 | 2498.850 | 2904.419 | 29651569/152931 | 0.3090516536228225195657662207/0 | unknown |
| qwen35-9b__S2 | 1/1 | 3.551 | 19.476 | 2333.071 | 2430.390 | 29651569/5204596 | 0.3887254534341407672172099018/0 | unknown |
| qwen35-9b__S3 | 1/1 | 0.801 | 0.202 | 983.456 | 1220.000 | 29651569/0 | 0.05720262028461712220465326407/0 | unknown |

Admissions are not all completed inference calls. Failed/cancelled work can lack telemetry. Resident runner logs include the 27B Manager when it shares that endpoint; independent Planner logs are separate for 4B/9B and are not applicable to 27B. Missing logs remain unknown. Runner timings are partial service-work proxies, not GPU busy time; caches/speculative decode units differ from billed token usage. Service sums can overlap and must not be added to E2E. Artifact bytes are application transfers, not wire traffic. Persisted API JSON sizes are storage proxies, not network counters. GPU prices and complete GPU/energy costs are unknown. Under shared-resource concurrency, log interval sums can overlap and duplicate work; they cannot identify exclusive costs. Per-call physical telemetry remains attributable, while its latency can include shared-resource waiting.

## Paired Skill comparisons

| Model | Comparison | Completion delta | TSR count delta | Schema-failure delta | Manager-turn delta | Verifier-turn delta | Physical-call delta | E2E diagnostic s delta | Known cloud USD delta |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| qwen35-4b | S0 → S1 | 2 | 1 | 2 | 16 | 18 | 3 | 1690.732 | 0.2652297213622291021671826625 |
| qwen35-4b | S0 → S2 | 0 | 0 | -2 | 5 | 5 | 2 | 1397.556 | 0.0286836418235692741067513519 |
| qwen35-4b | S0 → S3 | 1 | 1 | -4 | 5 | 6 | 1 | 1364.808 | -0.0337488300402609654659243414 |
| qwen35-4b | S1 → S2 | -2 | -1 | -4 | -11 | -13 | -1 | -293.176 | -0.2365460795386598280604313106 |
| qwen35-4b | S1 → S3 | -1 | 0 | -6 | -11 | -12 | -2 | -325.925 | -0.2989785514024900676331070039 |
| qwen35-4b | S2 → S3 | 1 | 1 | -2 | 0 | 1 | -1 | -32.748 | -0.0624324718638302395726756933 |
| qwen35-9b | S0 → S1 | 1 | 0 | 10 | 29 | 31 | 2 | 2145.879 | 0.2900437741665448650659721761 |
| qwen35-9b | S0 → S2 | 1 | 0 | 9 | 26 | 27 | 1 | 1671.850 | 0.3697175739778631127174158572 |
| qwen35-9b | S0 → S3 | 1 | 0 | 9 | 8 | 9 | 1 | 461.459 | 0.03819474082833946770485921950 |
| qwen35-9b | S1 → S2 | 0 | 0 | -1 | -3 | -4 | -1 | -474.029 | 0.0796737998113182476514436811 |
| qwen35-9b | S1 → S3 | 0 | 0 | -1 | -21 | -22 | -1 | -1684.420 | -0.2518490333382053973611129566 |
| qwen35-9b | S2 → S3 | 0 | 0 | 0 | -18 | -18 | 0 | -1210.391 | -0.3315228331495236450125566377 |
| qwen35-27b | S0 → S3 | 0 | 0 | 0 | -7 | -7 | -1 | -210.386 | -0.0953561952723262334073001236 |

Differences are comparison minus reference on identical task indices. Lower cost caused by an early failure is not evidence of efficiency. Inspect completion, TSR and failure layers together with each resource vector; the machine-readable artifact retains every paired task delta.

## Same-task S0 → S1 → S2 → S3 behavior

| Model/task | Condition | Outcome | Score | Workflow operators | Nodes/edges/depth | Handoffs | Repeated calls |
| --- | --- | --- | --- | --- | --- | --- | --- |
| qwen35-4b/t1 | S0 | turn_budget_exhausted | unknown | aggregate_artifacts → bm25_retrieve → bm25_retrieve → top_k_records → filter_records → filter_records → read_artifact → invoke_model → filter_records → invoke_model → select_fields → filter_records → bm25_retrieve | 13/5/2 | 0 | 0 |
| qwen35-4b/t1 | S1 | turn_budget_exhausted | unknown | bm25_retrieve → bm25_retrieve → bm25_retrieve → bm25_retrieve → invoke_model → bm25_retrieve → bm25_retrieve → bm25_retrieve → invoke_model → read_artifact → read_artifact → bm25_retrieve → read_artifact → bm25_retrieve | 14/8/2 | 0 | 0 |
| qwen35-4b/t1 | S2 | turn_budget_exhausted | unknown | bm25_retrieve → bm25_retrieve → read_artifact → bm25_retrieve → bm25_retrieve → bm25_retrieve → invoke_model → bm25_retrieve → bm25_retrieve → bm25_retrieve → bm25_retrieve | 11/3/2 | 0 | 0 |
| qwen35-4b/t1 | S3 | turn_budget_exhausted | unknown | aggregate_artifacts → bm25_retrieve → read_artifact → bm25_retrieve → bm25_retrieve → invoke_model → bm25_retrieve → bm25_retrieve | 8/3/2 | 0 | 2 |
| qwen35-4b/t2 | S0 | provider_timeout_error | unknown | aggregate_artifacts → invoke_model → bm25_retrieve → invoke_model → read_artifact | 5/4/3 | 0 | 0 |
| qwen35-4b/t2 | S1 | incorrect_answer | 0.000 | aggregate_artifacts → invoke_model → select_fields → bm25_retrieve → bm25_retrieve → invoke_model → bm25_retrieve → bm25_retrieve → invoke_model → bm25_retrieve → bm25_retrieve → invoke_model | 12/14/4 | 0 | 0 |
| qwen35-4b/t2 | S2 | provider_timeout_error | unknown | read_artifact → bm25_retrieve → invoke_model | 3/1/2 | 0 | 0 |
| qwen35-4b/t2 | S3 | provider_timeout_error | unknown | bm25_retrieve → invoke_model → bm25_retrieve → invoke_model → bm25_retrieve | 5/2/2 | 0 | 0 |
| qwen35-4b/t3 | S0 | provider_timeout_error | unknown | sample_frames | 1/0/1 | 0 | 0 |
| qwen35-4b/t3 | S1 | success | 1.000 | sample_frames → invoke_model → make_contact_sheet → invoke_model | 4/33/3 | 0 | 0 |
| qwen35-4b/t3 | S2 | terminal_contract_failed | unknown | invoke_model → sample_frames → invoke_model → invoke_model → invoke_model → invoke_model | 6/29/2 | 0 | 0 |
| qwen35-4b/t3 | S3 | success | 1.000 | extract_clip → invoke_model → sample_frames → invoke_model → invoke_model | 5/13/3 | 0 | 0 |
| qwen35-9b/t1 | S0 | provider_timeout_error | unknown | none | 0/0/0 | 0 | 0 |
| qwen35-9b/t1 | S1 | turn_budget_exhausted | unknown | bm25_retrieve → bm25_retrieve → bm25_retrieve → invoke_model → bm25_retrieve → bm25_retrieve → bm25_retrieve → invoke_model → bm25_retrieve → bm25_retrieve → bm25_retrieve → aggregate_artifacts → bm25_retrieve → bm25_retrieve → bm25_retrieve → aggregate_artifacts → invoke_model → invoke_model | 18/14/3 | 0 | 0 |
| qwen35-9b/t1 | S2 | context_budget_exceeded | unknown | aggregate_artifacts → bm25_retrieve → read_artifact → bm25_retrieve → read_artifact → filter_records → select_fields → filter_records → filter_records | 9/8/3 | 0 | 0 |
| qwen35-9b/t1 | S3 | provider_timeout_error | unknown | none | 0/0/0 | 0 | 0 |
| qwen35-9b/t2 | S0 | provider_timeout_error | unknown | invoke_model | 1/0/1 | 0 | 0 |
| qwen35-9b/t2 | S1 | incorrect_answer | 0.000 | select_fields → bm25_retrieve → invoke_model → aggregate_artifacts → bm25_retrieve → invoke_model | 6/3/2 | 0 | 0 |
| qwen35-9b/t2 | S2 | incorrect_answer | 0.000 | bm25_retrieve → invoke_model → select_fields → filter_records → filter_records → filter_records → read_artifact → bm25_retrieve → read_artifact → invoke_model | 10/8/3 | 0 | 0 |
| qwen35-9b/t2 | S3 | incorrect_answer | 0.000 | bm25_retrieve → bm25_retrieve → bm25_retrieve → bm25_retrieve → invoke_model | 5/0/1 | 0 | 0 |
| qwen35-9b/t3 | S0 | provider_timeout_error | unknown | sample_frames | 1/0/1 | 0 | 0 |
| qwen35-9b/t3 | S1 | provider_timeout_error | unknown | none | 0/0/0 | 0 | 0 |
| qwen35-9b/t3 | S2 | provider_timeout_error | unknown | none | 0/0/0 | 0 | 0 |
| qwen35-9b/t3 | S3 | provider_timeout_error | unknown | sample_frames | 1/0/1 | 0 | 0 |
| qwen35-27b/t1 | S0 | incorrect_answer | 0.000 | bm25_retrieve → bm25_retrieve → bm25_retrieve → invoke_model → bm25_retrieve → bm25_retrieve → bm25_retrieve → invoke_model | 8/6/2 | 0 | 0 |
| qwen35-27b/t1 | S3 | incorrect_answer | 0.000 | bm25_retrieve → bm25_retrieve → bm25_retrieve → bm25_retrieve → bm25_retrieve → bm25_retrieve → invoke_model → bm25_retrieve → bm25_retrieve → bm25_retrieve → bm25_retrieve → bm25_retrieve → bm25_retrieve → invoke_model | 14/12/2 | 0 | 0 |
| qwen35-27b/t2 | S0 | incorrect_answer | 0.000 | bm25_retrieve → bm25_retrieve → invoke_model → bm25_retrieve → bm25_retrieve → bm25_retrieve → invoke_model → bm25_retrieve → bm25_retrieve → bm25_retrieve → invoke_model | 11/14/3 | 1 | 0 |
| qwen35-27b/t2 | S3 | incorrect_answer | 0.000 | bm25_retrieve → invoke_model → bm25_retrieve → invoke_model | 4/2/2 | 0 | 0 |
| qwen35-27b/t3 | S0 | success | 1.000 | sample_frames → invoke_model → invoke_model → invoke_model | 4/19/3 | 0 | 0 |
| qwen35-27b/t3 | S3 | success | 1.000 | sample_frames → invoke_model → invoke_model | 3/21/2 | 0 | 0 |

Unscheduled 27B Skill conditions are not run, not failed. Workflow edges describe artifact dependencies; the operator sequence is executed graph order rather than a claim that all calls were sequential. Missing artifact inputs are a structural metric, not proof that reasoning lacked evidence.

## Skill context overhead

The following numeric receipts come from each deployed model's independent tokenizer, with no generation. Token lengths and instruction increments are model-specific; bytes and words are not substituted for tokens. Actual Manager usage above includes Skills within each request and the evolving history. Usage deltas also reflect different call counts and workflows.

| Tokenizer model | Condition | UTF-8 bytes | Standalone tokens | Manager instruction tokens | Instruction increment | Base instruction | Tokenizer generation calls |
| --- | --- | --- | --- | --- | --- | --- | --- |
| qwen35-4b | S0 | 0 | 0 | 115 | 0 | 115 | 0 |
| qwen35-4b | S1 | 1555 | 280 | 396 | 281 | 115 | 0 |
| qwen35-4b | S2 | 11342 | 2535 | 2651 | 2536 | 115 | 0 |
| qwen35-4b | S3 | 12565 | 2834 | 2950 | 2835 | 115 | 0 |
| qwen35-9b | S0 | 0 | 0 | 115 | 0 | 115 | 0 |
| qwen35-9b | S1 | 1555 | 280 | 396 | 281 | 115 | 0 |
| qwen35-9b | S2 | 11342 | 2535 | 2651 | 2536 | 115 | 0 |
| qwen35-9b | S3 | 12565 | 2834 | 2950 | 2835 | 115 | 0 |
| qwen35-27b | S0 | 0 | 0 | 115 | 0 | 115 | 0 |
| qwen35-27b | S1 | 1555 | 280 | 396 | 281 | 115 | 0 |
| qwen35-27b | S2 | 11342 | 2535 | 2651 | 2536 | 115 | 0 |
| qwen35-27b | S3 | 12565 | 2834 | 2950 | 2835 | 115 | 0 |

## Provider parsing failure evidence

| Cell | Role | HTTP | Response body shape | Class | Component confirmed | XML line/open/close | JSON after-key/in-string |
| --- | --- | --- | --- | --- | --- | --- | --- |
| qwen35-4b-t2-S2 | manager | unknown | null | provider_timeout_error | False | unknown/unknown/unknown | False/False |
| qwen35-4b-t2-S3 | manager | unknown | null | provider_timeout_error | False | unknown/unknown/unknown | False/False |
| qwen35-4b-t2-S0 | manager | unknown | null | provider_timeout_error | False | unknown/unknown/unknown | False/False |
| qwen35-4b-t3-S0 | manager | unknown | null | provider_timeout_error | False | unknown/unknown/unknown | False/False |
| qwen35-9b-t1-S0 | manager | unknown | null | provider_timeout_error | False | unknown/unknown/unknown | False/False |
| qwen35-9b-t1-S3 | manager | unknown | null | provider_timeout_error | False | unknown/unknown/unknown | False/False |
| qwen35-9b-t2-S0 | manager | unknown | null | provider_timeout_error | False | unknown/unknown/unknown | False/False |
| qwen35-9b-t3-S2 | manager | unknown | null | provider_timeout_error | False | unknown/unknown/unknown | False/False |
| qwen35-9b-t3-S3 | manager | unknown | null | provider_timeout_error | False | unknown/unknown/unknown | False/False |
| qwen35-9b-t3-S0 | manager | unknown | null | provider_timeout_error | False | unknown/unknown/unknown | False/False |
| qwen35-9b-t3-S1 | manager | unknown | null | provider_timeout_error | False | unknown/unknown/unknown | False/False |

Only matching static log source markers establish a specific Qwen XML parser attribution. JSON syntax messages alone leave the particular parser/renderer component unknown. Absence of OOM/timeout/truncation markers is limited to the captured cell service logs. These are this pilot's observed errors; historical seven-error findings are not imported as new results.
Persisted JSON null on an APITimeoutError means no object response was captured, not that the model produced malformed JSON. The original null file is preserved and hashed, HTTP status and usage remain unknown, and the timeout is classified at the transport/provider layer. Shared-service queuing can contribute to these failures; they do not isolate intrinsic Planner competence.

## Interpretation and next stage

This is a descriptive three-task pilot, one execution per condition/task, not a significant TSR comparison, non-inferiority result or competence threshold estimate. Balanced frozen order reduces some order imbalance but does not eliminate caching, residency, external workload or temporal confounding. More detailed Skills also supply additional procedural content and tokens, so improvements cannot be assigned solely to granularity.

A useful next-stage candidate must retain task success while improving protocol reliability/recovery at an acceptable full resource vector. No complete monetary frontier is identified with GPU cost unknown. Resolve persistent protocol/terminal failures before attributing a gain to semantic planning; a larger held-out evaluation would be needed for generalization or an Infra-aware Workflow Adapter decision.

## Integrity and evidence

The runner's final integrity receipt is referenced by hash and exported as sanitized numeric evidence; this analyzer does not repeat source, history, evaluator or system scans. No new inference or selective task reruns were performed by analysis. Raw traces, prompts, responses, task bodies, artifact identities and private evidence paths stay on the experiment machine. Anonymous file IDs and SHA256 hashes link evidence; the private mapping remains there. Export generation is refused until the completion marker and all 30 sanitized cell results exist.

| Final receipt | SHA256 | Sanitized integrity evidence |
| --- | --- | --- |
| final-integrity | 12a2c64fadc22a9d38473eeb60ad1aca334694bcb0d9f11432818e303af6548e | {"all_executed_workers_drained_and_exited": true, "analysis_errors": [], "executed_cell_records": 30, "matrix_complete": true, "network_restored": true, "original_five_executor_instances_unchanged": true, "planned_cells": 30, "private_raw_evidence_exported": false, "protected_files_checked": 95, "protected_history_tasks_and_skills_unchanged": true, "semantic_retries": 0, "source_files_checked": 564, "source_unchanged": true, "system_problems": []} |

Final concurrency metadata audit: passed. The administration source matches the protocol amendment; every concurrent cell appears exactly once in fixed remaining dispatch order, and original serial cells are excluded from waves. Each wave requires exited child processes and a real observed idle-model drain receipt. Only slot counts/checks and receipt hashes are exported; original slot payloads and concurrent launch configurations remain private. This final metadata audit does not query models or repeat historical source scans.

| Wave | Cells | Actual size | Exited | Real model drain | Checks passed |
| --- | --- | --- | --- | --- | --- |
| wave-001 | qwen35-4b-t1-S2,qwen35-4b-t1-S3,qwen35-4b-t2-S1 | 3 | True | True | True |
| wave-002 | qwen35-4b-t2-S2,qwen35-4b-t2-S3,qwen35-4b-t2-S0 | 3 | True | True | True |
| wave-003 | qwen35-4b-t3-S2,qwen35-4b-t3-S3,qwen35-4b-t3-S0 | 3 | True | True | True |
| wave-004 | qwen35-4b-t3-S1 | 1 | True | True | True |
| wave-005 | qwen35-9b-t1-S0,qwen35-9b-t1-S1,qwen35-9b-t1-S2 | 3 | True | True | True |
| wave-006 | qwen35-9b-t1-S3,qwen35-9b-t2-S1,qwen35-9b-t2-S2 | 3 | True | True | True |
| wave-007 | qwen35-9b-t2-S3,qwen35-9b-t2-S0,qwen35-9b-t3-S2 | 3 | True | True | True |
| wave-008 | qwen35-9b-t3-S3,qwen35-9b-t3-S0,qwen35-9b-t3-S1 | 3 | True | True | True |
| wave-009 | qwen35-27b-t1-S0,qwen35-27b-t1-S3,qwen35-27b-t2-S3 | 3 | True | True | True |
| wave-010 | qwen35-27b-t2-S0,qwen35-27b-t3-S0,qwen35-27b-t3-S3 | 3 | True | True | True |

Administrative resume/interruption records are preserved below. Resuming an unchanged queue is distinct from rerunning a claimed task; the concurrency audit separately checks each concurrent cell appears exactly once. Port-bind interruptions are administrative events, not new benchmark attempts or model capability outcomes. Raw exception messages and resume logs remain private.

| Network batch | Interruption | Class | Exception type | Network restored |
| --- | --- | --- | --- | --- |
| resume-network-001 | True | port_bind_conflict | OSError | True |
| resume-network-002 | False | unknown | unknown | True |

| Resume event | Model-group transition | Class | Completed cells preserved | Unfinished claims | Runtime changed | Semantic retries | Receipt SHA256 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| concurrent-resume-002 | True | port_bind_conflict | 12 | 0 | False | 0 | aa768d7747563c0b3937e8e35d337ebd1e17200fad23eeb4da963aa61d3320de |

The model-group transition encountered an administrative tokenizer port-bind interruption. The unchanged-runtime resume receipt preserves 12 completed cells, with zero unfinished claims and zero semantic retries. This event is not counted as a model capability failure or an additional benchmark attempt.
