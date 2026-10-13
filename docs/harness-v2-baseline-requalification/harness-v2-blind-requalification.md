# H1 resource-blind baseline requalification

The 18 preregistered H1 cells completed without selective reruns. The Stage 1
engineering boundary passed: all claimed cells produced durable results,
Workers drained and exited, the shaped network was restored, and the recorded
context checks found no silent truncation. Evaluator consistency checks ran
on completed outputs. The task manifest was frozen at SHA256
`25e65b22b452bc164efe61ad895d20e5fcf3c8d407e4e9c7380a204bbec9b3ad`.

| Planner | Cells | Completed | TSR (score 1) | Manager raw-schema failures | Verifier raw-schema failures | Cloud API USD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Local 27B, trial 1 | 6 | 3 | 3 | 2 | 3 | 0.4453 |
| Local 27B, trial 2 | 6 | 4 | 3 | 2 | 2 | 0.4051 |
| Cloud `qwen3.8-max` | 6 | 3 | 3 | 0 | 2 | 1.2307 |

The 27B trials together completed 7/12 and scored 6/12; the cloud reference
completed and scored 3/6. These are repeated executions of the same six tasks,
not twelve independent task samples. The cloud API totals include the fixed
cloud Verifier and any cloud Specialist. Local GPU monetary cost remains
unknown.

| Task | Local trial 1 | Local trial 2 | Cloud reference |
| --- | --- | --- | --- |
| MultiHop-RAG 1 | 1 | 0 (wrong answer) | 1 |
| MultiHop-RAG 2 | 1 | 1 | 1 |
| LongBench-v2 1 | interrupted | interrupted | 1 |
| LongBench-v2 2 | interrupted | interrupted | interrupted |
| Video-MME 1 | interrupted | 1 | interrupted |
| Video-MME 2 | 1 | 1 | interrupted |

Seven interrupted runs followed a Verifier function call whose raw arguments
failed its frozen JSON Schema. One additional cloud run passed the raw schema
but failed the `VerificationResult` semantic validator. The invalid verdicts
were not accepted as successful verification. These eight failures are
observable Verifier/model behavior under the unchanged cloud endpoint, and
remain in both Completion and TSR denominators. Four local Manager raw tool
calls also failed schema validation; those runs recovered within their
original turn budgets. The other completed wrong-answer case is MultiHop-RAG
1, local trial 2. No task was retried on account of these outcomes.

| Planner | Manager model calls | Verifier calls | Specialist turns in completed loops | Physical inference calls | Physical service work, s | Sum task E2E, s | Data transfer, MB |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Local trial 1 | 36 | 33 | 0 | 5 | 224.0 | 575.5 | 238.838 |
| Local trial 2 | 34 | 32 | 0 | 5 | 227.6 | 548.4 | 238.829 |
| Cloud reference | 40 | 37 | 8 | 6 | 720.1 | 1158.1 | 249.223 |

| Planner | Manager input / output tokens | Verifier input / output tokens | Specialist input / output tokens |
| --- | ---: | ---: | ---: |
| Local trial 1 | 358,923 / 14,318 | 313,433 / 5,554 | 0 / 0 |
| Local trial 2 | 337,523 / 13,735 | 297,469 / 5,304 | 0 / 0 |
| Cloud reference | 505,847 / 14,580 | 530,318 / 7,109 | 104,712 / 980 |

Provider usage receipts have no missing prompt/completion token counts or
unknown cloud-priced calls for these 18 cells. Physical service work sums
successful physical model telemetry and is distinct from Manager/Verifier
provider latency. Interrupted runs lack a completed loop usage object, so
the table uses durable per-role request receipts and trace observations
rather than treating missing loop totals as zero.

The baseline demonstrates real task completion and evaluator operation on
H1. Verifier validity is the dominant observed completion limit in this
small sample, so the Stage 2 paired comparison must retain and report
Verifier-invalid outcomes; they cannot be interpreted as evidence that one
Planner method improved logical planning.
