# Frozen financial Skill activation results

The nine predeclared `financial-analysis-4` trials all received the unchanged official binary verifier. **S1: 0/3; S2: 1/3; S3: 0/3.** The 68-token generic S3 trigger appeared in the model request, but none of the three S3 Agents used a tool to read either original main `SKILL.md`. Native S1 also read neither file in all three runs. S2 put both exact original main bodies in every model request and produced a scorable artifact in all three runs. Its one pass and two failures on the same question show that delivery helped at least one execution but did not make task success reliable.

The [frozen v2 manifest](frozen-manifest-v2.json) and [method](activation-method.md) define the independent fresh-container repetitions, balanced run order, equal 900-second Agent budget, original task/Skill/verifier hashes, no exposed tests, and treatment bytes. The official source reference scored 1, while an intentionally incomplete artifact scored 0 ([preflight summary](evidence/oracle-preflight-summary.json)). The original verifier score remains 0 for context rejection and timeout cells; they are marked separately below. Development trigger probes on the previously seen `financial-analysis-2` are excluded from this denominator.

| Run | Condition | Official reward | Agent execution | Main Skill tool read | Original main bodies in model requests | Output artifact |
|---|---|---:|---|---|---|---|
| 1 | S1 | 0 | HTTP 400 context rejection | neither | 0/19 requests | absent |
| 1 | S2 | 1 | completed | neither; bodies injected | both in 58/58 | present |
| 1 | S3 | 0 | HTTP 400 context rejection | neither | 0/39 | absent |
| 2 | S2 | 0 | completed; second answer rejected | neither; bodies injected | both in 44/44 | present |
| 2 | S3 | 0 | completed; second answer rejected | neither | 0/30 | present |
| 2 | S1 | 0 | 900-second budget timeout | neither | 0/172 | absent |
| 3 | S3 | 0 | completed; second answer rejected | neither | 0/23 | present |
| 3 | S1 | 0 | HTTP 400 context rejection | neither | 0/26 | absent |
| 3 | S2 | 0 | completed; second answer rejected | neither; bodies injected | both in 27/27 | present |

Both native Skill names, descriptions and paths were visible in the first model request of **every** cell. The S3 read trigger was also visible. No S1/S3 command even attempted to open either main `SKILL.md`, and no successful full-body tool observation was later sent back to the model. In S2, an explicit full-body file read was unnecessary because the exact original text was already injected. The Agent used referenced Skill scripts in S2 repetitions 1 and 2, but not repetition 3. These measurements come from successful command outputs and archived request bodies, not Agent self-report ([per-cell evidence](evidence/activation-summary.json)).

All three S2 outputs passed file-existence checking. In S2 repetitions 2 and 3, the first answer passed but the second failed because the Agent used a total-holdings count to answer a stock-only question. S3 repetitions 2 and 3 made the same mistake without ever loading the original Skill. S2 repetition 1 passed after using the relevant helper. The repeated loaded-Skill failure is analyzed as a **candidate** rule-selection/completion-check gap in [the case study](procedural-gap-case-studies.md), with compaction and tool errors retained as possible contributors.

| Median per condition, 3 runs | S1 | S2 | S3 |
|---|---:|---:|---:|
| Model requests | 26 | 44 | 30 |
| Reported input tokens, including cached | 289,572 | 531,081 | 348,061 |
| Reported cached input tokens | 256,080 | 486,288 | 315,216 |
| Output tokens | 5,803 | 7,873 | 4,598 |
| Nominal treatment tokens per request | 0 | 1,202 | 68 |
| Nominal repeated treatment tokens | 0 | 52,888 | 2,040 |
| Shell tool calls | 25 | 36 | 27 |
| End-to-end seconds | 152 | 357 | 176 |
| Five-second-sampled GPU energy, Wh | 13.03 | 17.91 | 9.11 |

S3's 68-token trigger is about **94% shorter** than S2's 1,202-token original-body injection in the static request prefix, and its nominal repeated treatment footprint is smaller. These are **prompt-footprint** observations, not a demonstrated cost-quality gain: S3 scored 0/3, and the conditions also changed what content entered the context and how salient it was. The token totals count cached prefixes; vLLM prefix caching means they cannot be priced as fresh GPU prefill. The GPU energy estimates integrate sparse power samples over each trial window, include service idle work, and do not isolate treatment energy. No confirmed AutoDL rental rate was recorded, so monetary cost is unknown ([GPU receipt](evidence/gpu-by-trial.json)). One task and three correlated temperature-zero repeats do not support statistical generalization.
