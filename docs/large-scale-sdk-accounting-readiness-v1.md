# Native SDK accounting and frozen-task execution readiness

2026-10-05. **Formal cells remain zero. This is implementation/test readiness,
not a study result or execution admission.**

## Accounting boundary

`experiments/sdk_api_meter.py` adds pass-through accounting outside the frozen
logical runtime. An SDK construction facade changes only the constructed Agent's
model wrapper. All Agents remain real SDK Agents, with the same instructions,
tools, settings, Runner, hooks and method-specific input filters. An independently
constructed fixed Qwen Verifier has its own explicitly labelled model wrapper.

Each model attempt has a ContextVar scope. Each HTTP request has its own call ID,
recipient and intended/requested/response model identities. Parallel specialists
are not assigned by response order. Raw provider usage, request/response bodies,
timestamps, latency, status, request ID and cost receipt go to a private remote
sink; auth/header values and exception text are not stored by the collector.
Provider errors and transport failures retain unknown costs. A model attempt
failing before HTTP is recorded but does not invent an API call. Explicit cache
zeros remain zeros; unreported usage does not become SDK-default zero.

The meter never changes responses, Agent inputs, cost feedback or stopping. B0
and B1 do not receive monetary accounting. The price calculator and frozen
regional price/FX receipts remain unchanged. This does not add an online objective.

Official SDK documentation supports explicit per-Agent model/provider setup;
the installed SDK's Model interface was checked for this non-streaming wrapper.
No SDK upgrade, model replacement or prompt change was made.
[Models and providers](https://developers.openai.com/api/docs/guides/agents/models),
[Running agents](https://developers.openai.com/api/docs/guides/agents/running-agents).

## Tests and limits

Sixteen new synthetic tests cover actual ChatCompletionsModel parsing, response
identity, concurrent reversed-order HTTP completion, missing usage/model drift,
HTTP and transport errors, pre-HTTP failure, scope restoration and unchanged SDK
construction. Integration tests exercise **all seven existing native variants**,
actual SDK function tools/ActionGateway and independently metered fixed Qwen
Verifier. A real SDK manager invokes two concurrent specialists-as-tools and
continues after their results; all six synthetic API receipts have correct roles.

These are deterministic local tests with MockTransport and synthetic task data:
**zero new live API calls and zero benchmark runs**. They do not establish live
benchmark quality, actual deployment/tc availability or full formal admission.

Native runtime source remains
`b6112f2fda45add527e54a5924c9a5693a94f4439e37785846bafbca32a15985`;
Verifier source remains
`6c7813735ceec02136008d74da99ae3e773ec93b95b5a50d8a8dd1fd992699e8`.

## Common execution entry point

`scripts/large_scale_execution_v1.py` loads exactly the existing second task
freeze, not the historical loader that imposed Yes/No on MultiHop. It verifies
task semantics, strict contract reload, private evaluator identity/source hash,
prepared bytes/digests, namespace and original output contract. Eight synthetic
tests cover reload, task/gold/artifact/evaluator/path drift and store/visibility
settings. Original free-text MultiHop contracts are not rewritten.

The execution function builds one of the existing seven native variants, an
explicit fixed Qwen Verifier, and the unchanged ControlPlaneBenchmarkRunner.
Fresh Worker verification, surface validation, real materialization and physical
resolution remain in their existing implementations. Individual attempt execution
does **not** itself authorize queue admission, reservation or operational replacement.

The **authoritative remote reload passed** on 4090 using execution-loader revision
`cfb6656442f158ae529801cc06e7ae0b7e2e4cc6`: all 18 original tasks and 31 prepared
artifacts, six tasks per family. No model call, Worker or tc operation occurred.
Receipt: `readiness/frozen-native-reload-001.json`, SHA-256
`bba34a7ce150998aecb68b192a87c404978ef0c35caa97b135e8ce0b46061c7a`.
Process stdout/stderr are retained separately remotely. Source-only archive
SHA-256 is `1122ab3cde74d38542635b003a880d8d9d569742fec045615e0318d0dce0e9f7`.
No dataset or artifact body was transferred to the development PC.

All-seven-method SDK integration now uses the **common formal runtime factory**,
not a second hand-built test factory. The factory accepts an explicit physical
service for synthetic testing; formal execution uses the unchanged service
constructed by ControlPlaneBenchmarkRunner. This does not replace a scheduler.

Full validation: **640 pytest passed**, Ruff passed, strict Pyright zero errors,
`git diff --check` passed. The live provider diagnostic count remains six from
the earlier compatibility probes; no new live provider request was made here.

Remaining before formal launch: common queue/attempt ledger, full live recipient/
method/privacy admission, source/config execution freeze, Worker deployment and
tc lifecycle checks. Full Phase I/II and their required reports remain
outstanding; this is not a substitute for them.
