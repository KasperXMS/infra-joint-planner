# Frozen cross-benchmark pre-decision Raw-Aware characterization v1

Date: 2026-10-03 (Asia/Hong_Kong). Existing MultiHop 12-run block at `91f11ff`
is retained unchanged and is not rerun. This extension has **24 new primary cells**.
It characterizes coarse infrastructure visibility, not a cost-guided method.

## Shared system

Reuse `infra-aware-predecision-v1` manifest (SHA-256
`cd184ee891e9227aa7f236e3361fc6d49a756a4429a8aa3e7070b286f144ba99`).
SDK-native persistent Manager and Blind Verifier: `qwen3.8-max`. Physical model:
`qwen3.8-27b-q4km-v1`, 32768 context / 2048 output, 1200 s model-service timeout.
Manager 20 turns, physical guard 64 calls, Verifier 20; specialists 8 turns,
4 created / 2 active. Manager/specialist/Verifier instructions, native runtime,
finite operators, capabilities, observer semantics, scheduler and physical substrate
are unchanged. No cost guidance, semantic tuning, future-DAG validation or new routing.

Blind receives task + semantic state + static capability contract. Aware additionally
receives the **existing** anonymous `PhysicalProfileView` freshly before every Manager
call, including H0. Verifier and specialists remain infrastructure-blind. Worker,
deployment, address, route and private benchmark fields stay outside logical inputs.

## Selection, representation and order

Freeze all tasks before any Manager call. Selection uses source question/public
metadata and natural document boundaries, never private answers or observed new runs.
No changes after seeing execution or quality. Source revisions remain those in
`blind-baseline-6task-semantic-cleanup-v1.yaml`.

| Fixed task order | Source task | Representation / selection |
| --- | --- | --- |
| 1 Financial | `66f7c780bb02136c067c35e8` | Existing hard long four-year ESG comparison; 1,033,800 UTF-8 bytes. Natural boundary lines 0/3277/9091/17721; A4/A5/A28/A5. |
| 2 Academic | `66f2c44e821e116aacb2b826` | Hard medium GPT-4 / Chroma comparison; 494,456 bytes. GPT-4 report including its appended system card and the paper starting “Illuminating protein space”; boundaries 0/5712; A4/A5. |
| 3 News | `66faa8efbb02136c067c7357` | Hard medium Sanofi Q4/Q2 pipeline comparison with recency; 228,792 bytes. Two original press releases at lines 0/4068; A4/A5. |
| 4 Video | `795-3` | Original 2495.121 s, 282,442,048-byte AV1 video on A4; visual identification of the first magic's tool. |
| 5 Video | `848-1` | Original 2037.781 s, 160,083,738-byte AV1 video on A4; chapter ordering across the timeline. |
| 6 Video | `795-2` | Same intact video as 795-3, distinct four-event ordering question; dispersed visual evidence. |

There are **three distinct Video questions on two distinct videos**, not three
independent videos. The shared source is explicit; do not treat 795-2/795-3 as
independent video draws. Both intact local source files have AV1 video + Opus audio,
1280x720, matching public duration. No MJPEG, temporal clipping or offline question-
dependent evidence selection. The 747 original is not available among the intact
source files; fragmented historical candidate chunks are not substituted.

LongBench uses the existing generic lossless natural-document-to-ordered-records
representation. Concatenating record `text` in document/chunk order must exactly
reconstruct source UTF-8 bytes. Preserve question, choices, private answer and
original evaluator. No corpus pruning, evidence hints or dataset-specific operator.
Every context is substantially larger than the shared one-call input envelope.

Complete LongBench local pool has 208 valid physical JSONL records. SHA-256:
`69e868ad966a62d4e0a510fbefcea3fd1d8bf1ceec29c7663c0277efa8d544ae`.
Source JSONL must be parsed on LF boundaries: Unicode U+2028 in JSON strings is
not a JSONL separator. Video sources:

- 795 SHA-256 `78c7158b4ea8a29a418f84cabe77caf0a35fb0f5416c8c1592fe781b5783a4b9`.
- 848 SHA-256 `41e26da8531c00b4ec39f03333b3f94637ec8b3ff94bc46ed2e1d01c1a38b641`.

## Network and execution

Within each task run Fast-Blind, Fast-Aware, Slow-Blind, Slow-Aware, once each.
Fast 100 Mbps + configured 5 ms; Slow 3 Mbps + configured 50 ms. Existing tc
controller only. Jetsons support HTB without netem; 4090 uses HTB + netem.
These are **not measured symmetric end-to-end RTT guarantees**. Keep limitation
identical to MultiHop, and do not reinterpret configured delays as applied Jetson RTT.

Each cell: inspect -> apply/attest tc -> start four fresh Workers -> verify empty
stores/surfaces -> run -> persist evidence/final Worker metadata -> stop owned
Workers -> restore/attest tc -> immediate operational/artifact/privacy audit.
Restore failure or privacy leakage is a hard stop. All artifacts/data stay remote;
development PC sends only code/config and receives bounded metadata/report summaries.

`--prepare` freezes exact task/public-bundle/source/capability/protocol/code hashes
before execution without an LLM call. Each cell checks this record before execution.
Task contract has original A/B/C/D choices; do not apply MultiHop Yes/No overrides.
Terminal answer is the designated successful model output with existing deterministic
format extraction only; original private evaluator is unchanged.

## Failure and continuation discipline

Wrong answers, legal inefficient actions, semantic/schema misuse where schemas are
present, poor stopping, context recovery and budget exhaustion are valid trajectories.
Retain and continue after audit, without modifying prompts/strategy/budget.

Genuine implementation defects: preserve attempt -> regression -> minimal generic
fix -> full pytest/Ruff/strict Pyright -> new frozen patch -> rerun affected cells.
Family-wide semantic defects require a new family revision, not pooling versions.
All evidence is append-only; never delete historical evidence or stores.

Cloud outage/reset, external timeout, pre-semantic Worker crash, or pre-execution tc
setup failure may receive **one identical operational replacement after audit**, with
new run ID/stores and unchanged task/settings. Never replace a semantic failure.
Second same-class failure is persistent: stop and report, no third attempt.

Final deliverables: `predecision-longbench-v1.md`, `predecision-videomme-v1.md`,
`predecision-crossbenchmark-v1.md`, and exception audit when needed. Compare task-level
workload, workflow, quality and physical/cloud work; no pooled cross-evaluator scores.
At n=1 per task/condition, characterize trajectories, not stochastic stability or
causal superiority. Do not implement a cost-guided method after completion.
