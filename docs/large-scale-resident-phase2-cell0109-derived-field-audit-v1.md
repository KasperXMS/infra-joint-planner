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
