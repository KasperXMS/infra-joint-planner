# Held-out private evidence audit preparation

This is tested preparation, not a completed semantic audit. Phase II is still
running. No real supporting/gold/artifact-body scan was performed, and no Agent,
Worker, scheduler, benchmark, model, budget or method behavior changed.

Added isolated entrypoint
`scripts/large_scale_resident_phase2_private_evidence_v1.py`, source commit
`443760b`. Historical Phase I entrypoints remain unchanged. Their scanner accepts
only Phase I run/store addresses; the new entrypoint accepts only exact Phase II
namespace/run/owner store addresses. It preserves the same owner-local scanner,
hash/size checks, frozen annotations/corpus/result checks, replica/membership
checks, document-ID/literal diagnostics and unknown semantic-retention behavior.
The original audit function is reused with a private local scanner binding, not
by rewriting its source or its historical module globals.

The formal audit entrypoint checks the unchanged global inactivity guard before
metadata collection. It then requires the full resolved frozen Phase II block,
exact source membership and verified exit of every selected Worker before the
first supporting-body scan. It rechecks inactivity before each task/remote scan
and journal membership at the end. Pending/partial/excluded/confounded blocks
fail closed. New adjudications require an independently reviewed reader rather
than silently relabeling evidence. Unannotated benchmarks retain unknown coverage,
quality stays separately reported, and no semantic cause is auto-guessed.

Tests: full1721passed/7Windows platform skips;15new targeted cases; Ruff,
strict project plus explicit script Pyright, and diff check pass. Actual4090
integration29passed in1.15s. The cases cover live-before-read rejection, incomplete
blocks, exact owner/run/namespace addressing, historical source checks, owner-local
transport, synthetic private-body nonexport, paraphrase-retention unknown, all
Worker exits checked before the first scan, and unannotated unknown preservation.

| Actual immutable preparation artifact | SHA256 |
| --- | --- |
| Code-only archive | `728314ef41b3c87834625a7519a0459df9adb9b4cdbc9d99442152b70f97f76c` |
| New auditor source | `16163c36c371005a925cbb046e6cb3b76f932ac0220fcf2f6ec3a20e5ff5d0d6` |
| validation-receipt-001.json | `178a3a233bdc7759b07e58d7e6cc696b0801a8ca3f254e2ea0e5a397c3356e39` |

Remote namespace:
`/home/super/xiaoming/large-scale-cost-guidance-resident-v1/audit-tools/resident-phase2-private-audit-control-001`.
It is outside the atomic source004 imports. Only code was uploaded; datasets,
models, full trace/API bodies and supporting evidence did not transit the PC.

Actual invocation while controller1676234 remained owned/live was rejected with
`private body audit requires inactive queue and atomic actions`, before collection
and body scans. This source-bound proof is in the validation receipt. It is not
an experiment failure, partial semantic audit, nor authority to bypass the guard.

After all192held-out cells and controllers terminate, the actual audit must still
run, followed by manual source-bound failure/adoption/semantic review and final
cross-Planner, quality-conditioned resource and Q1–Q10 analysis. Literal/document
presence will not be called semantic sufficiency, and unknown will not become0.
