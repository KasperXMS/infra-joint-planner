# Phase II cell107: initial record-field recovery audit

## Queue stop and preserved original

Original `phase2-multihop_rag-6-21c8b34e79c81848-p1-slow-B1`, attempt1,
completed its agent loop and invoked the original evaluator. It nevertheless
triggered the conservative admission gate
`typed_action_failure_requires_audit:validation_failed`. Controller018 exited1
at2026-10-08T05:45:19.840039UTC; at05:47:50UTC its owned supervisor/controller
handles were absent. No108 was reserved.106 admitted nominal cells,108 preserved
settled attempts, no pending, one unresolved, one excluded and85 unstarted.
Raw journal SHA256:
`c94295590114df5bf148e5054fc4544340e4a931f485f433fdeaef8c003f636f`.

Original107 admission file SHA256:
`f2a5196459bb93de277bab5141d9daef0ae4d815d77ede8f198629e0f55693f9`.
Trace has274 events, SHA256
`b7896422d7aab0536b3313f38fb7163552a898425852db4d899fe986a67fb1dd`.
Execution completion and evaluation presence are true; Worker shutdown is
verified. There is no terminal run.failure, operational incident, API audit
problem or method audit problem. No answer correctness claim or quality aggregate.

## Exact source-bound diagnosis

Three first-turn `bm25_retrieve` actions on the initial source shards selected
`text_field=text`. The public schema and actual hash-identical historical record
shape declare `body` as their text field. Each returned the typed execution
failure `document field must be text: text`. These are source-bound semantic
field misuses, not a missing operator or an undeclared static contract.

The existing frozen `large_scale_resident_phase2_field_review_v1.proof`
passed a read-only reproduction at2026-10-08T05:51:29.877830UTC:
3 field misuses,9 actual Manager SDK requests containing the exact public task
schema, unchanged actual Worker003/atomic004 operator sources. It reuses the
historical Phase I record proof pinned to
`0beb9d71b6c71371f683bcc2e7e6680319cb3bf0f8641f65ed7544e82a2e9735`.
Proposed reviewed admission SHA256:
`3f0a75dee9020b1d9d895e4bec0e1259e9fe24dd436d92c276c45ac26b08f4f1`.
No corpus/Worker-store body was decoded and no new model call occurred.

Three subsequent output-ID collisions were returned as
`semantic_validation_failed`; these are recorded companion observations, not
additional raw admission findings. The actual agent loop continued and reached
terminal evaluation. Do not rewrite its actions, erase failed calls, retry the
task or automatically alias `text` to `body`.

## Required offline continuation integration

Native001 binds all five existing proof groups, including original105's native
JSON failure and original71's sole authorized exclusion/replacement. Its renewal
creator currently requires a new native-JSON proof;107 instead adds another
already-supported initial-field proof. Historical files and their source hashes
must not be edited to weaken that frozen creator.

Separate offline initial-field creator, same-five-group generic renewal authority
and final adapter are being implemented. They must reproduce every old raw/
effective pair, exact disjoint inventory, source/journal/metadata history, full
original gate and strict inactivity/recipient/private audit guards. A nonempty
addition must have its actual unchanged type-specific proof; no wildcard waiver
or new semantic capability is permitted. Runtime, SDK, prompts, budgets, model
pool, operators, scheduler, tasks, evaluator and method definitions remain frozen.

At this note's freeze no107 durable sidecar, renewal authority, independent
bootstrap or019 launch is claimed. Keep018 terminal; do not retry107. Full
pytest/Ruff/strict Pyright/diff and actual4090 Linux verification are required
before the new offline source freeze. Original192/all193 plus final private/
manual/failure/retention/adoption/quality/Q1–Q10 remain incomplete; next ordinary112.
