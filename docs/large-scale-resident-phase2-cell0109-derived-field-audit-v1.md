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
