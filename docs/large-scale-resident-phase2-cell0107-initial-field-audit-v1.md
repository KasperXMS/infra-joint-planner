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

## Separate offline implementation validated

Implementation commit `b4e45c5bdec2957845d918e4c871671e0a26f4ac` adds only
three offline audit modules and three test files. The unchanged five proof
groups are reused; a renewal may accept any nonempty independently reproduced
addition, with every old raw/effective pair and the original exclusion retained.
The original full gate is checked against an in-memory candidate before any
new authority file is written. No frozen ancestor source/global is modified.

Authoritative Windows verification: full pytest2530 passed/7 existing skips,
245.81s; combined native/renewed tests216 passed/87.83s; Ruff, strict project
Pyright, explicit strict new-script Pyright and diff check pass. Actual4090
Linux verification: all31 selected files,944 passed/0 skips/14.67s, owner
3654432/start196721332. Historical test-only support remains outside the formal
controller path. Separate validation receipt SHA256s:
local `154723591f5195932c4b9370b83b0fc390d0f9f1ce6763b13f179d1e795ef664`;
Linux `967b6060d1f9c17df18304ba10f49a23f3792ca806d632e406be0b52eb0c874f`.

Source-only archive178 members/1822208 bytes, SHA256
`126d380995ea840e3e5b1d0061e4814ec31440249b7f5280c4df7c4160d33134`,
installed in `audit-tools/resident-phase2-native-renew-control-001`.
Actual final-source closure138, all135 ancestor hashes unchanged, pin
`e3c99e68186f35408efa07678643f2241715dfacea28d027d435a447b9129861`.
An earlier local-only incomplete four-member archive is preserved and explicitly
non-authoritative; it was not transferred or used. No experiment was retried.

At06:10:30UTC,018 handles remained absent,106 admitted/108 preserved/one
unresolved, unchanged journalc942...636f and no108 reservation. These tests and
source receipts do not themselves create107's durable proof, renew authority,
run independent bootstrap or launch019. Those exclusive steps remain pending.

The exact107 exclusive creator was submitted once, session97337, owner
3655315/start196732934 at06:16:39UTC. Readback06:17:28UTC verified the same
live owner; sidecar/creator receipt/new authority remained absent, journal
unchanged and018 handles absent. Wait/poll this handle, never resubmit on an
observation timeout. No new benchmark call or Worker is involved.
