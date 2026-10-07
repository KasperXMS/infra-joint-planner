# Phase II cell71: external GPU contention

Capture2026-10-07 11:43:43Z /19:43HKT. Metadata and owner-local admission
investigation only, not the final private semantic audit.

## Follow-up: actual service owner and resumption boundary

Read-only11:48–11:51Z investigation independently traces engine3105968
to Python3105959, then user-systemd3791. Both workload processes belong to
`super`,UID1000, within
`/user.slice/user-1000.slice/user@1000.service/app.slice/strata.service`.
Unit fragment`/home/super/.config/systemd/user/strata.service` is owned by
super,mtime06:36:10Z. It starts`/home/super/Strata/.venv/bin/python`
with`serve/server.py` and`strata-iq2_xs.json`; description is
`Strata Qwen3.8-Flash-Next IQ2_XS`. Description is not independent proof
of model weights. Unit is enabled and uses`Restart=on-failure`,15s delay.

Original user-journal lifecycle records show11:29:08Z start, SIGKILL exits
at11:29:48/11:30:44Z, automatic restarts11:30:03/11:31:00Z, stop11:31:15Z
and latest start11:34:49Z. SIGKILL alone does not establish OOM or who killed
the process. At11:51:53Z unit remains active/running, same main/engine PIDs
and invocation108ca52e8d284fefb93cc9b047bae9f6. GPU1reported13024MiB.
Controller010remains terminal,70admitted/71preserved/0pending/1unresolved;
no new dispatch, ancestor source or PhaseI journal change.

The user explicitly says this external workload is not theirs. The available
SSH login metadata identifies a contemporaneous key labelled
`Home Workstation stage0` from172.28.221.223, alongside other super sessions.
This is a lead, not proof that this key/session started the unit. No saved
Strata systemctl command found in bash history; auditd inactive. The evidence
identifies the account/service, not a specific person or starting client.
No private key, full model payload, unrelated prompt or complete environment
was exported. No foreign process/service/key/config modified.

Resumption requires external resource isolation plus permissible disposition
of original71. Current safe alternatives were checked: accepting its score
would waive residency; repeating it as provider outage would invent an
unsupported reason; skipping it changes frozen order; routing away fromGPU1
changes frozen substrate; terminating another workload exceeds the inspected
experiment-owned process scope. None has been performed. Thus the same
external-coordination/protocol boundary persists, not a transient SSH timeout
or a running experiment controller. All192and final audits remain required;
normal16-cell cadence cannot resolve this immediate finding by itself.

## State and cause

Controller010PID3068687 and supervisor3068686 are no longer live; exit1 at
11:36:16.687331Z.003ledger:70admitted settled cells,71preserved attempts,
0pending,121unstarted,8original findings,1unresolved. Settled admitted cells
include valid failures, not70correct answers. No72 or replacement dispatched.
Full64is independently closed; full80does not yet exist.

Run`large-scale-cost-guidance-resident-v1-phase2-video_mme-5-332db0bfa03dd109-p1-slow-E-attempt1`
reports execution completed, format valid, evaluator score1.0. Atomic3101589
exited1. Raw immutable admission`confounder/admission_unverifiable/FileNotFoundError`
and settlement sequence142 remain. A correct answer does not prove admission.

Earlier failure: unchanged`compare_residency` rejected
`external GPU compute contention changed during the cell` after saving before/
after residency. It never wrote`private/residency-validation.json`; the outer
admission wrapper then encountered the missing file. Do not fabricate it.

Five experimental server/runner/target identities match before/after:
A4/1835641,A5/1915965,A28/2734491,GPU0/1130531,GPU1/1130540.

| External GPU1 process | Before | After |
| --- | --- | --- |
| command |strata |strata |
| PID |3102868 |3105968 |
| reported GPU memory MiB |5226 |13024 |

GPU1UUID`GPU-bf1b70c4-b2d7-ed3b-54d5-95685863f06d`. Actual11:41:29Z
process readback: executable`/home/super/Strata/engine/strata`, cwd
`/home/super/Strata`, UID1000,parent3105959,start190002125. It is outside
the experiment-owned namespace; no unrelated process killed or suspended.
Persisted cells61–70before/after samples have no Strata entry, only the two
previous GPUStack RPC processes outside experimental runners. Endpoint
samples cannot prove absence of arbitrary transient contention between them
or establish the causal latency penalty of cell71.

## Independent original admission

At11:43:43Z, after original inactivity guard passed, the actual admission
function bound to archived`execute_cell` reproduced base admission`valid`,
264trace events, no API/method problems or operational incidents. This does
not waive the missing residency gate. Worker shutdown verified; original/
restored qdisc equal. Zero new model calls, corpus/support/store-body decodes
or payload exports. Original admission/result/trace/journal untouched.

| Original file | SHA256 |
| --- | --- |
| admission.json |c86cc8f1f92396253862c12dedf8b70bf62025314a6125dc42dc1fa0d2c4855d |
| attempt-error.json |14dd59f63a4d12eee30575112dc179d5d265dad6b5d407c30b2ff461a2ecf019 |
| residency-before.json |19ba96506d497f66da9037d629918f332706028591997e3600bf1a58b4547366 |
| residency-after.json |679fda8add5df4b6228b96fb8a63e9129737cb477f25bc48a682f036d23656cb |
| process-exit.json |997cf1dab68dddcc38818e738c4cb61030481bac0c06f4232655647f7c5db686 |
| worker-shutdown.json |38ebec77d2e236478da3506dd58bc040ef688d6d2de6d4da21f36e8d666e70bd |
| tc-attestation.json |49cd17c4b7a366d1cd8426ee5f905f02825545e9252349eb757b7bb97db23c03 |
| trace.jsonl/1664147bytes |da14d90949de930420f91cbca442112019b432fed04c01f1045b992e3c40ee0e |
| result.json/498312bytes |4290d1fa8ef2852fb9c2e630e371737383519b5aa51112176df706a1bc3ca8a7 |

PhaseII journal SHA256
`f1c1e5cba2548b18ebb4e61ae9fc4f04241d1a63562fb5dc935601eb738f9a94`.
Original canonical admission digest
`96d977ddfd2bfc7256537439838cec0631a9d9b4f45c87d1e7c8ab305e7c1b4c`
legitimately differs from file-byte digest.

## Disposition and next gate

Primary finding: external environment/resource-contention confounder, not
ordinary semantic planning failure, nor proved model reload. Cell71 remains
unresolved and is not among70admitted cells. No hidden retry, rewritten
journal, accepted sidecar, new control/manifest, full80 or queue restart.

Frozen operational replacement vocabulary does not explicitly include
external GPU contention. Do not relabel this as provider outage or infer
replacement authority from a correct answer. First establish resource
isolation and evidence-bound permissible disposition. User asked which
external Strata workload owns GPU1 and expected end time; no authority to
terminate it inferred. Queue stays stopped, goal remains active.

Normal full audits remain every16cells plus tail, with immediate finding
stops. Production/models/prompts/tools/budgets/scheduler/benchmark/evaluator/
resident settings unchanged. Existing1843fullpass/7platformskip,69targeted,
22Linux,Ruff/strictPyright results retain their prior scope; not new tests.
All192and final strict-inactive private/manual/failure/recipient/adoption/
retention/Q1–Q10/named reports remain incomplete.
