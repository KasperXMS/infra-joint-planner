# Eighteen-task pre-outcome freeze v1

2026-10-05. **All 18 task identities, complete representations, initial placements
and the 168-cell Phase I order were frozen before outcomes. Formal runs were0
at that preparation checkpoint.** The sections below preserve the pre-outcome
task/schedule freeze, not current execution progress. Execution, monetary metering
and full effective-recipient privacy admission were subsequently implemented and
frozen; Phase I is now in progress, as recorded in
[Phase I results](large-scale-phase1-results-v1.md). This status clarification
does not change a task, artifact, evaluator, initial placement or schedule hash.

Preparation code `af0f3ce`; serialization-only correction `18b9748`. Neither
changes Manager/Verifier instructions, SDK-native runtime, operators, scheduler,
physical model contract or benchmark evaluators. No outcome informed selection.
Every family's positions 1–2 enter Phase I; positions 3–6 are held for Phase II.
No replacements based on performance are permitted.

## Remote authoritative materials

Root: `/home/super/xiaoming/large-scale-cost-guidance-v1/preparation`.
Current freeze: `task-freeze-002/manifest.json`.

| Receipt | SHA-256 |
|---|---|
| Current 18-task manifest | `25e65b22b452bc164efe61ad895d20e5fcf3c8d407e4e9c7380a204bbec9b3ad` |
| Canonical ordered Phase I schedule | `9e5da533b84834c9da84be586ca353f8a71171e8cf19d1505c5d2c5c03d94171` |
| Task preparation/reload audit | `93ace03b7f86c3eea54a80299c8048d0ab7196b2b96e9a2ef5e63a6a7e7fb381` |
| Preparation code archive, alias correction | `13b4e88575882b998f04024f7dd976232c185dadea7cef2e1da2f8563d3d2bf4` |
| Original Video-MME annotation parquet | `7fffab8ed38ecc2f9f0eca4c44d8a11636f0ee96116ede83580c8b9ae0faf986` |

The manifest contains every task/evaluator/source/artifact digest, complete initial
placement mapping, original output contract and equivalence/provenance records.
Each task directory has `execution.json`, a sanitized `agent-task-view.json`,
private evaluation, prepared bytes and receipt. All bodies stay on 4090. Initial
placement here is a frozen configuration, not a claim that Workers were started.
Fresh Worker stores and actual placement occur separately for each future cell.

## MultiHop-RAG: six complementary evidence strata

Pinned existing source revision `71ac0d0bd1f951d2d6b70311f7d2ae404e1ffa82`.
Every task receives the same complete 609-document corpus, represented by the
existing lossless bounded-body adapter and three nonsemantic content-hash shards.
The union is complete; no support-based candidate filtering is performed.
Prepared input is **7,696,522 bytes per task**, placed `[A4, A5, A28]`.
The original source corpus file is 6,785,567 bytes; JSON/chunk overhead explains
the different prepared size.

Counts below come from private, pre-run annotation audit. They are never included
in Manager/specialist/Verifier input. "Sources" counts distinct publishers;
supporting documents and publishers are explicitly different quantities.

| Position | Original task ID | Original row | Pattern | Supporting documents / publishers / shards | Full supporting-document body bytes |
|---|---|---:|---|---|---:|
| 1 | `multihop-rag-train-4b6de4acbde051fee1f727f3` | 3 | comparison | 2 / 2 / 2 | 27,406 |
| 2 | `multihop-rag-train-fe71f374676e35359d12c83e` | 8 | inference; higher volume | 4 / 1 / 3 | 73,741 |
| 3 | `multihop-rag-train-facda0bcd2ae340c909be414` | 0 | inference | 3 / 2 / 3 | 23,157 |
| 4 | `multihop-rag-train-29a31b9c1104c2e563cc501f` | 17 | temporal | 3 / 2 / 3 | 69,257 |
| 5 | `multihop-rag-train-77510aa6e6be8914ec641d33` | 133 | comparison | 3 / 2 / 3 | 18,151 |
| 6 | `multihop-rag-train-9833c1c381017ce6e94f30e6` | 4 | inference; shard-local contrast | 3 / 2 / 1 | 48,988 |

Five of six require multiple shards and five require multiple publishers. The
four-document case deliberately separates document aggregation from publisher
count. Body bytes are not a minimum sufficient-evidence budget: they measure
whole supporting documents, not annotated fact snippets. Retrieval difficulty
and achievable reduction ratio are unknown before execution, not invented.

Use the original short-text output contract and official token-overlap evaluator.
Do not force all new questions into the old comparison task's Yes/No labels;
some original inference answers are free-form. That evaluator's token-intersection
rule is weak semantic evidence and must be reported as such, not upgraded.

## LongBench-v2: length, domain and task-pattern diversity

Pinned existing revision `2b48e494f2c7a2f0af81aae178e05c7e1dde0fe9`;
source is the existing 208-record remote selection file. Preserve every context
character, original question/options/gold and exact-choice evaluator. Reuse the
existing 3,000-character ordered text-record preparation, without new operators.

| Position | Original task ID | Original pattern / length / difficulty | Original context bytes | Prepared bytes | Prepared groups / initial placement | Audited original document count |
|---|---|---|---:|---:|---|---|
| 1 | `66f2c44e821e116aacb2b826` | Academic multi-document / medium / hard | 494,456 | 514,789 | 2 / A4, A5 | 2 |
| 2 | `66f94f9ebb02136c067c4fde` | Governmental multi-document / long / hard | 2,020,467 | 2,119,778 | 1 / A4 | unknown |
| 3 | `66fa0d88bb02136c067c5a8a` | Financial multi-document / long / hard | 926,221 | 967,830 | 1 / A4 | unknown |
| 4 | `66fcf2f2bb02136c067c9169` | Multi-news multi-document / short / easy | 112,153 | 115,726 | 1 / A4 | unknown |
| 5 | `66f016e6821e116aacb25497` | Legal multi-document / medium / hard | 324,269 | 340,278 | 1 / A4 | unknown |
| 6 | `66fa208bbb02136c067c5fc1` | Code Repository QA / long / easy | 1,932,425 | 2,032,683 | 1 / A4 | unknown |

Academic's previously audited starts `[0, 5712]` are retained. For the other five,
internal natural-source boundaries could not be independently established from
the available context metadata. **Their complete context is one logical container
of ordered records, not a claim of one original source/document.** No arbitrary
uniform partitions are labeled as natural documents. The adapter's prepared
`document_count` describes these execution containers; original counts are the
separate nullable manifest field `original_document_count` above.

This covers a verified two-document case, original benchmark-labeled multi-document
cases, medium/very-long inputs and a different repository task pattern. The large,
symbol-focused repository query is a local-evidence proxy, not an audited guarantee
that one snippet suffices. Cross-document evidence span and unknown source counts
must not be asserted from a domain label alone. Prepared record text concatenation
was checked byte-for-byte against the original context for all six.

## Video-MME: six distinct original videos, not smoke derivatives

Original [Video-MME repository](https://github.com/MME-Benchmarks/Video-MME)
links to [LMMS original data](https://huggingface.co/datasets/lmms-eval/Video-MME).
Pinned revision `ead1408f75b618502df9a1d8e0950166bf0a2a0b`, 2,700 original questions,
900 video members across twenty ZIP archives. Video-MME-v2 is not substituted.
Use the existing video-only/no-subtitle execution setting and original choice
evaluator; intact MP4 files retain their original streams. No MJPEG, re-encoding,
prefix clipping or question-dependent preprocessing is used as source data.
Any frames/sheets later requested by the Agent are runtime evidence reductions,
not equivalent replacements for the frozen full source.

| Position | Original question | Original video | Declared task type / domain | Actual duration s | Source/prepared bytes | Initial placement |
|---|---|---|---|---:|---:|---|
| 1 | `602-2` | `w0Wmc8C0Eq0` | temporal reasoning / Knowledge | 2,819.854453 | 213,739,837 | A4 |
| 2 | `131-3` | `HdBsD5VspVM` | object recognition / Sports | 77.995746 | 7,037,220 | A4 |
| 3 | `481-2` | `CwzjlmBLfrQ` | action reasoning / Artistic Performance | 336.921484 | 15,239,623 | A4 |
| 4 | `394-2` | `V6ui161NyTg` | information synopsis / Film & Television | 356.078000 | 9,320,768 | A4 |
| 5 | `224-3` | `g1MCVp5xICM` | temporal reasoning / Life Record | 60.000313 | 2,076,341 | A4 |
| 6 | `891-1` | `uuCVnqV4cNc` | object reasoning / Multilingual | 3,030.042000 | 233,097,342 | A4 |

All six source streams report **h264**, not AV1. Semantic artifact schemas use
their measured codec/duration through the existing identity VideoMMEAdapter.
Options are decoded by exact label-prefix parsing, never gold-based guessing.
Temporal/object task types are dispersion/localization proxies: no reliable
evidence timestamp annotation was found, so `evidence_span_seconds` stays unknown.
Do not claim that all temporal questions necessarily require distant timestamps.

All acquisition occurred on 4090. Validated HTTP206 ranges downloaded ZIP indexes
(9,113,673 bytes) and only six selected members; original video total is
480,511,131 bytes, member-acquisition network bytes 488,385,190 including range
overhead. Archive member CRC validation and per-file SHA-256 succeeded. The dev PC
received source code and bounded metadata only, not annotations/videos/artifacts.
The preparation-only PyArrow21.0.0 environment is separate from frozen execution
dependencies. No Worker, model inference or tc operation was started for preparation.

## Hash index

These are full task-bundle and private-evaluation digests. Full source/artifact and
evaluator-code hashes are additionally bound by the manifest above. Digests and
this researcher-facing table are not Agent inputs.

| Family / position | Task bundle SHA-256 | Private evaluation SHA-256 |
|---|---|---|
| MH1 | `178e287b098d8c7e3667fa68d986b7c7f0bace97cbb622d763ec0df876364ea4` | `95ef3a28dd26e27a5a8fb00e52fa407bba1dbb6c24146745a9409a07371926ff` |
| MH2 | `1292d49f402c122637731b33005b95891876bb82e17e2d0cd97a46b2a9c5a76b` | `bcda00de1233bdb8a847b924cd374af454b671fd744ec3db122d2cb63ee8c60c` |
| MH3 | `df18db59c12a5d45965767647fb0779528271e7bd6bfbf695e2510a3fe7d1fa1` | `f0dda50a661bf38ebe1f75ed9a4aaa434b1d5d2697741a3b00929d1fe1e6d376` |
| MH4 | `2af5291a58b468d0ff31e71726b20188ed769a01f1f1f49eead8d4a08b92fe9f` | `6557848016749d0390c66fdd332dabc1afc908c4f1ac914911f0c2876d94044a` |
| MH5 | `a7898fae9de8428d59d2f6e8a37406c3e79cc8fe5a3273503bf23c5969cea754` | `7ca02ca840df66b668ab2db5554928a9c34acc2b919effe69dd2e25710b61ef1` |
| MH6 | `fe4159a3a42724ff4617dc74ec23dde7454e617a07d2b5608750e704cbef1c07` | `404767eb682ea6aeaa18a338de5ca050eed2b2e38f0059c8bc34e8857ec6be02` |
| LB1 | `2fb48b41810afcd166a0917f28396d5fe8d704ce7550c376d5df8e56edd76ad0` | `676783f7b4acc69e4d02deb50bf7a2841c404ec490e231b1debef6cd75d6dd35` |
| LB2 | `bde8d96c779ff22658a7ed96eec0c44db85435053ea7e63b3d7ecae07b73db84` | `3c657d8ac6bc34bd6b01ce9bf73dbf2cfefd73b4c8e6b058478e2c010eb02442` |
| LB3 | `ace99de13e6a6d28c347f434a135e52f177ac09e2b44d33ec1780fe0578058e8` | `ec66f885663f707d3bb7f4fbeb5a66b30959147dc1434871d71fa2022f3868b3` |
| LB4 | `8dbdcaee9e87419dbb2f4a95a817b0427b395d9826da0a2a6001ef3fa07e3a07` | `e5fad23e125767b5faa6725cd6366cc7c435bc0de27c1fa0d3b84cc698f5da62` |
| LB5 | `4bae7c2195d755bc0ad079ffa25c81af923ebb6aa8cf69af65b0e1934918d0d0` | `6ff8dbf8e7ad0bf2e025e586700771ee6ab02792cf612ae4c674731996916535` |
| LB6 | `e03c553cddb90522a2359ffcd49053cc7160d9a89fc41124190e7c0a547d0846` | `18ad64af056993e6cc351a7265868441a0380f3858ea55d4c29a0c31bf83aae5` |
| V1 | `c5c60e9f3b346074dc84b96e2af23b7d47fa169852c2229530cdeaaa9e175be7` | `f7b094792518703879ccaf167ba5b60e72c80cbb304becc1dee55585bb403f74` |
| V2 | `6019c5446f6061729625c20631108b62904ba1a20269b4321fc12e13f631bcdb` | `c0c38c295d958d639c63d8000e8970a7586d78a3ec47d81981535772cc46ca65` |
| V3 | `13b9882683e99178a47902d5f36a5a4d5d3a5ede5b328c936ec60a371aa41f12` | `ecd5a8b50eea494d63a03a5391e2154a53dae46b26e70ab00de98433a47cf96e` |
| V4 | `61bd0a7273b0c2e7808c42878605abfa9ac457d651fc2e39d079a71256bb1b3e` | `d56e66bd55f05fa271d40fe9a13cfb91adf4886bf3d843637d7ae5414c46d8f5` |
| V5 | `f31464c9957c8bdca1990a73bdd906fda15d74fdeef08b517fd1dd7b6a9fc2ad` | `d72c445167dfbd6372b45792c8cab6fd5f23249a23bb0a4fb6a55e3958848449` |
| V6 | `e59d559588c0ab6a0a140ce37b93a71887e7ccfc0abee4dd5c63d07b16f29f4a` | `2f747e51fd69aedf6fdb5cd6e12dd25c8d3f4e5ab7c84d64022394e71a4e0367` |

Original evaluator-code hashes: MultiHop
`1827d44c974d1ae8211218c7ae1b801b834f604dcc3bf129e4d6bbe4c9a354cc`;
existing exact-choice module used by LongBench/Video
`8ade0b3b0fcd7e63826bc5c8147a3814d84c788c64fda8c56b5b940d511c8e72`.

## E holdout and immutable repair audit

Reuse the identical historical six-rule set for both Planners. Rules hash
`6b2152aaf9c3e1ba90deacd4031bddc8870e0ac01e32c72be68fb24dc0b43be9`;
rules manifest hash
`36ba6e780bbf39b9509b70a98b80a8cd5478ce532420207070bdde9e7f2f0887`.
Its actual `source_tasks` map to Financial `66f7c780bb02136c067c35e8`, News
`66faa8efbb02136c067c7357`, Video `795-3`. All 18 identities are disjoint;
the entire source video `D97vMwfWxvI` is additionally excluded. No new distillation
call or formal outcome is used. Historical profile data remain separately frozen.

The first preparation freeze is preserved as `task-freeze-001` (manifest hash
`56c4df21417f2c7ebfd0255625b77e45f926d7301484f6a8a934b4a106f4726b`).
Strict dictionary reload rejected the persisted internal `schema_definition`
name; the public contract uses `schema`. A synthetic regression reproduced this,
then preparation persistence was changed to `by_alias=True`. No core contract
or loader relaxation was introduced. A separate read-only audit also initially
selected system Python3.10, which lacks StrEnum; existing project Python3.12 was
used instead. Both diagnostic failures have append-only receipts under001.

Freeze002 changes serialization only. The audit compares all 18 original IDs,
task-bundle/source/private-evaluation/evaluator hashes, artifact hashes/sizes and
placements against001: **no semantic, selection or placement drift**. The order
hash is identical. No Planner/benchmark call was repeated, and no old file was
deleted or overwritten. Full regression: **601 passed**, Ruff passed, strict
Pyright0errors/0warnings, diff-check passed.

The task preparation audit verifies 18 strict execution/AgentTaskView reloads,
31 prepared artifact sizes/hashes, six lossless LongBench reconstructions and
absence of private/physical keys in sanitized task views, with zero findings.
This does **not** substitute for full runtime SDK recipient-context audit.

## Phase I order and remaining gate

Seed **20261005**; `task-freeze-002/phase1-schedule.json` records every ordered
cell ID/Planner/method/network. Each four-cell block balances Planner×network;
method assignments rotate. Exact count **168**. No formal cells are reserved
or launched by these preparation scripts.

Next: freeze provider prices/FX and per-recipient API accounting; integrate all
seven existing method variants with independently fixed Qwen Verifier; verify
actual recipient isolation, Worker surfaces and operational reservation/cleanup;
run the full execution-freeze checks. Only then admit the complete Phase I queue.
