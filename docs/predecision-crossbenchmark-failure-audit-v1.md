# Cross-benchmark exception audit v1

Updated 2026-10-03. Current admission: 23/24; final isolated Video SA is live.
Historical attempts, logs, incident sidecars and reports remain immutable or
versioned in Git. This note supersedes earlier checkpoint status claims, not
their evidence. Repairs below do not tune semantic behavior.

## Incident inventory and disposition

| Incident | Affected formal attempts | Disposition / repair |
| --- | --- | --- |
| JSONL Unicode separators | Pre-run source/diagnostic parser only | Split physical LF, not splitlines; regression; no formal rerun |
| Observer disconnect | Financial SA primary and identical operational replacement | Both excluded; generic client idle-expiry mitigation; one transport-patch cell admitted |
| Backend hidden retry/read deadline | 795-2 FB primary | Excluded; explicit max_retries=0/read1200; one backend-client-patch cell admitted |
| Specialist dynamic-profile exposure | Financial FA, News FA originals; 795-2 SA interrupted original | Exclude/preserve; actual-recipient isolation; three authorized affected-cell reruns |
| Same exposure in existing MultiHop | FA r2/r3, SA r1 | Excluded, not rerun; nine eligible, unequal counts |
| User-reported Qwen balance exhaustion | Completed, interrupted and active new-block traces/logs checked | No observed billing failure; no replacement/API probe authorized on that basis |

Expected final new-block inventory if the live cell passes: 30 attempts =
24 admitted completions + five excluded completions + one excluded interruption.
Do not fabricate a normal result or run.end for the interrupted primary.
No semantic retry, task replacement, score-based rerun or full-family replay.

## Parser diagnostic

A source diagnostic initially used Python splitlines, splitting legal U+2028/
U+2029 inside JSON strings. Physical LF parsing confirms all 208 LongBench source
records parse; source bytes were never modified/discarded. The same issue in
queue trace parsing was fixed generically before cells began and regression-tested.
It was not dataset corruption or a reason to retry an Agent.

## Observer transport defect / mitigation

Financial SA primary had one failed A4 /state probe of 264; a pre-decision input
received three instead of four available candidates. Its one identical allowed
replacement had two failed probes of 200 on A5/A28 and a false missing_input.
Both completed/evaluated A/0 but are confounded and excluded.

The repeated class triggered the operational hard-stop; there was no third
identical replacement. Failed gaps were 4.539/4.966 s near five-second defaults.
A deterministic synthetic loopback counterexample reproduced a stale keep-alive
race; it did **not** prove the historical packet-level cause. HTTP idle expiry
was reduced 5 -> 4 s, no retry, same observer fail-closed semantics/connections.
Freeze `d43c3b3`; admitted Financial SA `transport-patch-1` still answers A/0.
Wrong quality remains a valid semantic result, not a transport-fix success target.
The exact historical transport cause remains unproved; no unresolved failed
observer probe is admitted into comparison.

## Physical backend client defect

795-2 FB primary's legal inference action encountered a read deadline and
implicitly repeated backend requests because AsyncOpenAI defaults were not
overridden. Controller-to-Worker 1200 s did not determine that internal backend
deadline. Preserve its failed result and actual requests; exclude the sample.

Freeze `5dafc43` explicitly sets physical backend max_retries=0/read1200 s.
Connect/write/pool settings, prompts, models, capability envelope and scheduler
remain unchanged. Tests capture actual constructor settings and fail propagation.
Only affected FB is rerun; its one real HTTP-200 inference completes, terminal
C/1. New sampling differs from the excluded stochastic trajectory, so quality
improvement cannot be causally attributed to a timeout repair.

795-2 FA's 664.541 s intermediate inference now legitimately exceeds the old
600 s deadline and finishes with explicit length/2048 output; a second
52.777 s inference stops normally. This is an output-limit observation, not
silent input truncation or another physical backend failure. Final B/0 is retained.

## Recipient-level privacy defect

Run-level Aware was incorrectly reused when returning specialist tool results.
Although the specialist's direct current_anonymous_profile was null, actual
SDK function_call_output contained non-null physical_profile. It violates the
experimental definition even when profile is anonymous and no IP/gold appears.

Full-context audit found Financial FA 14 distinct exposed tool calls, News FA
two, interrupted 795-2 SA seven, and existing MultiHop FA r2/r3/SA r1.
Financial SA excluded historical attempts also had exposure; their prior
transport exclusion remains. Direct-profile-only gates were insufficient.

At 2026-10-03 11:19:45 UTC, owned controller/driver were stopped, all four Workers
subsequently exited and tc restored. The interrupted trace has no normal result/
summary/run.end, so a separate hash-validated hard-stop-result records the
external interruption. Forty-one expected artifacts persisted. See
[immutable incident audit](predecision-specialist-profile-isolation-hard-stop-v1.md).

After explicit user authorization, generic implementation `4a81081`, separately
frozen as `3c3bd95`, allows tool-result profiles only for Aware root Manager,
strips them from Blind recipients before trace/state/SDK return, and guards
actual accumulated SDK context before Blind model calls. Immediate/retrospective
gates scan recipient tool outputs too. Physical selection/failure telemetry remains
recorded separately; Manager pre-decision freshness is unchanged.

Red regression: two original Aware child-context tests fail, two Blind controls
pass. Installed SDK integration, success/failure recovery, injection fail-closed,
immediate/retro gates, historical private-leak tests and external-stop admission
all pass. Full **479 pytest**, Ruff, strict Pyright zero errors/warnings.
No instructions, Verifier, schemas, models, task, budget, strategy or scheduler
change. Only three affected new cells rerun once in original relative order:
Financial FA -> News FA -> 795-2 SA. Existing MultiHop is not rerun.

Financial FA patch: C/1, 1282.028 s, five genuine inferences; News FA patch:
C/1, 713.826 s, five inferences. All actual specialist SDK contexts remain
Blind, all Manager profiles fresh. Final Video patched attempt remains live.
See [repair audit](predecision-specialist-profile-isolation-patch-v1.md).

## Billing investigation

At 10:27 UTC, 26 new trace files and recent controller/driver logs showed no
billing/arrearage/balance/quota error. Next already-scheduled Slow-Blind Manager
call completed at 10:30:37 UTC; no extra cloud probe/retry/replacement occurred.
The prior follow-up SHA:
`c219a45c890d957e1ac967b81d526a674aa8d42145323f5bfc4c23b7f5125d44`.

At 14:00 UTC, a read-only follow-up covers 30 new-block traces including all
completed attempts, the interrupted primary and the active rerun. No billing
indicator in failure/error events; latest actual Blind Verifier completed
13:57:44 UTC. `qwen-billing-failure-event-followup-002.json`, SHA:
`5b24b6ad72aeb06a460d9fecd0d531c66ee8457efdd9b635a539bb3a1293410d`.
This does not independently attest balance, errors that were never logged, or
future availability. No account status is guessed.

## Valid Agent/model failures, not repaired

All current admitted samples have terminal answers and private evaluations.
Wrong answers: Financial FB/SB/SA; News SA; Video 795-3 FB; all four 848-1;
795-2 FA/SB. Final SA is not classified before completion.

Primary category is evidence selection/interpretation and terminal synthesis.
Trace does not uniquely distinguish missing decisive evidence from reasoning
error. Static context misuse, inefficient legal reduction, phase/argument
recovery and early Verifier readiness may contribute, but are not silently fixed.
Turn-ceiling completion is not itself budget exhaustion.

Text preflight uses a conservative UTF-8 byte-as-token upper bound and static
2048 tokens per image, plus actual deployment reserve2048. These refusals occur
before transfer/inference, not measured tokenizer capacity or dynamic OOM.
Financial FA requests rejected at input bounds1084127/105544/64981; News FA at
64231/117140/33526/32291 (all plus reserve2048). Four option notes or four news
notes are explicit purposeful analyses, not four hidden repeated model retries.

A valid wrong canonical answer is evaluated and retained. No evidence, prompt,
choice or score is post-hoc guessed. More branches, traffic savings, natural
continuation and parallel overlap do not guarantee quality or E2E benefit.

## Preservation and limits

Authoritative current root:
`/home/super/xiaoming/predecision-crossbenchmark-v1-3c3bd95`.
Original/transport/backend roots and existing MultiHop remain intact.
All six task freezes and static capability hashes match earlier versions;
141 source/script blobs match the isolation freeze on all four nodes.
Historical hard-stop verification retains 156 original new-attempt files and
72 existing MultiHop files. No result bodies are copied through the PC.

Per-cell result/trace/graph, observer diagnostics, tc attestations, empty-store
state, model request/selection telemetry and terminal provenance remain remote.
Full LongBench content-hash verification covers 48 roots/256 replicas.
Final family-wide Video content, fresh profile, request-count and cleanup checks
await the active cell. Fixed order, persistent inference state and n=1 limit
causal interpretation even when implementation confounders are removed.
