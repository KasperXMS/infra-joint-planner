# Large-scale provider readiness audit v1

2026-10-05 Asia/Hong_Kong. **Prelaunch diagnostic, not a benchmark result.**
Formal cells 0; no Worker processes, stores, tc or benchmark payloads used.
The original SDK-native runtime and Blind Verifier source hashes are unchanged.

## Actual configured service

Existing Alibaba Model Studio Beijing workspace:
`https://llm-6tbxas81ayf65rd1.cn-beijing.maas.aliyuncs.com/compatible-mode/v1`.
Its authenticated `/models` returned both `deepseek-v4-pro` and `qwen3.8-max`.
No direct DeepSeek credential was available in the inspected remote assignment
file; the existing Alibaba credential supports the requested DeepSeek model.
No key/authorization headers were copied, printed or persisted in receipts.

The native Chat Completions SDK adapter used the exact requested identifier,
`enable_thinking=false`, default Manager temperature, client timeout180/retry0.
Qwen Verifier uses the existing instructions, required `submit_verification`
function tool, temperature0, one SDK turn, and unchanged schema. Each response
reported the same model identifier as its request. This is not an independently
verified underlying snapshot identity or a guarantee against later alias drift.

## Live non-benchmark checks

Synthetic Manager calls one `record_integer(7)` function tool. The tool calls
the existing Blind Verifier on a synthetic, identity-free empty-evidence context,
then returns its typed result. Manager continues after receiving that tool result.
This tests actual native function-call encoding, fixed-Qwen compatibility and
continuation, not benchmark reasoning or physical ActionGateway integration.
No formal Manager instructions, tool vocabulary or Verifier logic were altered.

| Diagnostic | Manager | Fixed Verifier | Native tool / continuation | Verifier schema | Toy final format | HTTP calls |
|---|---|---|---|---|---|---:|
| 001 | deepseek-v4-pro | qwen3.8-max | PASS | PASS; continue | FAIL; prose, not exactly7 | 3 |
| 002 | qwen3.8-max | qwen3.8-max | PASS | PASS; continue | PASS;7 | 3 |

The initial diagnostic gate incorrectly conflated provider compatibility with
toy-answer format compliance. Diagnostic001 therefore originally records failure.
That failure, request/response bodies and usage receipts are preserved unchanged.
A separate read-only adjudication validates the actual three-call chain and
tool-result continuation, while retaining its toy-format failure. **DeepSeek was
not called again.** Only the not-yet-started Qwen diagnostic ran under the corrected
generic admission predicate. This does not repair or replace a benchmark answer.
Both Verifier `continue` verdicts are valid for an empty-evidence context; neither
check proves final synthesis, a correct answer or formal baseline completion.

## Observed API usage

All six HTTP requests returned200 with explicit provider usage and cached_tokens0.
Zeros here come from raw provider fields, not SDK default substitution.
Times below are response wall time, not benchmark E2E.

| Diagnostic / recipient | Model | Input / output tokens | Cached input | Latency ms |
|---|---|---:|---:|---:|
|001 Manager turn1|deepseek-v4-pro|336 /44|0|2217.474|
|001 Verifier|qwen3.8-max|902 /103|0|1855.240|
|001 Manager continuation|deepseek-v4-pro|471 /63|0|3042.486|
|002 Manager turn1|qwen3.8-max|332 /25|0|922.775|
|002 Verifier|qwen3.8-max|902 /99|0|1738.883|
|002 Manager continuation|qwen3.8-max|448 /1|0|583.765|

Mandatory per-run API monetary accounting is **not yet integrated** into all
seven formal methods. Do not infer completed pricing/FX coverage from these raw
usage fields. Alibaba-hosted models must use Alibaba region/model pricing,
not DeepSeek-direct pricing. Freeze list prices and currency-conversion provenance
before formal execution; missing usage/price stays unknown, not0.

## Durable evidence and hashes

4090 root: `/home/super/xiaoming/large-scale-cost-guidance-v1/readiness`.
Original source-only diagnostic file remains alongside the separately named gate
patch file; no original source/attempt receipt was overwritten.

| Receipt | SHA-256 |
|---|---|
|provider-audit-001/attempt.json|9c02db1da85c97e8a075634ae8aeaeebc266fb62e4980d79718148e6f93f52ac|
|provider-audit-001/failure.json|7b14c3edb498368b773faf4e5668ab0b89e606074af88a8527f13ac7b8f7759e|
|provider-audit-001/compatibility-adjudication-001.json|f7bf7cf93571f1301208c910a15ce4580e82bb48099bba695570c58eff9024fc|
|provider-audit-002/attempt.json|46a32c77f4eab2b6cd05dd55703d47c0326760803200b24b7e2007fa523708ef|
|provider-audit-002/summary.json|b2b730f2c12b6fe76b67e5908a923c6f8002e133cb244c1ac2ba541f767f3fa5|

Base runtime SHA:
`b6112f2fda45add527e54a5924c9a5693a94f4439e37785846bafbca32a15985`.
Verifier source SHA:
`6c7813735ceec02136008d74da99ae3e773ec93b95b5a50d8a8dd1fd992699e8`.
Verifier instruction string SHA:
`181c185e9c735007b0eb941c87279be597985e50c4e9b8b63a83ced9852b0b71`.

Code: protocol `da2c61c`; deterministic schedule/gate tests `5ff53fe`;
initial diagnostic `0f75962`; gate-only correction `75bb46e`.
Full **591 tests passed**, Ruff passed, strict Pyright0errors/0warnings,
git diff --check passed. New tests cover exact168 cells, balanced P×H blocks,
all18-task/independent-E selection, deterministic schedule, complete Phase I
admission and420cap; synthetic context isolation/remote namespace and separation
of transport compatibility from answer-format compliance. They do not constitute
real formal-cell admission or a completed task freeze.

## Remaining prelaunch work

Remote inventory confirms2556 MultiHop questions and208 available LongBench
records. No task selected based on method outcomes. Natural source boundaries and
stratified selection still need private remote verification. The inspected original
video source directory has only three videos, one used in E history; this is not
enough to claim six independent held-out videos. Search/download additional sources
on4090 only, or explicitly document the permitted shared-video limitation if needed.

All18 task identities/hashes/representations/placement and frozen E holdouts,
pricing/FX/accounting, full native runtime/method integration, actual recipient
privacy admission, remote reservation/queue and complete execution freeze remain
pending. Do not start a partial168-cell block or claim Phase I has begun.
