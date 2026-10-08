# Phase II cell109 — exact derived-field finding (audit in progress)

Original `phase2-multihop_rag-3-2ff3526bbe141424-p2-fast-E`, attempt1, is preserved.
019 exited1 at2026-10-08T07:11:09.968636UTC; independently checked supervisor
3676203/start196998739 and controller3676204/start196998742 both absent.
No original110 reservation, pending action, or replacement. Original109 completed
and has an evaluator result; score/answer and semantic quality are not reviewed here.
All four Workers exited, cleanup errors empty; API/method problem lists empty.

Raw admission has exactly `typed_action_failure_requires_audit:validation_failed`.
File SHA256 `0232bd7f6a6550647332ecd26f067cd5df9dd6cf4047fb0da9eae8554b8a29b0`;
raw trace SHA256 `86b3d9d50af65ef20e57e4571ef25a9cdf4a3de5bb8b7fd2b8f24061e53c93f4`
(257 events). Current journal SHA256
`04e336a9379df372bef9e5b9b0576acfe0939f2c39b5ab48f525246e107eb08a`.
108 admitted,110 preserved/settled, one unresolved, one original71 exclusion,
zero pending,83 unstarted. Full112 checkpoint remains due before113.

## Narrow typed evidence (not a private semantic audit)

| Observation | Owner / action | Recorded failure |
| --- | --- | --- |
| Synthesis-phase guard | Manager `call_79297fcefa8a48ef86d0fdf6` | Only invoke_model/final response allowed in synthesis |
| Model context preflight | Manager `call_7e74a07f09844a9998f6f81a` | estimated input90133 + reserved2048 >32768; before inference/transfer |
| Original field gate | answer-extractor `call_0620da6521904cebb77d1c3a` | BM25 `text_field=text` on aggregated-all-shards: document field must be text:text |
| Read limit | answer-extractor `call_7f25da553a78431bafadf5ee` | aggregated-all-shards89768B exceeds65536B |
| Output collision | Manager `call_ab198f8a48734b7bbb3e82fe` | final-answer output ID already exists; semantic validation |

Six Manager task inputs are present. Source-bound field/provenance review must
reproduce public schema, exact successful producer chain, actual source hashes,
closed graph/lifecycles and every companion before any effective admission.
Current frozen v1/v2 reviewers do not cover the additional read-limit and
pre-prepared output-collision companions. They must not be modified in place or
bypassed by removing observations. An additive, offline-only reviewer/authority
with strict negative tests is being prepared; no sidecar or successor authority
has yet been created.

This is not permission to rerun109, repair Agent arguments, expose private data,
alias text to body, change tools/prompts/budgets or claim quality. Original
admission/journal/result/trace remain immutable. Any new authority requires full
pytest/Ruff/strict Pyright/diff and remote source/recipient/bootstrap verification.
All192/all193, final inactive private/manual audit and final reports remain due.

## Independently confirmed metadata and additive audit implementation

At07:21:59UTC the strict global inactive scanner, Strata-stopped check and
current frozen manifest/source fence all passed. Both108/109 process exits are0,
residency is valid, allWorkers exited, tc cleanup has no error and original qdisc
equals restored qdisc.109 raw canonical admission SHA256
`5f286e91ac41880f9ec3e7c6599858bc8b40959f228208219316f5bd9a3b7e16`;
result SHA256 `fae278a40d3de8d2c7062d3ef4bc74149af5e5e2f16d384a0946c3224efb6be7`.
108 raw canonical admission SHA256
`3b04fd25b56eebd6dc3e68ca326b360612e1edbe3322b445cbe29a5d496c4ef4`.
No score/answer/corpus body was exported or quality aggregated.

The output collision is an earlier **reservation**, not a successfully produced
artifact: the context-failed model action declared final-answer before physical
selection; the frozen semantic validator keeps that declaration after failure.
The later request reused its ID and was rejected before preparation/execution.
Source-defined behavior is retained, not repaired. Both failed calls remain in
the original trace; no context failure is counted as actual inference.

Four additive offline source files and four new test files are prepared. v3
proves exact read-limit/collision companions while retaining all original
trace/result/graph hashes; creator binds four serialized Worker65536 settings,
CLI/server/config sources, and actual SDK request/response/usage tool arguments.
The generic specialist receipt category is not treated as its logical identity:
the actual assignment, reasoning-input hash, selected decision/action ID and
provider tool-call are explicitly joined. No prompt/query/answer body is copied
into these new wire-proof metadata. Only the original derived map gains explicit
version dispatch; old81 still uses its original v1 reviewer and all five groups
remain exact. Final adapter retains strictinactive and all192/all193 guards.

Independent read-only review reproduced source closure144 with every138 ancestor
hash unchanged. Two draft integration issues (source-traversal wrapper ancestry
and explicit CLI inclusion) were fixed before any source freeze or remote use.
Current candidate source pin
`ed90bbcb25d42d0807d0476e3758b071d8be0057d3d93be3c29a8268dee488b9`.
Focused tests passed; whole Ruff, project strict Pyright and explicit four-script
strict Pyright pass. Full local pytest is still live, session53460; no full-suite
pass, Linux validation, formal source freeze,109 sidecar, successor manifest,
bootstrap or queue020 launch is yet claimed.

Source-only local archive is prepared (183 regular source members/178 Python test
files,1918976B), SHA256
`92440ed9f823f26ec65443c753d5ac31e36d06b65dcf1ee08ff7fa12a273885c`.
It has not been transferred or used on the4090. No dataset, model, Worker store,
benchmark payload, full SDK archive or secret file is in this source archive.
Journal04e336a9...eb08a and unresolved109 remain unchanged until a full-source
validated, exact proof and independently gated successor authority are complete.

## Full validation closed; actual109 dry proof reproduced

Local fullpytest53460 finished exit0:2768 passed/7 existing skips/255.91s.
Whole Ruff, project strict Pyright and explicit four-script strict Pyright pass;
diffcheck passes and all eight new source/test hashes stayed unchanged during
validation. Source implementation commit `376bb25e4cab1dac4174969859b1ca91b9f7a185`.
Only the183-member/1.9MB source archive was transferred; no dataset/model/store
or raw SDK archive traversed the development PC. Installed fresh namespace
`audit-tools/resident-phase2-derived-companion-control-001` reproduced actual144
source hashes/pin ed90bbcb...88b9, every138 ancestor retained; atomic004 unchanged.
Actual4090Linux97336 exited0:1182 passed/0skip/19.82s across35 files (all previous31
plus4 new test files). The unchanged old test-only helper was used only by pytest,
never on formal Python paths.

Exclusive validation receipt SHA256:

- Local: `a7c4c0b9963e82967dee83431e8ba111ccafe659c53286b59a4a114e9880e263`.
- Linux: `dfbd8bcf4ab55e1709e74944642394f3bebbe982e732e1f700ecbd433d67ca16`.

Readonly actual109 dry proof28046 exited0 at07:49:09UTC: exactly1 field misuse,
1 read-limit,1 output-collision,1 context and1 phase companion,6 actual Manager
schema wires and4 actual selected tool wires. The original completion/evaluator
presence is retained. Reviewed admission canonical SHA256
`c65b11784c89d2b6fe25d5329dd6f411b191c3e0f66f23d81907775edf056494`.
No sidecar/receipt, new model call, retry, corpus/store body decode or journal
mutation occurred during the dry proof.

The separate source-bound creator was then submitted **once**: session60298,
PID3702007/start197298645, started07:50:56UTC. At07:52:02UTC exact interpreter
argv/start ticks prove it live; source-bound sidecar and creator completion
receipt are still absent. Wait this owner; never resubmit or infer failure from
duration. No successor authority/bootstrap or queue020 exists yet. Original109
is not rerun;108 admitted/110 preserved, one unresolved, zero pending,83 unstarted.
All192/all193 and final private/manual/quality/adoption/Q1–Q10 remain incomplete.

## Creator failed closed before writing: historical proof header mismatch

Session60298 finished exit1 during the complete in-memory preflight, not during
benchmark execution. At07:58:08UTC owner3702007 is absent,109 sidecar and creator
completion receipt are absent; journal04e336a9...eb08a is unchanged. The strict
inactive scanner passed again. An exclusive failure receipt preserves this:
`analysis/phase2-derived-companion-field-creator-109-001-failure.json`, SHA256
`e7e1677691c0fc3688ca0b3206c1f95de7ed10dc6cd0b7d894e67d7c8b4e4682`.

Root cause is a genuine offline version-dispatch bug: v1's wrapper expected
`phase2-source-propagated-derived-field-review-v1`, but the actual frozen81
sidecar header is `metadata-bound-derived-record-field-proof-v1`. Its existing
SHA256 remains exactly
`fbcc67af95896a03f20dc27d4df68b7ebc529449d3d32b3aa9e04261a83159cf`.
The original proof's `**verified` data determines the persisted header. Prior
synthetic version-dispatch fixtures assumed the wrapper header and missed this
real serialization detail; passing tests did not prove historical81 compatibility.

The immutable v1 source namespace/archive/commit,144 source hashes and both
validation receipts are retained, not patched in place. New v2 wrapper,
environment and final adapter plus negative/real-header regressions are being
prepared as additive files. Current authority remains the original renewed001
(16cc...903a): no failed-v1 successor manifest/control/ledger exists. v2 must
dispatch actual81 only to the unchanged original reviewer, reject the invented
old wrapper header, prove a complete in-memory preflight, retain all144 hashes,
and pass full pytest/Ruff/strict Pyright/diff/Linux before any new creator.
Never resubmit60298, rerun109 or start020 until that separate successor is gated.
This failure is not a new Planner/model/benchmark failure or an operational
replacement.108 admitted/110 preserved, one unresolved, zero pending,83 unstarted;
all full-goal completion/private/manual/quality/adoption/Q1–Q10 work remains due.

## Additive v2 full validation closed; real complete preflight pending

Source implementation `757483d453412320c222b3f5cb099c95b8643bf1` adds only three
v2 scripts and three test files. Exact persisted old81 header routes to the
unchanged original reviewer; invented outer header is rejected. The complete
preflight regression exercises real v2 dispatch within all five proof groups.
Independent read-only review found no new blocker; the actual4090 source closure
is147 and every144 previously frozen source hash remains unchanged. Source pin:
`1f7f4b0699212f937fc79bc7f86c7cfb24e75a68d8053d87e6e12a43c5d43af1`.

Full local pytest25015 exited0:2854 passed/7existing skips/315.03s. Whole Ruff,
strict project and explicit three-script Pyright plus diff check pass. Actual
Linux28690 exited0:1268 passed/0skip/19.73s across38files, retaining all35 prior
test files and unchanged test-only support outside formal paths. All14 source/
test hashes from v1 and v2 stayed unchanged through validation.

Fresh source-only namespace `audit-tools/resident-phase2-derived-companion-control-002`
uses189 members/181 Python test files/2191360B archive SHA256
`f1dc9fdcb9d56ba8593d81752c742aa81f6710fea0a7e452f8bc04e048727f57`.
No dataset, model, Worker store or full SDK archive transfer occurred. New
exclusive validation receipts preserve rather than overwrite v1:

- Local: `82f9624a13cfd21ead5a9ec5c6b7dcc131ae583d523fb25294170615edddeda9`.
- Linux: `510724650a7eedc53f107a2b545dc28a1b9349185443338015d884ab242da1cf`.

Readonly actual leaf plus full-preflight session48054 remains live at08:13:28UTC,
PID3710239/start197415627, exact owner and stateR/CPU17958. Leaf proof passed;
complete five-group historical proof is still pending, not inferred from unit
tests. No new source-bound creator, authority, bootstrap or queue020 yet exists.
Original109 is not rerun and the original journal remains04e336a9...eb08a.

## Actual full preflight and exclusive v2 creator completed

Readonly48054 exited0 at08:15:26UTC: real81header and complete five-group
preflight passed, exact1field+readlimit/collision/context/phase companions,
6Manager schema wires/4selected tool wires, reviewedcanonicalc65b1178...6494.
No sidecar or corpus/store decode occurred in this readonly proof.

New source-bound creator109-002 was submitted once (session97815/PID3712940/
start197451703) and finished exit0. Owner absent08:24:37UTC; sidecarSHA256
`0d4640d11f06b1cfacf4d7152d3e45e83a31bc111a007e27f297b92107a0acb7`,
creatorcompletionreceiptSHA256
`58b04c2be2bfea04be71b60c226e8c3789202ae2649af62c566427929d84997c`.
Original journal/trace/result/graph and all five failures remain unchanged;
newmodelcalls0/retryfalse/atomicexecutionchangedfalse. This is not a rerun of
the failed creator or benchmark: it is a separately validated additive reviewer.

Authority session38560/PID3717258/start197503190 submitted once08:25:02UTC;
new control012/ledger012/v2manifest freeze is pending, not yet claimed complete.
Wait this owner; never repeat creators. Independent all110 actual SDK source/
recipient bootstrap remains required before020/original110. Next full112 before
113; all192/all193 and private/manual/quality/adoption/Q1–Q10 remain due.
